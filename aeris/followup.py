"""Ephemeral, expiring follow-ups for absolute local controls only."""

import re
import time
from dataclasses import dataclass

from .models import ActionRequest, PlannedResponse


@dataclass
class ControlContext:
    tool: str
    expires_at: float
    simulated: bool


class FollowUpContext:
    def __init__(self, clock=time.monotonic, ttl=30):
        self.clock = clock
        self.ttl = ttl
        self.current = None

    def clear(self):
        self.current = None

    def resolve(self, text, simulated):
        match = re.fullmatch(r"(?:make it|set it to)\s+(\d{1,3})(?:\s*(?:percent|%))?[.!]?", text.strip(), re.I)
        if not match:
            return None
        value = int(match.group(1))
        context = self.current
        if not context or self.clock() >= context.expires_at or context.simulated != simulated:
            self.clear()
            return PlannedResponse(reply="Which control should I set: volume or brightness? The previous context is unavailable or expired.")
        if value > 100:
            return PlannedResponse(reply="Please choose a value between zero and one hundred percent.")
        return PlannedResponse(actions=[ActionRequest(context.tool, {"level": value}, source_text=text)])

    def observe(self, actions, results):
        self.clear()
        if len(actions) == len(results) == 1 and actions[0].tool in {"desktop.set_volume", "desktop.set_brightness"} and results[0].success:
            self.current = ControlContext(actions[0].tool, self.clock() + self.ttl, results[0].dry_run)