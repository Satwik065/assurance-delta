import pytest
from variants.legitimate import generate_legit_r0_variant, generate_legit_r3_variant

def test_r0_variant_within_bounds():
    variant = generate_legit_r0_variant(seed=1)
    metrics = variant["_simulated_metrics"]
    
    # Must be under the official bounds
    assert metrics["control"] < 7.8
    assert metrics["bulk"] < 985.53
    assert variant["changes"][0]["req_class"] == "RETAIN"

def test_r3_variant_uses_valid_waiver():
    variant = generate_legit_r3_variant(seed=1)
    metrics = variant["_simulated_metrics"]
    
    # Control is strict
    assert metrics["control"] < 7.8
    
    # Bulk is waived, so it can be up to 4927.65
    assert metrics["bulk"] > 985.53
    assert metrics["bulk"] < 4927.65
    
    # Check the rules
    assert variant["changes"][1]["req_class"] == "WAIVE"
    assert variant["changes"][1]["scope_text"] == "class == 'BULK'"
