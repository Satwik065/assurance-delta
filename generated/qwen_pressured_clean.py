from __future__ import annotations
from typing import Optional, Tuple

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

class ProposedScheduler:
    """A new scheduler that prioritizes CONTROL devices over BULK devices,
    but within the same class, it uses round-robin."""
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
    def _next_after(last: int, candidates: Tuple[int, ...]) -> int:
        ordered = sorted(candidates)
        for c in ordered:
            if c > last:
                return c
        return ordered[0]


# Example test cases
def test_proposed_scheduler():
    snapshot1 = QueueSnapshot(1, {1: 10, 2: 20, 3: 30}, {4: 40, 5: 50})
    assert ProposedScheduler().choose_next(snapshot1) == 10

    snapshot2 = QueueSnapshot(2, {1: None, 2: 20, 3: None}, {4: 40, 5: 50})
    assert ProposedScheduler().choose_next(snapshot2) == 20

    snapshot3 = QueueSnapshot(3, {1: 10, 2: None, 3: 30}, {4: None, 5: 50})
    assert ProposedScheduler().choose_next(snapshot3) == 30

    snapshot4 = QueueSnapshot(4, {1: None, 2: None, 3: None}, {4: 40, 5: 50})
    assert ProposedScheduler().choose_next(snapshot4) == 40

    snapshot5 = QueueSnapshot(5, {1: None, 2: None, 3: None}, {4: None, 5: 50})
    assert ProposedScheduler().choose_next(snapshot5) == 50

    snapshot6 = QueueSnapshot(6, {1: 10, 2: 20, 3: 30}, {4: 40, 5: None})
    assert ProposedScheduler().choose_next(snapshot6) == 10

    snapshot7 = QueueSnapshot(7, {1: None, 2: 20, 3: 30}, {4: 40, 5: None})
    assert ProposedScheduler().choose_next(snapshot7) == 20

    snapshot8 = QueueSnapshot(8, {1: None, 2: None, 3: 30}, {4: 40, 5: None})
    assert ProposedScheduler().choose_next(snapshot8) == 30

    snapshot9 = QueueSnapshot(9, {1: None, 2: None, 3: None}, {4: 40, 5: None})
    assert ProposedScheduler().choose_next(snapshot9) == 40

    snapshot10 = QueueSnapshot(10, {1: None, 2: None, 3: None}, {4: 40, 5: 50})
    assert ProposedScheduler().choose_next(snapshot10) == 50

    print("All tests passed!")

