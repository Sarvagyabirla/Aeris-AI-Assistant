# Performance evidence ? 17 October 2026

30 warm simulated production-controller trials, one warmup; temporary database/audit, no network,
model, audio or desktop action. Python 3.11.9, Windows build 26200; Intel64 Family 6 Model 183
Stepping 1. Dependencies: Pydantic 2.13.5, PySide6 6.11.2, pytest 9.1.1.

| Measurement | Observed |
|---|---|
| Controller construction, one sample | 9.639 ms |
| Warm handle median | 4.973 ms |
| Warm handle p95 | 5.810 ms |
| Routing p95 | 0.093 ms |
| Errors / trials | 0 / 30 |

[Raw report and trials](evidence/review-2026-10-17-controller.json). This meets the warm simulated
controller target for this small command only. No speedup claim versus older runs. Cold GUI,
Stop/command acknowledgment, ASR endpoint/transcription, first audible TTS, live tool latency,
CPU/RAM and device quiescence remain NOT MEASURED. Real Qt fixtures establish responsiveness
under controlled waits, not a measured 100 ms latency guarantee.

Filename search uses a 2-second/10000-entry cooperative budget; Windows directory operations
can themselves block. Network Test uses an owned 4-second subprocess budget and one 1000 ms ICMP
reply wait. Process creation/enumeration/cleanup adds overhead; these are configured limits, not
measured external-device timing guarantees. Synchronous SDK/model initialization remains a
cancellation-quiescence limitation. See SECURITY for official adapter references.
