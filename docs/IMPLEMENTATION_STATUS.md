# Aeris Implementation Status — 12 October 2026

## Native-cancellation / Qt-lifecycle continuation (newest evidence)

Checkout still HEAD `6b22de3d6624ea2ad5aa58de0cc0edc00ff1907d`, same branch/root/interpreter.
Previous uncommitted increment preserved. Baseline 161 passed/1 skipped. Three new regressions
failed before repair: tokenless winget, tokenless Defender, process-exit-only install success.

- **Implemented / fixture verified:** common bounded owned-process runner connected to winget,
  Defender and signature inspection; cancellation/deadline/output-limit/reaping tests using harmless
  Python child processes; no real software installs. Detached/elevated children remain outside a
  guaranteed ownership boundary. Install interruption is uncertain, no blind retry.
- **Implemented / fixture verified:** install exit is followed by exact package-list observation;
  missing presence fails `installation_unverified`. Table parsing is conservative, not version proof.
- **Implemented:** installer scan-unavailable/error/cancel fails closed; token checks before launch.
  Approved hash/signer binding and file-identity race protection remain incomplete.
- **Implemented / Qt fixture verified:** async settings apply; adapters prepare before save/effective
  publish; failed catalog preparation leaves previous executor/settings; async one-owned close cleanup;
  shutdown waits are not on GUI thread. Failure retains window. No unsafe QThread termination.
- **Implemented / fixture verified:** 30-second ephemeral absolute-control follow-up; no model call
  for missing/expired/invalid context. Intervening task/mode change/cancel clears reference.
- **Implemented:** separate task Stop, microphone mute, Emergency Stop with explicit resume;
  task cancellation no longer writes a mismatching global kill flag into app_store.

Final regression: **172 passed, 1 skipped**, 173 collected. Ruff/compileall/diff check passed.
Real microphone, UI desktop effects, UAC/account/browser and frozen executable are NOT RUN.
All broader incomplete phases above/below remain incomplete. Do not read historical statements
about blocking GUI settings as current: those specific waits are now moved off the event loop.

Next priorities: cancellable DNS/socket transport and owned Windows Job Objects where practical;
scoped installer hash/signature approval; explicit cached-ASR setup/interruption; typed observations
and selected-screen preview; durable reminders/routines/project repair Undo; reviewed release build.

## Follow-on increment against 6b22de3 (current; supersedes conflicting history)

Starting checkout clean, branch `fix/responsive-aeris-desktop`; existing Windows Python 3.11.9 interpreter retained.
Six confirmed failing reproductions were created before changes. All are repaired with fixture evidence.

| Phase | Current narrower status |
|---|---|
| 1 Reliability/privacy | PARTIAL, fixture verified: generation/repair/staging cancellation, atomic publication gate, deadline support, honest post-publication result; exact expiring SESSION scope, stale confirmation invalidation, global Stop preserved through settings and blocks planner entry; strict saved types/recovery banner, metadata-only audit and separate coding cloud consent |
| 2 Voice | PARTIAL: useful native import failure, verified-result speech. Acoustic interruption, cached-model onboarding/VAD and short-lived follow-up remain incomplete |
| 3 Executor | INCOMPLETE: existing sequential failure blocking remains; no typed observation references/dependency controller |
| 4 Screen/apps | INCOMPLETE: no-scope guard preserved; no connected selector/preview/UIA/watch |
| 5 Browser/packages | INCOMPLETE: native blocking calls, peer DNS enforcement, DOM-bound target authorization and verified package presence remain |
| 6 Coding | PARTIAL: cancellation-before-publication fixed; syntax-only validation remains. No multi-file diff/check/Undo workflow |
| 7 Daily work | PARTIAL: bounded authorized Calendar/Gmail Daily Brief connected to shortcut/text and local rendering; local history inspect/correct/forget tab. Durable facts/reminders/routines/project continuation remain incomplete |
| 8 UI | PARTIAL: real Qt memory controls and structured outcome speech. Settings/close cleanup still needs off-GUI lifecycle work; no tray/character/companion |
| 9 Performance | 30 warm simulated production-controller trials recorded; not voice/device latency |
| 10 CI/release | Ubuntu audio dependency and independent lint job implemented; remote run not performed. PyInstaller absent, no executable built |

### Exact next implementation checklist (not external blockers)
1. Owned cancellable subprocess adapter for winget/Defender; bounded streaming downloads; honest uncertain installation status.
2. Off-GUI staged adapter/settings replacement and idempotent asynchronous shutdown; recovery for credential-store failure before window construction.
3. Explicit cached-ASR first-use consent/readiness, interruption design and synthetic endpointing/follow-up tests.
4. Typed observed step references/postconditions, bounded replan, screen selector/preview and transport-enforced browser restrictions.
5. Durable timezone reminders/routines/projects plus transactional multi-file repair/Undo and account-specific Daily Brief readiness.
6. Tray/companion/accessibility, maintained portable lock strategy, reviewed pinned packaging and clean-account frozen acceptance.

No runtime memory, credentials, mail or browser profiles were read. No installs, real sends, desktop effects,
model downloads, hidden commits or branch changes. Google generation can still wait for its existing 30-second
HTTP timeout; checks prevent late publication, not instantaneous network quiescence.

## Current verified status (supersedes the legacy checklist below)

This is a foundation repair increment, **not completion of the personal Jarvis mission**.
Repository root: `C:\AI Related project BY AI\AERIS_AI_ASSISTANT\Aeris`.
Starting commit: `bec9ca9b37c67a80b7f0d35bd70b012b4ed726fc`; clean starting worktree.
No repository reset, runtime-data deletion, credential readout, hidden commit or personal-device action was used.

| Requested checkpoint | Status and evidence |
|---|---|
| 1 Baseline | COMPLETE for local audit: Python 3.11.9, Windows build 26200; 96 passed/1 failed baseline after preload fixture hygiene; eight new failing reproductions |
| 2 Foundation | PARTIAL: tested memory migration/privacy, canonical arguments, executor settings, credential adapter, fail-fast plans, result renderers, browser startup failures, coding patch hashes/confinement, Qt cancellation/close and speech ownership |
| 3 Connected voice | PARTIAL: GUI response-to-speech, transcript/busy feedback, boundary activation, push-to-talk, mute controls; real audio quality, activation/VAD strategy, background preload readiness and follow-up binding remain incomplete |
| 4 Task/screen | INCOMPLETE: sequential failure blocking; no typed dependency graph, postcondition/replan controller, selected-window preview, UIA adapters or watch workflow |
| 5 Personal assistance | INCOMPLETE: memory inspection/correction/forget/export/retention APIs exist; durable reminders, routines, project-continuation UI and retrieved Daily Brief are not implemented |
| 6 Presence/UI | INCOMPLETE: existing Qt dashboard extended, no companion/animated character/tray/onboarding/global shortcut or DPI acceptance |
| 7 Release | INCOMPLETE: module diagnostics and frozen source entrypoint repaired; no built or launched executable; PyInstaller absent |

### Safety limitations that must remain visible

- Screen requests without an explicit region now fail closed. There is no connected crop/preview UI yet.
- Background screen monitoring is unavailable pending persistent selected-window sharing scope; it must not silently upload all screens.
- Browser click/fill require confirmation and the observed URL. URL identity is not full DOM identity; same-URL DOM mutation and semantic effect classification still need coverage.
- Browser wildcard blocks literal private addresses/local names but **does not yet validate DNS-resolved addresses**. Browser network policy is not a complete SSRF boundary.
- Settings are applied only between assistant tasks; voice restarts after capture cleanup. OS credential backend failures produce errors rather than plaintext fallback. Malformed JSON fails closed, but invalid typed saved values need a more complete recovery UI.
- Local-only history is excluded from cloud planner payloads. Current flexible cloud requests require explicit approval; explicit SHAREABLE rows are bounded. This does not yet provide a complete attachment/file-context sharing manager.
- Coding applies one unique UTF-8 patch with an expected hash and atomic replacement. Multi-file transactions, encoding detection, rollback/Undo and race-resistant file handles remain incomplete.
- Stop cancels task tokens, approvals, pending commands and speech. Some native handlers still have bounded blocking calls without cooperative cancellation. Quiescence is not the same as acknowledgment.
- Hands-free activation remains full transcription with addressed phrase matching, not a trained wake engine; audio must be tested on speakers before claiming reliable self-trigger prevention.

See `VALIDATION_REPORT.md`, `PERFORMANCE.md` and `CAPABILITY_MATRIX.md` for narrower evidence.

## Historical checklist — claims below were not sufficient acceptance evidence

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
