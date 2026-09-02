<div align="center">

# ⚡ AERIS

### Local-First Cognitive Desktop Assistant for Windows

**Voice • Vision • Desktop Automation • AI Reasoning • Coding • Gmail • Safe Computer Control**

<br>

> **Aeris is a permission-based AI desktop assistant designed to understand, reason, and safely interact with your Windows computer through natural language.**

<br>

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge\&logo=python\&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?style=for-the-badge\&logo=windows\&logoColor=white)
![Gemini](https://img.shields.io/badge/Google-Gemini_AI-8E75B2?style=for-the-badge\&logo=google\&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active_Development-00C853?style=for-the-badge)
![Local First](https://img.shields.io/badge/Architecture-Local_First-111111?style=for-the-badge)
![Safety](https://img.shields.io/badge/Safety-Permission_Based-EA4335?style=for-the-badge)

<br>

**One assistant. One application. One evolving Aeris ecosystem.**

</div>

---

## ✨ What is Aeris?

**Aeris** is a local-first, permission-based cognitive desktop assistant built for Windows.

Instead of functioning as only a chatbot, Aeris combines:

* 🎙️ Voice interaction
* 👁️ Screen understanding
* 🧠 Gemini-powered reasoning
* 💻 Desktop automation
* 📁 Secure filesystem operations
* 🧑‍💻 Coding project generation
* 🌐 Browser and web actions
* 📧 Gmail integration
* 📦 Windows package management
* 🛡️ Permission-based execution
* ⚡ Offline desktop commands
* 🖥️ Animated sci-fi HUD interface

Aeris is designed around one important principle:

> **AI should be powerful enough to help control your computer, but restricted enough that it cannot silently take control of it.**

Aeris therefore separates **understanding**, **planning**, **permission**, and **execution** instead of allowing unrestricted AI-generated system commands.

---

# 🖥️ Aeris HUD

Aeris launches directly into an animated sci-fi desktop interface designed to make its internal state visible.

The HUD includes:

* Central animated AI character
* System telemetry
* Activity stream
* Microphone status
* Screen-access status
* Gemini/AI state
* Live-action status
* Permission indicators
* Listening state
* Thinking state
* Executing state
* Speaking state
* Failure state
* Fullscreen HUD
* Always-on-top mode

Aeris visually changes state depending on what the assistant is currently doing.

```text
STANDBY
   ↓
LISTENING
   ↓
UNDERSTANDING
   ↓
PLANNING
   ↓
PERMISSION CHECK
   ↓
EXECUTING
   ↓
RESPONDING
   ↓
STANDBY
```

---

# 🚀 Current Capabilities

## 🎙️ Voice & Wake-Word Control

Aeris can:

* Automatically enter wake-word standby
* Detect the wake name `Aeris`
* Accept hands-free commands
* Support push-to-talk interaction
* Perform speech recognition using Faster Whisper
* Speak responses through local text-to-speech
* Handle common transcription variations
* Remove wake-name prefixes automatically

Examples:

```text
Aeris, open YouTube

Okay Aeris, open Chrome

Aeris, set volume to 40 percent

Aeris, check my battery
```

---

## 🧠 Intelligent Command Routing

Routine desktop operations are handled through the local offline router whenever possible.

Gemini is used only when more flexible reasoning is required.

This provides:

* ⚡ Faster execution
* 🌐 Reduced internet dependency
* 🔐 Better privacy
* 💸 Fewer unnecessary AI API requests
* 🛡️ Smaller execution attack surface

The offline router understands flexible phrases such as:

```text
set volume to 60 percent

set volume for 60

set the volume at sixty percent

okay Aeris, open YouTube

please open Chrome
```

If Gemini is required but internet access is unavailable, Aeris remains operational and suggests:

```text
offline help
```

instead of exposing a network exception.

---

# 👁️ Screen Understanding

Aeris can inspect the currently visible screen after receiving session permission.

Examples:

```text
what is on my screen

look at my screen

look at my screen and explain this Python error

explain what I am seeing
```

### Privacy model

Screen access is:

* On-demand
* Permission controlled
* Visible in the HUD
* Temporary
* Not continuously recorded

A temporary screen capture may be sent to Gemini for interpretation.

The image is **not retained by Aeris after processing**.

---

# 🧑‍💻 AI Coding Workspace

Aeris can generate complete coding projects from natural-language requests.

Examples:

```text
build a weather app

create a Python expense tracker

write Python code for an expense tracker with a Tkinter interface

create a machine learning starter project
```

Generated projects are placed inside:

```text
AERIS_CODING_WORKSPACE
```

### Coding safety rules

Aeris:

✅ Generates projects inside the dedicated coding workspace
✅ Creates new project folders
✅ Validates Python syntax
✅ Validates JSON
✅ Validates TOML
✅ Opens projects in VS Code when available
✅ Preserves existing projects

Aeris does **not**:

❌ Overwrite existing projects
❌ Automatically execute generated code
❌ Run arbitrary model-generated terminal commands

This allows AI-assisted development without giving the model unrestricted shell access.

---

# 🖥️ Windows Application Control

Aeris can launch trusted applications configured in:

```text
config/apps.windows.json
```

Example:

```json
{
  "my app": [
    "C:\\Program Files\\My App\\my-app.exe"
  ]
}
```

Then say:

```text
open my app
```

Aeris can also discover exact application names registered in the Windows Start menu.

### Security

Spoken application names are never passed directly into a shell command.

---

# 🌐 Browser & Web Actions

Aeris can:

* Open websites
* Perform Google searches
* Perform YouTube searches
* Navigate common browser destinations

Examples:

```text
open youtube

Google latest computer vision research

search YouTube for Python DSA tutorial
```

---

# 📥 Safe Downloads

Aeris can download direct public HTTP or HTTPS files.

Examples:

```text
download https://example.com/course.zip

download https://example.com/file.bin as course.zip
```

Before potentially sensitive download actions, Aeris asks for confirmation.

Downloaded files can be scanned using **Microsoft Defender** when available.

Aeris never automatically executes downloaded files.

---

# 📦 Windows Package Management

Aeris integrates with **Windows Package Manager (`winget`)**.

Supported operations include:

```text
search apps for OBS

install VLC

update VLC

list app updates

list installed apps

uninstall VLC
```

For normal software installation, using an exact `winget` package is preferred.

---

# 🛡️ Local Installer Protection

Aeris can launch downloaded installers only after safety checks.

Example:

```text
install downloaded installer C:\Users\YourName\Downloads\trusted-setup.exe
```

Before installation Aeris checks:

1. User confirmation
2. Microsoft Defender scanning when available
3. Digital signature validity

Aeris does not:

* Bypass Windows UAC
* Silently execute downloads
* Circumvent system security controls

---

# 🔊 Volume, Brightness & Media

Aeris supports local system controls.

### Volume

```text
set volume to 35

increase volume

decrease volume
```

### Brightness

```text
set brightness to 70

increase brightness

decrease brightness
```

### Media

```text
play music

pause music

next song

previous song
```

---

# 🪟 Window & Desktop Control

Supported commands include:

```text
show desktop

switch window

maximize window

minimize window

close current window
```

Potentially destructive operations remain permission-aware.

---

# 📋 Clipboard Actions

Aeris can interact with clipboard text using permission controls.

Examples:

```text
copy Aeris is ready to clipboard

read clipboard
```

---

# 📁 Safe File Management

Aeris supports filesystem operations only inside approved folders.

Supported actions include:

* Find files
* List files
* Read files
* Open files
* Create folders
* Create notes
* Copy files
* Move files
* Recoverably delete files

Examples:

```text
find file resume

list files in C:\Users\YourName\Documents

read file C:\Users\YourName\Documents\notes.txt

create folder C:\Users\YourName\Documents\Aeris Notes

create note ideas saying Build the download manager

copy file notes.txt to backups\notes.txt

move file notes.txt to archive\notes.txt
```

Allowed locations are configured using:

```env
AERIS_ALLOWED_PATHS=
```

This prevents the AI from freely traversing the entire computer.

---

# 📊 Computer Health Monitoring

Aeris can inspect local system health.

Examples:

```text
computer health

check battery
```

Information may include:

* CPU usage
* Memory usage
* Disk usage
* Battery percentage
* Charging status
* System health information

---

# ⚡ Power Controls

Aeris can perform system power actions after confirmation.

Supported actions include:

```text
lock computer

sleep computer

restart computer

shut down computer

cancel shutdown
```

Sensitive actions require explicit approval.

---

# 📸 Screenshots

After receiving screen-session permission, Aeris can capture screenshots.

Example:

```text
take a screenshot
```

Screen access remains visible inside the HUD.

---

# ⌨️ Safe Typing Automation

Aeris can type into the active application.

Example:

```text
type Hello, this was typed by Aeris
```

Typing requires **exact confirmation** before execution.

This prevents model-generated text from silently being entered into another application.

---

# 📧 Gmail Integration

Aeris integrates with Gmail through Google's official OAuth flow.

Aeris can:

### Read recent messages

```text
check my emails
```

### Compose and send mail

```text
send email to friend@example.com subject Hello message This is a test from Aeris.
```

Before sending an email, Aeris shows:

```text
Recipient
Subject
Message body
```

and requires confirmation.

Aeris never asks for or stores your Gmail password.

See:

```text
docs/GMAIL_SETUP.md
```

---

# 🛡️ Safety Architecture

Aeris is intentionally designed around controlled execution.

## Default behavior

Aeris starts in:

```text
DRY-RUN MODE
```

In dry-run mode, Aeris can understand and prepare actions without performing real computer changes.

Real system actions require:

```text
--live
```

or enabling:

```text
LIVE ACTIONS
```

inside the interface.

---

## 🔐 Permission Levels

Aeris distinguishes between different classes of operations.

```text
User Command
     │
     ▼
Offline / AI Router
     │
     ▼
Validated Tool
     │
     ▼
Permission Manager
     │
     ├── Safe action
     │      ↓
     │   Execute
     │
     └── Sensitive action
            ↓
       Exact Approval
            ↓
         Execute
```

Sensitive operations require additional approval even when live actions are enabled.

---

## 🚨 Built-In Protection

Aeris includes:

* Dry-run mode
* Kill switch
* Audit logging
* Secret redaction
* Allowed filesystem boundaries
* Explicit session permissions
* Exact-action confirmations
* Digital signature verification
* Defender scanning
* Validated tool registry
* Restricted execution adapters
* Visible access indicators

---

# 🚫 What Aeris Intentionally Does Not Do

Security boundaries are part of the architecture, not missing features.

Aeris does **not**:

* Run arbitrary AI-generated shell commands
* Bypass Windows UAC
* Automatically execute downloaded files
* Reuse private browser cookies
* Bypass paywalls
* Silently send emails
* Continuously record your screen
* Give unrestricted filesystem access to Gemini
* Automatically execute AI-generated coding projects
* Silently overwrite existing coding projects

> **The reasoning model proposes. Aeris decides what is allowed to execute.**

---

# 📴 Offline Mode

Many everyday commands work without Gemini or an internet connection.

### Local capabilities

✅ Wake-word detection
✅ Speech recognition after model installation
✅ Text-to-speech
✅ Application launching
✅ Volume control
✅ Brightness control
✅ Media control
✅ Screenshots
✅ File operations
✅ Computer health
✅ Desktop operations

### Internet-dependent capabilities

🌐 Gemini reasoning
🌐 Gemini screen understanding
🌐 AI project generation
🌐 Gmail
🌐 Downloads
🌐 Package searching
🌐 Package installation and updates

Aeris continues operating locally when internet access disappears.

---

# ⚙️ Requirements

| Requirement      | Details                                     |
| ---------------- | ------------------------------------------- |
| Operating System | Windows 10 or Windows 11                    |
| Python           | Python 3.11                                 |
| Microphone       | Required for voice mode                     |
| Gemini API Key   | Required for AI planning, vision and coding |
| Google OAuth     | Required only for Gmail                     |
| Internet         | Required only for online integrations       |

---

# 📦 Installation

## 1. Download Aeris

Clone or extract the Aeris project folder.

Enter the folder:

```powershell
cd Aeris
```

---

## 2. Run the Windows Setup

Double-click:

```text
SETUP_AERIS.bat
```

The setup process:

* Configures PowerShell execution policy only for setup
* Creates `.venv`
* Installs required Python packages
* Creates `.env`
* Runs automated tests
* Prepares Aeris for Windows

---

# 🔑 Environment Configuration

Open `.env` using the **Aeris Settings** interface and configure:

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

> [!CAUTION]
> Never commit `.env` to GitHub.

Do not write:

```env
GEMINI_API_KEY = key
```

Use:

```env
GEMINI_API_KEY=key
```

without spaces around `=`.

---

# ▶️ Starting Aeris

For normal daily use, double-click:

```text
START_AERIS.bat
```

Aeris will:

1. Launch the HUD
2. Initialize system services
3. Speak its startup greeting
4. Enter wake-word standby
5. Wait for `Aeris`
6. Remain in safe dry-run mode until live actions are enabled

---

# 💻 Terminal Launch

Development and troubleshooting modes remain available.

### Standard

```powershell
.\.venv\Scripts\python.exe -m aeris
```

### Voice + live actions

```powershell
.\.venv\Scripts\python.exe -m aeris --voice --live
```

---

# 💬 Command Examples

```text
Aeris, open Chrome

open VS Code

what is on my screen

look at my screen and explain this Python error

build a weather app

write Python code for an expense tracker with a Tkinter interface

search YouTube for Python DSA tutorial

Google latest computer vision research

download https://example.com/course.zip

search apps for OBS

install VLC

update VLC

list app updates

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

take a screenshot

type Hello, this was typed by Aeris

check my emails

send email to friend@example.com subject Hello message This is a test from Aeris.

stop Aeris

resume Aeris

offline help
```

---

# 🏗️ Architecture

```text
                       ┌─────────────────────┐
                       │       USER          │
                       │ Voice / Text / HUD  │
                       └──────────┬──────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │   Aeris Assistant   │
                       │   Orchestration     │
                       └──────────┬──────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
          ┌──────────────────┐       ┌────────────────────┐
          │  Offline Router  │       │  Gemini Planner    │
          │ Fast Local Tasks │       │ Flexible Reasoning │
          └────────┬─────────┘       └──────────┬─────────┘
                   │                            │
                   └─────────────┬──────────────┘
                                 ▼
                    ┌────────────────────────┐
                    │    Validated Registry  │
                    │    Approved Tools Only │
                    └────────────┬───────────┘
                                 ▼
                    ┌────────────────────────┐
                    │   Permission Manager   │
                    │ Dry Run / Confirmation │
                    └────────────┬───────────┘
                                 ▼
              ┌──────────────────────────────────┐
              │          Tool Adapters           │
              ├──────────────────────────────────┤
              │ Desktop │ Files │ Browser        │
              │ Gmail   │ Voice │ Packages       │
              │ Screen  │ Coding│ Downloads      │
              └──────────────────────────────────┘
                                 │
                                 ▼
                       ┌─────────────────────┐
                       │   Windows System    │
                       └─────────────────────┘
```

---

# 📂 Project Structure

```text
Aeris/
│
├── aeris/
│   ├── assistant.py
│   │   └── Orchestration and safe execution
│   │
│   ├── permissions.py
│   │   └── Permission levels and exact-action approvals
│   │
│   ├── registry.py
│   │   └── Validated tool boundary
│   │
│   ├── router.py
│   │   └── Fast offline command routing
│   │
│   ├── integrations/
│   │   ├── Gemini
│   │   ├── Gmail
│   │   ├── Voice
│   │   └── Screen vision
│   │
│   └── tools/
│       ├── Coding
│       ├── Browser
│       ├── Desktop
│       ├── Package manager
│       ├── System
│       ├── Downloads
│       └── Filesystem
│
├── tests/
│   └── Automated security and routing tests
│
├── config/
│   └── Trusted Windows application catalog
│
├── docs/
│   ├── Security documentation
│   ├── Gmail setup
│   ├── Capability map
│   ├── Build plan
│   └── Windows testing guide
│
├── scripts/
│   └── Windows setup and launcher scripts
│
├── SETUP_AERIS.bat
│   └── One-time Windows setup
│
└── START_AERIS.bat
    └── Daily Aeris launcher
```

---

# 🧪 Testing

Aeris includes automated tests for critical routing and security behavior.

The Windows setup process automatically runs the test suite.

Before enabling full live voice control, complete:

```text
docs/WINDOWS_TESTING.md
```

Also review:

```text
docs/SECURITY.md
docs/JARVIS_CAPABILITY_MAP.md
```

---

# 🗺️ Development Roadmap

Aeris uses a single evolving architecture.

There are **no separate Aeris editions**.

Every new capability becomes part of the same canonical project.

### ✅ Current Foundation

* [x] Sci-fi HUD
* [x] Voice commands
* [x] Automatic wake-word standby
* [x] Local speech recognition
* [x] Local text-to-speech
* [x] Offline command router
* [x] Gemini reasoning
* [x] Screen understanding
* [x] AI coding workspace
* [x] Windows application control
* [x] Browser actions
* [x] Secure downloads
* [x] Winget integration
* [x] Safe installer validation
* [x] Volume control
* [x] Brightness control
* [x] Media control
* [x] Window management
* [x] Clipboard control
* [x] Safe filesystem operations
* [x] System health monitoring
* [x] Power controls
* [x] Screenshots
* [x] Confirmed typing automation
* [x] Gmail reading
* [x] Confirmed Gmail sending
* [x] Dry-run execution
* [x] Live-action mode
* [x] Permission management
* [x] Audit logs
* [x] Kill switch

### 🔬 Planned

* [ ] Dedicated Playwright browser profile
* [ ] Richer browser automation
* [ ] Advanced Gmail operations
* [ ] Google Calendar integration
* [ ] Durable schedules and reminders
* [ ] Optional Ollama offline planner
* [ ] Persistent structured memory
* [ ] Specialist software adapters
* [ ] Richer multi-step workflows
* [ ] Improved local reasoning
* [ ] Expanded developer automation
* [ ] Advanced HUD interactions

Development details are maintained in:

```text
docs/BUILD_PLAN.md
```

---

# 🧩 Design Philosophy

Aeris is built around five core principles.

### 🏠 1. Local First

Routine tasks should remain on the computer whenever possible.

### 🔐 2. Permission Before Power

Having the technical ability to perform an action does not mean the AI should perform it automatically.

### ⚡ 3. Fast Paths for Simple Commands

Opening Chrome should not require an LLM reasoning cycle.

### 🧠 4. AI Where AI Adds Value

Gemini is reserved for tasks requiring interpretation, planning, vision, or generation.

### 👁️ 5. Visible AI State

Users should always be able to tell whether Aeris is listening, reasoning, accessing the screen, or performing an action.

---

# 🎯 Long-Term Vision

Aeris is being developed toward a broader **AI operating layer for the desktop**.

The goal is not simply:

```text
User → Chatbot → Response
```

The goal is:

```text
User Intent
     ↓
Understanding
     ↓
Context
     ↓
Reasoning
     ↓
Safe Planning
     ↓
Permission
     ↓
Execution
     ↓
Verification
     ↓
Natural Response
```

Aeris aims to become an assistant capable of helping across:

* Daily computer operations
* Software development
* AI/ML workflows
* Research
* Communication
* Browser workflows
* Productivity
* File organization
* System monitoring
* Creative applications
* Multi-step desktop automation

while maintaining user visibility and control.

---

# 🔒 Security Notice

Aeris can interact with real applications, files, email, downloads, and Windows system controls.

Before enabling live actions:

1. Review `docs/SECURITY.md`
2. Configure `AERIS_ALLOWED_PATHS`
3. Test commands in dry-run mode
4. Complete `docs/WINDOWS_TESTING.md`
5. Verify all credentials are stored correctly
6. Keep `.env` outside version control
7. Enable live mode only when ready

> [!IMPORTANT]
> Arbitrary terminal execution is intentionally unavailable because unrestricted model-generated shell commands could bypass Aeris permissions, validation, and safety boundaries.

---

# 🤝 Contributing

Aeris is under active development.

Contributions should preserve the project's main architectural rule:

> **New capabilities must use validated tools and Aeris's permission system rather than bypassing them through unrestricted shell execution.**

Potential contribution areas include:

* New safe desktop tools
* Offline routing improvements
* Voice recognition improvements
* HUD enhancements
* Browser automation
* Testing
* Windows compatibility
* AI planning
* Documentation
* Accessibility

---

# 💡 Why Aeris?

Most AI assistants live inside a browser tab.

Aeris is being built to live **with the computer itself**.

It can understand natural-language intent, observe the screen when permitted, reason using AI when necessary, execute local actions through controlled tools, and clearly expose what it is doing.

The goal is not unlimited automation.

The goal is:

<div align="center">

### **Useful AI + Local Control + Explicit Permission**

</div>

---

<div align="center">

# ⚡ AERIS

### Think. Understand. Assist. Execute Safely.

**Built as a local-first cognitive desktop assistant for Windows.**

<br>

⭐ If you find Aeris interesting, consider starring the repository.

<br>

`Python` • `Artificial Intelligence` • `Windows Automation` • `Computer Vision` • `Voice AI` • `Gemini` • `Desktop Assistant`

</div>
