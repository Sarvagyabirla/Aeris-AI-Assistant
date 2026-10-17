# Aeris ? Windows personal assistant

One Python/PySide6 application in active development. Daily launcher: **START_AERIS.bat**.
The 17 October 2026 increment repairs unsafe local routing, existing-file cancellation and outcome
loss, then connects recovery and local diagnostic workflows. **The full assistant is unfinished.**

Current checks: **240 passed, 1 skipped**, Ruff/compile/offline self-test pass; isolated Qt Stop and
synthetic screenshot pass. A source wheel contains catalogs/LICENSE and imports outside the
checkout. No microphone/UAC/OAuth/screen-control or frozen-executable acceptance is claimed.

See [current status](docs/IMPLEMENTATION_STATUS.md), [validation](docs/VALIDATION_REPORT.md),
[requirements/tool/module traceability](docs/REQUIREMENTS_TRACEABILITY.md),
[capabilities](docs/CAPABILITY_MATRIX.md), and [exact continuation](docs/CONTINUATION.md).
Earlier snapshots remain in docs/history and are not the current feature checklist.

## Start and use

Keep the existing Python 3.11 .venv and setup/start launchers. SETUP_AERIS.bat installs the declared
full optional requirements and Chromium; review that setup before running it. Portable core uses
pyproject base dependencies. requirements-lock.txt/uv.lock still need a unified reviewed strategy.
No environment was replaced or dependency installed for this increment.

Start in SIMULATION. Saved mode is restored; --simulate/--live are intentional overrides. New
hands-free settings default off. Text works without audio/cloud setup. Opted-in hands-free startup
loads cached speech assets on the audio thread. Normal voice use is now cache-only: no surprise
model download. First-download onboarding/progress and input-device selection remain unfinished.

Local examples: `open notepad`, `set volume to 35`, `set brightness to 50`, `volume kam karo`,
`make it 40` after a recent successful volume/brightness task, `system health`, `daily brief`.
Negated/quoted/conditional controls and invalid quantities clarify locally. Unsupported compounds
request one command at a time. Mute/unmute set absolute state; `toggle playback` is an explicit
toggle. Absolute play/pause currently explains that a selected-session adapter is missing.

Stop cancels the current task. Mute microphone pauses capture. Emergency Stop blocks tasks until
explicit Resume and remains latched across Settings. Cancellation does not undo committed effects:
retained artifacts/uncertain outcomes remain visible while stale speech is suppressed. Cleanup
failure retains the window with Retry. Some native/model/SDK waits cannot stop immediately.

System Health and Network Test shortcuts resolve without a planner. Live Network Test requires
approval for one bounded www.microsoft.com ICMP probe; failed ping does not prove offline status.
Daily Brief retrieves authorized bounded Gmail/Calendar metadata without cloud summarization or
sending. Account/end/timezone metadata and reminder/project display remain incomplete.

## Privacy and limitations

Only explicitly SHAREABLE history enters cloud planner context. Existing sensitive history is
omitted, and `/private <request>` omits conversation persistence even for reply-only answers.
The Local memory tab inspects/corrects/forgets existing records. Audit defaults store safe metadata.
Keyring failures leave local simulation text available with AI/listening disabled; no plaintext-key
fallback. Saved settings retain precedence over environment. Malformed effective environment
values recover safely. See [security boundaries](docs/SECURITY.md).

No screen selector/preview exists yet: no-scope capture and background watch fail closed. Browser
DOM identity/peer enforcement, immutable installer approvals, full native controls, typed dependent
tasks, multi-file Undo, durable routines/projects and companion/tray remain unfinished. Existing
uncommitted reminder modules are preserved but are not a complete reminder notification workflow.
App launch catalog entries do not imply specialist Blender/Office/Resolve/FL automation support.

## Checks on this PC

```powershell
Set-Location 'C:\AI Related project BY AI\AERIS_AI_ASSISTANT\Aeris'
& .\.venv\Scripts\python.exe -m aeris --self-test
& .\.venv\Scripts\python.exe -m aeris --no-ai --simulate --once 'open notepad'
& .\.venv\Scripts\python.exe -m pytest -ra
& .\.venv\Scripts\python.exe -m ruff check .
```

Self-test checks package/catalog/route presence without user config, models, accounts, devices or
network. Test counts are fixture evidence, not live PC certification. See
[supervised Windows checks](docs/WINDOWS_TESTING.md) and [measured performance](docs/PERFORMANCE.md).
BUILD_AERIS.bat still needs a reviewed pinned PyInstaller path and clean-account executable
acceptance; no verified executable is supplied. The existing MIT declaration now has a matching
LICENSE. Dependency redistribution attribution remains a release task.
