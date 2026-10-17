# Performance evidence - 17 October 2026, launch/reminders increment

30 warm simulated production-controller trials, one warmup; temporary database/audit, no network,
model, audio or desktop action. Same Windows build 26200 / Intel64 Family 6 Model 183 Stepping 1 /
Python 3.11.9, Pydantic 2.13.5, PySide6 6.11.2, pytest 9.1.1.

Construction single sample 9.809 ms; warm median 5.286 ms, p95 7.275 ms; routing p95 0.089 ms;
0 failures / 30. [Raw trials](evidence/launch-reminders-controller.json). These are simulated
controller overhead, not real voice/device/GUI acknowledgment or proof of a speedup.

Reminder scans occur on the owned background scheduler every second, up to 100 due records per
transaction; UI storage snapshots run in QThreads. SQLite busy waits are configured to one second;
Stop does not interrupt a native commit/fsync instantly. Job runner polls every 20 ms and waits for
owned descendants/pipes; cleanup has additional bounded waits. Elevated/service effects remain
outside a guaranteed ownership boundary. No 100 ms real-device Stop guarantee is claimed.

Cold GUI, actual ASR/TTS, microphone, live controls, resource use and physical DPI remain unmeasured.
Synthetic real-widget captures at 1280x720/1920x1080 and Qt scales 1.25/1.5/2 rendered successfully;
representative dashboard/reminder/200 percent captures were visually inspected. This is not complete
keyboard/accessibility/device performance acceptance. Older runs remain in docs/history/evidence.
