# Aeris

Aeris is a local-first, permission-based Windows cognitive desktop assistant. It combines an animated sci-fi HUD, automatic wake-word standby, text and voice commands, screen understanding, safe coding-project generation, local computer control, Gemini reasoning, Gmail, browser actions, and permission management.

There is only one canonical Aeris project. New capabilities are added to the same folder and application instead of being distributed as separate editions.

## Working capabilities

- Launch directly into an animated HUD with a central AI character, telemetry, activity stream, safety indicators, fullscreen HUD, and always-on-top mode
- Speak a startup greeting and enter visible wake-word standby automatically; say `Aeris` before a hands-free command
- Change the character and interface state while listening, thinking, executing, speaking, stopped, or failed
- Inspect the currently visible screens on request after session permission, send one temporary capture to Gemini, and retain no screenshot
- Generate complete new coding projects inside `AERIS_CODING_WORKSPACE`, validate Python/JSON/TOML, never overwrite, never auto-run, and open VS Code when available
- Open configured applications or exact names registered in the Windows Start menu
- Open websites, Google searches, and YouTube searches
- Download a direct public HTTP/HTTPS file into Downloads after confirmation
- Scan downloads with Microsoft Defender when available and never auto-run them
- Search, install, update, and uninstall exact applications through Windows Package Manager (`winget`)
- Launch a local installer only after confirmation, Defender scanning, and a valid digital-signature check
- Set or change volume and brightness
- Control media playback
- Show the desktop, switch windows, maximize/minimize windows, and close the current window safely
- Read or copy text through the clipboard with permission controls
- Find, list, read, open, create, copy, move, and recoverably delete files within allowed folders
- Show computer health, disk, memory, CPU, battery, and charging status
- Lock, sleep, restart, shut down, or cancel a pending power action after confirmation
- Capture screenshots after session permission
- Type into the active window after exact confirmation
- Read recent Gmail messages after session permission
- Send Gmail after showing recipient, subject, body, and receiving confirmation
- Automatic wake-word standby and push-to-talk speech recognition with Faster Whisper
- Local text-to-speech
- Optional Gemini planning for commands not handled by the offline router
- Offline-tolerant voice routing for common transcription variations
- Wake-name cleanup for phrases such as `Okay Aeris, open YouTube`
- HUD access monitor showing microphone, screen, AI, and live-action state
- One-click Windows setup and daily launchers
- Dry-run mode, kill switch, audit log, secret redaction, and exact-action approvals

## Requirements

- Windows 10 or Windows 11
- Python 3.11
- A microphone for voice mode
- Gemini API key for flexible planning, screen understanding, and code generation
- Google OAuth desktop credentials only for Gmail

Routine desktop commands do not require Gemini or internet access. Downloads, package searches, package
installation, Gemini, and Gmail require internet access.

## Offline mode

Voice recognition, text-to-speech, application launching, volume, brightness, media controls, screenshots, and allowed-file operations run locally after initial installation and model download.

The offline router accepts flexible variations including:

```text
set volume to 60 percent
set volume for 60
set the volume at sixty percent
okay Aeris, open YouTube
please open Chrome
```

If an open-ended request requires Gemini while the internet is unavailable, Aeris keeps running and suggests `offline help` instead of exposing a network exception.

## Simple Windows setup

Extract the `Aeris` folder and double-click:

```text
SETUP_AERIS.bat
```

The launcher handles the PowerShell execution policy only for the setup process, creates `.venv`, installs required packages, creates `.env`, and runs the tests.

Open `.env` from the Aeris Settings button and configure:

```env
GEMINI_API_KEY=your_key_here
AERIS_ALLOWED_PATHS=C:\Users\YourName\Desktop;C:\Users\YourName\Documents;C:\Users\YourName\Downloads
AERIS_DOWNLOAD_DIR=C:\Users\YourName\Downloads
AERIS_CODING_WORKSPACE=C:\Users\YourName\Documents\Aeris Projects
AERIS_HANDS_FREE=true
AERIS_WAKE_WORD=aeris
AERIS_VOICE_DEVICE=cpu
AERIS_VOICE_LANGUAGE=en
```

Do not put spaces around `=` and do not commit `.env`.

## Daily use

Double-click:

```text
START_AERIS.bat
```

The HUD comes online immediately, speaks its greeting, and enters wake-word standby when enabled. It still starts in safe dry-run mode. Use **LIVE ACTIONS** when you want real computer actions. Sensitive actions always show a separate confirmation.

Terminal access remains available for troubleshooting:

```powershell
.\.venv\Scripts\python.exe -m aeris
.\.venv\Scripts\python.exe -m aeris --voice --live
```

## Example commands

```text
open chrome
open vscode
look at my screen and explain this Python error
what is on my screen
write Python code for an expense tracker with a Tkinter interface
build a weather app
search YouTube for Python DSA tutorial
Google latest computer vision research
download https://example.com/course.zip
download https://example.com/file.bin as course.zip
search apps for OBS
install VLC
update VLC
list app updates
list installed apps
install downloaded installer C:\Users\YourName\Downloads\trusted-setup.exe
open downloads folder
set volume to 35
increase brightness
next song
show desktop
switch window
copy Aeris is ready to clipboard
read clipboard
computer health
check battery
find file resume
list files in C:\Users\YourName\Documents
read file C:\Users\YourName\Documents\notes.txt
create folder C:\Users\YourName\Documents\Aeris Notes
create note ideas saying Build the download manager
copy file notes.txt to backups\notes.txt
move file notes.txt to archive\notes.txt
take a screenshot
type Hello, this was typed by Aeris
check my emails
send email to friend@example.com subject Hello message This is a test from Aeris.
stop Aeris
resume Aeris
offline help
```

For software, prefer `install VLC` or another exact `winget` package. If a website supplies an installer,
download its direct link, inspect it, and then use `install downloaded installer ...`. Aeris does not reuse
private browser cookies, bypass paywalls, bypass UAC, or silently execute a download.

## Add an application

Edit `config/apps.windows.json` and provide one or more trusted executable paths:

```json
{
  "my app": ["C:\\Program Files\\My App\\my-app.exe"]
}
```

Then say `open my app`. Aeris never passes the spoken application name into a shell.

## Gmail

Follow [docs/GMAIL_SETUP.md](docs/GMAIL_SETUP.md). Gmail uses official OAuth and Windows Credential Manager. Aeris never requests your Gmail password.

## Safety

Aeris starts in dry-run mode. `--live` is required for real actions. Wake listening and screen access are shown in the HUD. Screen capture is on-demand, not continuous. Read [docs/SECURITY.md](docs/SECURITY.md), [docs/JARVIS_CAPABILITY_MAP.md](docs/JARVIS_CAPABILITY_MAP.md), and complete [docs/WINDOWS_TESTING.md](docs/WINDOWS_TESTING.md) before enabling live voice mode.

## Project structure

```text
aeris/
  assistant.py       Orchestration and safe execution
  permissions.py     Permission levels and exact-action approvals
  registry.py        Validated tool boundary
  router.py          Fast offline command routing
  integrations/      Gemini, Gmail, voice, and screen vision
  tools/             Coding, browser, desktop, package, system, download, and filesystem adapters
tests/                Automated security and routing tests
config/               Trusted Windows application catalog
docs/                 Security, Gmail, and manual test guides
scripts/              Windows setup and launch scripts
SETUP_AERIS.bat       One-time setup
START_AERIS.bat       Daily desktop launcher
```

## Continuing development

Aeris already provides the secure HUD, wake listening, screen assistance, code generation, and daily computer-management foundation. A dedicated Playwright browser profile, richer Gmail and calendar actions, durable schedules, an optional Ollama offline planner, and specialist software adapters remain on the same project plan. See [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md).

Arbitrary terminal execution remains intentionally unavailable because unrestricted model-generated shell commands would bypass Aeris's permissions and tool validation.
