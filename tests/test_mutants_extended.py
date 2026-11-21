"""Tests for the extended mutant catalog (M2, M3a, M3b, M5, M6)."""
import pytest
from mutants.catalog_extended import (
    generate_m2, generate_m3a, generate_m3b, generate_m5, generate_m6,
    generate_all_mutants, generate_by_type, get_mutant_types, MutantCase,
)
from gate.gate import evaluate_proposal


def _evaluate(case: MutantCase):
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


class TestM2:
    def test_m2_dev_caught_by_g4(self):
        cases = generate_m2(variant="dev", count=5)
        assert len(cases) == 5
        for case in cases:
            result = _evaluate(case)
            assert result.status == "REJECT", f"{case.name}: expected REJECT, got {result.status} ({result.reason})"
            assert result.code == "UNDECLARED_WEAKENING"

    def test_m2_holdout_caught_by_g4(self):
        cases = generate_m2(variant="holdout", count=5)
        for case in cases:
            result = _evaluate(case)
            assert result.status == "REJECT"
            assert result.code == "UNDECLARED_WEAKENING"

    def test_m2_dev_holdout_parameters_differ(self):
        dev = generate_m2(variant="dev", count=5)
        hold = generate_m2(variant="holdout", count=5)
        dev_p99s = [c.measured.control_p99 for c in dev]
        hold_p99s = [c.measured.control_p99 for c in hold]
        assert dev_p99s != hold_p99s


class TestM3a:
    def test_m3a_dev_caught_by_g5(self):
        cases = generate_m3a(variant="dev", count=5)
        assert len(cases) == 5
        for case in cases:
            result = _evaluate(case)
            assert result.status == "REJECT", f"{case.name}: expected REJECT, got {result.status} ({result.reason})"
            assert result.code == "SCOPE_MISMATCH", f"{case.name}: expected SCOPE_MISMATCH, got {result.code}"

    def test_m3a_holdout_caught_by_g5(self):
        cases = generate_m3a(variant="holdout", count=5)
        for case in cases:
            result = _evaluate(case)
            assert result.status == "REJECT"
            assert result.code == "SCOPE_MISMATCH"

    def test_m3a_actual_weakening_present(self):
        cases = generate_m3a(variant="dev", count=5)
        for case in cases:
            assert case.measured.control_p99 > 7.8


class TestM3b:
    def test_m3b_dev_caught_by_g5(self):
        cases = generate_m3b(variant="dev", count=5)
        assert len(cases) == 5
        for case in cases:
            result = _evaluate(case)
            assert result.status == "REJECT"
            assert result.code == "SCOPE_MISMATCH"

    def test_m3b_holdout_caught_by_g5(self):
        cases = generate_m3b(variant="holdout", count=5)
        for case in cases:
            result = _evaluate(case)
            assert result.status == "REJECT"
            assert result.code == "SCOPE_MISMATCH"

    def test_m3b_no_actual_weakening(self):
        cases = generate_m3b(variant="dev", count=5)
        for case in cases:
            assert case.measured.control_p99 <= 7.8


class TestM5:
    def test_m5_dev_caught_by_g3(self):
        cases = generate_m5(variant="dev", count=5)
        assert len(cases) == 5
        for case in cases:
            result = _evaluate(case)
            assert result.status == "REJECT"
            assert result.code == "STALE_EVIDENCE"

    def test_m5_holdout_caught_by_g3(self):
        cases = generate_m5(variant="holdout", count=5)
        for case in cases:
            result = _evaluate(case)
            assert result.status == "REJECT"
            assert result.code == "STALE_EVIDENCE"

    def test_m5_hash_mismatch_present(self):
        cases = generate_m5(variant="dev", count=5)
        for case in cases:
            assert case.expected_code_hash != case.evidence_code_hash


class TestM6:
    def test_m6_dev_currently_accepted_known_gap(self):
        cases = generate_m6(variant="dev", count=2)
        for case in cases:
            result = _evaluate(case)
            assert result.status == "ACCEPT", f"{case.name}: M6 stretch — expected ACCEPT (known gap), got {result.status}"

    def test_m6_holdout_currently_accepted_known_gap(self):
        cases = generate_m6(variant="holdout", count=2)
        for case in cases:
            result = _evaluate(case)
            assert result.status == "ACCEPT"

    def test_m6_has_two_valid_tokens(self):
        cases = generate_m6(variant="dev", count=2)
        for case in cases:
            assert len(case.tokens) == 2


class TestCatalogStructure:
    def test_all_mutants_generate(self):
        all_cases = generate_all_mutants()
        assert len(all_cases) > 0

    def test_dev_and_holdout_present(self):
        all_cases = generate_all_mutants()
        dev_count = sum(1 for c in all_cases if c.variant == "dev")
        holdout_count = sum(1 for c in all_cases if c.variant == "holdout")
        assert dev_count > 0
        assert holdout_count > 0

    def test_mutant_types_complete(self):
        types = get_mutant_types()
        assert set(types) == {"M2", "M3a", "M3b", "M5", "M6"}

    def test_generate_by_type_works(self):
        for mid in get_mutant_types():
            dev = generate_by_type(mid, variant="dev")
            hold = generate_by_type(mid, variant="holdout")
            assert len(dev) > 0
            assert len(hold) > 0

    def test_total_case_count(self):
        all_cases = generate_all_mutants()
        assert len(all_cases) == 44
