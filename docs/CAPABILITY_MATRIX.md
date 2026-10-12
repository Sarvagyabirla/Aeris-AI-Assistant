# Capability/setup matrix — 12 October 2026

“Fixture verified” means no device/account success is asserted.

| Capability | Actual status | Evidence/setup |
|---|---|---|
| Text local commands/simulation | Available offline, fixture verified | Production controller + Qt dispatch; no LLM health probe for recognized route |
| Notepad/Chrome/Explorer/VS Code launch | Needs real Windows acceptance | Existing catalog tools preserved; simulation alone does not verify opening |
| Volume/brightness/window/clipboard | Needs device acceptance | Existing tools retained; toggle-only media semantics not fixed |
| GUI speech results | Connected, needs audio setup/acceptance | Owned TTS engine fixture, not actual playback |
| Push-to-talk | Connected, needs microphone/model | Defaults muted; capture errors visible |
| Hands-free | Opt-in, partially implemented | Addressed phrase boundaries; still continuous transcription, not trained wake model |
| Startup greeting/model background readiness | Incomplete | No greeting/preload claim |
| Gemini flexible requests | Available online after explicit request consent | Private history excluded; actual serialization fake-client tested |
| Ollama planning | Needs configured installed-model selection work | Existing llama3 default remains; no available-model claim |
| Browser navigate/extract/click/fill | Fixture policy/startup checked; runtime acceptance pending | Isolated ephemeral context; no copied Chrome credentials; confirm click/fill |
| Screen explanation | Needs selected-region/crop preview workflow | No-region live request fails closed; online reasoning only |
| Screen watch | Unavailable pending safe scope UI | Full-desktop background upload disabled |
| Coding search | Bounded offline implementation | Symlink privilege skip; Windows junction/race acceptance pending |
| Coding patch | Single-file hash/unique-match guard fixture verified | UTF-8 only; no multi-file Undo/check workflow |
| Conversation history | Local, migration/privacy fixture verified | Inspection/correction/export/retention APIs; no full memory UI |
| Reminders/routines/project continuity | Not implemented as connected workflows | No app-closed delivery promise |
| Gmail/Calendar | Needs account setup | Existing adapters/renderers; designated account verification pending |
| Daily Brief | Shortcut only, not finished retrieved workflow | Do not advertise as current authorized data aggregation |
| Companion/animated core/tray/global shortcut | Not implemented | Existing native Qt dashboard, not holographic presence |
| Packaged executable | Not built/verified | PyInstaller absent; entrypoint/build command repairs only |

Supported-app matrix must be expanded only after exact real operations and denial/cancellation evidence exist.