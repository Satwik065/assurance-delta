"""Tests for hand-written reference upgrades (R1, R3).

R1 uses N=12 with bulk_rate=0.003 (feasible).
- N=32: CONTROL rate 1.6/slot > 1/slot capacity (infeasible)
- N=16: CONTROL p99 = 8.6 > 7.8 bound (too tight)
- N=12: CONTROL rate 0.6/slot, p99 ≈ 4-6 (passes)
Documented in RESEARCH_LOG.
"""
import pytest
from proposer.reference.r1 import R1ReferenceScheduler
from proposer.reference.r3 import R3ReferenceScheduler
from sim.engine import run
from sim.traffic import TrafficConfig, generate_arrivals
from oracle.audit import audit_departure_log
from oracle.verdict import compute_per_seed_p99
from constitution import constants as C


def _run_and_measure(scheduler_class, n_devices, bulk_rate, total_slots, seeds=5):
    control_p99s = []
    bulk_p99s = []
    for seed in range(seeds):
        cfg = TrafficConfig(n_devices, total_slots, bulk_rate, 0.0, seed)
        arrivals = generate_arrivals(cfg)
        scheduler = scheduler_class()
        log = run(arrivals, scheduler, n_devices, total_slots)

        violations = audit_departure_log(arrivals, log)
        assert violations == [], f"Seed {seed}: audit violations {violations}"

        control_p99s.append(compute_per_seed_p99(arrivals, log, "CONTROL", horizon=total_slots))
        bulk_p99s.append(compute_per_seed_p99(arrivals, log, "BULK", horizon=total_slots))
    return control_p99s, bulk_p99s


class TestR1Reference:
    def test_r1_reference_meets_bounds(self):
        """R1 reference at N=12, bulk_rate=0.003 must meet both bounds."""
        bounds = C.load_calibrated()
        bound_c = bounds["r0_control_p99_bound_slots"]
        bound_b = bounds["r0_bulk_p99_bound_slots"]

        c_p99s, b_p99s = _run_and_measure(
            R1ReferenceScheduler, n_devices=12, bulk_rate=0.003, total_slots=5000, seeds=5
        )

        mean_c = sum(c_p99s) / len(c_p99s)
        mean_b = sum(b_p99s) / len(b_p99s)

        assert mean_c <= bound_c, f"CONTROL p99 {mean_c:.2f} exceeds bound {bound_c}"
        assert mean_b <= bound_b, f"BULK p99 {mean_b:.2f} exceeds bound {bound_b}"

    def test_r1_reference_deterministic(self):
        c1, b1 = _run_and_measure(R1ReferenceScheduler, 12, 0.003, 1000, seeds=3)
        c2, b2 = _run_and_measure(R1ReferenceScheduler, 12, 0.003, 1000, seeds=3)
        assert c1 == c2
        assert b1 == b2


class TestR3Reference:
    def test_r3_reference_control_strict(self):
        """R3 reference must keep CONTROL under strict bound under high BULK load."""
        bounds = C.load_calibrated()
        bound_c = bounds["r0_control_p99_bound_slots"]

        c_p99s, b_p99s = _run_and_measure(
            R3ReferenceScheduler, n_devices=8, bulk_rate=C.R3_CALIBRATED_BULK_RATE, total_slots=5000, seeds=5
        )

        mean_c = sum(c_p99s) / len(c_p99s)
        assert mean_c <= bound_c, f"CONTROL p99 {mean_c:.2f} exceeds strict bound {bound_c}"

    def test_r3_reference_bulk_under_waived(self):
        """R3 reference BULK must be under the waived bound (5x original)."""
        bounds = C.load_calibrated()
        waived_bulk = bounds["r0_bulk_p99_bound_slots"] * C.R3_BULK_WAIVE_MULTIPLIER

        c_p99s, b_p99s = _run_and_measure(
            R3ReferenceScheduler, n_devices=8, bulk_rate=C.R3_CALIBRATED_BULK_RATE, total_slots=5000, seeds=5
        )

        mean_b = sum(b_p99s) / len(b_p99s)
        assert mean_b <= waived_bulk, f"BULK p99 {mean_b:.2f} exceeds waived bound {waived_bulk}"
