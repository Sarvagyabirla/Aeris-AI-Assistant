import time
import logging

class StageTimer:
    def __init__(self, logger_name: str = "aeris.timing"):
        self.logger = logging.getLogger(logger_name)
        self.stages = {}
        self.start_times = {}

    def start(self, stage_name: str):
        self.start_times[stage_name] = time.perf_counter()

    def end(self, stage_name: str):
        if stage_name in self.start_times:
            elapsed = time.perf_counter() - self.start_times.pop(stage_name)
            self.stages[stage_name] = elapsed
            self.logger.info(f"[TIMING] {stage_name}: {elapsed:.4f}s")
            return elapsed
        return 0.0

    def get_results(self) -> dict[str, float]:
        return self.stages

    def reset(self):
        self.stages.clear()
        self.start_times.clear()

global_timer = StageTimer()
