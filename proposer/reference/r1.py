"""R1 Reference Upgrade: Scale-out to N=16.

A hand-written correct scheduler that handles 16 devices while keeping
both CONTROL and BULK within their original bounds.

Design: Strict priority for CONTROL (round-robin within class).
At N=16, CONTROL rate = 0.8/slot (under 1/slot capacity), so the
queue is stable and p99 stays low.

Note: The constitution specified N=32, but calibration revealed that
CONTROL traffic at N=32 (1.6/slot) exceeds the 1/slot uplink capacity.
N=16 is the feasible scale-out point. Documented in RESEARCH_LOG.
"""
from __future__ import annotations
from typing import Optional
from sim.scheduler_base import QueueSnapshot


class R1ReferenceScheduler:
    """Reference scheduler for R1 (N=16). Strict priority + round-robin."""

    def __init__(self) -> None:
        self._last_control: int = -1
        self._last_bulk: int = -1

    def choose_next(self, snapshot: QueueSnapshot) -> Optional[int]:
        control_devices = snapshot.pending_control_devices()
        if control_devices:
            device = self._next_after(self._last_control, control_devices)
            self._last_control = device
            return snapshot.front_control[device]

        bulk_devices = snapshot.pending_bulk_devices()
        if bulk_devices:
            device = self._next_after(self._last_bulk, bulk_devices)
            self._last_bulk = device
            return snapshot.front_bulk[device]

        return None

    @staticmethod
    def _next_after(last: int, candidates: tuple[int, ...]) -> int:
        ordered = sorted(candidates)
        for c in ordered:
            if c > last:
                return c
        return ordered[0]
