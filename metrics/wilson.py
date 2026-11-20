"""Calculates Wilson confidence intervals for detection/rejection rates."""
from __future__ import annotations
import math

def wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """Returns the (lower, upper) 95% Wilson confidence interval.
    z=1.96 corresponds to 95% confidence.
    """
    if trials == 0:
        return (0.0, 1.0)
        
    p = successes / trials
    denominator = 1 + (z**2 / trials)
    centre = (p + (z**2 / (2 * trials))) / denominator
    margin = (z * math.sqrt((p * (1 - p) / trials) + (z**2 / (4 * trials**2)))) / denominator
    
    lower = max(0.0, centre - margin)
    upper = min(1.0, centre + margin)
    return (lower, upper)
