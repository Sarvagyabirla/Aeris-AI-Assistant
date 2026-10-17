# AERIS current implementation - 17 October 2026

Current increment continues the same Python/PySide6 application at nested Aeris root,
branch fix/responsive-aeris-desktop, HEAD e97687470b46e0c2f9030b331de17df33d9ff903 plus
preserved uncommitted work. No commits, pushes, installs or environment replacement.

The eleven-phase roadmap remains incomplete. [Traceability](REQUIREMENTS_TRACEABILITY.md)
retains every requirement and tool; [validation](VALIDATION_REPORT.md) separates fixture
results from supervised device/account acceptance. Previous snapshots are in history/.

| Working increment | Production connection and evidence | Remaining boundary |
|---|---|---|
| Exclusive transfers/downloads | files.copy/files.move/downloads.download stage bytes, publish exclusively through Stop gate and retain receipts; Windows holds source/stage identity during move; partial cleanup excludes active/recent files | Hard-link filesystem required; safe move Windows-only; directory/junction revalidation does not prove hostile-parent race immunity; progress/Undo remain missing |
| Unicode typing | Dashboard Select typing window, exact text/window/control confirmation and deliberate refocus; real registry preflight; native UTF-16 scalar dispatch with per-batch identity/focus/Stop checks; partial input receipts | Input delivery is unverified; Windows offers no atomic focus-and-inject API, leaving one scalar race; title-changing apps abort safely; no semantic UI Automation/password-field support |
| Provider lifecycle | Failed retired/staged Gemini/Ollama clients remain owned and retryable; cleanup cannot interrupt an active task; no stale cancelled Ollama response | A synchronous SDK close/read still has its native timeout/quiescence boundary |
| Credential recovery | Secret-free recovery journal before key mutation; failed rollback forces simulation, AI/listening off; restart/CLI --live cannot bypass recovery; successful explicit Settings save resolves it | Concurrent independent settings writers and full power-loss durability are not proven |
| Audio readiness/interruption | Explicit states, shared exact address grammar/custom wake phrase, single capture ownership, bounded 300ms pre-roll, silence skips ASR; passive capture pauses during AERIS speech/global Stop; PTT stops speech before capture; contaminated/late transcripts discarded | Energy endpointing is not a new trained wake/VAD system; microphone/device/download onboarding, global shortcut and real acoustic testing remain |
| Speech cleanup | Failed engine stop/endLoop retains the owner for explicit Retry, reports incomplete cleanup and blocks capture/new speech; COM cleanup is balanced on successful retry | COM release failure itself may be unrecoverable in-process; actual SAPI/native device acceptance NOT RUN |
| Previous increments retained | Correct parent launch/interpreter; Windows Job Objects; connected timezone reminders; exact-window graceful close; per-display brightness readback; calendar metadata; P0 intent/schema/publication/privacy repairs | See full traceability and acceptance matrix |

Final validation: **356 passed, 1 skipped**; Ruff, compile, offline self-test, isolated Qt Stop,
wheel import/resource and source-archive build checks pass. Artifacts are in VALIDATION_REPORT. Source-wheel/import
checks are separate from a frozen release; no verified executable exists. Real microphone,
SAPI, desktop typing, OAuth, browser/account, UAC/install and power checks were not performed.

Typed dependent execution, selected-screen preview/watch, browser DOM/peer enforcement,
immutable installer approval, multi-file coding/Undo, routines/projects, companion/tray/global
shortcuts, account workflows and specialist adapters remain in scope. Exact next steps are in
[CONTINUATION](CONTINUATION.md). No whole phase is claimed complete.
