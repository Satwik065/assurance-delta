import pytest
from gate.gate import evaluate_proposal
from gate.measure import MeasuredMetrics
from ledger.tokens import Token
from variants.legitimate import generate_legit_r0_variant, generate_legit_r3_variant

def test_gate_accepts_legit_r0():
    """Proves the Gate does not falsely reject a valid R0 upgrade."""
    key = "secret"
    variant = generate_legit_r0_variant(seed=42)
    metrics = variant["_simulated_metrics"]
    
    measured = MeasuredMetrics(control_p99=metrics["control"], bulk_p99=metrics["bulk"])
    bounds = {"CONTROL_p99": 7.8, "BULK_p99": 985.53}
    
    result = evaluate_proposal(
        raw_proposal=variant,
        expected_code_hash="hash123",
        evidence_code_hash="hash123",
        measured=measured,
        original_bounds=bounds,
        tokens=[],
        current_slot=500,
        secret_key=key
    )
    
    assert result.status == "ACCEPT"

def test_gate_accepts_legit_r3():
    """Proves the Gate accepts a valid R3 upgrade with a scoped BULK waiver."""
    key = "secret"
    variant = generate_legit_r3_variant(seed=42)
    metrics = variant["_simulated_metrics"]
    
    # R3 requires the token
    token = Token("R3_BULK_WAIVED", "class == 'BULK'", 4927.65, "admin", 10000).sign(key)
    
    measured = MeasuredMetrics(control_p99=metrics["control"], bulk_p99=metrics["bulk"])
    bounds = {"CONTROL_p99": 7.8, "BULK_p99": 985.53}
    
    result = evaluate_proposal(
        raw_proposal=variant,
        expected_code_hash="hash123",
        evidence_code_hash="hash123",
        measured=measured,
        original_bounds=bounds,
        tokens=[token],
        current_slot=500,
        secret_key=key
    )
    
    assert result.status == "ACCEPT"
