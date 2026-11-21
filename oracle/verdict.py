"""Computes latency and packet loss verdicts from raw departure logs (Oracle v1.1).

Oracle v1.1 rules (see ERRATA.md):
- Unfinished packets at horizon (reason == "HORIZON", both CONTROL and BULK)
  enter the latency distribution as censored latencies (horizon - arrival_slot).
- Overflow drops (reason == "BUFFER_OVERFLOW") enter as +inf in the percentile.
- An empty latency list returns +inf (never 0.0, never PASS).
- Percentile interpolation explicitly handles +inf endpoints without NaN.
- CONTROL zero-loss rule counts BUFFER_OVERFLOW drops only.
- Amendment D8: bootstrap statistic is mean of per-seed p99s + 95% upper bound
  + >= 19/20 per-seed guard.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
import numpy as np

from constitution import constants as C
from sim.engine import DepartureLog
from sim.traffic import Packet


@dataclass
class VerdictResult:
    passed: bool
    reason: str
    mean_p99: float
    bootstrap_upper_bound: float
    seeds_passing: int


def _safe_percentile(values: list[float], q: float) -> float:
    """Linear-interpolation percentile matching numpy, but +inf-safe (never NaN)."""
    if not values:
        return float("inf")
    ordered = sorted(values)
    n = len(ordered)
    pos = (q / 100.0) * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if math.isinf(ordered[lo]) or math.isinf(ordered[hi]):
        return float("inf")
    if lo == hi:
        return float(ordered[lo])
    frac = pos - lo
    return float(ordered[lo] + frac * (ordered[hi] - ordered[lo]))


def compute_per_seed_p99(
    arrivals: list[Packet],
    log: DepartureLog,
    target_class: str,
    horizon: int | None = None,
) -> float:
    """Calculate v1.1 p99 latency for target_class in a single seed run."""
    latencies: list[float] = [
        float(dep.departure_slot - dep.arrival_slot)
        for dep in log.departures
        if dep.packet_class == target_class
    ]

    eff_horizon = horizon
    if eff_horizon is None:
        max_dep = max((d.departure_slot for d in log.departures), default=0)
        max_arr = max((p.arrival_slot for p in arrivals), default=0)
        eff_horizon = max(max_dep, max_arr)

    for dr in log.drops:
        if dr.packet_class != target_class:
            continue
        if dr.reason == "HORIZON":
            latencies.append(float(max(0, eff_horizon - dr.arrival_slot)))
        else:
            # BUFFER_OVERFLOW (or any non-horizon drop) counts as +inf latency
            latencies.append(float("inf"))

    if not latencies:
        return float("inf")

    return _safe_percentile(latencies, 99.0)


def calculate_control_loss(arrivals: list[Packet], log: DepartureLog) -> float:
    """Fraction of CONTROL packets dropped due to BUFFER_OVERFLOW (overflow-only)."""
    total_control = sum(1 for p in arrivals if p.packet_class == "CONTROL")
    if total_control == 0:
        return 0.0
    dropped_control = sum(
        1 for d in log.drops if d.packet_class == "CONTROL" and d.reason == "BUFFER_OVERFLOW"
    )
    return dropped_control / total_control


def calculate_delivered_fraction(
    arrivals: list[Packet], log: DepartureLog, target_class: str
) -> float:
    """Diagnostic metric (not an obligation): delivered / arrived for target_class."""
    total_arr = sum(1 for p in arrivals if p.packet_class == target_class)
    if total_arr == 0:
        return 0.0
    total_dep = sum(1 for d in log.departures if d.packet_class == target_class)
    return total_dep / total_arr


def bootstrap_upper_bound(
    per_seed_values: list[float], resamples: int = C.BOOTSTRAP_RESAMPLES
) -> float:
    """Resample per-seed values to find the 95% upper bound of the mean (+inf safe)."""
    if not per_seed_values:
        return float("inf")
    rng = np.random.default_rng(seed=42)
    arr = np.asarray(per_seed_values, dtype=float)
    n = len(arr)
    means: list[float] = []
    for _ in range(resamples):
        idx = rng.integers(0, n, size=n)
        sample = arr[idx]
        if not np.all(np.isfinite(sample)):
            means.append(float("inf"))
        else:
            means.append(float(np.mean(sample)))
    return _safe_percentile(means, 95.0)


def evaluate_latency_verdict(
    per_seed_p99s: list[float],
    bound: float,
    min_passing: int = C.PER_SEED_GUARD_MIN_PASSING,
) -> VerdictResult:
    """Apply D8 rule: mean of per-seed p99s + 95% bootstrap upper bound + guard."""
    if not per_seed_p99s:
        return VerdictResult(False, "EMPTY_LATENCY_LIST", float("inf"), float("inf"), 0)

    all_finite = all(math.isfinite(p) for p in per_seed_p99s)
    mean_p99 = float(np.mean(per_seed_p99s)) if all_finite else float("inf")
    upper_bound = bootstrap_upper_bound(per_seed_p99s)
    seeds_passing = sum(1 for p in per_seed_p99s if math.isfinite(p) and p <= bound)

    if seeds_passing < min_passing:
        return VerdictResult(
            False,
            f"GUARD_FAILED: Only {seeds_passing}/{len(per_seed_p99s)} seeds passed (need {min_passing})",
            mean_p99,
            upper_bound,
            seeds_passing,
        )

    if not math.isfinite(upper_bound) or upper_bound > bound:
        return VerdictResult(
            False,
            f"LATENCY_FAILED: Bound {upper_bound:.2f} > {bound}",
            mean_p99,
            upper_bound,
            seeds_passing,
        )

    return VerdictResult(True, "PASS", mean_p99, upper_bound, seeds_passing)
