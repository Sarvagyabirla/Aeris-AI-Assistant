# Validation report ? 17 October 2026

Current evidence supersedes [historical reports](history/before-2026-10-17-VALIDATION_REPORT.md). Scope and unfinished work are authoritative in [REQUIREMENTS_TRACEABILITY](REQUIREMENTS_TRACEABILITY.md) and [CONTINUATION](CONTINUATION.md).

Baseline: nested Git root `C:\AI Related project BY AI\AERIS_AI_ASSISTANT\Aeris`; branch `fix/responsive-aeris-desktop`; HEAD `e97687470b46e0c2f9030b331de17df33d9ff903` plus uncommitted changes. Existing assistant/schema/UI/reminder work preserved. No commit/push/branch switch. No AGENTS.md found in project/ancestors.

Windows build 26200, Intel64 Family 6 Model 183 Stepping 1; existing Windows Python 3.11.9, Pydantic 2.13.5, PySide6 6.11.2, pytest 9.1.1. Dependencies were not installed or replaced. PyInstaller/build module absent; wheel/setuptools available.

Baseline full suite: **184 passed, 1 skipped**, 8.56 s. Final full suite: **240 passed, 1 skipped**, 3.45 s. Skip: Windows symlink privilege/Developer Mode in test_settings_lifecycle.py:183; existing Windows junction fixture retained. Ruff passes. No blanket audio/UI test skips were introduced.

| Reproduction against old boundary | Result before repair | Result after repair |
|---|---|---|
| Router non-imperatives/quantities/compound requests; real controller no-provider; patch final resolve; artifact details; real JSON region | 22 failures, 0.37 s | All pass |
| Credential backend/env recovery and real Qt failed cleanup | 7 failures, 25 pass, 0.73 s | All pass |
| Absolute versus toggle controls/COM/readback/cancellation | 9 failures, 1 pass, 0.25 s | All pass; absolute playback remains explicitly unsupported |
| Health/network production shortcut paths | 3 failures, 0.32 s | All pass with fake probe |
| HEAD filesystem source replay in isolated module | 3 failures: competing note overwritten, missing cancellation signatures | Working-tree note/search tests pass |
| First wheel catalog inspection | Both catalogs absent despite build success | Both present; extracted-wheel import/self-test from another cwd exit 0 |

Additional checks: real Qt event-loop receipt/no stale speech, cached-model warmup ownership/Stop, private reply-only omission, settings-save credential rollback, post-replace CRLF retention, payload denial, independent optional imports and unrelated-error propagation. Portable failure reproduced by globally blocking NumPy: corrected PortAudio regression plus independent import test **2 passed**. No microphone/model downloads or devices involved.

Commands used from the nested repository (existing interpreter):

```powershell
& .\.venv\Scripts\python.exe -m pytest -ra --tb=short
& .\.venv\Scripts\python.exe -m ruff check .
& .\.venv\Scripts\python.exe -m compileall -q aeris
& .\.venv\Scripts\python.exe -m aeris --self-test
$env:QT_QPA_PLATFORM='offscreen'
& .\.venv\Scripts\python.exe test_ui_manual.py
& .\.venv\Scripts\python.exe scripts/capture_fixture_ui.py docs/evidence/review-2026-10-17-desktop.png
& .\.venv\Scripts\python.exe scripts/measure_local.py --output docs/evidence/review-2026-10-17-controller.json
& .\.venv\Scripts\python.exe -m pip wheel . --no-deps --no-build-isolation --wheel-dir "$env:TEMP\aeris-review-wheel-20261017"
& .\.venv\Scripts\python.exe scripts/check_wheel.py "$env:TEMP\aeris-review-wheel-20261017\aeris_assistant-1.0.0-py3-none-any.whl"
git diff --check
```

Offline self-test succeeds (package/catalog/local-route presence only). Wheel built without dependency installation; import/resource check used extracted wheel with `python -I`, temporary cwd and no source imports. Final wheel SHA256 `3df3ce61a66a756d1ce0c3bdc6f26ef9c7770d0318213ab3a9fff56b5ad67ed0`; artifact names excluded credentials/settings/databases/private keys. This is **not** a frozen executable or clean-account dependency test. License restored to match existing MIT metadata; dependency redistribution attribution remains a release check.

Sanitized [real-widget screenshot](evidence/review-2026-10-17-desktop.png) visually inspected at 1100x700. It shows simulation, input, Stop, Emergency Stop, Resume and microphone/speech controls. Required resolutions/DPI/keyboard/accessibility matrix NOT RUN.

Performance: 30 warm simulated production-controller trials, no app launch/cloud/audio; construction single sample 9.639 ms; p50 4.973 ms, p95 5.810 ms, routing p95 0.093 ms, zero failures. [Raw trials](evidence/review-2026-10-17-controller.json). These are controller overhead, not voice/device/GUI-acknowledgment latency.

No real mail, runtime memory, keys, browser profiles or sensitive windows were read. Tests used disposable workspaces/fake accounts/providers. No remote connectivity probe, installs, generated-code execution, model downloads, UAC, power action or live audio/desktop-control acceptance was performed. Official sounddevice, faster-whisper, Pycaw and Microsoft COM documentation informed the changed adapters; references are in SECURITY/PERFORMANCE.

## Required end-to-end acceptance matrix

All real-device/account rows: **NOT RUN**, explicit supervision required. NOT IMPLEMENTED describes missing end-to-end code; NOT RUN describes unperformed acceptance. Per-scenario timings are NOT MEASURED; the aggregate controller benchmark above is separate.

| Scenario / requested outcome | Implementation state | Fixture result | Real device/account | Timing | Remaining limitation |
|---|---|---|---|---|---|
| Open application with existing config ? UI usable automatically; no surprise listening/upload/live mode | IMPLEMENTED | PASS: isolated offscreen dashboard/async settings/cache fixtures | NOT RUN | NOT MEASURED | Actual returning-user launch and consent onboarding NOT RUN |
| "Don't set volume to 100" / quoted/conditional command ? No volume effect and no cloud fallback that disregards negation | FIXTURE_VERIFIED | PASS: router/controller no action/provider | NOT RUN | NOT MEASURED | No actual desktop effect invoked |
| Negative, decimal, out-of-range or mixed quantities ? Defined validation/clarification; no silent sign/decimal loss | FIXTURE_VERIFIED | PASS: integral 0?100 grammar; invalid requests clarify | NOT RUN | NOT MEASURED | Decimal semantics deliberately rejected |
| "Set volume to 50 and brightness to 20" ? Both intended steps or a clear clarification; no silent partial execution | FIXTURE_VERIFIED | PASS: entire compound clarifies | NOT RUN | NOT MEASURED | Two-command execution not implemented |
| Repeated pause/mute/unmute ? Absolute desired state where supported; never a mislabeled toggle | IMPLEMENTED | PASS: mute/unmute idempotence; pause never toggles | NOT RUN | NOT MEASURED | Absolute play/pause session missing |
| Offline: volume 35, brightness change, pause media, open Notepad ? Deterministic local path; no cloud/Ollama dependency; verify effect where supported | IMPLEMENTED | PASS: deterministic routing/simulation; volume fake readback | NOT RUN | NOT MEASURED | Pause returns unsupported; real Windows effects not tested |
| Say a tested English/Hinglish variation ? Correct local action or brief clarification; no dangerous guessing | FIXTURE_VERIFIED | PASS: existing English/Hinglish corpus | NOT RUN | NOT MEASURED | ASR language accuracy untested |
| "Okay, Aeris, open YouTube" via hands-free and text ? Consistent addressed-speech handling with no false wake matches | IMPLEMENTED | PASS: greeting extraction/local routing | NOT RUN | NOT MEASURED | Full shared alias catalog and actual hands-free recognition untested |
| Stop during TTS, model load, code generation, download, package work ? Honest acknowledgment and bounded cleanup; no unpublished late write | IMPLEMENTED | PASS: existing generation/process fixtures; Qt cached-load stop blocks capture | NOT RUN | NOT MEASURED | Synchronous load/SDK waits and real audio/network/install quiescence untested |
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
| Reminder across app restart/sleep ? Durable local event, no duplicate notification, explicit overdue behavior | IMPLEMENTED | PASS: pre-existing store fixtures only | NOT RUN | NOT MEASURED | Notification/deterministic routes/scheduler/DST/restart acceptance incomplete |
| Run study-mode routine ? Authorized bounded low-risk steps, progress, Stop and error recovery | MISSING | NOT IMPLEMENTED end-to-end | NOT RUN | NOT MEASURED | Workflow code and fixture acceptance required; see phase ledger |
| Daily Brief with fake email/calendar ? Summarize fetched records with provenance; drafts never auto-send | IMPLEMENTED | PASS: existing fake Gmail/Calendar grounding; reminder count preserved | NOT RUN | NOT MEASURED | Account/end/timezone/project provenance incomplete |
| Deny/cancel/stale approval ? No provider call, write, capture, or external action under denied scope | IMPLEMENTED | PASS: registry/cloud/coding and Qt stale approval regressions | NOT RUN | NOT MEASURED | Full browser/account/window boundaries incomplete |
| Credential store unavailable or settings invalid ? Clear recovery, no plaintext fallback, no silent live mode | FIXTURE_VERIFIED | PASS: keyring failure/env recovery; no env-key bypass | NOT RUN | NOT MEASURED | All malformed paths and backend rollback-failure recovery not tested |
| Close/reopen during busy work ? Responsive lifecycle, no orphan workers/processes or stale effects | IMPLEMENTED | PASS: real Qt async worker cleanup fixtures | NOT RUN | NOT MEASURED | Full reopen/single-instance/device/model stress missing |
| Cleanup failure / keyring unavailable / interrupted settings save ? Usable retry/recovery, preserved data and effective configuration | FIXTURE_VERIFIED | PASS: explicit Retry/keyring recovery/credential rollback | NOT RUN | NOT MEASURED | All native cleanup and rollback-backend failures not tested |
| Built-in System Health and Network Test ? Available deterministic workflows without needing a model to invent tools | FIXTURE_VERIFIED | PASS: deterministic health/status; approved bounded network probe fake | NOT RUN | NOT MEASURED | Real endpoint response not probed |
| Reply-only explanation versus failed planner in CLI ? Correct distinct structured status and exit code | FIXTURE_VERIFIED | PASS: actual CLI return 0 versus failed planner 1 | NOT RUN | NOT MEASURED | No provider request performed |
| Optional specialist app absent/present ? Honest readiness, supported typed actions and separate real-app acceptance | MISSING | NOT IMPLEMENTED: catalogs provide launch only | NOT RUN | NOT MEASURED | Typed specialist adapters/version matrices missing |
| Frozen app from another cwd ? Launch/resources/settings work; optional unavailable services degrade clearly | MISSING | NOT IMPLEMENTED: no frozen executable; wheel import/resources PASS | NOT RUN | NOT MEASURED | PyInstaller absent; pinned build and clean Windows account acceptance required |

Final change scan: 57 changed/untracked text files, zero high-confidence Gemini/GitHub/private-key patterns. Only repository changes were scanned, never user .env/keys/runtime data. This is a targeted pattern check, not a guarantee that all sensitive material can be detected. [Machine-readable evidence and source hashes](evidence/review-2026-10-17-validation.json).
