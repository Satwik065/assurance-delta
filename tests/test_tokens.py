import pytest
from ledger.tokens import Token

def test_valid_token_verifies():
    key = "super_secret_key"
    t = Token("R3_BULK_WAIVED", "class == 'BULK'", 4927.65, "experimenter", 10000)
    signed = t.sign(key)
    assert signed.verify(key) is True

def test_tampered_token_fails():
    key = "super_secret_key"
    t = Token("R3_BULK_WAIVED", "class == 'BULK'", 4927.65, "experimenter", 10000)
    signed = t.sign(key)
    # Forge the bound to allow infinite trucks
    forged = Token(signed.requirement_id, signed.scope_text, 999999.0, signed.issuer, signed.expiry_slot, signed.signature)
    assert forged.verify(key) is False

def test_wrong_key_fails():
    t = Token("R3_BULK_WAIVED", "class == 'BULK'", 4927.65, "experimenter", 10000)
    signed = t.sign("real_key")
    assert signed.verify("fake_key") is False
