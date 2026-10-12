"""30+ warm production-controller trials, simulation only, isolated runtime data."""
import argparse
import json
import platform
import statistics
import sys
import tempfile
import time
from importlib.metadata import version
from pathlib import Path

from aeris.assistant import AerisAssistant
from aeris.config import AerisConfig


def percentile(values, fraction):
    values = sorted(values)
    return values[min(len(values) - 1, int((len(values) - 1) * fraction + 0.5))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 30 <= args.trials <= 1000:
        parser.error("trials must be between 30 and 1000")
    samples = []
    with tempfile.TemporaryDirectory(prefix="aeris-benchmark-") as temporary:
        root = Path(temporary)
        config = AerisConfig(data_dir=root / "data", allowed_paths=(root,), dry_run=True, ai_enabled=False,
                             hands_free=False, coding_workspace=root)
        start = time.perf_counter()
        assistant = AerisAssistant(config)
        construction_ms = (time.perf_counter() - start) * 1000
        assistant.handle("open notepad")
        for _ in range(args.trials):
            start = time.perf_counter()
            turn = assistant.handle("open notepad")
            samples.append({"total_ms": (time.perf_counter() - start) * 1000,
                            "routing_ms": assistant.last_timing.stages["routing"] * 1000,
                            "success": bool(turn.results and turn.results[0].success and turn.results[0].dry_run)})
        assistant.close()
    totals = [item["total_ms"] for item in samples]
    report = {
        "procedure": "One controller warmup then repeated handle('open notepad'); simulated executor; temp database/audit; no cloud, app launch or audio.",
        "python": sys.version, "os": platform.platform(), "processor": platform.processor(),
        "dependencies": {name: version(name) for name in ("pydantic", "PySide6", "pytest")},
        "controller_construction_ms": construction_ms, "trials": args.trials,
        "p50_total_ms": statistics.median(totals), "p95_total_ms": percentile(totals, 0.95),
        "p95_routing_ms": percentile([item["routing_ms"] for item in samples], 0.95),
        "failure_rate": sum(not item["success"] for item in samples) / len(samples), "samples": samples,
        "not_measured": ["cold/warm GUI start", "voice", "speech start", "cloud", "approval wait", "actual device effects", "idle/active CPU and RAM"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "samples"}, indent=2))
    return 0 if report["failure_rate"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())