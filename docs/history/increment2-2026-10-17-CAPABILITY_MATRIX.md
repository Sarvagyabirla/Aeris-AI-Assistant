# Capability matrix ? 17 October 2026

States follow REQUIREMENTS_TRACEABILITY. IMPLEMENTED does not certify hardware.
See VALIDATION_REPORT for exact fixtures and all requested scenarios.

| Capability | State | Evidence / limitation |
|---|---|---|
| Local intent/whole percentages/Hinglish | FIXTURE_VERIFIED | Router/controller corpus; negatives/decimals/compounds clarify with no cloud fallback |
| Existing-file patch cancellation | FIXTURE_VERIFIED | Registry final-check cancellation preserves original; after-replace receipt retains CRLF artifact |
| Cancellation UI receipts | FIXTURE_VERIFIED | Real Qt event loop retains artifact and suppresses stale speech |
| Settings/keyring/env/cleanup recovery | FIXTURE_VERIFIED | Fake keyring/env/disk errors; real Qt Retry; no plaintext fallback |
| Absolute mute/unmute and volume | IMPLEMENTED | Fake endpoint/COM/readback PASS; NEEDS_DEVICE for native acceptance |
| Absolute play/pause | UNSUPPORTED | Selected-session adapter missing; explicit error; toggle playback remains deliberately separate |
| Brightness/window/clipboard/apps/power | IMPLEMENTED | Brightness readback/per-display relative control and exact-window graceful close fixtures added; remaining Unicode/window/power/app postconditions and supervised acceptance pending |
| Voice cached warmup/capture | IMPLEMENTED | Cache-only constructor, optional imports and synthetic capture fixtures; NEEDS_DEVICE for actual mic/SAPI |
| Voice downloads/wake detector/VAD/devices | MISSING | No first-download UI, trained Aeris detector or production VAD/device selector |
| Busy voice interruption | IMPLEMENTED | Pre-existing busy capture retained; exact stop grammar tightened; echo/self-playback/device acceptance missing |
| 30-second control follow-up | FIXTURE_VERIFIED | Successful recent volume/brightness only; expiry/mode/intervening-task/Stop invalidation |
| System Health / Network Test shortcuts | FIXTURE_VERIFIED | Deterministic controller paths; network denial/cancel/fake bounded probe; real ICMP NOT RUN |
| Typed dependencies/output references | MISSING | Sequential action list remains; no observed-reference executor |
| Selected-screen explanation/watch | MISSING | JSON scope fixed; no-scope/watch fail closed; preview/window/destination UI missing |
| Browser automation | IMPLEMENTED | Existing guards/startup tests; DOM identity/peer enforcement/local browser fixtures still needed |
| Downloads/packages | IMPLEMENTED | Owned commands/presence fixtures preserved; immutable identities, transport and real UAC acceptance missing |
| Notes / filename search | FIXTURE_VERIFIED | Staged exclusive note publication and bounded cancellable search; filesystem native stalls remain possible |
| Multi-file coding/Undo/organization | MISSING | Single-file patch/generation remain partial foundations |
| Local memory /private | FIXTURE_VERIFIED | Existing inspect/correct/forget; private reply-only request omitted from persisted history |
| Daily Brief | IMPLEMENTED | Grounded authorized metadata fixture preserved; local reminders connected; calendar end/all-day/source/timezone metadata fixed; account identity/rich agenda incomplete |
| Gmail/Calendar account workflows | IMPLEMENTED | Adapters exist; NEEDS_ACCOUNT for account acceptance; explicit setup/draft/attachment/idempotency code still incomplete |
| Reminders | IMPLEMENTED | Local/Qt create/list/snooze/cancel, India timezone, recurrence/overdue/claims/restart and global Stop fixtures; running-app local notices only; broader DST/supervised acceptance pending |
| Routines/project records | MISSING | Durable reviewed workflow/project UI not implemented |
| Companion/tray/global shortcuts | MISSING | Existing Qt dashboard remains first screen |
| Wheel resources | FIXTURE_VERIFIED | Built/extracted/imported from another cwd with catalogs and license; dependency/native acceptance separate |
| Frozen executable | MISSING | PyInstaller absent; pinned build/clean-account acceptance not done |
| Specialist document/Blender/Resolve/FL/ML/Git workflows | MISSING | App catalog launch support does not implement specialist automation |

Current launch: parent START_AERIS.bat / AERIS.bat -> child RUN_AERIS.bat. Native runner now uses Windows Job Objects before resume when Windows extras are available; elevated/service boundaries remain uncertain. UI captures cover 1280x720, 1920x1080 and Qt scales 125/150/200 percent, not physical DPI acceptance.
