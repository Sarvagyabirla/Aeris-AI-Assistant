# Security and privacy boundaries ? 17 October 2026

Local routing declines negated, quoted, conditional/reported controls, invalid quantities and
unsupported compounds. These requests produce a local clarification and never a cloud fallback.
Strict tool schemas reject extra fields, integer coercion and oversized JSON arguments (256 KiB).

Task Stop, microphone mute and latched Emergency Stop are separate controls. Resume is explicit
and invalidates grants. Settings retain global Stop. Canonical exact SESSION grants expire and
are pruned; pending dialogs/queued command generations invalidate on task Stop. Account/window/
sharing-destination identity beyond supplied arguments remains unfinished.

Patch replacement and staged note publication use the token's short commit gate. Cancellation
winning that gate publishes nothing; later cancellation retains visible artifacts. Notes publish
with an exclusive same-filesystem hard link, never overwrite an existing destination, and fail
closed where hard links are unsupported. This does not eliminate external-writer TOCTOU races
across hostile directory/junction replacement. Transfers/downloads now use exclusive publication;
Windows moves protect source/destination identities before owned deletion. Hard links are required,
safe move is Windows-only, and ACL/ADS preservation and general transactional Undo remain unfinished. Document-batch Undo is now implemented with conflict checks.
Staging/partial cleanup retains active/recent/unowned entries; no blanket partial deletion.

Only explicitly SHAREABLE history is sent to the cloud planner. Existing coding cloud consent
remains separate. `/private <request>` omits user/reply history even for reply-only requests;
transient transcript display is separate from persistence. Metadata-only audit defaults remain.
Configured keys do not grant screenshot/file/mail sharing. Unified content-sharing/account setup
and full sensitive-input retention controls remain incomplete.

Keyring failure does not select an environment-key bypass: startup exposes a recovery message
and retains local simulation text use with AI/listening disabled. Invalid effective boolean,
numeric/device/wake environment settings fail safely. Saving a settings file after changing a
credential uses a secret-free intent journal and rolls back on write failure. Failed rollback
retains the journal and forces current/restarted/CLI use into simulation with AI/listening off;
no ambiguous stored/environment key is used. Explicit successful Settings save clears recovery.
Independent concurrent settings writers and full power-loss durability are not guaranteed.
Existing data is preserved.

Whisper loading uses local_files_only=True, including CPU fallback. Normal listening cannot
start a model download. Cached warmup runs off the Qt event loop after hands-free opt-in. There
is no first-download consent/progress UI yet, no trained Aeris detector, and no certified acoustic
echo suppression/barge-in. A synchronous native model load or SDK request cannot be instantly
interrupted. Cancelled CUDA failure starts no CPU fallback. Stale screen-provider output and
cancelled task speech are discarded. Passive capture pauses during AERIS speech/global Stop;
PTT stops speech and waits for quiet. A playback generation discards contaminated transcripts
even if playback ends during inference. This is an echo guard, not native acoustic certification.
Failed provider cleanup remains owned; failed speech stop/endLoop retains its owner thread for
explicit Retry. Failed COM release itself can remain unrecoverable in-process and blocks restart.

Native process cancellation uses the existing bounded run_owned runner. With Windows extras,
children are created suspended, assigned to an unnamed kill-on-close Job Object and resumed through
the short cancellation gate. The runner waits for owned descendants and inherited pipes, not just
the parent exit, and reports weaker fallback ownership explicitly. UAC/service/broker-launched
processes can still escape. Install interruption remains uncertain; never blindly retry. Installer
hash/signer/version and browser/download peer enforcement remain unfinished.

Close-app approval now binds one observed HWND/PID/creation/title and rechecks it before WM_CLOSE.
It never blanket-terminates matching processes. The app retains its own unsaved-work prompt; a
posted close is not proof the window closed. Unicode typing now binds window/process creation/title
and focused control, previews exact text and deliberately restores only the approved target.
Identity/focus/Stop are checked per scalar; Windows cannot atomically check focus and inject, so
one scalar can race a focus change. Input-event delivery does not prove insertion, and semantic
password/terminal field classification is absent. Other window/clipboard/screenshot scopes remain.
Permission dialogs use plain text so app titles cannot render HTML.

Reminders are durable local records, excluded from conversation-history copies. No scheduler starts
in the assistant constructor or without a listener. The UI owns delivery; simulation/global Stop
pause it. Claims are committed before callbacks, under SQLite BEGIN IMMEDIATE across store instances;
callbacks run outside the data lock. Queued generic notices contain no private reminder text and
speech is not used for due notifications. A crash between claim and signal can leave an occurrence
visible only in the durable Due list. Snooze is explicit; closed-app delivery is unavailable. SQLite
writes check cancellation before transaction commit, but native commit/fsync waits are not instantly
interruptible. Broad recurrence DST policy and all locked-screen speech behavior remain unfinished.

Cleanup failure retains the window and offers Retry. Reminder/read workers are owned during close.
Network Test still requires approval for one www.microsoft.com ICMP probe; no HTTP body is fetched.

Release exclusions cover additional environment variants, credentials, keys, databases/WALs,
runtime/screenshots/generated-project folders. Only sanitized .env.example is exempted. Local
wheel artifact-name checks pass; no executable/release bundle exists. MIT metadata now has a
matching LICENSE (declared author and local Git history). Third-party attribution remains a
release task; this does not assert a dependency-license audit was completed.

Official references consulted:

- [Microsoft SetMute absolute-state contract](https://learn.microsoft.com/en-us/windows/win32/api/endpointvolume/nf-endpointvolume-iaudioendpointvolume-setmute)
- [Microsoft COM lifetime](https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-couninitialize)
- [Pycaw examples](https://andremiras.github.io/pycaw/examples/index.html)
- [sounddevice installation/native PortAudio](https://python-sounddevice.readthedocs.io/en/latest/installation.html)
- [faster-whisper cache-only constructor](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py)
- [Windows Job Object ownership and boundaries](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)

Additional official references: [WM_CLOSE](https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-close), [PostMessage](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-postmessagew), [suspended process flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags), [screen brightness API](https://github.com/Crozzers/screen_brightness_control).

Additional official native references consulted for this increment:

- [SendInput and UIPI restrictions](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput)
- [KEYBDINPUT Unicode contract](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-keybdinput)
- [GetGUIThreadInfo](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getguithreadinfo)
- [SetForegroundWindow restrictions](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow)
- [FILE_DISPOSITION_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_disposition_info)

Portable copy/cleanup use observed identity/hash checks; POSIX check-to-unlink races are not
fully excluded and safe move is unsupported there. Partial ownership is process-local; the
24-hour cutoff does not prove another process's hung job inactive. Native DNS/socket/fsync
blocking limits remain. No adversarial parent-directory/junction immunity is claimed.

## Connected companion increment boundaries

Permission categories can be revoked before target preparation. Folder/drive revocations persist
in access-revocations.json and remain effective through unrelated Settings saves. PathGuard is
shared by file/coding/install-file adapters and excludes credentials, browser secret stores,
security data, other users and .git internals. Downloads retain their separately configured
destination and category; a folder grant does not silently widen download or cloud permissions.
There is no special elevated access and no sensitive-store exception workflow yet. Cross-process
revocation and malicious-directory-handle races are not proven closed.

Whole tasks preflight all static arguments/dependencies before any effect. Observed output fields
are allowlisted, never instructions, and are revalidated under the consumer schema and policy.
Cooperative deadlines do not interrupt every native/SDK call. Durable task history stores only
tool/status/safe effect receipts; it excludes user goal text, arguments, mail bodies and pixels.
Receipt paths remain local. Storage failure retains visible results and blocks subsequent steps;
PID-based interrupted-work detection needs stronger process identity. No restart replay occurs.

Routines are explicitly saved local typed plans, never keyboard recordings, Python/eval/shell
macros or inferred authorization. App catalog content, local scope/revocation/category state and
live/simulation mode are bound to review. Manual runs only; changed scope requires re-review.
Account/sending/install/destructive operations are outside the routine allowlist. Assist previews
effects; Trusted mode requires reviewed context. Sensitive ordinary actions retain exact approval.

Document organization reads only requested scoped file identities/hashes, confirms an exact bounded
manifest once and uses the owned exclusive transfer adapter. All sources are checked before the
first move and again while staging. Undo refuses source/destination changes and newer edits.
Partial/uncertain work is retained; a crashed in-progress batch is not silently replayed or undone.
No claim of full multi-file atomicity, ACL/ADS preservation or hostile-parent immunity is made.

The companion has no context-capture function. Click-through requires a recovery path and is
never persisted. Global shortcuts use RegisterHotKey, not a general keyboard hook. Microphone
mute is persisted separately from hands-free opt-in; malformed saved presentation data mutes
passive listening. Single-instance IPC accepts only a restore connection, never task arguments.
