# Next supervised Windows checks ? 17 October 2026

Do not run installs, real mail sends, power actions, private captures or generated code simply
to fill acceptance rows. Live device/account testing requires explicit supervision. This session
used only disposable fixtures and offscreen Qt.

1. From the parent AERIS_AI_ASSISTANT folder, run .\START_AERIS.bat; no activation is needed. Confirm SIMULATION, a responsive input and microphone state. Type
   `don't set volume to 100`, `set brightness to -10`, `set volume to 35.5`, then
   `set volume to 50 and brightness to 20`: each must clarify without executing anything.
2. Type `set volume to 35`, `make it 40`; both should report simulation. Wait 31 seconds and
   repeat the follow-up: it must ask which control. Check System Health and Network Test:
   simulation does not probe the network; deny any live probe approval.
3. Use Emergency Stop, try `open notepad`, verify blocked, then use Resume. Save simulation
   Settings while stopped and verify the latch persists. Task Stop and microphone mute differ.
4. Inspect/correct/forget a deliberately non-private fixture sentence in Local memory. A request
   prefixed `/private ` must not persist in that view. Close/reopen and check usability.
5. After separate authorization for harmless live controls: record initial volume/mute values,
   set a modest volume, mute twice/unmute twice, compare readback, and restore initial values.
   Pause/play currently explain that a selected-session adapter is missing; they must not toggle.
6. Authorize cached-model microphone/SAPI acceptance separately. No automatic model download
   should occur. Test addressed speech, background noise, TTS self-triggering and Stop during
   load/task/speech, reporting acknowledgment separately from actual cleanup.

Remaining implementation checks precede broader acceptance: screen selector/redaction/preview,
DOM identity/peer enforcement, immutable installer approvals, typed observed dependencies,
multi-file Undo, broad reminder DST/crash-delivery, routines/projects, companion/tray,
account setup and specialist adapters. Required DPI/resolution/keyboard matrix remains pending.
No frozen executable exists; a source wheel check is not clean-account executable acceptance.

Launch diagnostics from the parent folder: `.\AERIS.bat --self-test`, `.\AERIS.bat --test`, `.\AERIS.bat --lint`. They use the child Python 3.11 environment; the parent Python 3.14 environment is not changed.

New supervised reminder check: first inspect the Reminders tab in simulation. After intentionally enabling LIVE for a harmless local reminder, use `remind me in 2 minutes to stretch`, keep Aeris open, verify one generic due notice, then snooze/cancel from the tab. Emergency Stop pauses delivery; Resume makes overdue records eligible. No closed-app service is promised.

Graceful-close acceptance (separate live authorization): create an unsaved disposable Notepad document; preview exactly that window, deny once, then approve a normal close and verify the app retains its save prompt. Never force-kill it as a test. Brightness acceptance should record initial values per supported display, request a modest change, compare readback and restore the original values.

Selected Unicode typing (separate live authorization): open a disposable Notepad document,
focus its text control, choose it with Select typing window, request `type Hello ?????? ??`,
review exact text and target, approve deliberate refocus and inspect actual insertion. Deny
once, switch focus during a longer harmless request and verify abort, then inspect the retained
character/event count before retrying. Title-changing applications may abort after the first edit.
Do not use password fields, terminals or private documents as acceptance fixtures.

Speech acceptance: verify passive capture pauses during AERIS TTS, Push to talk stops speech
before recording, and Emergency Stop requires explicit Resume. Observe actual mic/SAPI cleanup
separately; fixture echo guards do not establish hands-free acoustic barge-in quality.

Copy/move acceptance: use only disposable files on a hard-link-capable Windows filesystem;
check source/destination bytes, collision denial and cancellation receipts. Test recovery with
fake credential backends only; do not deliberately damage the real credential store.
