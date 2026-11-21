"""R3 Reference Upgrade: Higher BULK load with scoped WAIVE.

A hand-written correct scheduler that handles higher BULK load while
keeping CONTROL strict and BULK under the waived bound (5x original).

Design: Strict priority for CONTROL (unchanged). BULK is served only
when no CONTROL is pending. The BULK latency rises but stays under
the waived bound of 4927.65 slots.

The WAIVE token is scoped to class == 'BULK', so CONTROL remains strict.
"""
from __future__ import annotations
from typing import Optional
from sim.scheduler_base import QueueSnapshot


class R3ReferenceScheduler:
    """Reference scheduler for R3. Strict priority + round-robin.
    Same algorithm as baseline — the waiver is in the requirement, not the code."""

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
