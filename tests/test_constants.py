"""Sanity tests that Constitution v0 matches the specification.

Each test documents which sentence of the specification (or which accepted
amendment) it pins. If any of these fails, the spec has been silently
changed.
"""
import pytest

from constitution import constants as C


def test_packet_budget_matches_spec():
    # §4.2 "at least 10^5 per class per seed"
    assert C.PACKETS_PER_CLASS_PER_SEED == 100_000
    assert C.PACKETS_PER_CLASS_PER_SEED_FALLBACK == 50_000


def test_verdict_seeds_matches_spec():
    # §4.2 "Seeds: 20 for the frozen verdict"
    assert C.VERDICT_SEEDS == 20
    assert C.DEV_MUTANT_SEEDS == 10


def test_bootstrap_resamples_matches_spec():
    # §4.2 "percentile bootstrap (2,000 resamples)"
    assert C.BOOTSTRAP_RESAMPLES == 2_000


def test_loss_bound_matches_spec():
    # §4.2 "upper 95% bound <= 3e-6 at >= 1e6 total packets"
    assert C.CONTROL_LOSS_UPPER_BOUND == 3e-6


def test_r0_multiplier_matches_spec():
    # §4.3 "1.5 x measured R0 reference p99"
    assert C.R0_BOUND_MULTIPLIER == 1.5
    assert C.R0_N_DEVICES == 8


def test_r3_waive_matches_spec():
    # §4.3 "5 x original BULK bound"
    assert C.R3_BULK_WAIVE_MULTIPLIER == 5.0


def test_t1_t2_ladder_matches_spec():
    # §4.2 "T1 = 2 min and T2 = 5 min"
    assert C.T1_SECONDS == 120
    assert C.T2_SECONDS == 300


def test_bootstrap_statistic_pre_registered():
    # D8 amendment: statistic must be pinned before any run
    assert C.BOOTSTRAP_STATISTIC == "mean_of_per_seed_p99"
    assert C.PER_SEED_GUARD_MIN_PASSING == 19
    assert C.PER_SEED_GUARD_TOTAL == 20
    assert C.PER_SEED_GUARD_MIN_PASSING < C.PER_SEED_GUARD_TOTAL


def test_audit_violation_codes_closed():
    # D1 amendment: audit codes are a closed set
    assert "DEPARTURE_WITHOUT_ARRIVAL" in C.AUDIT_VIOLATION_CODES
    assert "MULTIPLE_DEPARTURES_PER_SLOT" in C.AUDIT_VIOLATION_CODES
    assert "TIME_TRAVEL_DEPARTURE_BEFORE_ARRIVAL" in C.AUDIT_VIOLATION_CODES


def test_verdict_and_calibration_seeds_disjoint():
    # Amendment: choosing R1 N / R3 load must not leak into the verdict
    assert set(C.VERDICT_SEED_SET).isdisjoint(set(C.CALIBRATION_SEEDS))


def test_verdict_and_holdout_seeds_disjoint():
    # Amendment: hold-out mutants use fresh seeds, not just unseen parameters
    assert set(C.VERDICT_SEED_SET).isdisjoint(set(C.HOLDOUT_SEEDS))
    assert set(C.CALIBRATION_SEEDS).isdisjoint(set(C.HOLDOUT_SEEDS))


def test_all_seed_sets_have_expected_lengths():
    assert len(C.VERDICT_SEED_SET) == C.VERDICT_SEEDS
    assert len(C.CALIBRATION_SEEDS) == 20
    assert len(C.HOLDOUT_SEEDS) == 20


def test_token_key_env_var_named():
    # D5 amendment: key transported via a named env var, scrubbed pre-launch
    assert C.TOKEN_KEY_ENV_VAR == "AD_TOKEN_KEY"


def test_ledger_head_path_named():
    # D6 amendment: head hash lives in ledger/head.hash
    assert C.LEDGER_HEAD_PATH == "ledger/head.hash"


def test_legit_variant_margin_under_one():
    # Amendment: keep variants at <= 80% of the applicable bound
    assert 0.0 < C.LEGIT_VARIANT_MAX_BOUND_FRACTION <= 1.0
    assert C.LEGIT_VARIANT_MAX_BOUND_FRACTION == 0.80


def test_min_sample_rule_cited():
    # Amendment: 12 caught / 0 misses => LB 0.75; 8 caught / 0 misses => 0.65
    assert C.DEV_MIN_CAUGHT_ZERO_MISS_LB_075 == 12
    assert C.HOLDOUT_MIN_CAUGHT_ZERO_MISS_LB_065 == 8


def test_wilson_reference_nit_encoded():
    # Nit: 2/20 upper bound is ~0.30, not 0.32
    assert C.WILSON_UB_2_OF_20_REFERENCE == 0.30


def test_calibrated_keys_closed():
    # Calibrated keys form a closed set; nothing else is calibrated
    assert set(C.CALIBRATED_KEYS) == {
        "r0_control_p99_bound_slots",
        "r0_bulk_p99_bound_slots",
        "r1_n_devices",
        "r3_bulk_load_multiplier",
        "r3_bulk_burstiness",
    }


def test_load_calibrated_raises_before_freeze(tmp_path):
    # Before calibration runs, callers must get a loud error, not None
    empty = tmp_path / "constitution.json"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(C.NotCalibratedError):
        C.load_calibrated(str(empty))


def test_load_calibrated_raises_on_missing_key(tmp_path):
    p = tmp_path / "constitution.json"
    p.write_text('{"calibrated": {"r0_control_p99_bound_slots": 1.0}}',
                 encoding="utf-8")
    with pytest.raises(C.NotCalibratedError):
        C.load_calibrated(str(p))
