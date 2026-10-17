# Validation report - 17 October 2026, launch/reminders increment

This is the current report. [Earlier same-day increment](history/increment1-2026-10-17-VALIDATION_REPORT.md) remains historical evidence. Scope: [traceability](REQUIREMENTS_TRACEABILITY.md); next work: [continuation](CONTINUATION.md).

Same nested Aeris root/branch fix/responsive-aeris-desktop/HEAD e97687470b46e0c2f9030b331de17df33d9ff903 plus preserved uncommitted changes. No commits, pushes, branch changes, dependency installation or environment replacement. Parent forwarding helpers are outside the nested Git root.

The user's pasted errors ran from AERIS_AI_ASSISTANT using its separate Python 3.14 environment. Actual source and the validated Python 3.11.9 environment are in its Aeris child. Activation does not change cwd; an explicit relative .venv path still selects the parent environment. New root START_AERIS/AERIS helpers forward to the canonical child RUN_AERIS, which chooses interpreter/cwd explicitly and never silently runs setup. Root diagnostics now report Python 3.11.9.

Baseline this turn: 240 passed/1 skipped, 3.23 s via parent helper. Final full suite via `.\AERIS.bat --test`: **261 passed, 1 skipped**, 4.53 s. Skip is unchanged Windows symlink privilege/Developer Mode (test_settings_lifecycle.py:183). Ruff/compileall/offline diagnostics/isolated manual Qt Stop pass. No whole-module exclusions added. Windows build 26200; Pydantic 2.13.5, PySide6 6.11.2, pytest 9.1.1; existing dependencies retained.

| Boundary reproduced | Before | Working evidence |
|---|---|---|
| Parent-folder launch and explicit parent interpreter | User log: launcher absent / No module named aeris | Parent START --self-test, AERIS --test/--lint/--help all exit 0 with child Python 3.11 |
| Parent exits while descendant retains output pipe | 1 failed, 3 passed; returncode 0/reason None despite incomplete cleanup | Real harmless Windows process tree uses suspended assignment/Job Object; deadline/cancel reaps child and reader; before-resume cancellation executes no child code |
| Reminder time/parser/consumption/lock/recurrence/controller | 8 failed, 1 passed | Strict India timezone/offset schedules, no consumption without listeners, callbacks after commit/outside lock, recurrence skips missed occurrences, local registry and Stop pause |
| Normal app close | 2 failed, 1 passed; old boundary attempted process.terminate | Registry prepares exact observed HWND/PID/creation/title before confirmation; denial and changed target post nothing; normal WM_CLOSE dispatch explicitly unverified |
| Brightness readback and relative displays | 2 failed; reported success without readback and changed [30,60] into [40,40] | Actual observed list compared; mismatch fails; relative fixture becomes [40,70] |
| Calendar event metadata / late cancellation | 2 failed: no end field / no token argument | End/all-day/timezone/source retained; cancelled response discarded; fake services only |
| Overdue snooze state | 1 failed; future snoozed record remained marked overdue | Snooze resets overdue flag; UI labels due records without falsely certifying external delivery |

Additional real Qt workflow: create a reminder through the worker/controller/registry, receive one generic local notice, snooze/cancel the selected UUID, and close with scheduler/read workers stopped. Actual SQLite two-store claim and restart fixture proves one dispatch per occurrence in this test. Persistent Due list remains the recovery view if a process crashes between claim and signal; no guaranteed external notification or closed-app delivery claim.

During implementation the first new launcher version check had quoting corrected after smoke failure, and installed pywin32 rejected a None job name (corrected to an unnamed empty string). Final tests cover the actual installed API. An unavailable brightness documentation URL was replaced with upstream documentation/local installed API docs. These intermediate failures are not final acceptance failures.

Commands from the user's parent folder (no activation):

```powershell
.\START_AERIS.bat --self-test
.\AERIS.bat --help
.\AERIS.bat --test
.\AERIS.bat --lint
```

Additional checks from Aeris: existing `.venv\Scripts\python.exe -m compileall -q aeris scripts`; isolated `test_ui_manual.py`; capture_fixture_ui.py with --view reminders and --width/--height; scripts/measure_local.py; pip wheel --no-deps --no-build-isolation and scripts/check_wheel.py. The wheel was extracted/imported/self-tested with python -I from a temporary cwd and no source imports. Source distribution contains its setup/launcher/lock/build resources and builds a wheel outside the checkout. No packages were installed into either environment. Final wheel SHA256 `b76104e4e9d302a5f02feb99b3ca4acd912020dca5873bf8e02967ef1f83c4c5`. No PyInstaller/frozen executable or clean-account dependency test exists.

Synthetic captures: [1280 dashboard](evidence/launch-reminders-dashboard-1280.png), [1280 reminders](evidence/launch-reminders-tab-1280.png), [1920 dashboard](evidence/launch-reminders-dashboard-1920.png), and Qt scale 1.25/1.5/2 reminder captures. Representative standard/200 percent captures were visually inspected. This is not physical Windows DPI/keyboard/accessibility acceptance. No screen resolution was changed.

Performance: 30 warm simulated controller trials, median 5.286 ms, p95 7.275 ms, 0 failures; construction single sample 9.809 ms; [raw report](evidence/launch-reminders-controller.json). No real audio/device/GUI acknowledgment latency or speedup claim. Native process tests use harmless Python children only. No real installs/UAC, mail, OAuth, private captures, live desktop controls, model downloads, generated code execution or remote connectivity probes were performed.

Official API references are retained in SECURITY. Source hashes/artifact checks are recorded in [machine-readable evidence](evidence/launch-reminders-validation.json).

## Required end-to-end acceptance matrix

All real-device/account rows: **NOT RUN**, explicit supervision required. NOT IMPLEMENTED describes missing end-to-end code; NOT RUN describes unperformed acceptance. Per-scenario timings are NOT MEASURED; the aggregate controller benchmark above is separate.

| Scenario / requested outcome | Implementation state | Fixture result | Real device/account | Timing | Remaining limitation |
|---|---|---|---|---|---|
| Open application with existing config ? UI usable automatically; no surprise listening/upload/live mode | IMPLEMENTED | PASS: isolated offscreen dashboard/async settings/cache fixtures | NOT RUN | NOT MEASURED | Actual returning-user launch and consent onboarding NOT RUN |
| "Don't set volume to 100" / quoted/conditional command ? No volume effect and no cloud fallback that disregards negation | FIXTURE_VERIFIED | PASS: router/controller no action/provider | NOT RUN | NOT MEASURED | No actual desktop effect invoked |
| Negative, decimal, out-of-range or mixed quantities ? Defined validation/clarification; no silent sign/decimal loss | FIXTURE_VERIFIED | PASS: integral 0?100 grammar; invalid requests clarify | NOT RUN | NOT MEASURED | Decimal semantics deliberately rejected |
| "Set volume to 50 and brightness to 20" ? Both intended steps or a clear clarification; no silent partial execution | FIXTURE_VERIFIED | PASS: entire compound clarifies | NOT RUN | NOT MEASURED | Two-command execution not implemented |
| Repeated pause/mute/unmute ? Absolute desired state where supported; never a mislabeled toggle | IMPLEMENTED | PASS: mute/unmute idempotence; pause never toggles | NOT RUN | NOT MEASURED | Absolute play/pause session missing |
| Offline: volume 35, brightness change, pause media, open Notepad ? Deterministic local path; no cloud/Ollama dependency; verify effect where supported | IMPLEMENTED | PASS: deterministic routes; volume/mute/brightness readback and selected graceful-close fixtures | NOT RUN | NOT MEASURED | Absolute play/pause session still unsupported; actual Windows app/device effects not tested |
| Say a tested English/Hinglish variation ? Correct local action or brief clarification; no dangerous guessing | FIXTURE_VERIFIED | PASS: existing English/Hinglish corpus | NOT RUN | NOT MEASURED | ASR language accuracy untested |
| "Okay, Aeris, open YouTube" via hands-free and text ? Consistent addressed-speech handling with no false wake matches | IMPLEMENTED | PASS: greeting extraction/local routing | NOT RUN | NOT MEASURED | Full shared alias catalog and actual hands-free recognition untested |
| Stop during TTS, model load, code generation, download, package work ? Honest acknowledgment and bounded cleanup; no unpublished late write | IMPLEMENTED | PASS: real Windows Job Object parent/child/pipe and pre-resume cancellation; prior generation/Qt cached-load fixtures | NOT RUN | NOT MEASURED | UAC/service effects and synchronous model/SDK waits remain; real audio/network/install quiescence not tested |
| Stop during existing-file patch final checks ? No publication after cancellation wins the commit gate | FIXTURE_VERIFIED | PASS: real registry cancels during second resolve; bytes unchanged | NOT RUN | NOT MEASURED | External filesystem writer races not eliminated |
| Stop after a write/install may have occurred ? Retained artifact/uncertain effect remains visible; stale speech suppressed | FIXTURE_VERIFIED | PASS: patch retained bytes/path; Qt receipt/no speech | NOT RUN | NOT MEASURED | Real external installation uncertainty untested |
| Follow-up: "make it 40" ? Bound to the recent correct task; expired/ambiguous context asks for clarification | FIXTURE_VERIFIED | PASS: production 30-second control context/expiry | NOT RUN | NOT MEASURED | Generic follow-ups missing |
| Screen help with no prior scope ? Selector and preview; no capture/upload before approval | MISSING | NOT IMPLEMENTED end-to-end | NOT RUN | NOT MEASURED | Workflow code and fixture acceptance required; see phase ledger |
| Model/CLI JSON region array ? Strictly validated compatible scope, not tuple_type failure | FIXTURE_VERIFIED | PASS: json.loads array through strict registry schema | NOT RUN | NOT MEASURED | No screen capture/device invoked |
| Screen help after changing region/window ? Fresh scope approval; old tool-name grant cannot authorize it | IMPLEMENTED | PASS: canonical exact-region grant/expiry regressions | NOT RUN | NOT MEASURED | Window/DPI/destination scope UI missing |
| Browser fixture with moving/replaced target ? Reobserve/reauthorize; do not act on same-URL stale approval | MISSING | NOT IMPLEMENTED end-to-end | NOT RUN | NOT MEASURED | Workflow code and fixture acceptance required; see phase ledger |
| Two-step browser/download task ? Consume actual outputs and verify final artifact; never guess URL/path | MISSING | NOT IMPLEMENTED end-to-end | NOT RUN | NOT MEASURED | Workflow code and fixture acceptance required; see phase ledger |
| Find and install a test package ? Preview exact package, honor UAC, verify actual presence; automated tests are mocks | IMPLEMENTED | PASS: existing fake process/presence/cancel fixtures | NOT RUN | NOT MEASURED | Observed selection/version/publisher/immutable approval/UAC incomplete |
| Generate/repair fixture project ? Staged validated diff/project, safe commit, optional authorized checks, explicit Undo | IMPLEMENTED | PASS: existing fake generation/syntax/repair and single-file cancellation | NOT RUN | NOT MEASURED | Multi-file diff/Undo/authorized checks missing |
| Organize fixture Downloads ? Preview and approved move plan, collision handling, Undo without overwriting newer edits | MISSING | NOT IMPLEMENTED end-to-end | NOT RUN | NOT MEASURED | Workflow code and fixture acceptance required; see phase ledger |
| Reminder across app restart/sleep ? Durable local event, no duplicate notification, explicit overdue behavior | IMPLEMENTED | PASS: local/Qt create/notice/snooze/cancel; fake-clock overdue recurrence; two-store claim and restart no redispatch | NOT RUN | NOT MEASURED | Running-app local notices only; broad DST/crash-delivery and supervised acceptance pending |
| Run study-mode routine ? Authorized bounded low-risk steps, progress, Stop and error recovery | MISSING | NOT IMPLEMENTED end-to-end | NOT RUN | NOT MEASURED | Workflow code and fixture acceptance required; see phase ledger |
| Daily Brief with fake email/calendar ? Summarize fetched records with provenance; drafts never auto-send | IMPLEMENTED | PASS: fake Gmail/Calendar grounding; end/all-day/timezone/source metadata; local reminder records | NOT RUN | NOT MEASURED | Account identity/setup, rich converted agenda and project tasks/drafts incomplete |
| Deny/cancel/stale approval ? No provider call, write, capture, or external action under denied scope | IMPLEMENTED | PASS: registry/cloud/coding and Qt stale approval regressions | NOT RUN | NOT MEASURED | Full browser/account/window boundaries incomplete |
| Credential store unavailable or settings invalid ? Clear recovery, no plaintext fallback, no silent live mode | FIXTURE_VERIFIED | PASS: keyring failure/env recovery; no env-key bypass | NOT RUN | NOT MEASURED | All malformed paths and backend rollback-failure recovery not tested |
| Close/reopen during busy work ? Responsive lifecycle, no orphan workers/processes or stale effects | IMPLEMENTED | PASS: owned Qt settings/cleanup/read workers and reminder scheduler; no constructor delivery | NOT RUN | NOT MEASURED | Full single-instance restore, real cold-ASR/native stress pending |
| Cleanup failure / keyring unavailable / interrupted settings save ? Usable retry/recovery, preserved data and effective configuration | FIXTURE_VERIFIED | PASS: explicit Retry/keyring recovery/credential rollback | NOT RUN | NOT MEASURED | All native cleanup and rollback-backend failures not tested |
| Built-in System Health and Network Test ? Available deterministic workflows without needing a model to invent tools | FIXTURE_VERIFIED | PASS: deterministic health/status; approved bounded network probe fake | NOT RUN | NOT MEASURED | Real endpoint response not probed |
| Reply-only explanation versus failed planner in CLI ? Correct distinct structured status and exit code | FIXTURE_VERIFIED | PASS: actual CLI return 0 versus failed planner 1 | NOT RUN | NOT MEASURED | No provider request performed |
| Optional specialist app absent/present ? Honest readiness, supported typed actions and separate real-app acceptance | MISSING | NOT IMPLEMENTED: catalogs provide launch only | NOT RUN | NOT MEASURED | Typed specialist adapters/version matrices missing |
| Frozen app from another cwd ? Launch/resources/settings work; optional unavailable services degrade clearly | MISSING | NOT IMPLEMENTED: no frozen executable; wheel import/resources PASS | NOT RUN | NOT MEASURED | PyInstaller absent; pinned build and clean Windows account acceptance required |
