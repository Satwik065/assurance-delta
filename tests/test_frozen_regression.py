"""Tests for the C1' frozen regression suite."""
import pytest
from oracle.frozen_regression import (
    frozen_regression_check,
    C1_PRIME_SEEDS, C1_PRIME_TOTAL_SLOTS,
)
from sim.scheduler_base import StrictPriorityRoundRobinScheduler


def test_c1_prime_uses_5_seeds():
    assert C1_PRIME_SEEDS == 5

def test_c1_prime_uses_5000_slots():
    assert C1_PRIME_TOTAL_SLOTS == 5000

def test_c1_prime_baseline_scheduler_passes():
    scheduler = StrictPriorityRoundRobinScheduler()
    result = frozen_regression_check(scheduler)
    assert result.passed, f"Baseline failed C1': {result.reason}"

def test_c1_prime_bad_scheduler_fails_control_loss():
    """A scheduler that never serves CONTROL must fail (zero-loss rule)."""
    class BadScheduler:
        def choose_next(self, snapshot):
            bulk_devices = snapshot.pending_bulk_devices()
            if bulk_devices:
                return snapshot.front_bulk[bulk_devices[0]]
            return None

    result = frozen_regression_check(BadScheduler())
    assert not result.passed
    assert "CONTROL loss" in result.reason or "CONTROL p99" in result.reason

def test_c1_prime_crashing_scheduler_fails_gracefully():
    class CrashScheduler:
        def choose_next(self, snapshot):
            raise RuntimeError("Crash!")

    result = frozen_regression_check(CrashScheduler())
    assert not result.passed
    assert "ENGINE_ERROR" in result.reason
