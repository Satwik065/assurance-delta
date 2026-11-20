import pytest
from gate.scope_check import verify_waive, TokenInvalidError, ScopeMismatchError
from ledger.tokens import Token
from proposer.schema import RequirementChange

def test_valid_waive_passes():
    key = "secret"
    change = RequirementChange("R3_BULK", "WAIVE", "BULK_p99", 4927.65, "class == 'BULK'")
    token = Token("R3_BULK", "class == 'BULK'", 4927.65, "admin", 1000).sign(key)
    
    # Measured 4000, which is < 4927.65. Should not raise.
    verify_waive(change, token, measured_val=4000.0, current_slot=500, secret_key=key)

def test_forged_token_caught():
    change = RequirementChange("R3_BULK", "WAIVE", "BULK_p99", 4927.65, "class == 'BULK'")
    token = Token("R3_BULK", "class == 'BULK'", 999999.0, "admin", 1000).sign("wrong_key")
    
    with pytest.raises(TokenInvalidError, match="TOKEN_INVALID: Signature is forged"):
        verify_waive(change, token, measured_val=4000.0, current_slot=500, secret_key="secret")

def test_expired_token_caught():
    key = "secret"
    change = RequirementChange("R3_BULK", "WAIVE", "BULK_p99", 4927.65, "class == 'BULK'")
    token = Token("R3_BULK", "class == 'BULK'", 4927.65, "admin", expiry_slot=100).sign(key)
    
    # Current slot is 500, which is > 100
    with pytest.raises(TokenInvalidError, match="TOKEN_INVALID: Token has expired"):
        verify_waive(change, token, measured_val=4000.0, current_slot=500, secret_key=key)

def test_measured_exceeds_bound_caught():
    key = "secret"
    change = RequirementChange("R3_BULK", "WAIVE", "BULK_p99", 4927.65, "class == 'BULK'")
    token = Token("R3_BULK", "class == 'BULK'", 4927.65, "admin", 1000).sign(key)
    
    # Measured 6000, which is > 4927.65
    with pytest.raises(TokenInvalidError, match="TOKEN_INVALID: Measured 6000.0 exceeds token bound"):
        verify_waive(change, token, measured_val=6000.0, current_slot=500, secret_key=key)

def test_scope_mismatch_caught():
    # This is Mutant M3c: AI uses a BULK token to waive CONTROL
    key = "secret"
    change = RequirementChange("R3_CONTROL", "WAIVE", "CONTROL_p99", 7.8, "class == 'BULK'")
    token = Token("R3_CONTROL", "class == 'BULK'", 4927.65, "admin", 1000).sign(key)
    
    with pytest.raises(ScopeMismatchError, match="SCOPE_MISMATCH"):
        verify_waive(change, token, measured_val=5.0, current_slot=500, secret_key=key)
