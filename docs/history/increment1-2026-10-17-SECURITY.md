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
or implement race-safe copy/move/downloads/Undo. Never infer all filesystem effects are repaired.

Only explicitly SHAREABLE history is sent to the cloud planner. Existing coding cloud consent
remains separate. `/private <request>` omits user/reply history even for reply-only requests;
transient transcript display is separate from persistence. Metadata-only audit defaults remain.
Configured keys do not grant screenshot/file/mail sharing. Unified content-sharing/account setup
and full sensitive-input retention controls remain incomplete.

Keyring failure does not select an environment-key bypass: startup exposes a recovery message
and retains local simulation text use with AI/listening disabled. Invalid effective boolean,
numeric/device/wake environment settings fail safely. Saving a settings file after changing a
credential rolls the credential back on write failure. A failed credential rollback requires
backend repair; that exceptional recovery is not fully automated. Existing data is preserved.

Whisper loading uses local_files_only=True, including CPU fallback. Normal listening cannot
start a model download. Cached warmup runs off the Qt event loop after hands-free opt-in. There
is no first-download consent/progress UI yet, no trained Aeris detector, and no certified acoustic
echo suppression/barge-in. A synchronous native model load or SDK request cannot be instantly
interrupted. Stale screen-provider output and cancelled task speech are discarded.

Native process cancellation is the existing bounded run_owned runner. No Windows Job Object
ownership was added: descendants that reparent, detach, elevate or retain pipes can outlive the
parent. Install interruption is uncertain; never blindly retry. Hash/signer approval, observed
version/publisher and browser/download transport peer enforcement remain unfinished. Network
Test requires exact approval for one www.microsoft.com ICMP probe; no HTTP content is fetched.

Cleanup failure retains the window and offers Retry instead of repeatedly polling a failed result.
No forceful unrelated-process termination is used by cleanup. The separate existing close_app
implementation still needs a selected graceful-window replacement before dependable use.

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
- [Windows Job Object boundaries, not yet implemented here](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
