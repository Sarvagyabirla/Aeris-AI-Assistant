# Aeris and the practical Jarvis capability map

JARVIS in the Iron Man stories is fictional and has unrestricted access to advanced hardware, global data, robotics, weapons, and Stark infrastructure. Aeris translates the useful assistant ideas into capabilities that can work on a normal Windows laptop without pretending those fictional systems exist.

| Jarvis-style capability | Practical Aeris equivalent | Current state |
| --- | --- | --- |
| Natural spoken conversation | Local Whisper speech recognition, Gemini reasoning, local spoken replies | Working |
| Comes online immediately | HUD opens ready, speaks a greeting, and enters visible wake standby | Working |
| Holographic presence | Original animated AI character, rotating core, state colors, HUD telemetry | Working |
| Understands what the user sees | One-shot visible-screen capture and Gemini explanation after permission | Working |
| Controls the computer | Apps, browser, media, volume, brightness, windows, files, clipboard, system and power controls | Working |
| Builds software | Creates new multi-file coding projects, validates them, and opens the workspace | Working with Gemini |
| Installs tools | Exact `winget` packages and verified signed installers after confirmation | Working |
| Performs multi-step requests | Gemini may plan up to five registered validated actions | Working |
| Communicates | Gmail reading and confirmed sending | Working after OAuth setup |
| Remembers context | Local recent-conversation memory with sensitive-command omission | Basic |
| Proactive reminders and schedules | Durable scheduler and notification center | Planned |
| Deep browser operation | Dedicated Aeris Playwright profile with authenticated workflows | Planned |
| Fully offline intelligence | Deterministic offline commands now; optional local LLM planner | Planned |
| Specialist engineering control | VS Code, Blender, DaVinci Resolve and FL Studio adapters | Planned |
| Physical-world robotics | Requires separate compatible hardware and safety engineering | Not part of the desktop app |

## Design direction

The two supplied references use a dark background, central circular intelligence core, cyan or orange state colors, dense telemetry, modular launch panels, and a holographic figure. Aeris uses those principles without copying the original images: cyan means online, green means listening, purple means thinking, amber means executing or awaiting caution, and red means stopped or failed.

## Non-negotiable boundaries

Aeris does not silently watch the screen, record the microphone invisibly, extract passwords, bypass UAC, run generated code automatically, execute arbitrary model-written shell commands, or install software without confirmation. These limits are what make a powerful desktop assistant usable on a real personal computer.
