```python
from collections import deque
from __future__ import annotations
from typing import Optional, Tuple

class QueueSnapshot:
    """Read-only view of queue fronts at a given slot."""
    __slots__ = ("slot", "front_control", "front_bulk", "bulk_buffer")

    def __init__(self, slot: int, front_control: dict[int, Optional[int]], front_bulk: dict[int, Optional[int]], bulk_buffer: deque[int]) -> None:
        self.slot = slot
        self.front_control = front_control
        self.front_bulk = front_bulk
        self.bulk_buffer = bulk_buffer

    def pending_control_devices(self) -> Tuple[int, ...]:
        return tuple(d for d, p in self.front_control.items() if p is not None)

    def pending_bulk_devices(self) -> Tuple[int, ...]:
        return tuple(d for d, p in self.front_bulk.items() if p is not None)

class BurstyBulkScheduler:
    """Scheduler for bursty BULK traffic with CONTROL latency constraint."""
    MAX_CONTROL_LATENCY = 7.8
    MAX_BULK_LATENCY = 985.53

    def __init__(self) -> None:
        self._last_control: Optional[int] = None
        self._bulk_buffer: deque[int] = deque()
        self._bulk_delay: int = 0

    def choose_next(self, snapshot: QueueSnapshot) -> Optional[int]:
        control_devices = snapshot.pending_control_devices()
        if control_devices:
            device = self._next_after(self._last_control, control_devices)
            self._last_control = device
            return snapshot.front_control[device]

        bulk_devices = snapshot.pending_bulk_devices()
        if bulk_devices:
            next_bulk = self._next_after(self._last_bulk, bulk_devices)
            self._bulk_buffer.append(next_bulk)

            if self._bulk_delay + len(self._bulk_buffer) * 100 > self.MAX_BULK_LATENCY:
                # Buffer is approaching latency limit, prioritize CONTROL
                self._last_bulk = self._last_control
                return self._next_after(self._last_control, control_devices) if control_devices else None

            self._last_bulk = next_bulk
            self._bulk_delay += 100
            return next_bulk

        return None

    @staticmethod
    def _next_after(last: Optional[int], candidates: Tuple[int, ...]) -> int:
        ordered = sorted(candidates)
        for c in ordered:
            if c > last:
                return c
        return ordered[0]
```