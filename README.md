# Aeris - Windows desktop companion

One Python/PySide6 application in the existing Aeris checkout. This increment connects an
original animated vector humanoid, floating companion, typed multi-step execution, permission
controls, reviewed local routines and document organization with guarded Undo. **The full
master prompt remains unfinished.** No native-device, account or frozen-release certification
is implied by fixture results.

[Current status](docs/IMPLEMENTATION_STATUS.md) | [Actual validation](docs/VALIDATION_REPORT.md) |
[All requirements](docs/REQUIREMENTS_TRACEABILITY.md) | [Continuation](docs/CONTINUATION.md)

## Launch and check

From your existing `AERIS_AI_ASSISTANT` parent folder:

```powershell
.\START_AERIS.bat
.\AERIS.bat --self-test
.\AERIS.bat --test
.\AERIS.bat --lint
```

The parent launchers forward to the nested Aeris repository and its existing Python 3.11
.venv. Inside Aeris, START_AERIS.bat / RUN_AERIS.bat use the same application. Normal launch
starts the controller automatically and restores dashboard/companion, motion and microphone
mute preferences. Saved live/simulation and hands-free opt-in remain effective. Invalid
credential/settings recovery forces simulation and disables AI/listening. No setup or model
download occurs during normal startup. No environments, personal files or settings were
replaced during implementation.

## Connected use

- Dashboard: character, conversation, actual task steps, measured process memory, input,
  microphone/speech controls, task Stop and latched Emergency Stop with explicit Resume.
- Floating companion: move/resize, optional on-top, PTT, mute microphone, Stop, dashboard and
  hide controls. Click-through requires a working tray or native restore shortcut and is
  never restored automatically. Reduced motion and hidden/minimized animation pausing apply
  to both views. Speech motion follows the speaking state; it is not phoneme lip sync.
- Windows shortcuts: Ctrl+Alt+A restore and recover clicks, Ctrl+Alt+S task/speech Stop,
  Ctrl+Alt+Space push to talk. Native registration can fail if another app owns a shortcut;
  tray/application controls remain available. Physical Windows acceptance is still needed.
- Permissions: choose any accessible folder or drive root, inspect/revoke it, and enable or
  revoke capability categories. Broad scopes exclude credential/security stores and .git
  internals; they never authorize automatic indexing or cloud upload. Local access, account
  permissions, external effects and cloud sharing remain distinct.
- Settings: Assist previews effects; Task Automation runs requested supported low-risk steps;
  Trusted Routines requires an explicitly reviewed local workflow. Simulation stays a separate
  setting. Sends, installs, destructive work and sharing retain their ordinary approvals.
- Tasks & routines: review/save one to twelve typed local steps, run from one text or voice
  command, inspect history, disable routines and review organization Undo. Use the Study
  template, review it, then say `run routine study mode`. No automatic trigger is enabled.

Examples: `open notepad, set volume to 35, and minimize this window`, `set volume to 50 and
brightness to 20`, `remind me in 15 minutes to stretch`, `daily brief`, `system health`.
Use **Select task / typing window** for the exact external window before target-specific work.
App launch alone does not establish control of that app. Each step retains its observed result;
failed dependencies block later work. Invalid quantities, negated/quoted/conditional commands
and unsupported compounds produce no partial execution or cloud reinterpretation.

To organize selected documents: grant the folder in Permissions, choose it in Tasks & routines
or type `organize documents in C:\path\to\fixtures`. Review all source/destination pairs once.
Batches are limited to 100 documents / 50 MiB / 1,000 directory entries, without recursion.
Windows owned-file moves require a hard-link-capable filesystem. Undo checks hashes/identities
and refuses intervening edits; empty category folders remain. Partial/uncertain effects are
retained for review. Ordinary copy/move is still not a general transactional rollback system.

## Preserved controls and limits

Local volume/mute/brightness, configured app launch, files, health, reminders and selected
window controls do not need cloud reasoning. Absolute play/pause remains unsupported until a
selected media-session adapter exists; explicit playback toggle remains separate. Selected
Unicode typing previews/refocuses the exact window/control, stops on focus changes and reports
input events; it does not read back insertion. Graceful close preserves app save prompts and
never force-kills a process. Close requests are explicitly unverified dispatches.

Microphone mute is saved separately from hands-free opt-in. PTT permits one utterance while
passive listening stays muted. Passive capture pauses during Aeris speech; PTT stops speech
before capture. Cached speech assets load off the UI thread. Acoustic barge-in, trained wake
assets, device selection and first-download onboarding are unfinished. Native model/SDK calls
can outlive Stop acknowledgment. Reminders need Aeris running in LIVE mode; tray can keep it
open, but no closed-app service or startup registration is promised.

Only SHAREABLE history reaches the cloud planner. `/private <request>` omits conversation
persistence. Task history stores safe tool/status/effect receipts, not request bodies, screenshots
or mail content. Account setup, sensitive input controls and destination-bound sharing need
more work. See [security](docs/SECURITY.md).

Still unfinished: selected-screen preview/redaction/watch, UI Automation and guarded visual
fallback, same-page browser identity/peer enforcement, immutable installer approvals,
account-specific Gmail drafts/OAuth, multi-file coding review/checks/Undo, broader project and
specialist adapters, onboarding, unified locks and a verified frozen executable. PyInstaller is
absent in this environment. The source wheel check does not certify a desktop release.

See [supervised Windows checks](docs/WINDOWS_TESTING.md), [capability evidence](docs/CAPABILITY_MATRIX.md)
and [performance](docs/PERFORMANCE.md). Earlier reports are retained in docs/history.
No commits or pushes were made.
