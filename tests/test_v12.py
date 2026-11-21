"""Unit tests for Constitution v1.2 freeze, seed disjointness, R1 reference, and scheduler diversity."""
import json
from pathlib import Path
from constitution import constants as C
from constitution.hashing import sha256_file
from sim.traffic import TrafficConfig, generate_arrivals
from sim.engine import run
from proposer.reference.r1_v12 import OldestFirstStrictScheduler
from sim.schedulers_v12 import (
    LEGIT_SCHEDULERS_V12,
    WEAK_DEV_MECHANISMS_V12,
    WEAK_HOLDOUT_MECHANISMS_V12,
)
from oracle.audit import audit_departure_log


def test_v12_seed_sets_disjoint():
    assert len(C.CALIBRATION_SEEDS) == 20
    assert len(C.VERDICT_SEED_SET) == 20
    assert len(C.HOLDOUT_SEEDS) == 20
    assert set(C.CALIBRATION_SEEDS).isdisjoint(set(C.VERDICT_SEED_SET))
    assert set(C.CALIBRATION_SEEDS).isdisjoint(set(C.HOLDOUT_SEEDS))
    assert set(C.VERDICT_SEED_SET).isdisjoint(set(C.HOLDOUT_SEEDS))


def test_v12_constitution_frozen_and_v11_intact():
    c11 = json.loads(Path("constitution/constitution.json").read_text(encoding="utf-8"))
    assert c11["schema_version"] == "1.1"
    assert c11["calibrated"]["r0_control_p99_bound_slots"] == 7.8

    c12 = json.loads(Path(C.CONSTITUTION_V12_JSON_PATH).read_text(encoding="utf-8"))
    assert c12["schema_version"] == "1.2"
    cal = C.load_calibrated_v12()
    assert cal["r0_control_p99_bound_slots"] == 8.77
    assert cal["r0_bulk_p99_bound_slots"] == 46.22
    assert cal["r1_n_devices"] == 13
    for rel, expected in c12["frozen_artifact_hashes"].items():
        assert sha256_file(rel) == expected, f"Hash mismatch for {rel}"


def test_v12_legit_scheduler_diversity_and_clean_audit():
    assert len(LEGIT_SCHEDULERS_V12) == 20
    families = {cls.FAMILY for _, cls in LEGIT_SCHEDULERS_V12}
    assert len(families) >= 8
    arr = generate_arrivals(TrafficConfig(8, 500, 0.009, 0.0, 10000))
    for name, cls in LEGIT_SCHEDULERS_V12:
        log = run(arr, cls(), 8, 500)
        assert audit_departure_log(arr, log) == [], f"{name} failed D1 audit"


def test_v12_weak_mechanism_diversity_and_disjoint_dev_holdout():
    assert len(WEAK_DEV_MECHANISMS_V12) >= 6
    assert len(WEAK_HOLDOUT_MECHANISMS_V12) >= 6
    dev_mechs = {cls.MECHANISM for _, cls in WEAK_DEV_MECHANISMS_V12}
    hold_mechs = {cls.MECHANISM for _, cls in WEAK_HOLDOUT_MECHANISMS_V12}
    assert len(dev_mechs) + len(hold_mechs) >= 12
    assert dev_mechs.isdisjoint(hold_mechs)
    arr = generate_arrivals(TrafficConfig(8, 500, 0.009, 0.0, 10000))
    for name, cls in WEAK_DEV_MECHANISMS_V12 + WEAK_HOLDOUT_MECHANISMS_V12:
        log = run(arr, cls(), 8, 500)
        assert audit_departure_log(arr, log) == [], f"{name} failed D1 audit"


def test_v12_r1_reference_runs_cleanly():
    arr = generate_arrivals(TrafficConfig(13, 1000, 0.002, 0.0, 10000))
    log = run(arr, OldestFirstStrictScheduler(), 13, 1000)
    assert audit_departure_log(arr, log) == []
    assert len(log.departures) > 0
