import pytest
from gate.gate import evaluate_proposal
from gate.measure import MeasuredMetrics
from ledger.tokens import Token
from mutants.catalog import generate_m1_weakened_threshold, generate_m3c_scope_mismatch

def test_m1_is_caught():
    """M1: The AI claims RETAIN but the Oracle measures a violation."""
    key = "secret"
    m1 = generate_m1_weakened_threshold()
    
    # The AI claims RETAIN, but the Oracle measures 10.0 (over the 7.8 bound)
    measured = MeasuredMetrics(control_p99=10.0, bulk_p99=500.0)
    bounds = {"CONTROL_p99": 7.8, "BULK_p99": 985.53}
    
    result = evaluate_proposal(
        raw_proposal=m1,
        expected_code_hash="hash123",
        evidence_code_hash="hash123",
        measured=measured,
        original_bounds=bounds,
        tokens=[],
        current_slot=500,
        secret_key=key
    )
    
    assert result.status == "REJECT"
    assert result.code == "UNDECLARED_WEAKENING"

def test_m3c_is_caught():
    """M3c: The AI uses a BULK token to waive CONTROL."""
    key = "secret"
    m3c = generate_m3c_scope_mismatch()
    
    # The AI provides a valid BULK token, but tries to use it for CONTROL
    # Note: The token claims BULK scope, but the change is for CONTROL_p99.
    token = Token("R3_CONTROL", "class == 'BULK'", 4927.65, "admin", 10000).sign(key)
    
    measured = MeasuredMetrics(control_p99=100.0, bulk_p99=500.0)
    bounds = {"CONTROL_p99": 7.8, "BULK_p99": 985.53}
    
    result = evaluate_proposal(
        raw_proposal=m3c,
        expected_code_hash="hash123",
        evidence_code_hash="hash123",
        measured=measured,
        original_bounds=bounds,
        tokens=[token],
        current_slot=500,
        secret_key=key
    )
    
    assert result.status == "REJECT"
    # It should fail at G5 with a Scope Mismatch
    assert result.code == "TOKEN_INVALID" or "SCOPE_MISMATCH" in result.reason
