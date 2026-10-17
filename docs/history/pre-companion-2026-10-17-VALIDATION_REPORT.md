# Validation report - 17 October 2026, effect/audio increment

Current report for the same nested Aeris root, branch fix/responsive-aeris-desktop, HEAD
e97687470b46e0c2f9030b331de17df33d9ff903 plus preserved uncommitted changes. Previous
launch/reminder snapshot: [history](history/increment2-2026-10-17-VALIDATION_REPORT.md).
All eleven phases remain in [traceability](REQUIREMENTS_TRACEABILITY.md); next work is in
[CONTINUATION](CONTINUATION.md). No whole phase or fictional Jarvis readiness is claimed.

Baseline: **261 passed, 1 skipped**, 4.65 s. Final full suite from the user's parent folder,
`.\AERIS.bat --test`: **356 passed, 1 skipped**, 7.47 s. The skip remains Windows symlink
privilege/Developer Mode in test_settings_lifecycle.py:183. Windows build 26200, Python 3.11.9,
Pydantic 2.13.5, PySide6 6.11.2, pytest 9.1.1; existing child .venv retained. No installs,
commits, pushes, branch changes, real credentials/runtime data, remote requests, model downloads,
mail, actual typing/capture/device effects, UAC/install/power or generated-project execution.

| Reproduced boundary | Before fix | Final connected evidence |
|---|---|---|
| Copy/move/download publication and receipts | Initial 8 failed / 1 passed | Exclusive hard-link publication via token gate; bounded staging/hash/identity checks; retained cancellation paths |
| Move destination mutation / stage replacement | Temporary production fixtures lost original bytes or deleted competing stage entry; destination regression also failed after first protection attempt | Windows destination-bound handle verified against stage before source deletion; owned cleanup refuses replacement; native ABI BOOLEAN corrected |
| Unicode typing | Initial 10 failures | Registry preflight binds process/window/control; UI selection/exact text/refocus fixtures; UTF-16 Hindi/accent/emoji batches, focus/Stop/modifier abort, partial-event receipts |
| Provider lifecycle | 7 initial failures, plus 2 active-task/reentrant failures | Failed retired/staged planners remain owned and retryable; settings/close cannot dispose in-flight clients |
| Credential rollback | 4 initial failures | Secret-free journal; failed rollback forces simulation/AI/listening off; safe restart and CLI override regression; explicit Settings repair |
| Audio/custom wake/Stop | Initial 3 failed / 1 passed | Shared configured phrase parser; passive capture blocked during TTS/global Stop; PTT/late transcript/capture ownership and bounded pre-roll fixtures |
| CUDA cancellation | 2 failures | Stop during load/inference failure starts no CPU fallback; previous normal CPU/int8 fallback retained |
| TTS native cleanup / queue | 2 cleanup failures (init fixture passed), plus 2 queue/teardown failures | Same-owner cleanup Retry; balanced COM; incomplete release blocks unsafe restart; stale queued speech drained before teardown |

The final 95 additional passing cases include these regressions and their broader boundary
fixtures. Tests use disposable files/SQLite, fake services/native window/input APIs, actual
harmless Windows process descendants, and offscreen Qt event loops. No new whole-module skips.
The portable NumPy-absence isolation regression was rerun with global NumPy imports blocked:
1 passed. Remote CI and other Python versions were not run.

Final commands/checks (parent folder unless stated):

```powershell
.\AERIS.bat --test
.\AERIS.bat --lint
.\AERIS.bat --self-test
# From the Aeris child:
.\.venv\Scripts\python.exe -m compileall -q aeris scripts
.\.venv\Scripts\python.exe test_ui_manual.py
```

All exit 0. The manual Qt fixture verifies Stop with temporary config and fake effects;
it does not use the user's settings. Git diff --check passes (line-ending conversion notices
only). Catalog/module self-test checks presence, not actual device/model/account readiness.
A diagnostic invocation overriding core.autocrlf=false flagged CRLF as trailing whitespace;
the repository's configured `git diff --check` passes. No line endings were rewritten for it.

Packaging: wheel built offline with pip wheel --no-index --no-deps --no-build-isolation;
extracted/imported with python -I from another cwd, catalogs present, excluded runtime artifact
names absent. SHA256 `c4d446b041c541fbc9c9e090868b38be2000ce43eb2ead1da3322d6a0421c918`.
Source archive contains setup/launch/catalog/new module/tests, no runtime/secrets/screenshots;
builds a wheel outside the checkout without installs. Source SHA256
`e3b67dc0eb0993b2cceced4bcc4be55b9ba6f801ffed75fe13f283beb6efad16`.
Setuptools emits a nonfatal legacy project.license-table deprecation; SPDX/build dependency
migration remains a release task. No PyInstaller/frozen or clean-account executable acceptance.

Synthetic real-widget captures: [1280x720](evidence/effect-audio-dashboard-1280.png),
[1920x1080](evidence/effect-audio-dashboard-1920.png), Qt scales
[125%](evidence/effect-audio-scale-1.25.png), [150%](evidence/effect-audio-scale-1.5.png),
[200%](evidence/effect-audio-scale-2.png). Standard/200% captures visually inspected; controls
readable. These are offscreen fixtures, not physical Windows DPI/keyboard/accessibility or
real screen capture. No screen resolution was changed.

Performance: 30 warm simulated controller trials, median 5.574 ms, p95 6.646 ms, routing p95
0.106 ms, 0 failures; one construction sample 10.569 ms. [Raw report](evidence/effect-audio-controller.json).
No real audio/Stop/UI acknowledgment speedup or device latency claim. Hashes/privacy-pattern
checks and artifact metadata: [machine-readable evidence](evidence/effect-audio-validation.json).

Native/filesystem limits: Windows safe move and hard-link-capable filesystem required; byte
transfers preserve timestamps but not ACL/ADS/readonly metadata. Hostile parent/junction races
are not proven closed. POSIX copy/cleanup have weaker observed checks; safe move is unsupported.
Partial ownership is process-local; 24-hour age does not prove another process's hung job inactive.
Native socket/DNS/fsync calls retain OS blocking limits. Unicode input delivery is not read back;
one scalar can race a focus change, and title-changing apps abort. Passive TTS gating is not
verified acoustic echo cancellation. COM release failure can remain unrecoverable in-process.

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
| "Okay, Aeris, open YouTube" via hands-free and text ? Consistent addressed-speech handling with no false wake matches | IMPLEMENTED | PASS: shared exact address parser, configured Nova/Aeris text/PTT boundary fixtures | NOT RUN | NOT MEASURED | Passive aliases remain explicit by configured phrase; no trained detector/multi-alias UI; actual recognition NOT RUN |
| Stop during TTS, model load, code generation, download, package work ? Honest acknowledgment and bounded cleanup; no unpublished late write | IMPLEMENTED | PASS: real Windows Job Object parent/child/pipe and pre-resume cancellation; exclusive transfer/download gates, owner-thread speech retry, cancelled CUDA fallback and prior Qt cached-load fixtures | NOT RUN | NOT MEASURED | UAC/service effects and synchronous model/SDK waits remain; real audio/network/install quiescence not tested |
| Stop during existing-file patch final checks ? No publication after cancellation wins the commit gate | FIXTURE_VERIFIED | PASS: real registry cancels during second resolve; bytes unchanged | NOT RUN | NOT MEASURED | External filesystem writer races not eliminated |
| Stop after a write/install may have occurred ? Retained artifact/uncertain effect remains visible; stale speech suppressed | FIXTURE_VERIFIED | PASS: patch/copy/download retained bytes/path; partial typing event counts; Qt receipt/no stale speech | NOT RUN | NOT MEASURED | Real external installation uncertainty untested |
| Follow-up: "make it 40" ? Bound to the recent correct task; expired/ambiguous context asks for clarification | FIXTURE_VERIFIED | PASS: production 30-second control context/expiry | NOT RUN | NOT MEASURED | Generic follow-ups missing |
| Screen help with no prior scope ? Selector and preview; no capture/upload before approval | MISSING | NOT IMPLEMENTED end-to-end | NOT RUN | NOT MEASURED | Workflow code and fixture acceptance required; see REQUIREMENTS_TRACEABILITY |
| Model/CLI JSON region array ? Strictly validated compatible scope, not tuple_type failure | FIXTURE_VERIFIED | PASS: json.loads array through strict registry schema | NOT RUN | NOT MEASURED | No screen capture/device invoked |
| Screen help after changing region/window ? Fresh scope approval; old tool-name grant cannot authorize it | IMPLEMENTED | PASS: canonical exact-region grant/expiry regressions | NOT RUN | NOT MEASURED | Window/DPI/destination scope UI missing |
| Browser fixture with moving/replaced target ? Reobserve/reauthorize; do not act on same-URL stale approval | MISSING | NOT IMPLEMENTED end-to-end | NOT RUN | NOT MEASURED | Workflow code and fixture acceptance required; see REQUIREMENTS_TRACEABILITY |
| Two-step browser/download task ? Consume actual outputs and verify final artifact; never guess URL/path | MISSING | NOT IMPLEMENTED end-to-end | NOT RUN | NOT MEASURED | Workflow code and fixture acceptance required; see REQUIREMENTS_TRACEABILITY |
| Find and install a test package ? Preview exact package, honor UAC, verify actual presence; automated tests are mocks | IMPLEMENTED | PASS: existing fake process/presence/cancel fixtures | NOT RUN | NOT MEASURED | Observed selection/version/publisher/immutable approval/UAC incomplete |
| Generate/repair fixture project ? Staged validated diff/project, safe commit, optional authorized checks, explicit Undo | IMPLEMENTED | PASS: existing fake generation/syntax/repair and single-file cancellation | NOT RUN | NOT MEASURED | Multi-file diff/Undo/authorized checks missing |
| Organize fixture Downloads ? Preview and approved move plan, collision handling, Undo without overwriting newer edits | MISSING | NOT IMPLEMENTED end-to-end | NOT RUN | NOT MEASURED | Workflow code and fixture acceptance required; see REQUIREMENTS_TRACEABILITY |
| Reminder across app restart/sleep ? Durable local event, no duplicate notification, explicit overdue behavior | IMPLEMENTED | PASS: local/Qt create/notice/snooze/cancel; fake-clock overdue recurrence; two-store claim and restart no redispatch | NOT RUN | NOT MEASURED | Running-app local notices only; broad DST/crash-delivery and supervised acceptance pending |
| Run study-mode routine ? Authorized bounded low-risk steps, progress, Stop and error recovery | MISSING | NOT IMPLEMENTED end-to-end | NOT RUN | NOT MEASURED | Workflow code and fixture acceptance required; see REQUIREMENTS_TRACEABILITY |
| Daily Brief with fake email/calendar ? Summarize fetched records with provenance; drafts never auto-send | IMPLEMENTED | PASS: fake Gmail/Calendar grounding; end/all-day/timezone/source metadata; local reminder records | NOT RUN | NOT MEASURED | Account identity/setup, rich converted agenda and project tasks/drafts incomplete |
| Deny/cancel/stale approval ? No provider call, write, capture, or external action under denied scope | IMPLEMENTED | PASS: registry/cloud/coding and Qt stale approval regressions | NOT RUN | NOT MEASURED | Full browser/account/window boundaries incomplete |
| Credential store unavailable or settings invalid ? Clear recovery, no plaintext fallback, no silent live mode | FIXTURE_VERIFIED | PASS: keyring/env recovery plus credential journal/current/restart/CLI safety | NOT RUN | NOT MEASURED | More malformed path coverage and simultaneous independent settings writer handling remain |
| Close/reopen during busy work ? Responsive lifecycle, no orphan workers/processes or stale effects | IMPLEMENTED | PASS: owned Qt settings/cleanup/read/audio workers, task-active/reentrant provider guard, reminder scheduler | NOT RUN | NOT MEASURED | Full single-instance restore, real cold-ASR/native stress pending |
| Cleanup failure / keyring unavailable / interrupted settings save ? Usable retry/recovery, preserved data and effective configuration | FIXTURE_VERIFIED | PASS: owned provider/TTS Retry, balanced COM fixtures, safe keyring/credential rollback journal and effective mode | NOT RUN | NOT MEASURED | Real native stress NOT RUN; throwing COM release can remain unrecoverable; cross-process settings/power-loss durability unproven |
| Built-in System Health and Network Test ? Available deterministic workflows without needing a model to invent tools | FIXTURE_VERIFIED | PASS: deterministic health/status; approved bounded network probe fake | NOT RUN | NOT MEASURED | Real endpoint response not probed |
| Reply-only explanation versus failed planner in CLI ? Correct distinct structured status and exit code | FIXTURE_VERIFIED | PASS: actual CLI return 0 versus failed planner 1 | NOT RUN | NOT MEASURED | No provider request performed |
| Optional specialist app absent/present ? Honest readiness, supported typed actions and separate real-app acceptance | MISSING | NOT IMPLEMENTED: catalogs provide launch only | NOT RUN | NOT MEASURED | Typed specialist adapters/version matrices missing |
| Frozen app from another cwd ? Launch/resources/settings work; optional unavailable services degrade clearly | MISSING | NOT IMPLEMENTED: no frozen executable; wheel import/resources PASS | NOT RUN | NOT MEASURED | PyInstaller absent; pinned build and clean Windows account acceptance required |
