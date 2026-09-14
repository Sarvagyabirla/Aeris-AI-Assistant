# Aeris Implementation Status

## Checkpoint 1: Repair Installation and Existing-Data Upgrades
- [x] Fix eager optional imports (TTS, Gemini, Playwright deferred)
- [x] Declare every directly used dependency in pyproject.toml (PySide6, playwright, pydantic, pywin32)
- [x] Fix scripts/setup_windows.ps1 (added Invoke-Native for exit code checking, literal path for spaces)
- [x] Add versioned SQLite migration for memory.db classification column
- [x] Repair BUILD_AERIS.bat (removed assets/icon.ico, added config dir)
- [x] Make launch failures visible with MessageBoxW catch block in cli.py

## Checkpoint 2: One Responsive Controller and Clear Cancellation
- [x] Create CancellationToken class in aeris/state.py
- [x] Update AssistantWorker in desktop.py to use a long-lived queue of size 1
- [x] Add explicit status updates in AssistantWorker
- [x] Implement cancellation in AssistantWorker and wire it to a Stop button
- [x] Update AerisAssistant to accept and check CancellationToken
- [x] Update Planners (Gemini/Ollama) to accept CancellationToken
- [x] Verify clean termination and cancellation

## Checkpoint 3: Dependable Cross-Platform System Actions
- [x] Refactor system tools to use Windows APIs or exact commands directly
- [x] Only lock the session, never alter user passwords
- [x] Validate volume/brightness boundaries strictly
- [x] Cancel shutdowns correctly (shutdown /a)
- [x] Catch typical COM/WMI exceptions during status queries

## Checkpoint 4: Secure, Visible Privileged Commands
- [x] Remove all implicit sudo/elevation wrapping from CLI package managers or Windows commands
- [x] Print clear output about exactly what package or script is about to be executed before it runs
- [x] Do not bypass UAC prompts. Ensure commands are run in a normal subprocess so the OS handles elevation checks properly
