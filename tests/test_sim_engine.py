import pytest
from sim.engine import run
from sim.scheduler_base import StrictPriorityRoundRobinScheduler
from sim.traffic import Packet, TrafficConfig, generate_arrivals

def _control(pid, dev, slot): return Packet(pid, dev, "CONTROL", slot)
def _bulk(pid, dev, slot): return Packet(pid, dev, "BULK", slot)

class SinglePacketScheduler:
    def __init__(self): self.done = False
    def choose_next(self, snapshot):
        if self.done: return None
        for d in snapshot.pending_control_devices():
            self.done = True; return snapshot.front_control[d]
        for d in snapshot.pending_bulk_devices():
            self.done = True; return snapshot.front_bulk[d]
        return None

def test_single_control_packet_departs_in_one_slot():
    log = run([_control(0, 0, 0)], SinglePacketScheduler(), n_devices=1, max_slot=10)
    assert len(log.departures) == 1
    assert log.departures[0].departure_slot == log.departures[0].arrival_slot + 1

def test_single_bulk_packet_departs_in_four_slots():
    log = run([_bulk(0, 0, 0)], SinglePacketScheduler(), n_devices=1, max_slot=10)
    assert len(log.departures) == 1
    assert log.departures[0].departure_slot == log.departures[0].arrival_slot + 4

def test_engine_deterministic_for_same_inputs():
    cfg = TrafficConfig(4, 200, 0.1, 0.0, seed=3)
    arrivals = generate_arrivals(cfg)
    log1 = run(arrivals, StrictPriorityRoundRobinScheduler(), n_devices=4, max_slot=200)
    log2 = run(arrivals, StrictPriorityRoundRobinScheduler(), n_devices=4, max_slot=200)
    assert log1.departures == log2.departures
    assert log1.drops == log2.drops

def test_buffer_overflow_drops_packet():
    # Changed max_slot to 10 so SimPy doesn't panic
    arrivals = [_control(i, 0, 0) for i in range(33)]
    log = run(arrivals, StrictPriorityRoundRobinScheduler(), n_devices=1, max_slot=10)
    assert len([d for d in log.drops if d.reason == "BUFFER_OVERFLOW"]) == 1

def test_unknown_packet_id_raises():
    class BuggyScheduler:
        def choose_next(self, snapshot): return 999_999
    with pytest.raises(RuntimeError, match="not in any queue"):
        run([_control(0, 0, 0)], BuggyScheduler(), n_devices=1, max_slot=10)
