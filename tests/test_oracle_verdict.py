import pytest
from oracle.verdict import evaluate_latency_verdict, calculate_control_loss, compute_per_seed_p99
from sim.engine import DepartureLog, Departure, Drop
from sim.traffic import Packet

def test_loss_calculation():
    arrivals = [Packet(0, 0, "CONTROL", 0), Packet(1, 0, "CONTROL", 0)]
    drops = [Drop(1, 0, "CONTROL", 0, "BUFFER_OVERFLOW")]
    log = DepartureLog(departures=[], drops=drops)
    # 1 drop out of 2 arrivals = 50% loss
    assert calculate_control_loss(arrivals, log) == 0.5

def test_per_seed_p99():
    # Latencies: 1, 2, 3, 4, 5, ..., 100
    arrivals = [Packet(i, 0, "CONTROL", 0) for i in range(100)]
    deps = [Departure(i, 0, "CONTROL", 0, i+1) for i in range(100)]
    log = DepartureLog(departures=deps, drops=[])
    # p99 of 1 to 100 is exactly 99.01 (numpy linear interpolation)
    assert compute_per_seed_p99(arrivals, log, "CONTROL") == pytest.approx(99.01)

def test_latency_verdict_passes_cleanly():
    # 20 seeds, all p99 = 10.0. Bound is 15.0.
    per_seed = [10.0] * 20
    res = evaluate_latency_verdict(per_seed, bound=15.0)
    assert res.passed is True
    assert res.seeds_passing == 20
    assert res.mean_p99 == 10.0

def test_latency_verdict_fails_guard():
    # 18 seeds pass at 10.0, but 2 seeds fail at 20.0. Bound is 15.0.
    # The mean would be 11.0 (which is under 15), but the guard MUST catch it.
    per_seed = [10.0] * 18 + [20.0] * 2
    res = evaluate_latency_verdict(per_seed, bound=15.0)
    assert res.passed is False
    assert res.seeds_passing == 18
    assert "GUARD_FAILED" in res.reason

def test_latency_verdict_fails_bootstrap():
    # All seeds pass the guard (all = 14.0, bound = 15.0).
    # But wait, let's set the bound to 13.0. 
    # All 20 seeds fail the bound (14 > 13), so the guard will catch it.
    per_seed = [14.0] * 20
    res = evaluate_latency_verdict(per_seed, bound=13.0)
    assert res.passed is False
    assert res.seeds_passing == 0
    assert "GUARD_FAILED" in res.reason
