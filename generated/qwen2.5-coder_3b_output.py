```python
from __future__ import annotations
from typing import Optional

class QueueSnapshot:
    """Read-only view of queue fronts at a given slot."""
    __slots__ = ("slot", "front_control", "front_bulk")

    def __init__(self, slot: int, front_control: dict[int, Optional[int]], front_bulk: dict[int, Optional[int]]) -> None:
        self.slot = slot
        self.front_control = front_control
        self.front_bulk = front_bulk

    def pending_control_devices(self) -> tuple[int, ...]:
        return tuple(d for d, p in self.front_control.items() if p is not None)

    def pending_bulk_devices(self) -> tuple[int, ...]:
        return tuple(d for d, p in self.front_bulk.items() if p is not None)

class ProposedScheduler:
    """A scheduler that prioritizes CONTROL packets over BULK packets."""
    def choose_next(self, snapshot: QueueSnapshot) -> Optional[int]:
        control_devices = snapshot.pending_control_devices()
        if control_devices:
            return snapshot.front_control[control_devices[0]]

        bulk_devices = snapshot.pending_bulk_devices()
        if bulk_devices:
            return snapshot.front_bulk[bulk_devices[0]]

        return None
```