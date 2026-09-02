# Aeris feature completion plan

Aeris is one continuous project. Features are added to the same application and the same folder. The stages below are engineering checkpoints, not separate products or downloads.

## Current foundation

- Online Gemini reasoning and offline deterministic commands
- Voice input and spoken responses
- Application, browser, volume, brightness, media, file, screenshot, and Gmail tools
- Direct downloads with public-network checks, size limits, non-overwrite behavior, and Defender scanning
- Trusted app search/install/update/uninstall through exact `winget` packages
- Signed local-installer launch with a separate Aeris confirmation and Windows/UAC prompt
- Clipboard, window navigation, system health, battery, lock, sleep, restart, and shutdown controls
- File and note creation, copy, move, folder opening/creation, and recoverable deletion
- Permission levels, exact-action confirmation, dry-run mode, kill switch, audit logging, and secret redaction
- Desktop interface, one-click setup, and one-click daily launcher
- CPU-first Whisper and flexible voice-command normalization
- Animated cyan HUD with a central AI character, telemetry, live state animation, fullscreen, and always-on-top controls
- Automatic startup greeting and visible wake-word standby
- One-shot screen understanding with session permission and no retained capture
- Safe coding-project generation with path isolation, syntax/config validation, non-overwrite behavior, and no automatic execution

## Hands-free interaction

- Improve the current Whisper wake standby with a lightweight dedicated local wake detector
- Add a microphone selector, noise-calibration wizard, mute indicator, and emergency-stop hotkey
- Add a configurable conversation window so repeated commands do not always require the wake word

## Browser and communication automation

- Playwright with a dedicated Aeris browser profile
- Domain-specific permissions
- Reliable YouTube search and playback
- Gmail drafts, replies, attachments, and send previews
- Calendar viewing and event creation with confirmation
- Authenticated downloads through a dedicated Aeris browser profile without borrowing the user's normal browser session

## Local intelligence and durable memory

- Optional Ollama model for offline natural-language planning
- Explicit remember, search-memory, and forget commands
- Durable reminders, schedules, retry protection, and restart recovery
- Personal contact aliases without exposing credentials

## Specialist software adapters

- VS Code project, testing, and Git workflows
- Blender scene actions
- DaVinci Resolve project helpers
- FL Studio transport and project helpers
- AI/ML research and coding workspaces

## Production hardening

- Signed Windows installer and automatic updates with rollback
- Permission dashboard and audit viewer
- Plugin signing and isolation
- Performance monitoring and crash recovery
- Complete Windows 10/11 verification matrix

The same Aeris application will receive each completed capability without creating parallel editions.
