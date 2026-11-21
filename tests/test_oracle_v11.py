"""Unit tests for Oracle v1.1 fixes, BULK buffer invariance, G5 boundary checks, and M6."""
import math
import pytest

from constitution import constants as C
from sim.traffic import Packet, TrafficConfig, generate_arrivals
from sim.engine import run, DepartureLog, Departure, Drop
from sim.scheduler_base import StrictPriorityRoundRobinScheduler
from oracle.verdict import (
    compute_per_seed_p99,
    calculate_control_loss,
    calculate_delivered_fraction,
    bootstrap_upper_bound,
    evaluate_latency_verdict,
)
from gate.gate import evaluate_proposal
from gate.measure import MeasuredMetrics
from ledger.tokens import Token

SECRET = "v11_test_secret"


def test_empty_latency_list_returns_inf_and_never_passes():
    p99 = compute_per_seed_p99([], DepartureLog([], []), "BULK", horizon=5000)
    assert math.isinf(p99) and p99 > 0
    verdict = evaluate_latency_verdict([p99] * 20, bound=985.53)
    assert verdict.passed is False


def test_overflow_counts_as_inf_without_nan():
    # 100 packets: 98 delivered with latency 10, 2 overflowed -> p99 MUST be +inf, NOT NaN
    arrivals = [Packet(i, 0, "BULK", 0) for i in range(100)]
    deps = [Departure(i, 0, "BULK", 0, 10) for i in range(98)]
    drops = [Drop(98, 0, "BULK", 0, "BUFFER_OVERFLOW"), Drop(99, 0, "BULK", 0, "BUFFER_OVERFLOW")]
    p99 = compute_per_seed_p99(arrivals, DepartureLog(deps, drops), "BULK", horizon=5000)
    assert not math.isnan(p99)
    assert math.isinf(p99) and p99 > 0
    ub = bootstrap_upper_bound([10.0] * 19 + [p99])
    assert not math.isnan(ub)
    assert math.isinf(ub)


def test_horizon_drops_enter_as_censored_latency():
    # 99 delivered with latency 5; 1 unfinished at horizon=5000 arriving at slot 4000 -> censored 1000
    arrivals = [Packet(i, 0, "BULK", 0) for i in range(99)] + [Packet(99, 0, "BULK", 4000)]
    deps = [Departure(i, 0, "BULK", 0, 5) for i in range(99)]
    drops = [Drop(99, 0, "BULK", 4000, "HORIZON")]
    p99 = compute_per_seed_p99(arrivals, DepartureLog(deps, drops), "BULK", horizon=5000)
    assert p99 == pytest.approx(14.95)  # 99th percentile between 5 (idx 98) and 1000 (idx 99): 5 + 0.01*995


def test_control_horizon_drop_enters_p99_but_loss_is_overflow_only():
    arrivals = [Packet(0, 0, "CONTROL", 0), Packet(1, 0, "CONTROL", 4990)]
    deps = [Departure(0, 0, "CONTROL", 0, 2)]
    drops = [Drop(1, 0, "CONTROL", 4990, "HORIZON")]
    log = DepartureLog(deps, drops)
    assert calculate_control_loss(arrivals, log) == 0.0
    p99 = compute_per_seed_p99(arrivals, log, "CONTROL", horizon=5000)
    assert p99 > 9.0  # censored latency = 10 enters p99


def test_delivered_fraction_diagnostic():
    arrivals = [Packet(i, 0, "BULK", 0) for i in range(10)]
    deps = [Departure(i, 0, "BULK", 0, 4) for i in range(7)]
    log = DepartureLog(deps, [])
    assert calculate_delivered_fraction(arrivals, log, "BULK") == pytest.approx(0.7)


def test_bulk_buffer_128_preserves_r0_r1_r2_zero_overflow():
    for n, rate, burst in [(8, 0.02, 0.0), (12, 0.003, 0.0), (8, 0.02, 1.0)]:
        arr = generate_arrivals(TrafficConfig(n, 5000, rate, burst, seed=0))
        log = run(arr, StrictPriorityRoundRobinScheduler(), n, 5000)
        ovf = [d for d in log.drops if d.reason == "BUFFER_OVERFLOW"]
        assert ovf == []


def test_g5_boundary_adjacent_load_rejected_and_inside_accepted():
    tok = Token("R3_BULK", "class == 'BULK' and load <= 0.035", 4927.65, "admin", 10000).sign(SECRET)
    prop = {
        "code_path": "proposed.py",
        "changes": [{
            "id": "R3_BULK", "req_class": "WAIVE", "target_metric": "BULK_p99",
            "new_bound": 4927.65, "scope_text": "class == 'BULK' and load <= 0.035",
        }],
    }
    bounds = {"CONTROL_p99": 7.8, "BULK_p99": 985.53}
    # Inside limit (load == 0.035) -> ACCEPT
    ok = evaluate_proposal(
        prop, "h1", "h1", MeasuredMetrics(5.0, 2000.0), bounds, [tok], 500, SECRET,
        scenario_context={"load": 0.035},
    )
    assert ok.status == "ACCEPT"
    # Just above limit (load == 0.0351) -> SCOPE_MISMATCH
    bad = evaluate_proposal(
        prop, "h1", "h1", MeasuredMetrics(5.0, 2000.0), bounds, [tok], 500, SECRET,
        scenario_context={"load": 0.0351},
    )
    assert bad.status == "REJECT"
    assert bad.code == "SCOPE_MISMATCH"


def test_g5_token_expired_by_one_slot_rejected():
    tok = Token("R3_BULK", "class == 'BULK'", 4927.65, "admin", 1000).sign(SECRET)
    prop = {
        "code_path": "proposed.py",
        "changes": [{
            "id": "R3_BULK", "req_class": "WAIVE", "target_metric": "BULK_p99",
            "new_bound": 4927.65, "scope_text": "class == 'BULK'",
        }],
    }
    bounds = {"CONTROL_p99": 7.8, "BULK_p99": 985.53}
    at_edge = evaluate_proposal(prop, "h", "h", MeasuredMetrics(5.0, 2000.0), bounds, [tok], 1000, SECRET)
    assert at_edge.status == "ACCEPT"
    past_edge = evaluate_proposal(prop, "h", "h", MeasuredMetrics(5.0, 2000.0), bounds, [tok], 1001, SECRET)
    assert past_edge.status == "REJECT"
    assert past_edge.code == "TOKEN_INVALID"


def test_g5_scope_name_variants_rejected():
    bounds = {"CONTROL_p99": 7.8, "BULK_p99": 985.53}
    for bad_scope in ("class == 'bulk'", "class == 'ALL'", "metric == 'BULK'", "class == 'BULK_EXTRA'"):
        tok = Token("R3_BULK", bad_scope, 4927.65, "admin", 10000).sign(SECRET)
        prop = {
            "code_path": "proposed.py",
            "changes": [{
                "id": "R3_BULK", "req_class": "WAIVE", "target_metric": "BULK_p99",
                "new_bound": 4927.65, "scope_text": bad_scope,
            }],
        }
        res = evaluate_proposal(prop, "h", "h", MeasuredMetrics(5.0, 2000.0), bounds, [tok], 500, SECRET)
        assert res.status == "REJECT"
        assert res.code == "SCOPE_MISMATCH"


def test_g4_and_g5_reject_inf_latency():
    bounds = {"CONTROL_p99": 7.8, "BULK_p99": 985.53}
    prop_retain = {
        "code_path": "proposed.py",
        "changes": [{"id": "R0_B", "req_class": "RETAIN", "target_metric": "BULK_p99", "new_bound": 985.53}],
    }
    res_g4 = evaluate_proposal(prop_retain, "h", "h", MeasuredMetrics(5.0, float("inf")), bounds, [], 500, SECRET)
    assert res_g4.status == "REJECT" and res_g4.code == "UNDECLARED_WEAKENING"

    tok = Token("R3_B", "class == 'BULK'", 4927.65, "admin", 10000).sign(SECRET)
    prop_waive = {
        "code_path": "proposed.py",
        "changes": [{"id": "R3_B", "req_class": "WAIVE", "target_metric": "BULK_p99", "new_bound": 4927.65, "scope_text": "class == 'BULK'"}],
    }
    res_g5 = evaluate_proposal(prop_waive, "h", "h", MeasuredMetrics(5.0, float("inf")), bounds, [tok], 500, SECRET)
    assert res_g5.status == "REJECT" and res_g5.code == "TOKEN_INVALID"
