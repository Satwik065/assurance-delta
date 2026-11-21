```python
from __future__ import annotations
from typing import Optional

class QueueSnapshot:
    __slots__ = ("slot", "front_control", "front_bulk")

    def __init__(self, slot: int, front_control: dict[int, Optional[int]], front_bulk: dict[int, Optional[int]]) -> None:
        self.slot = slot
        self.front_control = front_control
        self.front_bulk = front_bulk

    def pending_control_devices(self) -> tuple[int, ...]:
        return tuple(d for d, p in self.front_control.items() if p is not None)

    def pending_bulk_devices(self) -> tuple[int, ...]:
        return tuple(d for d, p in self.front_bulk.items() if p is not None)

class BurstyBulkScheduler:
    def __init__(self) -> None:
        self._last_control: int = -1
        self._last_bulk: int = -1
        self._current_bulk_slot: int = 0
        self._bulk_burst_slots: int = 0

    def choose_next(self, snapshot: QueueSnapshot) -> Optional[int]:
        control_devices = snapshot.pending_control_devices()
        if control_devices:
            device = self._next_after(self._last_control, control_devices)
            self._last_control = device
            return snapshot.front_control[device]

        bulk_devices = snapshot.pending_bulk_devices()
        if bulk_devices:
            if self._bulk_burst_slots >= 10:  # Arbitrary threshold to simulate burstiness
                self._bulk_burst_slots = 0
                return None  # No more bulk devices can be processed until a control device arrives
            else:
                device = self._next_after(self._last_bulk, bulk_devices)
                self._last_bulk = device
                self._bulk_burst_slots += 1
                return snapshot.front_bulk[device]

        return None

    @staticmethod
    def _next_after(last: int, candidates: tuple[int, ...]) -> int:
        ordered = sorted(candidates)
        for c in ordered:
            if c > last:
                return c
        return ordered[0]
```