from __future__ import annotations

import json
import re
import socket
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from . import schemas
from .access import AccessProfile, ScopePolicy
from .audit import AuditLogger
from .config import AerisConfig, SettingsRecoveryError
from .followup import FollowUpContext
from .integrations.gemini import GeminiPlanner
from .integrations.gmail import GmailClient
from .integrations.google_calendar import GoogleCalendarClient
from .integrations.ollama import OllamaPlanner
from .integrations.screen_vision import ScreenVision
from .memory import MemoryStore
from .models import ActionRequest, ActionResult, AssistantTurn, PermissionLevel, PlannedResponse
from .permissions import ApprovalCallback, PermissionEngine
from .registry import ToolRegistry, ToolSpec
from .reminders import ReminderStore
from .router import LocalRouter
from .routines import RoutineStore, scope_fingerprint
from .state import CancelledError
from .tasks import TaskJournal, TaskPlan
from .timing import StageTimer
from .tools import (
    BrowserAdvancedTools,
    BrowserTools,
    CodingTools,
    DesktopTools,
    DownloadTools,
    FilesystemTools,
    PackageTools,
    SystemTools,
)
from .tools.organization import OrganizationTools
from .tools.reminders import ReminderTools


class AerisAssistant:
    def __init__(self, config: AerisConfig | None = None):
        self.config = config or AerisConfig.load()
        self._task_lock = threading.RLock()
        self._task_depth = 0
        # A failed close never releases ownership. Retired adapters remain here
        # until an explicit settings/cleanup retry confirms their release.
        self._retired_providers: list[Any] = []
        self.audit = AuditLogger(self.config.audit_log)
        self.memory = MemoryStore(self.config.memory_db)
        self.permissions = PermissionEngine()
        self.permissions.profile = AccessProfile(self.config.data_dir / 'access-profile.json')
        self.permissions.mode = self.config.automation_mode
        self.scope_policy = ScopePolicy(self.config.allowed_paths, self.config.data_dir / 'access-revocations.json')
        self.registry = ToolRegistry(self.permissions, self.audit, dry_run=self.config.dry_run)
        self.router = LocalRouter(self.config.wake_word)
        self.followup = FollowUpContext()
        self.task_journal = TaskJournal(self.config.data_dir / 'tasks.db')
        self.routine_store = RoutineStore(self.config.data_dir / 'routines.db')
        self._gemini = (
            GeminiPlanner(self.config.gemini_api_key, self.config.gemini_model)
            if self.config.ai_enabled and self.config.gemini_api_key
            else None
        )
        self._ollama = OllamaPlanner() if self.config.ai_enabled else None
        self.reminder_store = ReminderStore(self.config.data_dir / "reminders.db", self.config.timezone_name,
            enabled=lambda: not self.permissions.stopped and not self.registry.dry_run)
        self._register_tools()

    def _register_tools(self) -> None:
        desktop = DesktopTools(self.config.app_catalog_file, self.config.data_dir / "screenshots")
        self._desktop = desktop
        browser = BrowserTools(self.config.allowed_domains)
        browser_adv = BrowserAdvancedTools(self.config.allowed_domains)
        self._browser = browser_adv
        files = FilesystemTools(self.config.allowed_paths)
        self._files = files
        files.guard.policy = self.scope_policy
        self._organization = OrganizationTools(files, self.config.data_dir / 'file-batches.db')
        downloads = DownloadTools(
            self.config.download_dir,
            self.config.allowed_domains,
            self.config.max_download_mb * 1024 * 1024,
        )
        packages = PackageTools(
            self.config.allowed_paths,
            self.config.package_catalog_file,
            self.config.require_signed_installers,
        )
        packages.guard.policy = self.scope_policy
        system = SystemTools()
        ai_key = self.config.gemini_api_key if self.config.ai_enabled else None
        vision = ScreenVision(ai_key, self.config.gemini_model)
        coding = CodingTools(
            self.config.allowed_paths,
            self.config.coding_workspace,
            ai_key,
            self.config.gemini_model,
        )
        coding.guard.policy = self.scope_policy
        gmail = GmailClient(self.config.gmail_credentials_file)
        calendar = GoogleCalendarClient(self.config.gmail_credentials_file)
        reminder_tools = ReminderTools(self.reminder_store)

        def status(_: dict[str, Any]) -> ActionResult:
            runtime = getattr(self, "_runtime_owner", self)
            data = runtime.config.public_summary() | {
                "dry_run": runtime.registry.dry_run,
                "stopped": runtime.permissions.stopped,
                "registered_tools": len(runtime.registry.names()),
                "provider_cleanup_pending": len(runtime._retired_providers),
                "settings_recovery_required": bool(runtime.config.recovery_message),
            }
            return ActionResult(True, "Aeris status loaded.", data=data)

        def stop(_: dict[str, Any]) -> ActionResult:
            self.permissions.stop()
            return ActionResult(True, "Aeris kill switch activated. Only status and resume are available.")

        def resume(_: dict[str, Any]) -> ActionResult:
            self.permissions.resume()
            return ActionResult(True, "Aeris resumed.")

        specs = [
            ToolSpec('files.organize', 'Review and organize at most 100 local documents with hash-checked Undo.',
                     PermissionLevel.CONFIRM, self._organization.organize, model=schemas.OrganizeFiles, prepare=self._organization.prepare),
            ToolSpec('files.undo_organization', 'Restore a reviewed organization batch without overwriting newer files.',
                     PermissionLevel.CONFIRM, self._organization.undo, model=schemas.UndoOrganization, prepare=self._organization.prepare_undo),
            ToolSpec(
                "system.status", "Show safe configuration and runtime status.", PermissionLevel.AUTO, status
            ),
            ToolSpec("system.stop", "Activate the global kill switch.", PermissionLevel.AUTO, stop),
            ToolSpec("system.resume", "Resume after the kill switch.", PermissionLevel.AUTO, resume),
            ToolSpec(
                "system.health",
                "Show CPU, memory, disk, battery, and Windows information.",
                PermissionLevel.AUTO,
                system.health,
            ),
            ToolSpec("system.battery", "Show battery and charging status.", PermissionLevel.AUTO, system.battery),
            ToolSpec("system.network_test", "One approved ICMP probe to Microsoft; not a general internet-health guarantee.",
                     PermissionLevel.CONFIRM, system.network_test, model=schemas.NetworkTest),
            ToolSpec("system.lock", "Lock the Windows session.", PermissionLevel.CONFIRM, system.lock),
            ToolSpec("system.sleep", "Put the computer to sleep.", PermissionLevel.CONFIRM, system.sleep),
            ToolSpec(
                "system.shutdown", "Schedule Windows shutdown in 10 seconds.", PermissionLevel.CONFIRM, system.shutdown
            ),
            ToolSpec(
                "system.restart", "Schedule Windows restart in 10 seconds.", PermissionLevel.CONFIRM, system.restart
            ),
            ToolSpec(
                "system.cancel_shutdown",
                "Cancel a pending shutdown or restart.",
                PermissionLevel.AUTO,
                system.cancel_shutdown,
            ),
            ToolSpec(
                "desktop.open_app",
                "Open a configured Windows application.",
                PermissionLevel.AUTO,
                desktop.open_app,
                model=schemas.OpenApp,
            ),
            ToolSpec(
                "email.send_email",
                "Draft and send a new email using Gmail.",
                PermissionLevel.CONFIRM,
                gmail.send_email,
                model=schemas.SendEmail,
            ),
            ToolSpec(
                "calendar.list_events",
                "List upcoming events from Google Calendar.",
                PermissionLevel.SESSION,
                calendar.list_events,
                model=schemas.ListCalendarEvents,
            ),
            ToolSpec(
                "desktop.close_app",
                "Preview and request one selected app window to close normally, preserving its own unsaved-work prompts.",
                PermissionLevel.CONFIRM,
                desktop.close_app,
                model=schemas.CloseApp,
                prepare=desktop.prepare_close_app,
            ),
            ToolSpec(
                "desktop.set_volume",
                "Set master volume from 0 to 100.",
                PermissionLevel.AUTO,
                desktop.set_volume,
                model=schemas.SetVolume,
            ),
            ToolSpec(
                "desktop.change_volume",
                "Increase or decrease master volume.",
                PermissionLevel.AUTO,
                desktop.change_volume,
                model=schemas.ChangeVolume,
            ),
            ToolSpec(
                "desktop.set_brightness",
                "Set display brightness from 0 to 100.",
                PermissionLevel.AUTO,
                desktop.set_brightness,
                model=schemas.SetBrightness,
            ),
            ToolSpec(
                "desktop.change_brightness",
                "Increase or decrease display brightness.",
                PermissionLevel.AUTO,
                desktop.change_brightness,
                model=schemas.ChangeBrightness,
            ),
            ToolSpec(
                "desktop.media_control",
                "Control media playback or mute.",
                PermissionLevel.AUTO,
                desktop.media_control,
                model=schemas.MediaControl,
            ),
            ToolSpec(
                "desktop.type_text",
                "Preview an exact application window and dispatch Unicode text; insertion is not read back.",
                PermissionLevel.CONFIRM,
                desktop.type_text,
                model=schemas.TypeText,
                prepare=desktop.prepare_type_text,
            ),
            ToolSpec(
                "desktop.screenshot",
                "Capture all screens to a local image.",
                PermissionLevel.SESSION,
                desktop.screenshot,
            ),
            ToolSpec(
                "desktop.clipboard_copy",
                "Copy text to the Windows clipboard.",
                PermissionLevel.AUTO,
                desktop.copy_clipboard,
                model=schemas.ClipboardCopy,
            ),
            ToolSpec(
                "desktop.clipboard_read",
                "Read text from the Windows clipboard.",
                PermissionLevel.SESSION,
                desktop.read_clipboard,
            ),
            ToolSpec(
                "desktop.window_action",
                "Switch, maximize, minimize, or show desktop using an approved shortcut.",
                PermissionLevel.AUTO,
                desktop.window_action,
                model=schemas.WindowAction,
                prepare=desktop.prepare_window_action,
            ),
            ToolSpec(
                "desktop.close_current_window",
                "Close the active window; unsaved work may be lost.",
                PermissionLevel.CONFIRM,
                desktop.close_current_window,
                model=schemas.CloseCurrentWindow,
                prepare=desktop.prepare_close_current_window,
            ),
            ToolSpec(
                "vision.inspect_screen",
                "Capture the visible screens once, analyze them with Gemini, and retain no screenshot.",
                PermissionLevel.SESSION,
                vision.inspect,
                model=schemas.InspectScreen,
            ),
            ToolSpec(
                "vision.monitor_screen",
                "Start a background loop to continuously monitor the screen for a specific event.",
                PermissionLevel.CONFIRM,
                vision.monitor_screen,
                model=schemas.MonitorScreen,
            ),
            ToolSpec(
                "coding.create_project",
                "Generate a new validated coding project inside the dedicated workspace without running it.",
                PermissionLevel.CONFIRM,
                coding.create_project,
                model=schemas.CreateProject,
            ),
            ToolSpec(
                "coding.search_workspace",
                "Search the coding workspace for text across files.",
                PermissionLevel.AUTO,
                coding.search_workspace,
                model=schemas.SearchWorkspace,
            ),
            ToolSpec(
                "coding.apply_diff",
                "Modify an existing file in the coding workspace.",
                PermissionLevel.CONFIRM,
                coding.apply_diff,
                model=schemas.ApplyDiff,
            ),
            ToolSpec(
                "browser.open_url",
                "Open an approved HTTP or HTTPS URL.",
                PermissionLevel.AUTO,
                browser.open_url,
                model=schemas.OpenUrl,
            ),
            ToolSpec(
                "browser.search_web",
                "Search the web in the default browser.",
                PermissionLevel.AUTO,
                browser.search_web,
                model=schemas.SearchWeb,
            ),
            ToolSpec(
                "browser.search_youtube",
                "Search YouTube in the default browser.",
                PermissionLevel.AUTO,
                browser.search_youtube,
                model=schemas.SearchWeb,
            ),
            ToolSpec(
                "browser.advanced_navigate",
                "Navigate to a URL using the interactive playwright browser.",
                PermissionLevel.AUTO,
                browser_adv.navigate,
                model=schemas.OpenUrl,
            ),
            ToolSpec(
                "browser.advanced_extract",
                "Extract text from the interactive playwright browser.",
                PermissionLevel.SESSION,
                browser_adv.extract,
            ),
            ToolSpec(
                "browser.advanced_click",
                "Click an element in the interactive playwright browser by CSS or text selector.",
                PermissionLevel.CONFIRM,
                browser_adv.click,
                model=schemas.BrowserClick,
            ),
            ToolSpec(
                "browser.advanced_fill",
                "Fill a text field in the interactive playwright browser.",
                PermissionLevel.CONFIRM,
                browser_adv.fill,
                model=schemas.BrowserFill,
            ),
            ToolSpec(
                "downloads.download",
                "Download one public HTTP/HTTPS file into the configured Downloads folder without executing it.",
                PermissionLevel.CONFIRM,
                downloads.download,
                model=schemas.Download,
            ),
            ToolSpec(
                "downloads.open_folder",
                "Open the configured Downloads folder.",
                PermissionLevel.AUTO,
                downloads.open_downloads,
            ),
            ToolSpec(
                "downloads.clear_partial",
                "Remove incomplete .part files created by Aeris.",
                PermissionLevel.CONFIRM,
                downloads.clear_partial_downloads,
            ),
            ToolSpec(
                "packages.search",
                "Search the trusted Windows Package Manager catalog.",
                PermissionLevel.AUTO,
                packages.search,
                model=schemas.PackageSearch,
            ),
            ToolSpec(
                "packages.install",
                "Install an exact app from the official winget source.",
                PermissionLevel.CONFIRM,
                packages.install,
                model=schemas.PackageAction,
            ),
            ToolSpec(
                "packages.update",
                "Update one exact app through winget.",
                PermissionLevel.CONFIRM,
                packages.update,
                model=schemas.PackageAction,
            ),
            ToolSpec(
                "packages.uninstall",
                "Uninstall one exact app through winget.",
                PermissionLevel.CONFIRM,
                packages.uninstall,
                model=schemas.PackageAction,
            ),
            ToolSpec(
                "packages.list_installed",
                "List installed applications through winget.",
                PermissionLevel.SESSION,
                packages.list_installed,
            ),
            ToolSpec(
                "packages.list_updates",
                "List available application updates through winget.",
                PermissionLevel.AUTO,
                packages.list_updates,
            ),
            ToolSpec(
                "packages.install_file",
                "Launch a downloaded Windows installer only after Defender and signature checks.",
                PermissionLevel.CONFIRM,
                packages.install_file,
                model=schemas.InstallFile,
            ),
            ToolSpec(
                "files.list", "List items inside an allowed folder.", PermissionLevel.AUTO, files.list_files, model=schemas.OptionalFilePath
            ),
            ToolSpec(
                "files.find",
                "Find files only inside allowed folders.",
                PermissionLevel.AUTO,
                files.find_files,
                model=schemas.FindFiles,
            ),
            ToolSpec(
                "files.read",
                "Read a small approved text file.",
                PermissionLevel.SESSION,
                files.read_text,
                model=schemas.FilePath,
            ),
            ToolSpec(
                "files.open",
                "Open a non-executable file inside allowed folders.",
                PermissionLevel.SESSION,
                files.open_file,
                model=schemas.FilePath,
            ),
            ToolSpec(
                "files.delete",
                "Move a file to the Recycle Bin.",
                PermissionLevel.CONFIRM,
                files.delete_file,
                model=schemas.FilePath,
            ),
            ToolSpec(
                "files.open_folder",
                "Open an allowed folder in File Explorer.",
                PermissionLevel.AUTO,
                files.open_folder,
                model=schemas.OptionalFilePath,
            ),
            ToolSpec(
                "files.create_folder",
                "Create a folder inside allowed paths.",
                PermissionLevel.CONFIRM,
                files.create_folder,
                model=schemas.FilePath,
            ),
            ToolSpec(
                "files.write_text",
                "Create a new text file without overwriting existing content.",
                PermissionLevel.CONFIRM,
                files.write_text,
                model=schemas.WriteText,
            ),
            ToolSpec(
                "files.copy",
                "Copy a file within allowed paths without overwriting.",
                PermissionLevel.CONFIRM,
                files.copy_file,
                model=schemas.CopyMove,
            ),
            ToolSpec(
                "files.move",
                "Move or rename a file within allowed paths without overwriting.",
                PermissionLevel.CONFIRM,
                files.move_file,
                model=schemas.CopyMove,
            ),
            ToolSpec(
                "email.list_recent", "List recent Gmail messages.", PermissionLevel.SESSION, gmail.list_recent, model=schemas.ListRecentEmails
            ),
            ToolSpec(
                "email.read_latest",
                "Read metadata and snippet for the latest Gmail message.",
                PermissionLevel.SESSION,
                gmail.read_latest,
            ),
            ToolSpec(
                "email.send",
                "Send a Gmail message after exact preview confirmation.",
                PermissionLevel.CONFIRM,
                gmail.send_email,
                model=schemas.SendEmail,
            ),
            ToolSpec(
                "reminder.set",
                "Set a durable reminder with timezone-aware schedule.",
                PermissionLevel.AUTO,
                reminder_tools.set_reminder,
                model=schemas.SetReminder,
            ),
            ToolSpec(
                "reminder.list",
                "List pending reminders.",
                PermissionLevel.SESSION,
                reminder_tools.list_reminders,
            ),
            ToolSpec(
                "reminder.snooze",
                "Snooze a pending reminder by ID for a specified number of minutes.",
                PermissionLevel.AUTO,
                reminder_tools.snooze_reminder,
                model=schemas.SnoozeReminder,
            ),
            ToolSpec(
                "reminder.cancel",
                "Cancel a reminder by ID.",
                PermissionLevel.AUTO,
                reminder_tools.cancel_reminder,
                model=schemas.CancelReminder,
            ),
        ]
        for spec in specs:
            self.registry.register(spec)

    def apply_settings(self, config: AerisConfig) -> None:
        """Swap adapters only between tasks; callers must stop voice separately."""
        config.validate()
        if not self._task_lock.acquire(blocking=False):
            raise RuntimeError("Aeris is busy. Stop or finish the task before applying settings.")
        staged = None
        published = False
        try:
            if self._task_depth:
                raise RuntimeError("Aeris is busy. Stop or finish the task before applying settings.")
            if not self._retry_retired_providers():
                raise RuntimeError("Provider cleanup is pending; retry cleanup before applying more settings.")
            staged = object.__new__(AerisAssistant)
            staged.config = config
            staged._runtime_owner = self
            staged.permissions = self.permissions
            staged.scope_policy = self.scope_policy
            staged.audit = self.audit
            staged._retired_providers = self._retired_providers
            staged.registry = ToolRegistry(self.permissions, self.audit, dry_run=config.dry_run)
            staged._gemini = GeminiPlanner(config.gemini_api_key, config.gemini_model) if config.ai_enabled and config.gemini_api_key else None
            staged._ollama = OllamaPlanner() if config.ai_enabled else None
            if config.data_dir != self.config.data_dir:
                staged.reminder_store = ReminderStore(config.data_dir / "reminders.db", config.timezone_name)
            else:
                staged.reminder_store = self.reminder_store
            staged._register_tools()
            if not self._browser.close():
                raise RuntimeError("Browser cleanup is pending; settings were not applied.")
            try:
                config.save()
            except SettingsRecoveryError as exc:
                self._enter_settings_recovery(str(exc))
                raise
            # A successful explicit save resolves an earlier recovery warning.
            config = config.with_overrides(recovery_message="")
            staged.config = config
            previous_providers = (self._gemini, self._ollama)
            previous_reminders = self.reminder_store
            self.config = config
            self.permissions.mode = config.automation_mode
            self.scope_policy.replace(config.allowed_paths)
            self.router = LocalRouter(config.wake_word)
            self.permissions.clear_session()
            self.followup.clear()
            self.registry = staged.registry
            self._browser = staged._browser
            self._desktop = staged._desktop
            self._files = staged._files
            self._organization = staged._organization
            self._gemini = staged._gemini
            self._ollama = staged._ollama
            self.reminder_store = staged.reminder_store
            self.reminder_store.timezone_name = config.timezone_name
            from .reminders import reminder_timezone
            self.reminder_store.timezone = reminder_timezone(config.timezone_name)
            self.reminder_store.enabled = lambda: not self.permissions.stopped and not self.registry.dry_run
            published = True
            if previous_reminders is not self.reminder_store:
                previous_reminders.stop()
            for provider in previous_providers:
                self._retire_provider(provider)
        finally:
            try:
                if staged is not None and not published:
                    for name in ("_gemini", "_ollama"):
                        self._retire_provider(getattr(staged, name, None))
                    if hasattr(staged, "_browser"):
                        staged._browser.close()
                    if getattr(staged, "reminder_store", self.reminder_store) is not self.reminder_store:
                        staged.reminder_store.stop()
            finally:
                self._task_lock.release()

    def _enter_settings_recovery(self, message: str) -> None:
        self.config = self.config.with_overrides(
            dry_run=True, ai_enabled=False, hands_free=False, gemini_api_key=None, recovery_message=message)
        self.registry.dry_run = True
        self.permissions.clear_session()
        self.followup.clear()
        for name in ("_gemini", "_ollama"):
            provider = getattr(self, name, None)
            setattr(self, name, None)
            self._retire_provider(provider)
        self.audit.write("settings_recovery_required", error="credential_settings_unconfirmed")

    def _close_provider(self, provider) -> bool:
        try:
            close = getattr(provider, "close", None)
            if close and close() is False:
                self.audit.write("provider_cleanup_failed", error="cleanup_incomplete")
                return False
            return True
        except Exception as exc:
            self.audit.write("provider_cleanup_failed", error=type(exc).__name__)
            return False

    def _retire_provider(self, provider) -> None:
        if provider is None:
            return
        if not any(item is provider for item in self._retired_providers):
            self._retired_providers.append(provider)
        if self._close_provider(provider):
            self._retired_providers[:] = [item for item in self._retired_providers if item is not provider]

    def _retry_retired_providers(self) -> bool:
        for provider in tuple(self._retired_providers):
            if self._close_provider(provider):
                self._retired_providers[:] = [item for item in self._retired_providers if item is not provider]
        return not self._retired_providers

    def close(self) -> bool:
        # Cleanup must not close an SDK client while the task holding it is in
        # flight. The existing cleanup worker presents an explicit Retry path.
        if not self._task_lock.acquire(blocking=False):
            return False
        try:
            if self._task_depth:
                return False
            reminders_cleaned = True
            if hasattr(self, "reminder_store") and self.reminder_store:
                reminders_cleaned = self.reminder_store.stop()
            provider_cleaned = self._retry_retired_providers()
            for name in ("_gemini", "_ollama"):
                provider = getattr(self, name, None)
                if self._close_provider(provider):
                    setattr(self, name, None)
                else:
                    provider_cleaned = False
            browser_cleaned = self._browser.close()
            return browser_cleaned and provider_cleaned and reminders_cleaned
        finally:
            self._task_lock.release()

    def handle(self, text: str, approval_callback=None, token=None) -> AssistantTurn:
        from .state import CancellationToken
        token = token or CancellationToken()
        with self._task_lock:
            self._task_depth += 1
            self.last_timing = StageTimer(command_id=getattr(token, "command_id", uuid.uuid4().hex))
            self.last_timing.start("task_total")
            try:
                return self._handle(text, approval_callback, token)
            finally:
                self.last_timing.end("task_total")
                self._task_depth -= 1

    def _handle(
        self,
        text: str,
        approval_callback: ApprovalCallback | None = None,
        token: Any = None,
    ) -> AssistantTurn:
        user_text = text.strip()
        private_request = user_text.lower().startswith("/private ")
        if private_request:
            user_text = user_text[len("/private "):].strip()

        if self.permissions.stopped:
            stopped_plan = self.router.route(user_text)
            if not stopped_plan or not stopped_plan.actions or any(action.tool not in {"system.status", "system.resume"} for action in stopped_plan.actions):
                result = ActionResult(False, "Global Stop is active. Explicitly resume Aeris first.", error="kill_switch")
                return AssistantTurn(user_text, result.message, [result], status="failed")
        
        if token:
            token.raise_if_cancelled()

        if user_text.lower().strip(" .!") in {"daily brief", "my daily brief", "show daily brief"}:
            self.followup.clear()
            return self._daily_brief(user_text, approval_callback, token)
            
        self.last_timing.start("routing")
        routine_name = None
        addressed = self.router.wake_word
        from .activation import strip_address
        routine_command = strip_address(user_text, (addressed,)).strip()
        plan = None
        if routine_command.lower().startswith('run routine '):
            routine_name = routine_command[len('run routine '):].strip()
            try:
                routine = self.routine_store.get(routine_name, scope_fingerprint(self.config))
                plan = PlannedResponse(steps=routine.steps)
            except ValueError as exc:
                return AssistantTurn(user_text, str(exc), status='failed')
        if plan is None:
            plan = self.followup.resolve(user_text, self.registry.dry_run)
        if plan is None:
            plan = self.router.route(user_text)
        self.last_timing.end("routing")
        if plan is None and self._gemini is not None:
            share_request = ActionRequest("privacy.share_request", {"text": user_text}, source_text=user_text)
            if not approval_callback or not approval_callback(
                share_request, PermissionLevel.CONFIRM,
                "Share this request with the configured cloud planner?\n" + user_text[:2000] +
                "\nOnly explicitly SHAREABLE history is included; no files or screenshots are attached.",
            ):
                return AssistantTurn(user_text, "Cloud sharing was not approved. Local commands remain available.", status="failed")
            if token:
                token.raise_if_cancelled()
            try:
                plan = self._gemini.plan(user_text, self.registry.definitions(), self.memory.provider_context(8), token)
            except CancelledError:
                return AssistantTurn(user_text, "Command cancelled before any tool ran.", status="cancelled")
            except Exception as exc:
                self.audit.write("gemini_planner_failed", error=type(exc).__name__)
                if self._is_network_error(exc) and self._ollama is not None:
                    # Fallback to offline planner
                    try:
                        plan = self._ollama.plan(user_text, self.registry.definitions(), self.memory.recent(8), token)
                    except CancelledError:
                        return AssistantTurn(user_text, "Command cancelled before any tool ran.", status="cancelled")
                    except Exception as ollama_exc:
                        self.audit.write("ollama_planner_failed", error=type(ollama_exc).__name__)
                        plan = PlannedResponse(reply=self._planner_failure_message(exc), error="planner_failed")
                else:
                    plan = PlannedResponse(reply=self._planner_failure_message(exc), error="planner_failed")
        elif plan is None and self._ollama is not None:
            try:
                plan = self._ollama.plan(user_text, self.registry.definitions(), self.memory.recent(8), token)
            except CancelledError:
                return AssistantTurn(user_text, "Command cancelled before any tool ran.", status="cancelled")
            except Exception as exc:
                self.audit.write("ollama_planner_failed", error=type(exc).__name__)
                plan = PlannedResponse(reply="Ollama offline planner failed. Say 'help' for local commands.", error="planner_failed")
        elif plan is None:
            plan = PlannedResponse(
                reply="I do not know that command yet. Say 'help', or configure GEMINI_API_KEY for flexible requests."
            )

        if token and token.is_cancelled:
            return AssistantTurn(user_text, "Command cancelled before any tool ran; late planner output discarded.", status="cancelled")

        if plan.steps:
            plan.actions = [ActionRequest(step.tool, step.arguments, user_text) for step in plan.steps]
        task_plan = None
        if plan.actions:
            try:
                task_plan = TaskPlan(steps=plan.steps) if plan.steps else TaskPlan.from_actions(plan.actions)
                task_plan.preflight(self.registry)
            except (ValueError, TypeError, KeyError):
                return AssistantTurn(user_text, 'The complete task could not be validated. No steps ran.',
                    [ActionResult(False, 'Invalid task plan or arguments.', error='invalid_arguments')], status='failed')

        sensitive = private_request or any(
            action.tool.startswith("email.")
            or action.tool.startswith("reminder.")
            or action.tool.startswith("desktop.clipboard")
            or action.tool.startswith("vision.")
            or action.tool.startswith("coding.")
            or action.tool == "downloads.download"
            or action.tool in {"files.read", "files.write_text", "desktop.type_text"}
            for action in plan.actions
        )
        self.memory.add("user", user_text, classification="SENSITIVE" if sensitive else "LOCAL_ONLY")

        results: list[ActionResult] = []
        lines = [plan.reply] if plan.reply else []
        task_id, progress = self.task_journal.begin(task_plan) if task_plan else (None, [])
        deadline = time.monotonic() + task_plan.timeout_seconds if task_plan else None
        if token and deadline:
            token.deadline = min(token.deadline, deadline) if token.deadline else deadline
        resolved_results = {}
        resolved_actions = []
        journal_failed = False
        def report(status='running'):
            nonlocal journal_failed
            if not task_id:
                return
            try:
                self.task_journal.update(task_id, progress, status)
            except Exception:
                journal_failed = True
            callback = getattr(token, 'progress_callback', None)
            if callback:
                try:
                    callback({'task_id': task_id, 'status': status, 'steps': [dict(item) for item in progress]})
                except Exception:
                    pass  # A presentation failure must not discard committed receipts.
        report()
        for index, step in enumerate(task_plan.steps if task_plan else []):
            try:
                action = task_plan.resolve(step, resolved_results, user_text)
            except ValueError:
                results.append(ActionResult(False, 'A required observed output is unavailable. Remaining steps were blocked.', error='missing_output'))
                progress[index]['status'] = 'blocked'
                lines.append('[FAILED] ' + results[-1].message)
                break
            resolved_actions.append(action)
            progress[index]['status'] = 'executing'
            report()
            self.last_timing.start("permission_and_tool_" + action.request_id)
            try:
                if token:
                    token.raise_if_cancelled()
                if time.monotonic() >= deadline:
                    raise CancelledError('Task deadline exceeded')
                with self.permissions.reviewed_workflow(routine_name is not None):
                    result = self.registry.execute(action, approval_callback, token=token)
            except CancelledError:
                result = ActionResult(False, "Remaining work cancelled; prior effects are retained below.", error="cancelled")
            finally:
                self.last_timing.end("permission_and_tool_" + action.request_id)
            results.append(result)
            resolved_results[step.id] = result
            progress[index]['status'] = ('simulated' if result.dry_run else 'completed') if result.success else ('cancelled' if result.error == 'cancelled' else 'failed')
            progress[index]['published'] = bool(result.data.get('published'))
            progress[index]['uncertain'] = bool(result.data.get('uncertain') or result.data.get('outcome_uncertain'))
            progress[index]['error'] = result.error if result.error is None or re.fullmatch(r'[a-z_]{1,60}', result.error) else 'adapter_error'
            receipt_keys = {'path', 'source', 'destination', 'batch_id', 'sha256', 'source_removed',
                            'verified', 'cleanup_complete', 'characters_dispatched', 'input_events_inserted'}
            progress[index]['receipt'] = {key: value for key, value in result.data.items() if key in receipt_keys
                and (type(value) in {bool, int} or isinstance(value, str) and len(value) <= 8192)}
            report()
            if journal_failed and index + 1 < len(task_plan.steps):
                lines.append('Further steps were blocked because durable task history is unavailable. Retained results follow.')
            prefix = "[OK]" if result.success else "[FAILED]"
            lines.append(f"{prefix} {result.message}")
            details = self._visible_details(action, result)
            if details:
                lines.append(details)
            if not result.success or journal_failed or (token and token.is_cancelled):
                lines.append("Remaining steps were not run because a required step failed.")
                break

        reply = "\n".join(line for line in lines if line).strip() or "Done."
        if token and token.is_cancelled:
            self.followup.clear()
            reply += "\nCommand cancelled. Effects already reported above are retained; cancellation does not undo them."
        else:
            self.followup.observe(resolved_actions, results)
        self.memory.add("assistant", reply[:10_000], classification="SENSITIVE" if sensitive else "LOCAL_ONLY")
        status = "failed" if plan.error or any(not result.success for result in results) or journal_failed and any(item['status'] == 'pending' for item in progress) else "completed"
        if token and token.is_cancelled:
            status = "cancelled"
        elif results and all(result.dry_run for result in results):
            status = "simulated"
        for item in progress:
            if item['status'] == 'pending':
                item['status'] = 'blocked'
        report(status)
        if routine_name:
            try:
                self.routine_store.result(routine_name, status)
            except Exception:
                journal_failed = True
        if journal_failed:
            reply += '\nTask history could not be fully saved. Preserve this result and review interrupted work before retrying.'
        return AssistantTurn(input_text=user_text, reply=reply, results=results, status=status, task_id=task_id)

    def _daily_brief(self, text, approval_callback, token) -> AssistantTurn:
        """Deterministic, local rendering of fetched records; never a cloud summary."""
        lines = ["Daily Brief — retrieved " + datetime.now(timezone.utc).isoformat(timespec="seconds")]
        results = []
        for tool, heading in (("calendar.list_events", "Upcoming calendar events"),
                              ("email.list_recent", "Recent email metadata")):
            if token:
                token.raise_if_cancelled()
            action = ActionRequest(tool, {"count": 5}, source_text=text)
            result = self.registry.execute(action, approval_callback, token=token)
            results.append(result)
            lines.append(heading + ": " + result.message)
            if result.success and not result.dry_run:
                lines.append(self._visible_details(action, result) or "No records returned.")
            if self.permissions.stopped or (token and token.is_cancelled):
                break

        if not (self.permissions.stopped or (token and token.is_cancelled)):
            rem_action = ActionRequest("reminder.list", {}, source_text=text)
            rem_result = self.registry.execute(rem_action, approval_callback, token=token)
            results.append(rem_result)
            lines.append("Pending reminders: " + rem_result.message)

        lines.append(
            "Sources: authorized primary Calendar / connected Gmail / local durable ReminderStore. "
            "No cloud summary or sending."
        )
        return AssistantTurn(text, "\n".join(lines), results)

    @staticmethod
    def _is_network_error(exc: Exception) -> bool:
        message = str(exc).lower()
        network_markers = (
            "getaddrinfo",
            "name resolution",
            "network is unreachable",
            "connection error",
            "connection refused",
            "timed out",
            "unavailable",
        )
        return isinstance(exc, (ConnectionError, TimeoutError, socket.gaierror)) or any(
            marker in message for marker in network_markers
        )

    @staticmethod
    def _planner_failure_message(exc: Exception) -> str:
        if AerisAssistant._is_network_error(exc):
            return (
                "Internet is unavailable, so Gemini was skipped. Offline computer commands still work. "
                "Say 'offline help' to hear examples."
            )
        return "Gemini could not plan that request safely. Try a direct command or say 'offline help'."

    @staticmethod
    def _visible_details(action: ActionRequest, result: ActionResult) -> str:
        if result.dry_run:
            return ""
        data = result.data
        if action.tool == "desktop.type_text" and data.get("input_events_inserted"):
            return (f"Input events inserted: {data['input_events_inserted']}; complete characters dispatched: "
                    f"{data.get('characters_dispatched', 0)} to window {data.get('window_id')}. "
                    "Text was not read back. Inspect the selected application before retrying.")
        if action.tool in {"files.copy", "files.move"} and (data.get("published") or data.get("created_directories")):
            lines = ["Destination published: " + str(data.get("destination"))] if data.get("published") else []
            lines.append("Source: " + str(data.get("source")) +
                         (" (removed by the owned move)" if data.get("source_removed") else
                          " (removal unverified)" if data.get("outcome_uncertain") else " (retained)"))
            if data.get("created_directories"):
                lines.append("Created folders: " + ", ".join(data["created_directories"]))
            if data.get("outcome_uncertain") or data.get("staging_cleanup_incomplete"):
                lines.append("Cleanup or source removal is uncertain; inspect both paths before retrying.")
            return "\n".join(lines)
        if action.tool.startswith("reminder.") and data.get("reminder_id"):
            return "Reminder ID: " + str(data["reminder_id"])
        if action.tool.startswith("packages.") and data.get("output"):
            return str(data["output"])
        if data.get("published") and (not result.success or action.tool != "coding.create_project"):
            return "Retained artifact: " + str(data.get("path") or data.get("project_path") or data.get("destination") or "See action result")
        if data.get("uncertain") or data.get("cleanup_complete") is False:
            return "External effects or cleanup are uncertain. Inspect the target before retrying."
        if not result.success:
            return ""
        if action.tool == "browser.advanced_extract":
            return str(data.get("content", ""))[:5_000] or "No page text was returned."
        if action.tool == "coding.search_workspace":
            return "\n".join(str(item) for item in data.get("matches", [])) or "No matches found."
        if action.tool == "calendar.list_events":
            return "\n".join(
                f"- {item.get('summary', '(Untitled)')} | {item.get('start', '')} | {item.get('end', '')}"
                + (" (all day; end date is exclusive)" if item.get("all_day") else "")
                for item in data.get("events", [])
            ) or "No upcoming events found."
        if action.tool == "files.find":
            return "\n".join(f"- {item}" for item in data.get("matches", []))
        if action.tool == "files.list":
            return "\n".join(f"- {item['name']} ({item['type']})" for item in data.get("items", []))
        if action.tool == "files.read":
            return str(data.get("content", ""))[:4_000]
        if action.tool == "email.list_recent":
            return "\n".join(
                f"- {item['from']} | {item['subject']} | {item['date']}" for item in data.get("emails", [])
            )
        if action.tool == "email.read_latest" and data.get("email"):
            item = data["email"]
            return f"From: {item['from']}\nSubject: {item['subject']}\n{item['snippet']}"
        if action.tool == "system.status":
            return json.dumps(data, indent=2, ensure_ascii=False)
        if action.tool == "system.health":
            return json.dumps(data, indent=2, ensure_ascii=False)
        if action.tool == "desktop.clipboard_read":
            return str(data.get("text", ""))
        if action.tool == "vision.inspect_screen":
            return str(data.get("analysis", ""))
        if action.tool == "coding.create_project":
            lines = [f"Project: {data.get('project_path', '')}"]
            if data.get("summary"):
                lines.append(str(data["summary"]))
            if data.get("files"):
                lines.append("Files: " + ", ".join(str(item) for item in data["files"]))
            instructions = data.get("run_instructions", [])
            if instructions:
                lines.append("Run manually:")
                lines.extend(f"- {item}" for item in instructions)
            return "\n".join(lines)
        return ""
