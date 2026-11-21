"""Code-hash-keyed Oracle v1.1 measurement cache (measure once, score configs offline)."""
from __future__ import annotations

import json, math, time
from pathlib import Path
from typing import Any

from constitution import constants as C
from constitution.hashing import sha256_canonical
from sim.traffic import TrafficConfig, generate_arrivals
from sim.engine import run
from oracle.audit import audit_departure_log
from oracle.verdict import (
    compute_per_seed_p99,
    calculate_control_loss,
    calculate_delivered_fraction,
    evaluate_latency_verdict,
)


def _json_safe(x: Any) -> Any:
    if isinstance(x, float):
        if math.isinf(x):
            return "INF" if x > 0 else "-INF"
        if math.isnan(x):
            return "NAN"
        return x
    if isinstance(x, list):
        return [_json_safe(v) for v in x]
    if isinstance(x, dict):
        return {k: _json_safe(v) for k, v in x.items()}
    return x


def _json_restore(x: Any) -> Any:
    if x == "INF":
        return float("inf")
    if x == "-INF":
        return float("-inf")
    if x == "NAN":
        return float("nan")
    if isinstance(x, list):
        return [_json_restore(v) for v in x]
    if isinstance(x, dict):
        return {k: _json_restore(v) for k, v in x.items()}
    return x


def measure_scheduler_v11(
    scheduler_cls,
    n_devices: int,
    bulk_rate: float,
    burstiness: float,
    seeds: tuple[int, ...],
    horizon: int = 5000,
    bound_c: float | None = None,
    bound_b: float | None = None,
    early_stop_fail_seeds: int | None = None,
) -> dict[str, Any]:
    """Run scheduler_cls through SimPy + D1 Audit + v1.1 Oracle metrics."""
    t0 = time.perf_counter()
    c_p99s: list[float] = []
    b_p99s: list[float] = []
    c_losses: list[float] = []
    c_delivs: list[float] = []
    b_delivs: list[float] = []
    c_arr_counts: list[int] = []
    b_arr_counts: list[int] = []
    c_fail_cnt = 0
    b_fail_cnt = 0
    early_stopped = False

    for seed in seeds:
        arrivals = generate_arrivals(
            TrafficConfig(n_devices, horizon, bulk_rate, burstiness, seed)
        )
        try:
            log = run(arrivals, scheduler_cls(), n_devices, horizon)
        except Exception as e:
            return {
                "exec_status": "ENGINE_ERROR",
                "error": str(e)[:120],
                "seeds_run": len(c_p99s),
                "wall_sec": round(time.perf_counter() - t0, 3),
            }

        violations = audit_departure_log(arrivals, log)
        if violations:
            return {
                "exec_status": "AUDIT_FAIL",
                "violations": violations,
                "seeds_run": len(c_p99s),
                "wall_sec": round(time.perf_counter() - t0, 3),
            }

        cp = compute_per_seed_p99(arrivals, log, "CONTROL", horizon=horizon)
        bp = compute_per_seed_p99(arrivals, log, "BULK", horizon=horizon)
        cl = calculate_control_loss(arrivals, log)
        cd = calculate_delivered_fraction(arrivals, log, "CONTROL")
        bd = calculate_delivered_fraction(arrivals, log, "BULK")
        ca = sum(1 for p in arrivals if p.packet_class == "CONTROL")
        ba = sum(1 for p in arrivals if p.packet_class == "BULK")

        c_p99s.append(cp)
        b_p99s.append(bp)
        c_losses.append(cl)
        c_delivs.append(cd)
        b_delivs.append(bd)
        c_arr_counts.append(ca)
        b_arr_counts.append(ba)

        if early_stop_fail_seeds is not None and bound_c is not None and bound_b is not None:
            if (not math.isfinite(cp)) or cp > bound_c:
                c_fail_cnt += 1
            if (not math.isfinite(bp)) or bp > bound_b:
                b_fail_cnt += 1
            if cl > 0.0 or c_fail_cnt >= early_stop_fail_seeds or b_fail_cnt >= early_stop_fail_seeds:
                early_stopped = True
                break

    res = {
        "exec_status": "OK",
        "seeds_requested": len(seeds),
        "seeds_run": len(c_p99s),
        "early_stopped": early_stopped,
        "horizon": horizon,
        "c_p99s": c_p99s,
        "b_p99s": b_p99s,
        "max_c_loss": max(c_losses) if c_losses else 1.0,
        "mean_c_deliv": sum(c_delivs) / len(c_delivs) if c_delivs else 0.0,
        "mean_b_deliv": sum(b_delivs) / len(b_delivs) if b_delivs else 0.0,
        "mean_c_packets_per_seed": sum(c_arr_counts) / len(c_arr_counts) if c_arr_counts else 0.0,
        "mean_b_packets_per_seed": sum(b_arr_counts) / len(b_arr_counts) if b_arr_counts else 0.0,
        "wall_sec": round(time.perf_counter() - t0, 3),
    }

    if bound_c is not None and bound_b is not None:
        min_pass = C.PER_SEED_GUARD_MIN_PASSING if len(seeds) == 20 else max(1, len(seeds) - 1)
        vc = evaluate_latency_verdict(c_p99s, bound_c, min_passing=min_pass)
        vb = evaluate_latency_verdict(b_p99s, bound_b, min_passing=min_pass)
        c_ok = (not early_stopped) and vc.passed and (res["max_c_loss"] == 0.0)
        b_ok = (not early_stopped) and vb.passed
        res.update({
            "c_mean_p99": vc.mean_p99,
            "c_boot_ub": vc.bootstrap_upper_bound,
            "c_seeds_passing": vc.seeds_passing,
            "b_mean_p99": vb.mean_p99,
            "b_boot_ub": vb.bootstrap_upper_bound,
            "b_seeds_passing": vb.seeds_passing,
            "oracle_pass": bool(c_ok and b_ok),
            "c_verdict_reason": "CONTROL_OVERFLOW" if res["max_c_loss"] > 0.0 else vc.reason,
            "b_verdict_reason": vb.reason,
        })
    return res


class OracleCache:
    """Disk-backed measurement cache keyed by (code_hash, scenario_signature)."""

    def __init__(self, path: str | Path = "generated/oracle_cache_v11.json"):
        self.path = Path(path)
        self.data: dict[str, dict[str, Any]] = {}
        if self.path.exists() and self.path.stat().st_size > 0:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.data = {k: _json_restore(v) for k, v in raw.items()}

    @staticmethod
    def make_key(code_hash: str, scenario: dict[str, Any]) -> str:
        return f"{code_hash}::{sha256_canonical(scenario)[:16]}"

    def get(self, key: str) -> dict[str, Any] | None:
        return self.data.get(key)

    def put(self, key: str, value: dict[str, Any]) -> None:
        self.data[key] = value

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(_json_safe(self.data), indent=2), encoding="utf-8")
