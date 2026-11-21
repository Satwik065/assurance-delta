"""Unit tests for code-hash-keyed OracleCache and real v1.1 scheduler classes."""
import math
from oracle.cache import OracleCache, measure_scheduler_v11
from sim.schedulers_v11 import LegitRRAsc, WeakBulkFirstDev1


def test_oracle_cache_roundtrip_preserves_inf(tmp_path):
    p = tmp_path / "cache.json"
    c1 = OracleCache(p)
    k = c1.make_key("abc123", {"rung": "R3", "rate": 0.03})
    c1.put(k, {"b_p99s": [10.0, float("inf")], "oracle_pass": False})
    c1.save()

    c2 = OracleCache(p)
    loaded = c2.get(k)
    assert loaded is not None
    assert loaded["oracle_pass"] is False
    assert math.isinf(loaded["b_p99s"][1])


def test_real_weak_scheduler_violates_control_under_v11():
    res = measure_scheduler_v11(
        WeakBulkFirstDev1, n_devices=8, bulk_rate=0.02, burstiness=0.0,
        seeds=(0, 1, 2), horizon=1000, bound_c=7.8, bound_b=985.53,
    )
    assert res["exec_status"] == "OK"
    assert res["oracle_pass"] is False
    assert res["c_boot_ub"] > 7.8


def test_real_legit_scheduler_passes_cleanly_under_v11():
    res = measure_scheduler_v11(
        LegitRRAsc, n_devices=8, bulk_rate=0.01, burstiness=0.0,
        seeds=(0, 1, 2), horizon=1000, bound_c=7.8, bound_b=985.53,
    )
    assert res["exec_status"] == "OK"
    assert res["oracle_pass"] is True
    assert res["mean_b_deliv"] > 0.90
