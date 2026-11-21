"""Tests for the complete mutant catalog (M1-M7) and conflict certificate."""
import pytest
from mutants.catalog_complete import (
    generate_all_mutants, generate_by_type, get_all_types,
    generate_m1, generate_m3c, generate_m4, generate_m7,
)
from ledger.conflict_certificate import (
    R4_CERTIFICATE, R4_CERTIFICATE_FROZEN_HASH,
    check_conflict_certificate, verify_certificate_integrity, ConflictError,
)
from gate.gate import evaluate_proposal, GateResult


SECRET = "pilot_secret_key"

def _eval(case):
    return evaluate_proposal(
        raw_proposal=case.raw_proposal,
        expected_code_hash=case.expected_code_hash,
        evidence_code_hash=case.evidence_code_hash,
        measured=case.measured,
        original_bounds=case.original_bounds,
        tokens=case.tokens,
        current_slot=case.current_slot,
        secret_key=case.secret_key,
    )


class TestCompleteCatalog:
    def test_all_types_present(self):
        assert set(get_all_types()) == {"M1", "M2", "M3a", "M3b", "M3c", "M4", "M5", "M6", "M7"}

    def test_total_count(self):
        all_cases = generate_all_mutants()
        # M1-M5, M7: 5+5=10 each = 70. M3c: 5+5=10. M6: 2+2=4. Total = 84.
        assert len(all_cases) == 84, f"Expected 84, got {len(all_cases)}"

    def test_dev_holdout_balance(self):
        all_cases = generate_all_mutants()
        dev = sum(1 for c in all_cases if c.variant == "dev")
        hold = sum(1 for c in all_cases if c.variant == "holdout")
        assert dev == 42
        assert hold == 42

    @pytest.mark.parametrize("mutant_id", ["M1", "M2", "M3a", "M3b", "M3c", "M4", "M5", "M7"])
    def test_mutant_dev_caught(self, mutant_id):
        cases = generate_by_type(mutant_id, variant="dev")
        for case in cases:
            result = _eval(case)
            assert result.status == "REJECT", f"{case.name}: expected REJECT, got {result.status}"

    @pytest.mark.parametrize("mutant_id", ["M1", "M2", "M3a", "M3b", "M3c", "M4", "M5", "M7"])
    def test_mutant_holdout_caught(self, mutant_id):
        cases = generate_by_type(mutant_id, variant="holdout")
        for case in cases:
            result = _eval(case)
            assert result.status == "REJECT", f"{case.name}: expected REJECT, got {result.status}"

    def test_m6_stretch_accepted(self):
        cases = generate_by_type("M6", variant="dev")
        for case in cases:
            result = _eval(case)
            assert result.status == "ACCEPT", f"{case.name}: M6 stretch — expected ACCEPT"

    def test_m3c_caught_by_scope_mismatch(self):
        cases = generate_m3c(variant="dev", count=5)
        for case in cases:
            result = _eval(case)
            assert result.code == "SCOPE_MISMATCH"

    def test_m4_caught_by_token_invalid(self):
        cases = generate_m4(variant="dev", count=5)
        for case in cases:
            result = _eval(case)
            assert result.code == "TOKEN_INVALID"

    def test_m7_caught_by_stale_evidence(self):
        cases = generate_m7(variant="dev", count=5)
        for case in cases:
            result = _eval(case)
            assert result.code == "STALE_EVIDENCE"


class TestConflictCertificate:
    def test_r4_is_conflict(self):
        assert R4_CERTIFICATE.is_conflict is True

    def test_r4_offered_exceeds_capacity(self):
        assert R4_CERTIFICATE.offered_load_per_slot > R4_CERTIFICATE.link_capacity_per_slot

    def test_check_blocks_r4(self):
        with pytest.raises(ConflictError, match="BLOCK_CONFLICT"):
            check_conflict_certificate("R4")

    def test_check_passes_r0(self):
        check_conflict_certificate("R0")  # Should not raise

    def test_certificate_integrity(self):
        assert verify_certificate_integrity(R4_CERTIFICATE, R4_CERTIFICATE_FROZEN_HASH)

    def test_tampered_certificate_detected(self):
        from ledger.conflict_certificate import ConflictCertificate
        tampered = ConflictCertificate("R4", 1.0, 1.0, False)
        assert not verify_certificate_integrity(tampered, R4_CERTIFICATE_FROZEN_HASH)
