# Performance evidence - 17 October 2026, companion increment

30 warm simulated production-controller trials, one warmup, isolated temporary runtime data.
Python 3.11.9 / Windows build 26200 / Intel64 Family 6 Model 183 Stepping 1; Pydantic 2.13.5,
PySide6 6.11.2, pytest 9.1.1. No app launch, cloud, microphone or speech occurred.

Construction (one sample): 15.952 ms. Warm median:
14.862 ms; p95: 20.002 ms. Routing p95:
0.111 ms. Zero failures in 30 trials.
[Raw trials](evidence/companion-controller.json). This measures controller overhead with the
new durable task journal, not GUI/audio/device latency. It is slower than the earlier 5.574 ms
median / 6.646 ms p95 snapshot; no speedup is claimed. The final recorded run followed completion
of regression/capture work. Individual acceptance-scenario timings remain NOT MEASURED.

Character rendering is capped at 30 fps. Reduced motion disables the timer; hidden/minimized
widgets pause it. Qt/event-loop tests verify these gates; actual idle/active CPU, startup time,
physical DPI, acknowledgment and native Stop/quiescence remain NOT MEASURED. Process memory
shown in the dashboard is sampled from the actual Aeris process, not decorative telemetry.

Task budgets default to 12 steps and 120 seconds, checked cooperatively; schema maximum timeout
is 300 seconds. Native model/SDK/filesystem calls retain their own blocking boundaries. No blind
retry/replay is used for external effects. SQLite/fsync can delay a task worker; the new ledger
connections are explicitly closed. Reminder/native process ownership measurements remain in
the archived report. No 100 ms or two-second real-device latency promise is made.
