# Validation report — 12 October 2026

## Scope/environment

Actual nested Git root confirmed with `git rev-parse --show-toplevel`; starting commit
`bec9ca9b37c67a80b7f0d35bd70b012b4ed726fc`. Initial status clean. No AGENTS.md files found under the workspace/project.
Existing interpreter: `C:\AI Related project BY AI\AERIS_AI_ASSISTANT\Aeris\.venv\Scripts\python.exe`.
Python 3.11.9 / Windows `10.0.26200`; Intel i7-13650HX, 14 cores/20 logical processors,
25,534,783,488 bytes installed RAM. Pydantic 2.13.5, Qt/PySide6 6.11.2, pytest 9.1.1.
Tests used temporary runtime data, fake providers/audio/browser/credential adapters, and Qt offscreen widgets.
No real mail, install, cloud request, microphone capture or volume/brightness change was performed.

## Baseline and reproductions

- Read dependency/setup/build files, CLI, desktop/voice/TTS paths, assistant routing, permission/registry boundary, memory/audit, schemas, browser, coding, both planners and existing tests.
- Production path: desktop bounded queue -> assistant local route -> optional planner -> registry validation -> PermissionEngine -> handler -> ActionResult renderer -> Qt transcript -> speech owner.
- Original voice preload test could load/download a real model. Mocked its loader before baseline execution; no test exclusion was used.
- Baseline: **97 collected, 96 passed, 1 failed**, 4.12 s; Ruff passed.
  `test_voice_silence_detection` failed after cancellation during first optional imports was cleared by capture startup.
- Added eight foundation reproductions: **8 failed**, 0.30 s before repair.

| Issue | Reproduction / changed files | Automated evidence | Real Windows acceptance |
|---|---|---|---|
| Duplicate memory startup / repeated commands | Legacy duplicate roles/timestamps; memory.py | Repeated initialization preserves ordered rows; repeated content retained | SQLite exercised on Windows temp files, not user's DB |
| Sensitive persistence | Unique marker raw SQL read; memory.py | SENSITIVE/DO_NOT_STORE omitted on add | Existing historical sensitive rows preserved, not automatically deleted |
| Cloud history leak / current request consent | assistant.py, memory.py | Actual fake Gemini generate_content serialization excludes private markers; denial invokes no provider | Live provider/account not tested |
| Effective mode / CLI | config.py, cli.py, assistant.py, desktop.py | Save/reload, explicit --live/--simulate, fixture side effect after settings apply | Effective label asserted in real Qt widgets |
| Plaintext credentials | secrets.py/config.py | Fake credential store migration/removal; no marker in JSON | Actual Windows Credential Manager writes not tested |
| Validation/approval | schemas.py/registry.py | Boolean volume rejection, JSON URL/default serialization, changed approval arguments cannot execute | Consequential real actions not used |
| Plans and visible results | planning.py, both planners, assistant.py | Oversized/malformed/unknown actions reject; calendar selection/fallback; required failure halts; three renderers | Provider planning only fixture-tested |
| Browser startup hangs | browser_advanced.py | Startup crash returns useful error in <1 s; exact/subdomain/port/local rules | No Chromium launch/navigation acceptance yet |
| File search/patch | coding.py | Hash/empty/ambiguous/stale patch checks; CRLF preserved; bounded search implementation | Symlink test skipped: Developer Mode/elevation unavailable; Windows junction fixture passed; TOCTOU not covered |
| Voice cancellation/test hygiene | voice.py/test_voice.py | Cancel-before-start, capture cancellation; preload mocked; CUDA generator failure retries once on CPU int8 | Audio device/quality unavailable as acceptance evidence |
| Worker lifecycle | desktop.py | Real Qt event loop: queue-full, stale approval, Stop wait release, simulated text command, clean close | Offscreen, not global shortcuts/tray/interactive hardware |
| TTS ownership | tts_worker.py | Engine/COM fixture verifies operations all on owner thread | Installed SAPI voice playback/Stop latency not tested |
| Release entrypoint | cli.py, diagnostics.py, BUILD_AERIS.bat, run_aeris.py | --help and --self-test checked from another cwd; no pytest invocation in diagnostics | Build not run: PyInstaller absent; executable launch not verified |
| Windows resource cleanup | memory.py | First benchmark failed with WinError 32 from open SQLite connections; explicit close fixed; benchmark rerun succeeded | Real Windows file handles exercised |
| Screen upload scope | screen_vision.py/schemas.py | No-key guard retained; explicit region required, monitor fails closed | Selected-window/crop/preview not implemented, A4 not ready |

## Final checks (update if further edits change results)

- `python -m pytest -ra`: **143 collected, 142 passed, 1 skipped**, 1.83 s at the final regression run.
- Skip: `test_search_symlink_outside_workspace_is_not_read` — Windows symlink creation requires Developer Mode or elevation.
- `python -m ruff check .`: passed.
- `git diff --check`: passed (Git reports LF/CRLF normalization warnings only).
- `python -m aeris --help`: confirms --simulate / --live / --self-test; no --benchmark advertised.
- `python -m aeris --self-test` from `%TEMP%`: local route/catalog/package presence passed; no models/devices/network inspected.
- `scripts/measure_local.py`: 30 warm controller trials, no failures; raw samples in `evidence/local-warm.json`.
- `scripts/capture_fixture_ui.py`: real Qt widgets screenshot in `evidence/desktop-fixture.png`;
  inspected after loading installed Windows fonts. The offscreen plugin printed harmless font-directory/size-hint warnings.
  Screenshot shows simulation result, effective mode, model-not-loaded status, text input, Stop and voice controls.
  It is **not a screenshot of a successful real microphone or live Notepad action**.
- New CI definitions provided, not executed remotely in this session.

## Remaining acceptance: do not equate incomplete work with an external blocker

A1–A3/A11: real desktop/microphone/SAPI interaction requires interactive human acceptance; first-use onboarding,
VAD activation, quiet playback capture, full adapter cancellation and tray remain implementation work.
A4: blocked by missing crop/preview/window scope implementation, not by an account alone.
A5: browser runtime/local fixture acceptance not performed; DNS/private-network and DOM identity work remains.
A6: staged diff/check/Undo production workflow not implemented; single-file patch guard only.
A7–A8: durable project records UI, reminders and routines incomplete.
A9: no designated accounts were configured; Daily Brief retrieval/draft follow-up workflow also incomplete.
A10: existing download/package tests retained; cancellation/installer completion acceptance remains.
A12: PyInstaller not installed in existing project environment; build/frozen-launch verification outstanding.

### Simple remaining user-device checks (only after associated implementation is ready)

1. Open START_AERIS.bat; verify SIMULATION, type `open notepad`, and confirm wording says “would execute”.
2. Enable hands-free intentionally in Settings; use a harmless addressed phrase and verify Heard transcript.
3. Use push-to-talk/mute/Stop; test actual voice playback, speakers self-trigger prevention, unplug recovery and close/reopen.
4. Enable LIVE only intentionally; verify harmless Notepad launch and denial/cancel separately.
5. Do not use screen monitoring or sensitive browser automation as finished workflows yet.
6. Install packaging tooling through a reviewed/pinned release setup, build, then launch from a clean Windows account/different cwd.