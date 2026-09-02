# Windows manual test checklist

Keep Aeris in dry-run mode for the first pass.

## Installation

- [ ] Python 3.11 is selected.
- [ ] `SETUP_AERIS.bat` finishes successfully.
- [ ] Automated tests pass.
- [ ] `.env` contains no quotation marks around Windows paths.
- [ ] Allowed paths match the actual Windows username.

## Desktop interface

- [ ] `START_AERIS.bat` opens one Aeris desktop window.
- [ ] Text commands work through the input box and Send button.
- [ ] Speak records and transcribes one command.
- [ ] Safe/live mode changes only after confirmation.
- [ ] Sensitive actions show a separate permission dialog.
- [ ] Stop Aeris blocks actions and Resume restores them.
- [ ] Settings opens the correct project `.env` file.
- [ ] The animated Aeris character and telemetry appear without layout clipping.
- [ ] HUD fullscreen and always-on-top controls work.
- [ ] Character color/state changes for listening, thinking, executing, speaking, and stopped.

## Wake listening

- [ ] Aeris speaks one startup greeting.
- [ ] The HUD visibly shows `WAKE LISTENING` while the microphone is active.
- [ ] `Aeris, open Chrome` is accepted.
- [ ] Ordinary speech without the Aeris wake name is ignored.
- [ ] Turning off Wake Listening releases continuous standby while Speak still works.
- [ ] Stop Aeris turns off wake listening.

## Screen understanding

- [ ] `look at my screen and explain this error` asks for session permission.
- [ ] Denying permission sends no screenshot.
- [ ] Approving analyzes only visible screens and shows the answer in the activity stream.
- [ ] No screen capture file is left in the Aeris data or screenshot folder.

## Coding projects

- [ ] `write Python code for an expense tracker` shows the project request and workspace before confirmation.
- [ ] The generated project appears under `AERIS_CODING_WORKSPACE` and opens in VS Code when available.
- [ ] Running the same request again creates a new folder instead of overwriting.
- [ ] Invalid Python/JSON/TOML output is repaired or rejected before files are committed.
- [ ] Generated code and dependencies do not execute automatically.

## Dry run

- [ ] `python -m aeris --once "open chrome"` shows a dry-run action.
- [ ] `python -m aeris --once "set volume to 40"` shows a dry-run action.
- [ ] `python -m aeris --once "delete file test.txt"` asks for confirmation before simulating.
- [ ] `stop Aeris` prevents later actions.
- [ ] `resume Aeris` restores commands.

## Live desktop controls

- [ ] Chrome opens.
- [ ] VS Code opens.
- [ ] Volume increases, decreases, and sets an exact value.
- [ ] Brightness changes on the internal display.
- [ ] Play/pause and next/previous media keys work.
- [ ] Screenshot asks for session permission and saves successfully.
- [ ] Typing shows the complete text before confirmation.
- [ ] Closing an app asks every time.
- [ ] Show desktop, switch window, maximize, and minimize work.
- [ ] Clipboard reading asks for session permission.
- [ ] Computer health and battery status load.

## Downloads and applications

- [ ] A direct HTTPS test file asks for confirmation and appears in Downloads.
- [ ] A second download with the same name does not overwrite the first.
- [ ] A loopback/private-network URL is rejected.
- [ ] `search apps for VLC` returns trusted `winget` results.
- [ ] Installing or updating an app shows the exact package and asks every time.
- [ ] A downloaded unsigned installer is rejected.
- [ ] A signed installer asks in Aeris and then shows the normal Windows/UAC prompt.

## Files

- [ ] Find searches only configured allowed paths.
- [ ] A path outside the allowed roots is rejected.
- [ ] Reading a text file asks for session permission.
- [ ] Executable files are blocked.
- [ ] Delete moves a test file to the Recycle Bin after confirmation.
- [ ] Creating, copying, or moving a file asks first and never overwrites an existing file.

## Power actions

- [ ] Lock and sleep ask every time.
- [ ] Restart and shutdown ask every time and use a 10-second cancellation window.
- [ ] `cancel shutdown` cancels a pending restart or shutdown.

## Voice

- [ ] The first run downloads the selected Whisper model.
- [ ] The correct microphone is selected by Windows.
- [ ] Push-to-talk transcribes a short English command.
- [ ] Push-to-talk transcribes a short Hinglish command.
- [ ] Aeris speaks the result.
- [ ] Voice failure does not crash text mode.

## Gmail

- [ ] OAuth asks for Google consent without requesting a password inside Aeris.
- [ ] Reading email asks for session permission.
- [ ] Sending displays recipient, subject, and body.
- [ ] Denying send leaves the mailbox unchanged.
- [ ] Approving send returns a Gmail message ID.

Do not enable startup-on-login until every relevant live test passes.
