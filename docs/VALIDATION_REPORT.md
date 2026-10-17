# Validation report - 17 October 2026, connected companion increment

Actual repository: `AERIS_AI_ASSISTANT/Aeris`; branch `fix/responsive-aeris-desktop`; HEAD
`e97687470b46e0c2f9030b331de17df33d9ff903` plus preserved pre-existing/current uncommitted work.
Baseline: **356 passed, 1 skipped**. Final: **395 passed, 1 skipped,
0 failed**, pytest console 12.21 s (JUnit suite 12.018 s). The sole skip is
`tests/test_settings_lifecycle.py:183`: Windows symlink creation needs Developer Mode or elevated
privileges. It was not hidden or removed. Two formerly unsupported valid compound examples
were moved out of the unsafe-command corpus and replaced by positive production-controller
coverage; negation/invalid quantity/unsupported compound coverage remains.

Environment: Windows build 26200, existing Python 3.11.9 child .venv, Pydantic 2.13.5,
PySide6 6.11.2, pytest 9.1.1, Ruff 0.16.5, psutil 7.2.2. No environment replacement,
installation, model download, real credential use, personal-window capture, native typing,
volume/display change, mail, UAC/install, power action, generated-project execution, commit or
push occurred. Native API export introspection did not invoke a window. Real device/account
acceptance and remote CI are NOT RUN. Linux/other Python versions were not run locally.

## Actual repaired/connected evidence

| Boundary | Reproduction / implementation | Final evidence |
|---|---|---|
| Existing critical bugs | P0 negation/quantities/patch commit/effect reporting repairs already present in baseline | Existing real registry/controller/Qt regressions preserved and pass |
| Compound tasks / JSON dependencies | Initial new set: 3 failed, 6 passed | Whole-plan static preflight, actual output refs, no invalid partial effects; exact 50/20 and Notepad/35/selected minimize fixtures |
| Missing companion | Initial 2 Qt failures | One controller/model across both views; Stop retains effects; non-activating flags, recovery gate, hidden/reduced animation |
| Missing organization workflow | Initial 3 failures | One exact batch approval, bounded file hashes/identities, changed-content/collision denial, retained Stop manifest and Undo conflict refusal |
| Routines/scopes/modes | Connected actual Qt review/save/run/disable and revoke flows | Scope/catalog/mode/category changes invalidate review; restart denials; Assist/Trusted context tests |
| New SQLite ownership | Offscreen screenshot initially failed Windows temp cleanup due open database handles | New stores close each connection explicitly; capture/cleanup and live-object rename fixture pass |
| Native window wrapper gap | Installed win32gui lacks ShowWindowAsync and IsZoomed despite mocked tests passing | Replaced with typed user32 exports; actual export-presence check + registry fake native postconditions; no user-window invocation |
| Durable effects | Journal failure and interrupted-owner fixtures | Retained visible artifact receipts, blocked later work when durable logging fails, no automatic restart replay |

Commands from the nested Aeris folder (all final checks exit 0):

```powershell
.\.venv\Scripts\python.exe -m pytest -ra --junitxml=docs/evidence/companion-tests.xml
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m compileall -q aeris scripts
.\.venv\Scripts\python.exe -m aeris --self-test
.\.venv\Scripts\python.exe test_ui_manual.py
.\.venv\Scripts\python.exe -m scripts.measure_local --output docs/evidence/companion-controller.json
```

[Junit results](evidence/companion-tests.xml), [machine-readable validation](evidence/companion-validation.json),
[wheel report](evidence/companion-wheel.json). Offline self-test reports presence/catalogs/local route,
not actual device/model/account readiness. The isolated manual Qt fixture uses temporary config and
fake effects. New CI ui-offscreen job is added; remote CI has not run. Windows-only organization
fixtures explicitly skip on non-Windows; a separate portable-adapter rejection test exists.

Source wheel built with `pip wheel . --no-index --no-deps --no-build-isolation --wheel-dir <temp>`.
`python scripts/check_wheel.py <wheel>` extracts/imports core and optional UI modules from another
cwd under `python -I`, checks catalogs and excluded runtime/credential artifact names. SHA256:
`422eec158b22390cfc456e1a500de5e9c59a3d7aa63f05e5d1620c6822ac8218`. No excluded entries; import/self-test exit 0. No PyInstaller/frozen executable exists.
A source-archive roundtrip was not repeated in this increment; the previous result is historical.

Known-key/private-key pattern scan: **131 changed text files,
0 candidate files**; ignored personal runtime files were not inspected. This is a bounded pattern
scan, not proof that every possible secret format is absent. Wheel checks are separate from a full
signed/attributed frozen-release audit. Existing MIT/license data was preserved.

## Synthetic UI and performance

[Dashboard 1280x720](evidence/companion-dashboard-1280.png),
[1920x1080](evidence/companion-dashboard-1920.png), [floating view](evidence/companion-floating.png),
[Tasks builder](evidence/companion-tasks.png), [Permissions](evidence/companion-permissions.png),
Qt scales [125%](evidence/companion-scale-1.25.png), [150%](evidence/companion-scale-1.5.png),
[200%](evidence/companion-scale-2.png). Dashboard, floating, permissions and 200% captures were
visually inspected. They show real widgets with disposable simulation data, not live desktop
capture. No physical display resolution was changed. Full physical focus/DPI/keyboard/disconnect
acceptance remains NOT RUN. Some earlier captures predate the last small control/text adjustment;
no screenshot is offered as evidence of native desktop control.

30 warm simulated controller trials: median **14.862 ms**, p95 **20.002 ms**, routing p95
0.111 ms, 0 failures. One construction sample: 15.952 ms. [Raw trials](evidence/companion-controller.json).
This includes durable journal overhead and is slower than the previous increment's 5.574/6.646 ms
median/p95. It is not a GUI, Stop, speech or real device latency measurement. Character rendering
has a 30 fps timer cap, disabled in reduced motion and hidden/minimized views; real CPU/performance
cost remains unmeasured. Individual acceptance-scenario timings below are NOT MEASURED.

## Eight required connected demonstrations

| # | Fixture result | Real-device result / unfinished work |
|---|---|---|
| 1 normal launch, character/controller, saved mic/mode | PASS: isolated Qt controller/preferences/character code | NOT RUN normal user shortcut; first-run onboarding incomplete |
| 2 dashboard/companion during task, Stop, focus | PASS: same model/worker, Stop, retained results and non-activating flags | NOT RUN physical focus/tray/hotkeys |
| 3 offline Notepad, volume 35, minimize selected window | PASS: exact typed three-step goal through registry with fake app/volume/native window | NOT RUN speech/actual apps/audio/window; selection required |
| 4 additional-drive documents, single batch, Undo, revoke | PASS: arbitrary disposable root, actual fixture file moves/Undo/conflicts/restart revoke | NOT RUN additional physical drive; Windows hard links needed |
| 5 selected error screen, grounded assistance, code preview/apply/check | NOT IMPLEMENTED end-to-end | Screen selector/redaction/sharing, multi-file review/check workflow missing |
| 6 reviewed study/coding routine, apps/project/control/reminder | PASS local subset: review/save/run/disable app/control/reminder | Project/coding template and real voice/app check unfinished; no automatic triggers |
| 7 Gmail reply draft or install plan, exact final approval/denial | NOT IMPLEMENTED full draft/immutable install-plan workflow; existing approval denial fixtures PASS | NOT RUN accounts/UAC; missing code remains explicit |
| 8 Stop long task during speaking, retain effects, responsive UI | PASS: owned speech/cancel and Qt shared-worker/effect receipt fixtures | NOT RUN actual microphone/SAPI/acoustic interruption/quiescence |

All eight individual timings: NOT MEASURED. No fixture is labeled device-verified.

## Complete required acceptance matrix

NOT IMPLEMENTED means missing workflow code. NOT RUN means unperformed acceptance of a stated
boundary. IMPLEMENTED (partial/foundation) is explicitly limited by the final column.

| Scenario / required outcome | Implementation | Fixture result | Real device/account | Timing | Remaining limitation |
|---|---|---|---|---|---|
| Open application with existing config - UI usable automatically; no surprise listening/upload/live mode | IMPLEMENTED | PASS: isolated Qt auto-controller, view/mic preference fixtures | NOT RUN | NOT MEASURED | Normal shortcut/native first-run onboarding NOT RUN; onboarding incomplete |
| Dashboard/companion switching during a task - One controller, real animated state, focus preserved, Stop available in both views | IMPLEMENTED | PASS: same worker/model, Stop and retained result in both views | NOT RUN | NOT MEASURED | Non-activating flags verified; actual focus/drag/tray/DPI NOT RUN |
| PC-wide scope on an additional approved drive - Relevant requested access works; revocation and protected-target checks are enforced | IMPLEMENTED | PASS: arbitrary selected-root fixture, revocation/category denial and restart | NOT RUN | NOT MEASURED | Fixture uses a disposable local folder, not another physical drive; cross-process revocation unproven |
| One goal across multiple supported applications - Validated output references, correct target focus and verified per-step effects without repeated next prompts | IMPLEMENTED | PASS: actual JSON refs and offline three-step goal through registry | NOT RUN | NOT MEASURED | App/volume/window native effects are fakes; semantic app controls and general replanning incomplete |
| Trusted routine changes its account/target/effect - Old grant cannot authorize changed scope; consequential actions await fresh approval | IMPLEMENTED (partial) | PASS: changed roots, app catalog, mode and categories invalidate reviewed routine | NOT RUN | NOT MEASURED | Account/effect workflows outside local allowlist NOT IMPLEMENTED; no account review is claimed |
| "Don't set volume to 100" / quoted/conditional command - No volume effect and no cloud fallback that disregards negation | FIXTURE_VERIFIED | PASS: router/controller no action or cloud fallback | NOT RUN | NOT MEASURED | Actual desktop volume effect was never invoked |
| Negative, decimal, out-of-range or mixed quantities - Defined validation/clarification; no silent sign/decimal loss | FIXTURE_VERIFIED | PASS: strict integral 0-100 parsing; no invalid partial compound effect | NOT RUN | NOT MEASURED | Decimal semantics deliberately rejected; ASR uncertainty remains |
| "Set volume to 50 and brightness to 20" - Both intended steps or a clear clarification; no silent partial execution | FIXTURE_VERIFIED | PASS: exact volume 50 and brightness 20 both execute via production controller with fake native effects | NOT RUN | NOT MEASURED | Real audio/display effects NOT RUN |
| Repeated pause/mute/unmute - Absolute desired state where supported; never a mislabeled toggle | IMPLEMENTED (partial) | PASS: mute/unmute idempotence; pause fails explicitly rather than toggling | NOT RUN | NOT MEASURED | Absolute selected-session play/pause NOT IMPLEMENTED |
| Offline: volume 35, brightness change, pause media, open Notepad - Deterministic local path; no cloud/Ollama dependency; verify effect where supported | IMPLEMENTED (partial) | PASS: deterministic local controls and selected-window three-step goal with fake adapters | NOT RUN | NOT MEASURED | Absolute pause unsupported; voice and real devices NOT RUN |
| Say a tested English/Hinglish variation - Correct local action or brief clarification; no dangerous guessing | FIXTURE_VERIFIED | PASS: existing English/Hinglish local corpus | NOT RUN | NOT MEASURED | Real microphone/recognition accuracy NOT RUN |
| "Okay, Aeris, open YouTube" via hands-free and text - Consistent addressed-speech handling with no false wake matches | IMPLEMENTED | PASS: shared configured addressed-speech grammar and text/PTT fixtures | NOT RUN | NOT MEASURED | Trained wake detector/multi-alias onboarding NOT IMPLEMENTED; real ASR NOT RUN |
| Stop during TTS, model load, code generation, download, package work - Honest acknowledgment and bounded cleanup; no unpublished late write | IMPLEMENTED | PASS: owned speech/Qt cancellation, native subprocess descendants, generation/download/package mocks | NOT RUN | NOT MEASURED | Acoustic interruption, actual SAPI/UAC/network/model quiescence NOT RUN; native waits remain |
| Stop during existing-file patch final checks - No publication after cancellation wins the commit gate | FIXTURE_VERIFIED | PASS: real registry cancellation during final existing-file checks keeps original bytes | NOT RUN | NOT MEASURED | Hostile external filesystem races not fully closed |
| Stop after a write/install may have occurred - Retained artifact/uncertain effect remains visible; stale speech suppressed | FIXTURE_VERIFIED | PASS: retained patch/copy/download/batch/typing receipts and no stale task speech | NOT RUN | NOT MEASURED | Real install/send uncertainty untested; all secondary storage-failure paths need further audit |
| Follow-up: "make it 40" - Bound to the recent correct task; expired/ambiguous context asks for clarification | FIXTURE_VERIFIED | PASS: recent successful absolute control context and expiry | NOT RUN | NOT MEASURED | Generic observed-choice/project follow-ups NOT IMPLEMENTED |
| Screen help with no prior scope - Selector and preview; no capture/upload before approval | MISSING | NOT IMPLEMENTED end-to-end | NOT RUN | NOT MEASURED | Selected-window/region selector, crop/redaction/preview and sharing workflow missing; no-scope path fails closed |
| Model/CLI JSON region array - Strictly validated compatible scope, not tuple_type failure | FIXTURE_VERIFIED | PASS: serialized JSON region array through strict registry | NOT RUN | NOT MEASURED | No capture/upload or device interaction performed |
| Screen help after changing region/window - Fresh scope approval; old tool-name grant cannot authorize it | IMPLEMENTED (partial) | PASS: exact region fingerprint/expiry denies changed supplied scope | NOT RUN | NOT MEASURED | Selected window/DPI/destination UI and observation freshness NOT IMPLEMENTED |
| Browser fixture with moving/replaced target - Reobserve/reauthorize; do not act on same-URL stale approval | MISSING | NOT IMPLEMENTED end-to-end | NOT RUN | NOT MEASURED | Same-URL DOM identity, changed-target reauthorization and peer enforcement unfinished |
| Two-step browser/download task - Consume actual outputs and verify final artifact; never guess URL/path | IMPLEMENTED (foundation) | PASS: generic declared-output dependency fixture; browser/download end-to-end NOT IMPLEMENTED | NOT RUN | NOT MEASURED | Actual observed browser/download producer-consumer and local DOM/HTTP acceptance remain |
| Find and install a test package - Preview exact package, honor UAC, verify actual presence; automated tests are mocks | IMPLEMENTED (partial) | PASS: existing fake owned process/presence/cancellation fixtures | NOT RUN | NOT MEASURED | Exact observed version/publisher/hash/signer/install plan incomplete; real UAC/install NOT RUN |
| Generate/repair fixture project - Staged validated diff/project, safe commit, optional authorized checks, explicit Undo | IMPLEMENTED (partial) | PASS: existing generated/single-file fixture and commit cancellation | NOT RUN | NOT MEASURED | Multi-file diff/check authorization/transactional Undo/project continuation NOT IMPLEMENTED |
| Organize fixture Downloads - Preview and approved move plan, collision handling, Undo without overwriting newer edits | IMPLEMENTED | PASS: one reviewed hash/identity-bound batch, collision/changed bytes, Stop receipts and newer-edit-safe Undo | NOT RUN | NOT MEASURED | Windows hard links; disposable temp folder only; actual Downloads/additional-drive test NOT RUN; no full atomic rollback |
| Reminder across app restart/sleep - Durable local event, no duplicate notification, explicit overdue behavior | IMPLEMENTED | PASS: durable local/fake-clock restart/overdue/recurrence/duplicate-claim and Qt notices | NOT RUN | NOT MEASURED | Needs running LIVE app; broad DST/crash/sleep/closed-app delivery unproven |
| Run study-mode routine - Authorized bounded low-risk steps, progress, Stop and error recovery | IMPLEMENTED (local subset) | PASS: Qt review/save/run/disable; app/control/reminder through one executor | NOT RUN | NOT MEASURED | Configured project/meeting/coding templates, automatic triggers and real voice/app checks unfinished |
| Daily Brief with fake email/calendar - Summarize fetched records with provenance; drafts never auto-send | IMPLEMENTED (partial) | PASS: fetched fake Gmail/Calendar provenance and local reminders; no send | NOT RUN | NOT MEASURED | Account identity/setup, rich project agenda and reviewable reply drafts incomplete |
| Deny/cancel/stale approval - No provider call, write, capture, or external action under denied scope | IMPLEMENTED | PASS: exact scope/cancel/expired approval, cloud no-call, category denial before preparation and stale target fixtures | NOT RUN | NOT MEASURED | Full account/browser/screen observation boundaries unfinished |
| Credential store unavailable or settings invalid - Clear recovery, no plaintext fallback, no silent live mode | FIXTURE_VERIFIED | PASS: keyring/env/recovery journal and safe current/restart/CLI paths | NOT RUN | NOT MEASURED | Actual credential backend failure NOT induced; malformed new-store recovery needs more work |
| Close/reopen during busy work - Responsive lifecycle, no orphan workers/processes or stale effects | IMPLEMENTED | PASS: owned Qt workers, async settings/cleanup, shared companion/controller and local restore socket | NOT RUN | NOT MEASURED | Native focus/tray/session stress and cold-ASR lifecycle NOT RUN |
| Cleanup failure / keyring unavailable / interrupted settings save - Usable retry/recovery, preserved data and effective configuration | FIXTURE_VERIFIED | PASS: explicit cleanup Retry, provider/TTS ownership, credential rollback and preserved settings fixtures | NOT RUN | NOT MEASURED | Real COM/native stress NOT RUN; cross-process settings/full power-loss durability unproven |
| Built-in System Health and Network Test - Available deterministic workflows without needing a model to invent tools | FIXTURE_VERIFIED | PASS: deterministic routes; explicit network denial/cancel and fake bounded probe | NOT RUN | NOT MEASURED | No actual remote probe performed |
| Reply-only explanation versus failed planner in CLI - Correct distinct structured status and exit code | FIXTURE_VERIFIED | PASS: actual CLI structured success/failure exit behavior | NOT RUN | NOT MEASURED | No real provider request performed |
| Optional specialist app absent/present - Honest readiness, supported typed actions and separate real-app acceptance | MISSING | NOT IMPLEMENTED specialist workflows; catalogs only launch apps | NOT RUN | NOT MEASURED | Typed/versioned Office/Blender/Resolve/FL/ML/Git adapters incomplete; real apps/SDKs NOT RUN |
| Frozen app from another cwd - Launch/resources/settings work; optional unavailable services degrade clearly | MISSING | NOT IMPLEMENTED frozen executable; wheel import/resource check PASS | NOT RUN | NOT MEASURED | PyInstaller absent; pinned freeze/resources/native imports/clean-account acceptance incomplete |

## Remaining release and workflow limits

All eleven phases remain in REQUIREMENTS_TRACEABILITY. Selected-screen preview/watch, semantic
UI Automation/guarded visual control, browser DOM/peer enforcement, immutable installer approval,
account-specific Gmail drafts/OAuth, voice onboarding/device/acoustic interruption, multi-file
coding/checks/Undo, broader projects/routine triggers, specialist adapters, unified locks and a
verified frozen executable remain unfinished code. Native microphone/SAPI, actual user apps,
physical additional drive/DPI/focus, OAuth and UAC are separate supervised checks after code exists.
No whole phase or full master-prompt completion is claimed. Exact next work: CONTINUATION.

References consulted for adapter decisions: [Qt tray](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QSystemTrayIcon.html),
[Qt local server](https://doc.qt.io/qtforpython-6/PySide6/QtNetwork/QLocalServer.html),
[RegisterHotKey](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey),
[ShowWindowAsync](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-showwindowasync).
These document APIs, not this device's successful effects. Previous reports remain in history/.
