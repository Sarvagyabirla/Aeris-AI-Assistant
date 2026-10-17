# AERIS current implementation - 17 October 2026

Current increment fixes the parent-folder launch errors and continues the same Python/PySide6
application. Same nested root/branch/HEAD e97687470b46e0c2f9030b331de17df33d9ff903 plus preserved
uncommitted changes. No commits, pushes, environment replacement or dependency installs.

The application is not the completed fictional Jarvis or the completed eleven-phase roadmap.
[Traceability](REQUIREMENTS_TRACEABILITY.md) retains 119 requirements, 65 tools and 43 production
modules. [Validation](VALIDATION_REPORT.md) records exact evidence and all acceptance scenarios.

| Working increment | Production connection / evidence | Limitation |
|---|---|---|
| Launch from parent folder | START_AERIS.bat / AERIS.bat forward to canonical child RUN_AERIS.bat; correct Python 3.11/cwd; diagnostics/test/lint pass from parent | Parent Python 3.14 environment remains separate; no install or activation needed for these launchers |
| Native process ownership | Existing runner uses suspended Windows child, Job Object assignment before resume, kill-on-close, bounded input/output; harmless real process-tree/cancel fixtures pass | UAC/service-launched effects can escape; portable Windows without extras has weaker ownership |
| Reminders | Text routes and real Qt create/list/snooze/cancel; timezone-aware India schedules; durable due/overdue list; daily/weekly recurrence; two-store claims; restart duplicate suppression; global Stop/simulation pause | Local running-app notices only; no tray/closed-app service; broad NLP/DST acceptance remains |
| Graceful close | One observed window bound to confirmation by HWND/PID/creation time/title; revalidated after approval; sends WM_CLOSE and never terminates matching processes | Close dispatch is not verified closure; app's own unsaved-work prompt remains; full chooser/native app tests pending |
| Brightness | Absolute values read back; relative change keeps each supported display's own starting value; mismatch fails | Hardware support and native latency need supervised acceptance |
| Calendar brief metadata | End/all-day/timezone/source fields retained; all-day exclusive end labelled; late cancelled response discarded | Account identity/setup and rich timezone agenda/drafts remain incomplete |
| Earlier repairs | Unsafe intent/quantities/compounds, patch/note gates, receipts/no stale speech, keyring/env recovery, cleanup Retry, exact expiring grants and /private preserved | Complete external-effect/provider cleanup audit still unfinished |

Current checks: **261 passed, 1 skipped** (final recorded command in VALIDATION_REPORT),
Ruff/compile/offline diagnostics/isolated Qt/package checks. Screenshots at standard sizes and Qt
scale factors are synthetic fixtures, not live hardware acceptance. No frozen executable exists.

Voice currently supports cached assets, push-to-talk and opt-in addressed transcription; dedicated
wake/VAD/device onboarding, reliable echo-safe interruption and absolute selected-session play/pause
remain missing. Typed dependent execution, screen preview/watch, browser peer/DOM enforcement,
installer immutable identity, multi-file Undo, routines/projects, companion/tray/global shortcuts,
account workflows and specialist adapters remain in scope and incomplete. See CONTINUATION.
