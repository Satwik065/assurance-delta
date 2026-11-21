"""C1' Frozen Regression Suite (Spec §5.2).

Reduced SimPy suite: 5 seeds, 5000 slots, encoding R0 bounds.
Checks the MEAN of 5 seeds against the bound (matching calibration methodology).
CONTROL loss must be zero per seed (Spec §4.2).
"""
from __future__ import annotations
from dataclasses import dataclass
from constitution import constants as C
from sim.engine import run
from sim.traffic import TrafficConfig, generate_arrivals
from oracle.audit import audit_departure_log
from oracle.verdict import compute_per_seed_p99, calculate_control_loss

C1_PRIME_SEEDS = 5
C1_PRIME_TOTAL_SLOTS = 5000
C1_PRIME_N_DEVICES = C.R0_N_DEVICES
C1_PRIME_BULK_RATE = 0.01


@dataclass(frozen=True)
class RegressionResult:
    passed: bool
    reason: str
    control_p99s: list
    bulk_p99s: list


def frozen_regression_check(scheduler, n_devices: int = C1_PRIME_N_DEVICES,
                             bulk_rate: float = C1_PRIME_BULK_RATE,
                             total_slots: int = C1_PRIME_TOTAL_SLOTS) -> RegressionResult:
    """Run the reduced oracle suite. PASS if mean p99s meet bounds and CONTROL loss is zero."""
    bounds = C.load_calibrated()
    bound_c = bounds["r0_control_p99_bound_slots"]
    bound_b = bounds["r0_bulk_p99_bound_slots"]

    control_p99s = []
    bulk_p99s = []

    for seed in range(C1_PRIME_SEEDS):
        cfg = TrafficConfig(n_devices, total_slots, bulk_rate, 0.0, seed)
        arrivals = generate_arrivals(cfg)

        try:
            log = run(arrivals, scheduler, n_devices, total_slots)
        except Exception as e:
            return RegressionResult(False, f"ENGINE_ERROR: {e}", [], [])

        violations = audit_departure_log(arrivals, log)
        if violations:
            return RegressionResult(False, f"AUDIT_FAIL: {violations}", [], [])

        # Spec §4.2: CONTROL passes iff zero observed losses (per-seed hard requirement)
        loss = calculate_control_loss(arrivals, log)
        if loss > 0:
            return RegressionResult(False, f"CONTROL loss={loss:.4f} on seed {seed} (must be zero)", control_p99s, bulk_p99s)

        control_p99s.append(compute_per_seed_p99(arrivals, log, "CONTROL"))
        bulk_p99s.append(compute_per_seed_p99(arrivals, log, "BULK"))

    # Check MEAN of 5 seeds against bound (matching calibration methodology)
    mean_c = sum(control_p99s) / len(control_p99s)
    mean_b = sum(bulk_p99s) / len(bulk_p99s)

    if mean_c > bound_c:
        return RegressionResult(False, f"CONTROL mean p99={mean_c:.2f} > {bound_c}", control_p99s, bulk_p99s)
    if mean_b > bound_b:
        return RegressionResult(False, f"BULK mean p99={mean_b:.2f} > {bound_b}", control_p99s, bulk_p99s)

    return RegressionResult(True, "PASS", control_p99s, bulk_p99s)
