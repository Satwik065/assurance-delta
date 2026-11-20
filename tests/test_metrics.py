import pytest
from metrics.wilson import wilson_interval

def test_wilson_20_out_of_20():
    # 20/20 caught
    lower, upper = wilson_interval(20, 20)
    # The spec says the lower bound for 20/20 is roughly 0.83
    assert round(lower, 2) == 0.84  # exact Wilson lower bound is 0.8388...
    assert upper == 1.0

def test_wilson_12_out_of_12():
    # Spec amendment: 12 caught with zero misses -> LB 0.75
    lower, upper = wilson_interval(12, 12)
    assert round(lower, 2) == 0.76  # exact is 0.7575...
    
def test_wilson_2_out_of_20():
    # Spec nit: 2 rejections in 20 -> UB ~ 0.30
    lower, upper = wilson_interval(2, 20)
    assert round(upper, 2) == 0.30
