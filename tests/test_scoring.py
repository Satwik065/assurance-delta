"""Tests for §6 metrics and Wilson CI."""
import pytest
from metrics.scoring import (
    wilson_ci, compute_detection_rate, compute_rejection_rate,
    compute_silent_acceptance, compute_tamper_acceptance,
)


class TestWilsonCI:
    def test_zero_successes(self):
        lb, ub = wilson_ci(0, 20)
        assert lb == 0.0
        assert ub < 0.25  # Must pass false-rejection threshold

    def test_all_successes(self):
        lb, ub = wilson_ci(20, 20)
        assert lb > 0.80
        assert ub == 1.0

    def test_2_of_20_upper_bound(self):
        """Spec nit: 2/20 Wilson UB ≈ 0.30 (not 0.32)."""
        lb, ub = wilson_ci(2, 20)
        assert 0.28 <= ub <= 0.32

    def test_1_of_20_upper_bound(self):
        """1/20 must pass the 0.25 threshold."""
        lb, ub = wilson_ci(1, 20)
        assert ub < 0.25

    def test_12_of_12_lower_bound(self):
        """Spec: dev needs ≥12 caught with 0 misses for LB ≥ 0.75."""
        lb, ub = wilson_ci(12, 12)
        assert lb >= 0.75

    def test_8_of_8_lower_bound(self):
        """Spec: hold-out needs ≥8 caught with 0 misses for LB ≥ 0.65."""
        lb, ub = wilson_ci(8, 8)
        assert lb >= 0.65

    def test_15_of_15_lower_bound(self):
        """M3a-M3c pooled: 15/15 should give LB ≥ 0.75."""
        lb, ub = wilson_ci(15, 15)
        assert lb >= 0.75

    def test_zero_total(self):
        lb, ub = wilson_ci(0, 0)
        assert lb == 0.0
        assert ub == 1.0


class TestMetrics:
    def test_detection_rate(self):
        r = compute_detection_rate(10, 10)
        assert r.value == 1.0
        assert r.wilson_lb > 0.5

    def test_rejection_rate(self):
        r = compute_rejection_rate(0, 20)
        assert r.value == 0.0
        assert r.wilson_ub < 0.25

    def test_tamper_zero(self):
        r = compute_tamper_acceptance(0, 10)
        assert r.value == 0.0
        assert "HARD STOP" in r.note
