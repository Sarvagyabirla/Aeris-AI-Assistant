# Performance — measured subset, 12 October 2026

## Native/lifecycle continuation measurement (newest)

30 simulated warm controller trials: construction 3.789 ms (single sample), p50 5.940 ms,
p95 7.126 ms, routing p95 0.0812 ms, zero failures. Hardware/procedure unchanged below.
Raw samples: `evidence/native-lifecycle-local-warm.json`. No optimization/speedup claim.
Owned process runner polls at 20 ms; termination waits total up to approximately 2.1 seconds,
plus 0.5-second reader join, excluding process creation/enumeration/OS scheduling. These are
implementation bounds, not measured device Stop timings; detached/elevated effects remain uncertain.
Settings/cleanup GUI responsiveness is event-loop fixture tested but acknowledgment latency,
real ASR/TTS and resource use remain NOT MEASURED.

## Current follow-on measurement (6b22de3 baseline plus uncommitted changes)

Same hardware/interpreter and simulated warm procedure below, 30 trials, all retained:
construction 6.657 ms (one sample), total p50 5.758 ms, total p95 6.836 ms,
routing p95 0.0704 ms, failure rate 0%. Raw samples: `evidence/phase1-local-warm.json`.
Reproduce with `scripts/measure_local.py --trials 30 --output docs/evidence/phase1-local-warm.json`.
No before/after optimization claim; disk/controller variation is not actual app/audio improvement.
UI acknowledgment, Stop acknowledgment/quiescence, idle/active CPU/RAM, ASR, TTS audible output,
cloud and real app effects remain NOT MEASURED. Generation has 30-second HTTP bound and
late-result checks; owned native process cancellation is not yet implemented.

## Production stage definitions

`StageTimer` uses monotonic `perf_counter`; per-task command identity is inherited from the GUI token
or generated for text callers. Logs contain identity/stage/duration, not utterance text.
Currently connected stages: `routing`, `permission_and_tool_<action id>` and `task_total`.
Approval and tool time are **not yet separated**. Queue/capture/transcription/provider/verification/render/speech
timestamps remain to be connected. Do not interpret these as complete end-to-end telemetry.

## Repeatable warm local fixture measurement

Hardware: Intel Core i7-13650HX, 14 cores/20 threads, 25,534,783,488 bytes RAM.
OS: Windows build 26200; Python 3.11.9; Pydantic 2.13.5; PySide6 6.11.2; pytest 9.1.1.
No ASR model/device/language was used. No cloud samples or network conditions apply.

Procedure: construct actual AerisAssistant using a temporary DB/audit, disable AI and voice,
simulate executor, warm up once, call `handle('open notepad')` 30 times. Include all 30 results.
This includes routing/validation/simulated executor and SQLite/audit persistence, **not launching Notepad**.

| Metric | Result |
|---|---:|
| Controller construction (single sample, not GUI startup) | 6.039 ms |
| Warm task p50 | 5.186 ms |
| Warm task p95 | 8.499 ms |
| Routing-only p95 | 0.0854 ms |
| Failure rate (30 trials) | 0% |

Raw retained samples: `evidence/local-warm.json`. The first run failed during temporary cleanup with
WinError 32: SQLite connections were not explicitly closed. Fixed MemoryStore._connect and reran;
the failed run is recorded in VALIDATION_REPORT rather than claimed as a successful trial set.
No before/after speedup is asserted.

Reproduce from PowerShell:

```powershell
Set-Location 'C:\AI Related project BY AI\AERIS_AI_ASSISTANT\Aeris'
& '.\.venv\Scripts\python.exe' '.\scripts\measure_local.py' --trials 30 --output '.\docs\evidence\local-warm.json'
```

## Target status

- <150 ms typed deterministic dispatch: narrow simulated synchronous controller sample is below target;
  GUI queue acknowledgment/real dispatch not measured.
- 100 ms visible acknowledgment / 250 ms Stop acknowledgment: not measured.
- Short voice p50 <1.5 s / p95 <3 s: not measured; no audio success claim.
- No-callback deadline: two-second guard retained; calibration/timing fixture coverage remains incomplete.
- Two-second warm main-window startup: not measured.
- Cold launch, model loading/download, UI idle/active CPU/RAM and hidden animation cost: not measured.
- Cloud latency/approval duration/native-adapter quiescence: not measured.

Next: separate approval from tool timing; add GUI queue/render markers, capture/transcription/speech owner events;
measure actual configured devices with 30+ trials and sample process CPU/RAM, including failures and slow trials.