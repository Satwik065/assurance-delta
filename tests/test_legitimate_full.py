"""Tests for the full legitimate variant suite (60 cases: R0×20, R1×20, R3×20)."""
import pytest
from variants.legitimate_full import (
    generate_r0, generate_r1, generate_r3,
    generate_all_legitimate, generate_by_rung, get_rungs, LegitimateCase,
)
from gate.gate import evaluate_proposal
from constitution import constants as C


def _evaluate(case: LegitimateCase):
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


class TestR0Legitimate:
    def test_r0_count(self):
        assert len(generate_r0()) == 20

    def test_r0_all_accepted(self):
        cases = generate_r0()
        for case in cases:
            result = _evaluate(case)
            assert result.status == "ACCEPT", f"{case.name}: expected ACCEPT, got {result.status} ({result.reason})"

    def test_r0_within_80pct(self):
        cases = generate_r0()
        bound_c = C.load_calibrated()["r0_control_p99_bound_slots"]
        bound_b = C.load_calibrated()["r0_bulk_p99_bound_slots"]
        for case in cases:
            assert case.measured.control_p99 <= bound_c * 0.8
            assert case.measured.bulk_p99 <= bound_b * 0.8

    def test_r0_dev_holdout_split(self):
        cases = generate_r0()
        dev = [c for c in cases if c.variant == "dev"]
        hold = [c for c in cases if c.variant == "holdout"]
        assert len(dev) == 10
        assert len(hold) == 10


class TestR1Legitimate:
    def test_r1_count(self):
        assert len(generate_r1()) == 20

    def test_r1_all_accepted(self):
        cases = generate_r1()
        for case in cases:
            result = _evaluate(case)
            assert result.status == "ACCEPT", f"{case.name}: expected ACCEPT, got {result.status} ({result.reason})"

    def test_r1_within_80pct(self):
        cases = generate_r1()
        bound_c = C.load_calibrated()["r0_control_p99_bound_slots"]
        bound_b = C.load_calibrated()["r0_bulk_p99_bound_slots"]
        for case in cases:
            assert case.measured.control_p99 <= bound_c * 0.8
            assert case.measured.bulk_p99 <= bound_b * 0.8


class TestR3Legitimate:
    def test_r3_count(self):
        assert len(generate_r3()) == 20

    def test_r3_all_accepted(self):
        cases = generate_r3()
        for case in cases:
            result = _evaluate(case)
            assert result.status == "ACCEPT", f"{case.name}: expected ACCEPT, got {result.status} ({result.reason})"

    def test_r3_control_strict(self):
        cases = generate_r3()
        bound_c = C.load_calibrated()["r0_control_p99_bound_slots"]
        for case in cases:
            assert case.measured.control_p99 <= bound_c * 0.8, "CONTROL must be under 80% of strict bound"

    def test_r3_bulk_under_waived(self):
        cases = generate_r3()
        waived = C.load_calibrated()["r0_bulk_p99_bound_slots"] * C.R3_BULK_WAIVE_MULTIPLIER
        for case in cases:
            assert case.measured.bulk_p99 <= waived * 0.8, "BULK must be under 80% of waived bound"

    def test_r3_has_valid_token(self):
        cases = generate_r3()
        for case in cases:
            assert len(case.tokens) == 1
            assert case.tokens[0].verify(case.secret_key)


class TestSuiteStructure:
    def test_total_count(self):
        all_cases = generate_all_legitimate()
        assert len(all_cases) == 60

    def test_rungs_complete(self):
        assert set(get_rungs()) == {"R0", "R1", "R3"}

    def test_dev_holdout_balance(self):
        all_cases = generate_all_legitimate()
        dev = sum(1 for c in all_cases if c.variant == "dev")
        hold = sum(1 for c in all_cases if c.variant == "holdout")
        assert dev == 30
        assert hold == 30
