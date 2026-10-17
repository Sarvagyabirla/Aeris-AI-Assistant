from typing import Literal, Optional

import pydantic


class AerisBaseModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid", strict=True)

class OpenApp(AerisBaseModel):
    name: str = pydantic.Field(description="The name of the application to open, e.g., 'chrome', 'notepad'")

class CloseApp(AerisBaseModel):
    name: str = pydantic.Field(description="The exact name of the application to close")
    window_id: int | None = pydantic.Field(None, ge=1, description="Observed selected window; refreshed before approval")
    process_id: int | None = pydantic.Field(None, ge=1)
    process_created: float | None = None
    expected_title: str | None = pydantic.Field(None, max_length=512)

class SetVolume(AerisBaseModel):
    level: int = pydantic.Field(description="Volume level from 0 to 100", ge=0, le=100)

class CloseCurrentWindow(CloseApp):
    name: str = 'selected window'

class ChangeVolume(AerisBaseModel):
    delta: int = pydantic.Field(description="Amount to change the volume by (e.g. 10 or -10)", ge=-100, le=100)

class SetBrightness(AerisBaseModel):
    level: int = pydantic.Field(description="Brightness level from 0 to 100", ge=0, le=100)

class ChangeBrightness(AerisBaseModel):
    delta: int = pydantic.Field(description="Amount to change the brightness by (e.g. 10 or -10)", ge=-100, le=100)

class MediaControl(AerisBaseModel):
    action: Literal["play", "pause", "play_pause", "next", "previous", "stop", "mute", "unmute", "toggle_mute"] = pydantic.Field(description="Absolute mute/unmute; explicit playback/mute toggles. Absolute play/pause requires a supported session adapter.")

class NetworkTest(AerisBaseModel):
    host: Literal["www.microsoft.com"] = "www.microsoft.com"

class TypeText(AerisBaseModel):
    text: str = pydantic.Field(description="Exact Unicode text to dispatch after the target preview. Max 5000 chars.", min_length=1, max_length=5000)
    window_id: int | None = pydantic.Field(None, ge=1, description="Selected target HWND, observed again before approval")
    process_id: int | None = pydantic.Field(None, ge=1)
    process_created: float | None = pydantic.Field(None, allow_inf_nan=False)
    expected_title: str | None = pydantic.Field(None, max_length=512)
    process_name: str | None = pydantic.Field(None, max_length=260)
    focus_window_id: int | None = pydantic.Field(None, ge=1, description="Observed focused child control; no automatic retargeting")

    @pydantic.field_validator("text")
    @classmethod
    def valid_unicode_text(cls, value):
        # Reject lone surrogates/NUL and control shortcuts before approval or dispatch.
        value.encode("utf-16-le", errors="strict")
        if any(ord(character) < 32 and character not in "\t\r\n" or ord(character) == 127 for character in value):
            raise ValueError("Text contains unsupported control characters")
        return value

class ClipboardCopy(AerisBaseModel):
    text: str = pydantic.Field(description="The text to copy to the clipboard. Max 20000 chars.", max_length=20000)

class WindowAction(AerisBaseModel):
    window_id: int | None = pydantic.Field(None, ge=1)
    process_id: int | None = pydantic.Field(None, ge=1)
    process_created: float | None = pydantic.Field(None, allow_inf_nan=False)
    expected_title: str | None = pydantic.Field(None, max_length=512)
    action: Literal["show_desktop", "switch_window", "task_view", "minimize_all", "maximize_current", "minimize_current"] = pydantic.Field(description="The window action to perform")

class InspectScreen(AerisBaseModel):
    question: str = pydantic.Field(description="A question or prompt about the current screen", max_length=4000)
    region: list[int] | None = pydantic.Field(None, min_length=4, max_length=4, description="Explicit approved screen rectangle (left, top, right, bottom); required for live capture")

    @pydantic.field_validator("region", mode="before")
    @classmethod
    def normalize_python_rectangle(cls, value):
        # Deliberate compatibility for existing Python callers; other types stay strict.
        return list(value) if isinstance(value, tuple) else value

    @pydantic.field_validator("region")
    @classmethod
    def valid_rectangle(cls, value):
        if value is not None and (value[2] <= value[0] or value[3] <= value[1]):
            raise ValueError("Screen rectangle must have positive width and height")
        return value

class MonitorScreen(AerisBaseModel):
    duration_minutes: int = pydantic.Field(description="How long to monitor the screen in minutes", ge=1, le=30)
    event_query: str = pydantic.Field(description="What specific event to look for on the screen")

class SearchWorkspace(AerisBaseModel):
    query: str = pydantic.Field(description="The exact text string to search for across all files in the workspace")

class ApplyDiff(AerisBaseModel):
    expected_sha256: str = pydantic.Field(pattern=r"^[0-9a-f]{64}$", description="SHA256 of the exact file bytes reviewed before approval")
    path: str = pydantic.Field(description="The relative path to the file inside the workspace")
    old_content: str = pydantic.Field(description="The exact old content block to replace", min_length=1)
    new_content: str = pydantic.Field(description="The new content block to insert")

class CreateProject(AerisBaseModel):
    prompt: str = pydantic.Field(description="Description of the coding project to build")

class OpenUrl(AerisBaseModel):
    url: pydantic.HttpUrl = pydantic.Field(description="The HTTP or HTTPS URL to open")

class BrowserClick(AerisBaseModel):
    expected_url: pydantic.HttpUrl = pydantic.Field(description="Exact page URL observed and approved for this action")
    selector: str = pydantic.Field(description="CSS selector of the element to click")

class BrowserFill(AerisBaseModel):
    expected_url: pydantic.HttpUrl = pydantic.Field(description="Exact page URL observed and approved for this action")
    selector: str = pydantic.Field(description="CSS selector of the input field to fill")
    text: str = pydantic.Field(description="The text to type into the field")

class SearchWeb(AerisBaseModel):
    query: str = pydantic.Field(description="The search query")

class Download(AerisBaseModel):
    url: pydantic.HttpUrl = pydantic.Field(description="The URL of the file to download")
    filename: Optional[str] = pydantic.Field(None, description="Optional specific filename to save as")

class PackageSearch(AerisBaseModel):
    query: str = pydantic.Field(description="The package name or keyword to search for")

class PackageAction(AerisBaseModel):
    package: str = pydantic.Field(description="The exact package ID to install, update, or uninstall")

class InstallFile(AerisBaseModel):
    path: str = pydantic.Field(description="The path to the downloaded installer file")

class FilePath(AerisBaseModel):
    path: str = pydantic.Field(description="The local file or folder path")

class OptionalFilePath(AerisBaseModel):
    path: Optional[str] = pydantic.Field(None, description="The local file or folder path. Defaults to current workspace if omitted.")

class FindFiles(AerisBaseModel):
    query: str = pydantic.Field(description="The filename or pattern to search for")

class WriteText(AerisBaseModel):
    path: str = pydantic.Field(description="The path to the file to write")
    text: str = pydantic.Field(description="The content to write to the file")

class CopyMove(AerisBaseModel):
    source: str = pydantic.Field(description="The source file path")
    destination: str = pydantic.Field(description="The destination file path")
    expected_sha256: str | None = pydantic.Field(None, pattern=r'^[0-9a-f]{64}$')
    expected_identity: list[int] | None = pydantic.Field(None, min_length=4, max_length=4)

class OrganizationItem(CopyMove):
    expected_sha256: str = pydantic.Field(pattern=r'^[0-9a-f]{64}$')
    expected_identity: list[int] = pydantic.Field(min_length=4, max_length=4)

class OrganizeFiles(AerisBaseModel):
    path: str = pydantic.Field(min_length=1, max_length=8192)
    batch_id: str | None = pydantic.Field(None, pattern=r'^[0-9a-f]{32}$')
    manifest: list[OrganizationItem] | None = pydantic.Field(None, max_length=100)

class UndoOrganization(AerisBaseModel):
    batch_id: str = pydantic.Field(pattern=r'^[0-9a-f]{32}$')
    manifest: list[OrganizationItem] | None = pydantic.Field(None, max_length=100)

class ListRecentEmails(AerisBaseModel):
    count: int = pydantic.Field(5, description="Number of emails to list", ge=1, le=20)

class SendEmail(AerisBaseModel):
    to: str = pydantic.Field(description="The recipient email address", max_length=254, pattern=r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$")
    subject: str = pydantic.Field(description="The email subject line")
    body: str = pydantic.Field(description="The email body text")

class ListCalendarEvents(AerisBaseModel):
    count: int = pydantic.Field(10, description="The maximum number of upcoming events to retrieve", ge=1, le=50)


class SetReminder(AerisBaseModel):
    message: str = pydantic.Field(description="The reminder message text (max 500 chars)", min_length=1, max_length=500)
    when: str = pydantic.Field(
        min_length=1, max_length=200,
        description=(
            "When to fire the reminder. ISO 8601 datetime string with timezone "
            "(e.g. '2026-10-14T09:00:00+05:30') or a natural English string "
            "like 'tomorrow at 9am', 'in 30 minutes', 'friday at 3pm'."
        )
    )
    recurrence: Optional[Literal["daily", "weekly"]] = pydantic.Field(
        None, description="Optional recurrence: 'daily' or 'weekly'. None for one-off."
    )


class SnoozeReminder(AerisBaseModel):
    reminder_id: str = pydantic.Field(description="The UUID of the reminder to snooze", pattern=r"^[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")
    minutes: int = pydantic.Field(10, description="How many minutes to snooze", ge=1, le=1440)


class CancelReminder(AerisBaseModel):
    reminder_id: str = pydantic.Field(description="The UUID of the reminder to cancel", pattern=r"^[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")
