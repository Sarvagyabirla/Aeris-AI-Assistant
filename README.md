# Aeris — Windows personal assistant (active development)

### Current continuation increment

Owned winget, Defender and signature-check processes now support token cancellation, bounded
output and deadlines. Detached/elevated installers are **not** guaranteed to stop; interrupted
installation state is uncertain and must be inspected before retrying. Package install success
requires a separate exact package-list observation; version/publisher checks remain incomplete.
Installer files fail closed unless Defender scanning completes. Downloads preserve/report artifacts
if cancellation arrives after publication; socket/DNS waits remain bounded but not instantly cancellable.

Settings adapters are prepared before effective publication and applied on a GUI-owned background
worker. Close cleanup also runs off the Qt event loop, once; a failed cleanup retains the window
instead of destroying live workers. Rapid voice restart callbacks are generation-guarded.

`make it 40` works for a recent successful absolute volume/brightness command for 30 seconds,
with unchanged simulation mode. Expired/intervening context asks which control; no generic `yes`
authorizes actions. Stop cancels a task; **Emergency Stop** blocks future tasks until `resume Aeris`.
Microphone mute remains separate. These workflows are fixture verified, not real-device certified.

One Python/PySide6 project. Daily launcher: **START_AERIS.bat**.

## Verified status — 12 October 2026

Current reviewed baseline: `6b22de3d6624ea2ad5aa58de0cc0edc00ff1907d`.
New increment adds cancellation checkpoints/atomic project publication, expiring exact-scope grants,
preserved global Stop across settings, typed saved-settings recovery, metadata-only audit defaults,
and native PortAudio failure recovery. CI now installs Ubuntu PortAudio with a separate lint job;
remote CI has not been rerun in this local session.

Daily Brief now retrieves up to five authorized upcoming events and five recent email metadata
records through the normal registry, without an LLM or sending. Simulation does not fetch.
It displays source timestamps verbatim (including offsets), not a timezone-converted all-day agenda.
The Local memory tab explicitly inspects, corrects and forgets recent conversation records.
It is not yet a durable project-fact/reminder manager. GUI speech uses tool outcomes, not planner promises.

The current increment repairs foundation defects and connects existing desktop voice/result paths.
It is **not yet the completed personal Jarvis application**. Do not treat registered tools as device verification.
See `docs/IMPLEMENTATION_STATUS.md`, `docs/VALIDATION_REPORT.md`, `docs/CAPABILITY_MATRIX.md`
and `docs/PERFORMANCE.md` for implemented versus incomplete work.

Verified with temporary data/fake adapters: duplicate-history migration, sensitive omission,
cloud serialization privacy, effective executor settings, secure credential adapter/removal,
strict arguments/canonical approval, failed-step blocking, browser startup error propagation,
bounded coding search/hash-checked single-file patches, Qt command/cancellation/close flow and TTS thread ownership.
Real microphone, installed voice, app/device effects, OAuth accounts and packaged executable still require acceptance.

The interface is the existing native Qt dashboard with Settings, shortcuts, text input, Stop,
effective simulation/live label, transcript, push-to-talk and mute controls. No holographic character,
companion overlay, tray service, trained wake model or verified voice barge-in is advertised.

## Install and daily use

Use Python 3.11 on Windows. Double-click SETUP_AERIS.bat for the full optional Windows setup;
its PowerShell script installs requirements-lock.txt then the project with --no-deps, checks native
exit codes, installs Chromium and runs developer tests. Preserve your existing .env and runtime data.

Double-click START_AERIS.bat for daily use. Start in **SIMULATION**: results say “would execute”
and must not be interpreted as actual PC changes. Enable live mode deliberately in Settings only
after harmless acceptance checks. Saved mode is restored unless an explicit CLI flag overrides it.

Hands-free defaults off in new configs/.env.example. Enable intentionally after microphone/model setup.
Existing saved preferences are retained. Push-to-talk is available. The current activation implementation
transcribes audio and checks an addressed phrase at word boundaries; it is not a dedicated wake detector.
Whisper may download its model on first actual voice use. Offline ASR requires cached assets.

## Settings/privacy

- Precedence: explicit CLI mode > saved settings > environment > defaults.
- Settings apply between assistant tasks. If busy, finish/Stop first. Voice restarts after capture cleanup.
- New API keys are saved using the optional OS keyring backend, never settings JSON. Legacy JSON keys
  migrate after a successful credential-store write. Clearing removes the stored key and blocks environment fallback.
  Credential backend errors are surfaced; legacy secrets are not deleted if migration fails.
- .env remains a user-managed plaintext configuration source; do not commit it. Prefer masked Settings for new keys.
- Settings are atomically replaced. Malformed JSON disables file access/listening and enables simulation with a warning.
- Repeated conversation text is retained as separate messages. New SENSITIVE/DO_NOT_STORE content is not persisted.
  LOCAL_ONLY history is never included in cloud planner context. Only bounded explicit SHAREABLE records are included.
- Flexible cloud requests require an exact current-request sharing decision before the provider call.
  Files/screens have separate permissions; a configured API key is not universal upload consent.
- Local memory supports inspect/correct/forget; export/retention UI and reminders remain pending.
- Screen capture without explicit region fails closed. Screen monitoring is unavailable until safe preview/scope UI exists.
- Browser click/fill require confirmation and observed URL. DNS-resolved private-network defense and same-URL
  DOM target identity remain unfinished; do not use this as a secure unattended consequential automation service.

## PowerShell checks

```powershell
Set-Location 'C:\AI Related project BY AI\AERIS_AI_ASSISTANT\Aeris'
& '.\.venv\Scripts\python.exe' -m aeris --help
& '.\.venv\Scripts\python.exe' -m aeris --self-test
& '.\.venv\Scripts\python.exe' -m aeris --no-ai --simulate --once 'open notepad'
& '.\.venv\Scripts\python.exe' -m pytest -ra
& '.\.venv\Scripts\python.exe' -m ruff check .
```

`--self-test` checks offline package/catalog/local-route presence without models, accounts, devices,
network or pytest. It is not hardware acceptance. `--live` and `--simulate` are mutually exclusive
intentional overrides. No --benchmark flag is advertised; the isolated measurement script is
`scripts/measure_local.py`. Developer tests mock model loading and do not download ASR assets.

Base text use needs only base dependencies (`python -m pip install -e .`); optional services report setup errors.
Qt tests require the UI extra, and audio-adapter tests require sounddevice. Those dependencies are explicitly
skipped when absent rather than blanket voice-test exclusion. Portable controller tests remain runnable.

## Build/release

BUILD_AERIS.bat now runs `python -m aeris --self-test`, developer tests, and packages run_aeris.py
instead of executing a relative-import package file. Catalog defaults resolve relative to source/frozen resources,
not caller cwd; writable data lives in LOCALAPPDATA\Aeris (or AERIS_DATA_DIR), not the install folder.
The build still needs a reviewed pinned PyInstaller installation and clean Windows executable acceptance.
No verified executable is supplied by this increment. Source packaging command success alone is not release readiness.

## Troubleshooting

- Busy settings/commands: finish the current task or press Stop, then retry; voice rejection is shown.
- Voice unavailable/model not loaded: use text, check device permissions and optional packages; toggle listening/restart capture.
- Credentials unavailable: configure a supported keyring backend; Aeris will not fall back to plaintext settings.
- Malformed settings: preserve/repair settings.json; file access is disabled until trusted paths are configured.
- Browser unavailable: install the browser extra and its Chromium runtime; waits now fail usefully rather than hang indefinitely.
- Screen scope required: selected-region/crop workflow is unfinished; do not bypass the guard.
- Patch rejected: use a fresh exact-byte SHA256 and a nonempty unique match; no hidden overwrite/commit/push occurs.
- Reminders require implementation, not merely leaving the app open. Daily Brief retrieves bounded event/mail metadata;
  local reminders, account display, conversational drafts and rich summaries remain incomplete.

Gmail OAuth setup remains documented in `docs/GMAIL_SETUP.md`. Use designated test accounts for acceptance;
never send to real contacts as an automated test. Pending workflows are listed in the status/matrix documents.