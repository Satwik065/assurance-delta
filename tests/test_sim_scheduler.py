from sim.scheduler_base import QueueSnapshot, StrictPriorityRoundRobinScheduler

def _snapshot(slot, fc, fb):
    return QueueSnapshot(slot=slot, front_control=fc, front_bulk=fb)

def test_empty_snapshot_returns_none():
    s = StrictPriorityRoundRobinScheduler()
    assert s.choose_next(_snapshot(0, {0: None}, {0: None})) is None

def test_control_preferred_over_bulk():
    s = StrictPriorityRoundRobinScheduler()
    snap = _snapshot(0, {0: 100, 1: None}, {0: 200, 1: None})
    assert s.choose_next(snap) == 100

def test_round_robin_within_control():
    s = StrictPriorityRoundRobinScheduler()
    snap = _snapshot(0, {0: 10, 1: 20}, {0: None, 1: None})
    first = s.choose_next(snap)
    second = s.choose_next(snap)
    assert {first, second} == {10, 20}
    assert first != second
