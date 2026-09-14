import pydantic
from typing import Optional, Literal

class OpenApp(pydantic.BaseModel):
    name: str = pydantic.Field(description="The name of the application to open, e.g., 'chrome', 'notepad'")

class CloseApp(pydantic.BaseModel):
    name: str = pydantic.Field(description="The exact name of the application to close")

class SetVolume(pydantic.BaseModel):
    level: int = pydantic.Field(description="Volume level from 0 to 100", ge=0, le=100)

class ChangeVolume(pydantic.BaseModel):
    delta: int = pydantic.Field(description="Amount to change the volume by (e.g. 10 or -10)")

class SetBrightness(pydantic.BaseModel):
    level: int = pydantic.Field(description="Brightness level from 0 to 100", ge=0, le=100)

class ChangeBrightness(pydantic.BaseModel):
    delta: int = pydantic.Field(description="Amount to change the brightness by (e.g. 10 or -10)")

class MediaControl(pydantic.BaseModel):
    action: Literal["play_pause", "next", "previous", "stop", "mute"] = pydantic.Field(description="The media action to perform")

class TypeText(pydantic.BaseModel):
    text: str = pydantic.Field(description="The text to type. Max 5000 chars.", max_length=5000)

class ClipboardCopy(pydantic.BaseModel):
    text: str = pydantic.Field(description="The text to copy to the clipboard. Max 20000 chars.", max_length=20000)

class WindowAction(pydantic.BaseModel):
    action: Literal["show_desktop", "switch_window", "task_view", "minimize_all", "maximize_current", "minimize_current"] = pydantic.Field(description="The window action to perform")

class InspectScreen(pydantic.BaseModel):
    question: str = pydantic.Field(description="A question or prompt about the current screen")

class MonitorScreen(pydantic.BaseModel):
    duration_minutes: int = pydantic.Field(description="How long to monitor the screen in minutes")
    event_query: str = pydantic.Field(description="What specific event to look for on the screen")

class SearchWorkspace(pydantic.BaseModel):
    query: str = pydantic.Field(description="The exact text string to search for across all files in the workspace")

class ApplyDiff(pydantic.BaseModel):
    path: str = pydantic.Field(description="The relative path to the file inside the workspace")
    old_content: str = pydantic.Field(description="The exact old content block to replace")
    new_content: str = pydantic.Field(description="The new content block to insert")

class CreateProject(pydantic.BaseModel):
    prompt: str = pydantic.Field(description="Description of the coding project to build")

class OpenUrl(pydantic.BaseModel):
    url: pydantic.HttpUrl = pydantic.Field(description="The HTTP or HTTPS URL to open")

class BrowserClick(pydantic.BaseModel):
    selector: str = pydantic.Field(description="CSS selector of the element to click")

class BrowserFill(pydantic.BaseModel):
    selector: str = pydantic.Field(description="CSS selector of the input field to fill")
    text: str = pydantic.Field(description="The text to type into the field")

class SearchWeb(pydantic.BaseModel):
    query: str = pydantic.Field(description="The search query")

class Download(pydantic.BaseModel):
    url: pydantic.HttpUrl = pydantic.Field(description="The URL of the file to download")
    filename: Optional[str] = pydantic.Field(None, description="Optional specific filename to save as")

class PackageSearch(pydantic.BaseModel):
    query: str = pydantic.Field(description="The package name or keyword to search for")

class PackageAction(pydantic.BaseModel):
    package: str = pydantic.Field(description="The exact package ID to install, update, or uninstall")

class InstallFile(pydantic.BaseModel):
    path: str = pydantic.Field(description="The path to the downloaded installer file")

class FilePath(pydantic.BaseModel):
    path: str = pydantic.Field(description="The local file or folder path")

class OptionalFilePath(pydantic.BaseModel):
    path: Optional[str] = pydantic.Field(None, description="The local file or folder path. Defaults to current workspace if omitted.")

class FindFiles(pydantic.BaseModel):
    query: str = pydantic.Field(description="The filename or pattern to search for")

class WriteText(pydantic.BaseModel):
    path: str = pydantic.Field(description="The path to the file to write")
    text: str = pydantic.Field(description="The content to write to the file")

class CopyMove(pydantic.BaseModel):
    source: str = pydantic.Field(description="The source file path")
    destination: str = pydantic.Field(description="The destination file path")

class ListRecentEmails(pydantic.BaseModel):
    count: int = pydantic.Field(5, description="Number of emails to list", ge=1, le=20)

class SendEmail(pydantic.BaseModel):
    to: str = pydantic.Field(description="The recipient email address")
    subject: str = pydantic.Field(description="The email subject line")
    body: str = pydantic.Field(description="The email body text")

class ListCalendarEvents(pydantic.BaseModel):
    count: int = pydantic.Field(10, description="The maximum number of upcoming events to retrieve")
