# Validation report — 12 October 2026

## Native cancellation and Qt lifecycle continuation (latest)

Nested root/HEAD/branch unchanged; pending previous increment retained; no user-data or secret reads.
Baseline rerun: **161 passed, 1 skipped**, 1.87 s; clean Ruff. Same existing Windows Python 3.11.9
environment. Three new native regressions failed before repair (0.24 s) and pass after repair.

| Issue | Production change / deterministic evidence | Real acceptance |
|---|---|---|
| Tokenless winget/Defender | process_runner.py, packages.py, downloads.py; cancelled tokens launch neither; real harmless Python child cancellation/timeout reaped; output capped at 1024 fixture bytes | No winget install or Defender scan run |
| False verified install | Separate winget exact-list observation; fake missing presence returns installation_unverified | Package version/publisher still incomplete; no install |
| Late download publication/scan | Atomic token commit; post-publication cancellation reports retained artifact; scan token passed | Network read/DNS cancellation still incomplete |
| Blocking settings | SettingsApplyWorker; slow fake cleanup/apply runs while Qt pumps; failed catalog preparation preserves old registry/config and no settings write | Supervised settings/credential backend not run |
| Blocking/repeated close cleanup | CleanupWorker owns one cleanup attempt; slow fixture runs off GUI, repeated close does not duplicate; voice restarts invalidated on close | Real cold-ASR and native shutdown not tested |
| Follow-up make it 40 | followup.py + real controller; volume reference/expiry/intervening task/out-of-range/Stop scenarios pass | Real ASR not run; only absolute volume/brightness numeric follow-up |
| Stop contract mismatch | Task cancellation clears task/follow-up; Emergency Stop calls authoritative PermissionEngine and requires resume | UI hardware Stop timing not measured |

Full suite: **173 collected, 172 passed, 1 skipped**, 2.79 s. Skip: Windows symlink privilege
(`test_settings_lifecycle.py:183`); junction fixture retained. Ruff, compileall, git diff --check pass
(LF/CRLF advisories only). Focused native/process/Qt tests: 12 passed in 1.36 s before later tests.
No dependency install, real network/model, device modification, sensitive capture or external send.
Qt/Python/psutil official threading/process references consulted; no new dependency introduced.

Screenshot `evidence/native-lifecycle-desktop.png` is a sanitized real-widget simulation screenshot,
not live device acceptance. 30 warm simulated-controller trials: p50 **5.940 ms**, p95 **7.126 ms**,
0 failures; raw samples `evidence/native-lifecycle-local-warm.json`. Construction single sample 3.789 ms.
This does not measure audible speech, capture, GUI acknowledgment or external task quiescence.

### Acceptance matrix updates (other rows retain the earlier incomplete/not-run status)

| Scenario | Current implementation / fixture | Real device | Timing |
|---|---|---|---|
| Stop during package/scan | Cooperative owned-process boundary PASS; detached installers uncertain | NOT RUN | 20 ms poll interval, cleanup waits bounded in code; no device latency measurement |
| Follow-up make it 40 | Connected absolute-control context PASS | NOT RUN | Not measured |
| Close/reopen busy and settings | Off-GUI owned cleanup/settings slow-fixture PASS; failure keeps window | NOT RUN | Not measured |
| Installer verification | Defender must pass; token checks; package presence observed | NOT RUN | Not measured; exact approved hash/signer incomplete |

Commands: existing interpreter `-m pytest -ra`, `-m ruff check .`, `-m compileall -q aeris`;
`git --no-pager diff --check`; measurement/capture scripts with output destinations above.
No executable build: PyInstaller remains absent; clean-account frozen acceptance incomplete.

## Follow-on local increment (current evidence; preserves earlier report below)

Baseline HEAD `6b22de3d6624ea2ad5aa58de0cc0edc00ff1907d`, branch
`fix/responsive-aeris-desktop`, clean worktree, nested root confirmed with git rev-parse.
No AGENTS.md found in parent/project. Existing `.venv\Scripts\python.exe`: Python 3.11.9,
Windows 10.0.26200, Pydantic 2.13.5, PySide6 6.11.2, pytest 9.1.1, installed Ruff 0.16.5,
google-genai 2.22.0. No dependencies installed or environment replaced.

Baseline: 142 passed, 1 skipped (143 collected), 1.62 seconds; Ruff and offline diagnostics passed.
Six newly added regressions failed before repair in 0.39 seconds:
generation/repair cancelled by model still opened published project (2); changed region/expiry
reused tool-name grant; settings reset global stop; native PortAudio import escaped; arbitrary
private audit markers persisted. These tests use the real registry/controller boundaries and fakes.

| Repair / connected addition | Changed files | Evidence |
|---|---|---|
| Cancellation-before-publication, repair and staging; honest after-publication outcome | coding.py, state.py | Provider cancels during generation/repair: no project/editor; staging removed; post-publish result includes existing artifact; expired deadline blocks commit |
| Exact expiring session capture scope, invalidated confirmation | permissions.py | Region A/B gives two prompts; expiry re-prompts; stop/resume during confirmation denies |
| Global Stop survives settings and blocks planner entry | assistant.py | Real settings apply remains stopped; next local command denied |
| Strict saved types/recovery without deleting original | config.py, desktop.py | Invalid booleans, numeric bool, roots list and device preserved; simulation/AI off/no roots; recovery banner |
| Metadata-only audit | audit.py | Unique private path/result/error/custom markers absent from actual persisted JSONL; safe tool/status retained |
| Separate coding cloud consent | registry.py | Denied sharing invokes no handler/model; explicit preview discloses generation/one repair |
| Broken native audio runtime | voice.py, regression.yml | Injected OSError becomes VoiceUnavailableError; Ubuntu audio job installs libportaudio2; remote CI not run |
| Verified speech summary | models.py, desktop.py | Failure spoken instead of planner promise; simulation speech explicitly says no changes |
| Real Daily Brief retrieval | assistant.py, desktop.py | Two authorized fake adapters return grounded event/mail metadata; denial/simulation fetch nothing; no planner/send path; malicious snippet does not become an action |
| Local conversation view | ui/memory_view.py, desktop.py | Qt event loop inspects and forgets chosen temp record; correction uses existing validated store API |

Final local checks: **162 collected, 161 passed, 1 skipped**, 1.89 seconds. Skip unchanged:
Windows symlink creation needs Developer Mode/elevation (`test_settings_lifecycle.py:172`).
Existing Windows junction fixture passes. No blanket voice exclusion. Ruff and compileall passed;
git diff --check passed apart from LF/CRLF advisory. --help flags unchanged and verified;
--self-test passed from TEMP, without device/account/model/network probing.

30 warm simulated production-controller trials: p50 5.758 ms, p95 6.836 ms, 0 failures.
Raw data: `evidence/phase1-local-warm.json`. Real-widget screenshot generated and visually inspected:
`evidence/phase1-desktop-fixture.png`; SIMULATION, result, controls, Local memory tab visible.
Font/size-hint warnings printed by offscreen Qt, but screenshot rendered legibly.
First benchmark/screenshot invocation omitted required output arguments and failed; rerun with
`--output` / destination succeeded. These invocation failures are not hidden as successful trials.

Official sounddevice installation reference checked: Linux may need separate PortAudio package.
Official Google Gen AI client-lifecycle documentation checked; installed Client.close exists and
generation now closes its client in finally. No model IDs/dependencies replaced.

### Required scenario matrix — current evidence, not a completion claim

Real-device checks below are **NOT RUN: supervised explicit authorization required**. Packaging
also cannot be exercised in the current interpreter without reviewed PyInstaller setup.
Only controller fixture timing is measured; scenario/device timings are NOT MEASURED.

| Scenario | Implementation / fixture result | Real-device result / remaining limitation |
|---|---|---|
| Open existing config | Qt dispatch/close fixture PASS; mode/listening preferences preserved | NOT RUN; full onboarding missing |
| Offline volume/brightness/pause/Notepad | Existing local route fixtures PASS | NOT RUN; media absolute-state/postconditions incomplete |
| English/Hinglish | Existing router fixtures PASS | NOT RUN; confidence/ambiguity ASR incomplete |
| Stop TTS/model/code/download/packages | Code generation/repair/staging + owner-TTS fixtures PASS | NOT RUN; network load/download/winget/scan quiescence remains incomplete |
| Follow-up make it 40 | NOT IMPLEMENTED as task-bound context | NOT RUN |
| Screen no prior scope | Guard PASS, selector/preview NOT IMPLEMENTED | NOT RUN; cannot claim connected screen help |
| Screen changed region/window | Exact-region permission regression PASS | NOT RUN; window identity/preview missing |
| Browser replaced target | Existing URL/uniqueness fixtures only | NOT RUN; same-URL DOM identity incomplete |
| Browser/download prior outputs | Typed output-reference executor NOT IMPLEMENTED | NOT RUN |
| Find/install package | Existing adapter fixtures only | NOT RUN; cancellable owned processes/verified presence incomplete |
| Generate/repair project | Syntax validation + publication cancellation PASS | NOT RUN; transactional diff/authorized checks/Undo incomplete |
| Organize Downloads | Reviewable organization/Undo NOT IMPLEMENTED | NOT RUN |
| Reminder restart/sleep | Durable scheduler NOT IMPLEMENTED | NOT RUN |
| Study routine | Persisted typed routine workflow NOT IMPLEMENTED | NOT RUN |
| Daily Brief fake mail/calendar | Connected bounded metadata retrieval PASS | NOT RUN; reminders/account display/drafts incomplete |
| Deny/cancel/stale approval | Scope/denied-cloud/no-late-publish fixtures PASS | NOT RUN; native adapters not universally cancellable |
| Invalid settings/credentials | Typed recovery + existing fake-keyring tests PASS | NOT RUN; startup credential-failure recovery UI incomplete |
| Close/reopen busy | Existing Qt worker cancellation/close PASS | NOT RUN; settings/cleanup joins need asynchronous redesign |
| Frozen different cwd | Source diagnostics/resources PASS | NOT BUILT: PyInstaller absent; executable acceptance outstanding |

### Commands actually executed

From project root with existing interpreter: `-m pytest -ra`, `-m ruff check .`,
`-m compileall -q aeris`, `-m aeris --help`, `git diff --check`;
`scripts/measure_local.py --trials 30 --output docs/evidence/phase1-local-warm.json`;
`scripts/capture_fixture_ui.py docs/evidence/phase1-desktop-fixture.png`.
From TEMP: absolute interpreter `-m aeris --self-test`.
No real sends, installs, account access, microphone capture, screen capture or device changes.

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