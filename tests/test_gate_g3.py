import pytest
from gate.evidence import verify_evidence_freshness, StaleEvidenceError

def test_fresh_evidence_passes():
    # Should not raise
    verify_evidence_freshness("hash123", "hash123")

def test_stale_evidence_caught():
    with pytest.raises(StaleEvidenceError, match="STALE_EVIDENCE"):
        verify_evidence_freshness("hash123", "hash_old")
