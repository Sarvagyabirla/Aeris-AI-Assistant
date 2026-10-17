# Current implementation - 17 October 2026, connected companion increment

Actual Git root: `AERIS_AI_ASSISTANT/Aeris`; branch `fix/responsive-aeris-desktop`; HEAD
`e97687470b46e0c2f9030b331de17df33d9ff903` plus preserved pre-existing and current uncommitted
work. One application and the original launchers/environments remain. No commit, push,
installation, model download, personal-window capture or account/hardware effects were performed.

| Working behavior | Production connection | Evidence and limits |
|---|---|---|
| Original vector humanoid and companion | ui/presence.py, companion.py, desktop.py; launch_desktop | Real shared worker/audio/TTS/permission state; 30 fps cap; reduced/hidden motion; synthetic Qt captures. Physical focus/DPI/tray/hotkeys NOT RUN |
| Typed bounded tasks | tasks.py, assistant.py, registry.py; local text/voice and both planners | Whole-plan preflight, ordered dependencies, declared observed output references, 12-step / 120-second cooperative default budget; actual JSON and registry fixtures. No general replanning or unsupported-app control |
| Real progress and durable receipts | worker task_updated -> dashboard/companion; tasks.db | Completed/uncertain effects survive Stop; safe local receipts; interrupted work is reviewed, never replayed. Native blocking calls and PID reuse remain limitations |
| PC-wide selected roots and category revocation | Permissions tab, ScopePolicy, AccessProfile, shared registry | Arbitrary accessible roots; immediate revocation + persistence; protected targets denied; capability revocation occurs before preparation. Additional physical drive NOT RUN |
| Three modes and local routines | Settings -> PermissionEngine; Tasks & routines -> RoutineStore -> existing executor | Assist preview, automatic low-risk requested tasks, explicitly reviewed local routines; scope/catalog/mode/category changes invalidate review. No account steps, automatic triggers or general macros |
| Document organization and Undo | files.organize / files.undo_organization; Tasks tab and local routes | Single exact hash/identity-bound batch approval, collision rejection, Stop receipts, guarded restore. Windows/hard links; no ACL/ADS preservation; uncertain effects need review; directory races not fully eliminated |
| Exact window operations | selected window -> native ShowWindowAsync/readback and normal WM_CLOSE | Own/stale target denied; minimized/maximized read back; graceful close dispatch is explicitly unverified. Native user-device acceptance NOT RUN |
| Earlier repairs preserved | P0 routing/publication, privacy, credential/provider/TTS ownership, audio, reminders and Job Objects | Full regression suite and real isolated Qt/native-process fixtures; see VALIDATION_REPORT for exact final counts |

The required virtual character and floating view now exist in production code. PC-wide task
automation is a bounded supported subset, not arbitrary control of every installed program.
All 67 registered names are retained (email compatibility alias omitted from planner catalog).
Registration is not readiness. No full phase or full master-prompt completion is claimed.

[Validation](VALIDATION_REPORT.md) records all 35 acceptance scenarios and eight connected
showcases. [Traceability](REQUIREMENTS_TRACEABILITY.md) retains all eleven phases, 60 original
tools and new surfaces. [Continuation](CONTINUATION.md) separates unfinished code from
account/device and frozen-release acceptance. Prior current views are archived in history/.
