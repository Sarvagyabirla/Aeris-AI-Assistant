# Native/lifecycle continuation

Owned process cancellation targets the process created by Aeris and descendants enumerated from
that PID, never application names or unrelated processes. This is not an isolation sandbox or a
Windows Job Object; reparented, detached or elevated installer effects can remain uncertain.
Native output is bounded and shown only in explicit tool results, not printed/logged by the runner.
Installer Defender failure/unavailability now blocks launch. Approved file hash/signer binding is
still incomplete. Network DNS and socket reads still have blocking boundaries; do not claim instant Stop.
Task Cancel and global Emergency Stop are distinct; global state is authoritative in PermissionEngine.
Settings preparation and shutdown are owned background jobs; failed cleanup retains the window.

# Current increment — 12 October 2026

SESSION grants now bind the canonical tool/argument fingerprint and expire after the configured
approval TTL (default 90 seconds). Different capture regions require new permission. Stop/settings
invalidate session grants; settings preserve global Stop. This is not full window/account identity
support: only identities actually supplied in canonical arguments are bound.
Audit files persist safe status/tool metadata, not arbitrary request/result/exception bodies.
Coding cloud generation requires separate explicit sharing consent. Sensitive default logging is off.
Short project publication is linearized against cancellation; cancellation after publication reports
the remaining artifact instead of promising rollback. Native blocking I/O, installer identity,
DNS peer restrictions and general filesystem race-resistant handles remain incomplete.
Untrusted mail/browser text is data; Daily Brief renders retrieved metadata locally and never
executes retrieved instructions or sends messages. No automatic cloud summarization is added.

# Aeris security model

Aeris is intentionally permission-first. The AI planner cannot call the operating system directly. It can only request registered tools, and the registry validates the tool name, required arguments, permission level, kill switch, and dry-run state.

## Permission levels

| Level | Behaviour | Examples |
| --- | --- | --- |
| `AUTO` | Executes without a prompt in live mode | Open configured apps, browser search, volume, brightness, media controls, app search, system health |
| `SESSION` | Asks once for that capability until Aeris exits | Screen understanding, screenshot, clipboard read, installed-app list, read/open allowed files, read Gmail |
| `CONFIRM` | Shows the exact action and asks every time | Code-project creation, download, install/update/uninstall, file changes, send email, close app, power actions |
| `BLOCKED` | Never executes | Password extraction, security bypass, arbitrary shell, automatic download execution |

Every confirmation token is bound to a SHA-256 fingerprint of the exact tool name and arguments, expires quickly, and can be used only once.

## File safety

- Aeris can only resolve paths inside `AERIS_ALLOWED_PATHS`.
- Symlink and `..` traversal is checked after canonical path resolution.
- Executables and scripts cannot be opened through the file tool.
- Deletion uses the Recycle Bin and always requires confirmation.
- Text reads are limited to approved extensions and 200 KB.
- New text files, copies, and moves never overwrite an existing item.

## Download and installation safety

- Downloads accept only complete public HTTP/HTTPS URLs and obey `AERIS_ALLOWED_DOMAINS`.
- Private, loopback, link-local, embedded-credential, and unsafe redirect targets are blocked.
- Files are saved only in `AERIS_DOWNLOAD_DIR`, have a configurable size limit, and never overwrite.
- Downloads are scanned with Microsoft Defender when it is available and are never automatically executed.
- Normal application installation uses only exact packages from the official `winget` source.
- A downloaded installer must be inside an allowed path and have a valid Authenticode signature by default.
- Aeris asks first; Windows/UAC can ask again. Aeris never bypasses UAC or silently elevates itself.

## Microphone and screen safety

- Wake listening is visible in the HUD and can be switched off immediately.
- The emergency stop disables wake listening along with computer tools.
- Wake standby only executes speech beginning with the configured Aeris wake name.
- Screen understanding asks for session permission before the first capture.
- Each screen request captures only currently visible pixels; hidden windows and files are not accessed.
- The temporary screen image is sent to the configured Gemini model and is not saved by Aeris.
- Passwords, API keys, payment details, recovery codes, and tokens must not be reproduced by screen analysis.

## Code-generation safety

- Generated projects are written only inside `AERIS_CODING_WORKSPACE`, which must also be allowed by `AERIS_ALLOWED_PATHS`.
- Aeris creates a new unique project folder and never overwrites an existing project.
- Paths containing traversal, drive letters, hidden files, scripts, executables, or unsupported file types are rejected.
- Python, JSON, and TOML content is validated before any project is committed.
- Failed drafts are rolled back; generated programs and dependencies are never automatically executed or installed.
- Requests for credential theft, spyware, ransomware, persistence malware, reverse shells, or security bypasses are blocked.

## Secrets

- `.env`, Gmail OAuth files, databases, and logs are ignored by Git.
- Gmail OAuth tokens are stored through the operating-system credential vault using `keyring`.
- Gmail passwords are never requested or stored.
- Audit logs redact common secret fields, bearer tokens, and sensitive signed-URL query values.

## Safety controls

- Aeris starts in dry-run mode unless `--live` is provided.
- Saying `stop Aeris` activates the kill switch.
- While stopped, only status and resume commands work.
- Unknown tools and missing arguments fail closed.
- Windows and cloud integrations fail safely when a dependency or credential is missing.

## Intentionally unavailable

- Arbitrary PowerShell, Command Prompt, or Python execution
- UAC bypass or silent administrator elevation
- Password or credential extraction
- Financial transactions
- Unconfirmed or model-generated software installation
- Silent email sending
- Automatic execution of downloaded files
