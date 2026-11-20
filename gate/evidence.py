"""Gate G3: Checks if the Oracle evidence matches the current code hash."""
from __future__ import annotations

class StaleEvidenceError(RuntimeError):
    pass

def verify_evidence_freshness(expected_code_hash: str, actual_evidence_hash: str) -> None:
    """Ensures the measurements were taken on the exact code being submitted."""
    if expected_code_hash != actual_evidence_hash:
        raise StaleEvidenceError(
            f"STALE_EVIDENCE: The provided evidence was measured on hash "
            f"{actual_evidence_hash}, but the submitted code has hash {expected_code_hash}."
        )
