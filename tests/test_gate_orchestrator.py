from gate.gate import evaluate_proposal
from gate.measure import MeasuredMetrics
from ledger.tokens import Token

def _base_proposal():
    return {
        "code_path": "scheduler.py",
        "changes": [
            {"id": "R0_CONTROL", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": 7.8},
            {"id": "R3_BULK", "req_class": "WAIVE", "target_metric": "BULK_p99", "new_bound": 4927.65, "scope_text": "class == 'BULK'"}
        ]
    }

def test_fully_legal_proposal_accepted():
    key = "secret"
    token = Token("R3_BULK", "class == 'BULK'", 4927.65, "admin", 10000).sign(key)
    
    # CONTROL is 5.0 (passes 7.8). BULK is 4000 (passes waived 4927.65).
    measured = MeasuredMetrics(control_p99=5.0, bulk_p99=4000.0)
    bounds = {"CONTROL_p99": 7.8, "BULK_p99": 985.53}
    
    result = evaluate_proposal(
        raw_proposal=_base_proposal(),
        expected_code_hash="hash123",
        evidence_code_hash="hash123",
        measured=measured,
        original_bounds=bounds,
        tokens=[token],
        current_slot=500,
        secret_key=key
    )
    assert result.status == "ACCEPT"

def test_undeclared_weakening_rejected():
    key = "secret"
    token = Token("R3_BULK", "class == 'BULK'", 4927.65, "admin", 10000).sign(key)
    
    # CONTROL is 9.0 (fails the 7.8 bound!)
    measured = MeasuredMetrics(control_p99=9.0, bulk_p99=4000.0)
    bounds = {"CONTROL_p99": 7.8, "BULK_p99": 985.53}
    
    result = evaluate_proposal(
        raw_proposal=_base_proposal(),
        expected_code_hash="hash123",
        evidence_code_hash="hash123",
        measured=measured,
        original_bounds=bounds,
        tokens=[token],
        current_slot=500,
        secret_key=key
    )
    assert result.status == "REJECT"
    assert result.code == "UNDECLARED_WEAKENING"

def test_missing_token_rejected():
    # We provide a WAIVE, but forget to give the token
    measured = MeasuredMetrics(control_p99=5.0, bulk_p99=4000.0)
    bounds = {"CONTROL_p99": 7.8, "BULK_p99": 985.53}
    
    result = evaluate_proposal(
        raw_proposal=_base_proposal(),
        expected_code_hash="hash123",
        evidence_code_hash="hash123",
        measured=measured,
        original_bounds=bounds,
        tokens=[], # Empty!
        current_slot=500,
        secret_key="secret"
    )
    assert result.status == "REJECT"
    assert result.code == "TOKEN_INVALID"
