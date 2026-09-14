from __future__ import annotations

import json
import socket
from typing import Any

from .audit import AuditLogger
from .config import AerisConfig
from .integrations.gemini import GeminiPlanner
from .integrations.gmail import GmailClient
from .integrations.google_calendar import GoogleCalendarClient
from .integrations.ollama import OllamaPlanner
from .integrations.screen_vision import ScreenVision
from .memory import MemoryStore
from .models import ActionRequest, ActionResult, AssistantTurn, PermissionLevel, PlannedResponse
from .permissions import ApprovalCallback, PermissionEngine
from .registry import ToolRegistry, ToolSpec
from .router import LocalRouter
from . import schemas
from .tools import (
    BrowserTools,
    BrowserAdvancedTools,
    CodingTools,
    DesktopTools,
    DownloadTools,
    FilesystemTools,
    PackageTools,
    SystemTools,
)


class AerisAssistant:
    def __init__(self, config: AerisConfig | None = None):
        self.config = config or AerisConfig.load()
        self.audit = AuditLogger(self.config.audit_log)
        self.memory = MemoryStore(self.config.memory_db)
        self.permissions = PermissionEngine()
        self.registry = ToolRegistry(self.permissions, self.audit, dry_run=self.config.dry_run)
        self.router = LocalRouter()
        self._gemini = (
            GeminiPlanner(self.config.gemini_api_key, self.config.gemini_model)
            if self.config.ai_enabled and self.config.gemini_api_key
            else None
        )
        self._ollama = OllamaPlanner() if self.config.ai_enabled else None
        self._register_tools()

    def _register_tools(self) -> None:
        desktop = DesktopTools(self.config.app_catalog_file, self.config.data_dir / "screenshots")
        browser = BrowserTools(self.config.allowed_domains)
        browser_adv = BrowserAdvancedTools()
        files = FilesystemTools(self.config.allowed_paths)
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
        system = SystemTools()
        ai_key = self.config.gemini_api_key if self.config.ai_enabled else None
        vision = ScreenVision(ai_key, self.config.gemini_model)
        coding = CodingTools(
            self.config.allowed_paths,
            self.config.coding_workspace,
            ai_key,
            self.config.gemini_model,
        )
        gmail = GmailClient(self.config.gmail_credentials_file)
        calendar = GoogleCalendarClient(self.config.gmail_credentials_file)

        def status(_: dict[str, Any]) -> ActionResult:
            data = self.config.public_summary() | {
                "dry_run": self.registry.dry_run,
                "stopped": self.permissions.stopped,
                "registered_tools": len(self.registry.names()),
            }
            return ActionResult(True, "Aeris status loaded.", data=data)

        def stop(_: dict[str, Any]) -> ActionResult:
            self.permissions.stop()
            return ActionResult(True, "Aeris kill switch activated. Only status and resume are available.")

        def resume(_: dict[str, Any]) -> ActionResult:
            self.permissions.resume()
            return ActionResult(True, "Aeris resumed.")

        specs = [
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
                "Close a configured application; unsaved work may be lost.",
                PermissionLevel.CONFIRM,
                desktop.close_app,
                model=schemas.CloseApp,
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
                "Type text into the currently active application.",
                PermissionLevel.CONFIRM,
                desktop.type_text,
                model=schemas.TypeText,
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
            ),
            ToolSpec(
                "desktop.close_current_window",
                "Close the active window; unsaved work may be lost.",
                PermissionLevel.CONFIRM,
                desktop.close_current_window,
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
                PermissionLevel.AUTO,
                browser_adv.click,
                model=schemas.BrowserClick,
            ),
            ToolSpec(
                "browser.advanced_fill",
                "Fill a text field in the interactive playwright browser.",
                PermissionLevel.AUTO,
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
        ]
        for spec in specs:
            self.registry.register(spec)

    def handle(
        self,
        text: str,
        approval_callback: ApprovalCallback | None = None,
        token: Any = None,
    ) -> AssistantTurn:
        user_text = text.strip()
        
        if token:
            token.raise_if_cancelled()
            
        plan = self.router.route(user_text)
        if plan is None and self._gemini is not None:
            try:
                plan = self._gemini.plan(user_text, self.registry.definitions(), self.memory.recent(8), token)
            except Exception as exc:
                self.audit.write("gemini_planner_failed", error=str(exc))
                if self._is_network_error(exc) and self._ollama is not None:
                    # Fallback to offline planner
                    try:
                        plan = self._ollama.plan(user_text, self.registry.definitions(), self.memory.recent(8), token)
                    except Exception as ollama_exc:
                        self.audit.write("ollama_planner_failed", error=str(ollama_exc))
                        plan = PlannedResponse(reply=self._planner_failure_message(exc))
                else:
                    plan = PlannedResponse(reply=self._planner_failure_message(exc))
        elif plan is None and self._ollama is not None:
            try:
                plan = self._ollama.plan(user_text, self.registry.definitions(), self.memory.recent(8), token)
            except Exception as exc:
                self.audit.write("ollama_planner_failed", error=str(exc))
                plan = PlannedResponse(reply="Ollama offline planner failed. Say 'help' for local commands.")
        elif plan is None:
            plan = PlannedResponse(
                reply="I do not know that command yet. Say 'help', or configure GEMINI_API_KEY for flexible requests."
            )

        sensitive = any(
            action.tool.startswith("email.")
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
        for action in plan.actions:
            if token:
                token.raise_if_cancelled()
            result = self.registry.execute(action, approval_callback, token=token)
            results.append(result)
            prefix = "[OK]" if result.success else "[FAILED]"
            lines.append(f"{prefix} {result.message}")
            details = self._visible_details(action, result)
            if details:
                lines.append(details)

        reply = "\n".join(line for line in lines if line).strip() or "Done."
        self.memory.add("assistant", reply[:10_000], classification="SENSITIVE" if sensitive else "LOCAL_ONLY")
        return AssistantTurn(input_text=user_text, reply=reply, results=results)

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
        if action.tool.startswith("packages.") and data.get("output"):
            return str(data["output"])
        if not result.success:
            return ""
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
