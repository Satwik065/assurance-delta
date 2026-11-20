import pytest
from ledger.tokens import Token
from ledger.ledger import Ledger

def test_ledger_append_and_verify():
    ledger = Ledger()
    t1 = Token("R1", "class == 'BULK'", 100, "admin", 1000).sign("key")
    t2 = Token("R2", "class == 'BULK'", 200, "admin", 2000).sign("key")
    
    ledger.append("ISSUE", t1)
    ledger.append("ISSUE", t2)
    
    assert ledger.verify_chain() is True
    assert len(ledger.entries) == 2

def test_ledger_tampering_detected():
    ledger = Ledger()
    t1 = Token("R1", "class == 'BULK'", 100, "admin", 1000).sign("key")
    ledger.append("ISSUE", t1)
    
    # Try to rewrite history by modifying the ledger entry directly
    bad_entry = ledger.entries[0]
    forged_token = Token("R1", "class == 'CONTROL'", 100, "admin", 1000).sign("key")
    
    # Create a fake entry that looks like the original but has forged data
    from ledger.ledger import LedgerEntry
    fake_entry = LedgerEntry("ISSUE", forged_token, bad_entry.prev_hash, bad_entry.entry_hash)
    
    ledger.entries[0] = fake_entry
    
    # The math won't add up
    assert ledger.verify_chain() is False
