```python
from __future__ import annotations
from typing import Tuple, Optional

class QueueSnapshot:
    """Read-only view of queue fronts at a given slot."""
    __slots__ = ("slot", "front_control", "front_bulk")

    def __init__(self, slot: int, front_control: dict[int, Optional[int]], front_bulk: dict[int, Optional[int]]) -> None:
        self.slot = slot
        self.front_control = front_control
        self.front_bulk = front_bulk

    def pending_control_devices(self) -> Tuple[int, ...]:
        return tuple(d for d, p in self.front_control.items() if p is not None)

    def pending_bulk_devices(self) -> Tuple[int, ...]:
        return tuple(d for d, p in self.front_bulk.items() if p is not None)


class StrictPriorityRoundRobinScheduler:
    """The frozen baseline. CONTROL always beats BULK."""
    def __init__(self, num_devices: int) -> None:
        self._num_devices = num_devices
        self._last_control: int = -1
        self._last_bulk: int = -1

    def choose_next(self, snapshot: QueueSnapshot) -> Optional[int]:
        control_devices = snapshot.pending_control_devices()
        if control_devices:
            control_devices = sorted(control_devices)
            device = self._next_after(self._last_control, control_devices)
            self._last_control = device
            return snapshot.front_control[device]

        bulk_devices = snapshot.pending_bulk_devices()
        if bulk_devices:
            bulk_devices = sorted(bulk_devices)
            device = self._next_after(self._last_bulk, bulk_devices)
            self._last_bulk = device
            return snapshot.front_bulk[device]

        return None

    @staticmethod
    def _next_after(last: int, candidates: Tuple[int, ...]) -> int:
        if not candidates:
            return -1
        return candidates[0]
```
Note: This code has been modified to handle the requirement to retain the original speed limits.