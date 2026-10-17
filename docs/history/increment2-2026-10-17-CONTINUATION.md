# Exact continuation - 17 October 2026

Same Aeris nested repository, branch fix/responsive-aeris-desktop, HEAD
e97687470b46e0c2f9030b331de17df33d9ff903 plus all existing uncommitted work. Preserve it.
Parent .venv (Python 3.14 in the user's log) is separate; canonical RUN_AERIS.bat uses the
existing child Python 3.11 environment. Parent START_AERIS.bat and AERIS.bat are forwarding
helpers outside the nested Git root. Do not create another app or replace either environment.

Latest baseline was 240 passed/1 skipped; this increment adds native process ownership, connected
reminders, safe close/brightness and calendar metadata regressions. Final checks and source hashes
are in VALIDATION_REPORT. No install, commit, push, model download or personal account/device test.

Completed working additions (not whole phases): parent launch/correct interpreter; suspended-child
Windows Job Object runner; local/Qt durable reminder workflow with timezone/claims/overdue and
Stop/lifecycle behavior; exact-window graceful close; per-display brightness readback; calendar
end/all-day/timezone/source fields. Earlier safety repairs remain. 119 requirements/65 tools/43
production modules are retained in REQUIREMENTS_TRACEABILITY.

Next implementation order:

1. Finish effect/resource/privacy audit: race-safe copy/move/download publication and Undo,
   Unicode/focus binding, editor/open-app effects, native power verification, immutable installer
   hash/signer/version identity, provider failed-cleanup retry and credential rollback failure.
   Job Objects cover ordinary owned descendants; UAC/service/broker effects remain uncertain.
2. Voice: shared activation/alias grammar, explicit states, device selector/VAD/single input,
   first-download size/progress/consent onboarding, echo-safe interruption and supported absolute
   media sessions. Normal ASR stays cache-only. Never silently download or advertise a trained
   Aeris wake model. Model/SDK loads still have synchronous quiescence limits.
3. Typed task/observation/dependency executor with whole-plan validation, actual output references,
   postconditions, bounded corrective planning and real adapter readiness. Preserve CLI failures,
   local shortcuts, exact approvals and global Stop. Do not expose model prose as completion proof.
4. Selected-screen crop/redaction/preview/window/destination scope; browser DOM replacement and
   transport peer enforcement; local HTTP/DOM fixtures. No full-screen background upload bypass.
5. Multi-file coding review/check/Undo; project continuation and reviewed routines/organization.
   Generated code/tests stay untrusted and require a scoped execution plan.
6. Expand reminders: broad NLP/DST/nonexistent recurrence-time policy, explicit long-sleep and
   crash-delivery UX, retention/acknowledgment and optional authorized tray/startup. Current claims
   are at-most-once per occurrence with durable Due view, not guaranteed external notification.
   Add account-specific OAuth/read/send scopes, drafts/attachments/idempotency, rich grounded brief
   and durable facts/projects. Calendar account identity and timezone agenda remain incomplete.
7. Companion/tray/global shortcuts/single-instance restore/accessibility and diagnostic views.
   Synthetic sizes/Qt scale captures exist; actual Windows DPI/keyboard/audio/device checks remain.
8. Reconcile locks/CI versions; pin/review PyInstaller, frozen clean-account acceptance, release
   privacy/attribution and rollback. Current source-wheel evidence is not an executable release.
9. Narrow detected specialist VS Code/Git/ML/Office/Blender/Resolve/FL/media adapters with version
   matrices and production fixtures. No arbitrary plugins/hidden updater or force pushes.

Next supervised check: from the parent folder run START_AERIS.bat, verify SIMULATION and controls.
Use the Reminders tab in simulation first; an actual local reminder needs intentional LIVE mode
and Aeris kept open. Real mic/SAPI/apps/accounts/install/power/sensitive windows remain separately
supervised checks. Ordinary tests use fake providers and disposable paths, never personal data.
