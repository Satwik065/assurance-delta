"""Computes latency and packet loss verdicts from the raw departure logs.

Amendment D8: The bootstrap statistic is the mean of per-seed p99s.
Guard: At least 19 of 20 seeds must individually pass the latency bound.
"""
from __future__ import annotations
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

def compute_per_seed_p99(arrivals: list[Packet], log: DepartureLog, target_class: str) -> float:
    """Calculates the p99 latency for a specific class in a single run."""
    latencies = []
    for dep in log.departures:
        if dep.packet_class == target_class:
            latencies.append(dep.departure_slot - dep.arrival_slot)
            
    if not latencies:
        return 0.0
    # np.percentile with 99 gives the p99 value
    return float(np.percentile(latencies, 99))

def calculate_control_loss(arrivals: list[Packet], log: DepartureLog) -> float:
    """Returns the fraction of CONTROL packets that were dropped."""
    total_control = sum(1 for p in arrivals if p.packet_class == "CONTROL")
    if total_control == 0:
        return 0.0
    dropped_control = sum(1 for d in log.drops if d.packet_class == "CONTROL" and d.reason == "BUFFER_OVERFLOW")
    return dropped_control / total_control

def bootstrap_upper_bound(per_seed_values: list[float], resamples: int = C.BOOTSTRAP_RESAMPLES) -> float:
    """Resamples the 20 per-seed values to find the 95% upper bound of the mean."""
    if not per_seed_values:
        return 0.0
    rng = np.random.default_rng(seed=42) # fixed seed for deterministic tests
    means = []
    for _ in range(resamples):
        # Sample with replacement
        sample = rng.choice(per_seed_values, size=len(per_seed_values), replace=True)
        means.append(np.mean(sample))
    return float(np.percentile(means, 95))

def evaluate_latency_verdict(per_seed_p99s: list[float], bound: float) -> VerdictResult:
    """Applies the D8 rule: mean of p99s + 95% bootstrap bound + 19/20 guard."""
    mean_p99 = float(np.mean(per_seed_p99s))
    upper_bound = bootstrap_upper_bound(per_seed_p99s)
    
    seeds_passing = sum(1 for p in per_seed_p99s if p <= bound)
    
    # Check the guard first
    if seeds_passing < C.PER_SEED_GUARD_MIN_PASSING:
        return VerdictResult(False, f"GUARD_FAILED: Only {seeds_passing}/20 seeds passed", mean_p99, upper_bound, seeds_passing)
        
    # Check the bootstrap bound
    if upper_bound > bound:
        return VerdictResult(False, f"LATENCY_FAILED: Bound {upper_bound:.2f} > {bound}", mean_p99, upper_bound, seeds_passing)
        
    return VerdictResult(True, "PASS", mean_p99, upper_bound, seeds_passing)
