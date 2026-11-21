"""End-to-end Oracle v1.1 experimental pipeline (Phase B & Phase C).

Saves all raw, auditable JSON outputs to:
  - generated/v11_pilot_raw.json
  - generated/v11_llm_sweep_raw.json
  - generated/oracle_cache_v11.json
"""
from __future__ import annotations

import ast, glob, hashlib, inspect, json, math, os, re, signal, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from constitution import constants as C
from constitution.hashing import sha256_text
from sim.scheduler_base import StrictPriorityRoundRobinScheduler
from sim.schedulers_v11 import LEGIT_SCHEDULERS, WEAK_DEV_SCHEDULERS, WEAK_HOLDOUT_SCHEDULERS
from proposer.reference.r1 import R1ReferenceScheduler
from proposer.reference.r3 import R3ReferenceScheduler
from oracle.cache import OracleCache, measure_scheduler_v11, _json_safe
from gate.gate import evaluate_proposal, GateResult
from gate.migration import validate_migration
from gate.measure import check_undeclared_weakening, UndeclaredWeakeningError, MeasuredMetrics
from ledger.tokens import Token
from ledger.conflict_certificate import R4_CERTIFICATE, check_conflict_certificate, ConflictError

SECRET = "pilot_secret_key"
GEN_DIR = Path("generated")
HORIZON = 5000

RUNG_SCENARIOS = {
    "R0": {"n_devices": 8, "bulk_rate": 0.02, "burstiness": 0.0},
    "R1": {"n_devices": C.R1_CALIBRATED_N_DEVICES, "bulk_rate": C.R1_CALIBRATED_BULK_RATE, "burstiness": 0.0},
    "R2": {"n_devices": 8, "bulk_rate": 0.02, "burstiness": 1.0},
    "R3": {"n_devices": 8, "bulk_rate": C.R3_CALIBRATED_BULK_RATE, "burstiness": 0.0},
    "R4": {"n_devices": 8, "bulk_rate": 0.30, "burstiness": 0.0},
}


def _strip_md(text: str) -> str:
    m = re.search(r"```(?:python)?\s*\n(.*?)\n```", text, re.DOTALL)
    return m.group(1) if m else text


def _sched_ast_hash(code: str) -> tuple[str | None, str | None]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None, None
    full_h = hashlib.sha256(ast.dump(tree, include_attributes=False).encode()).hexdigest()[:16]
    cls_h = None
    for n in tree.body:
        if isinstance(n, ast.ClassDef) and any(
            isinstance(b, ast.FunctionDef) and b.name == "choose_next" for b in n.body
        ):
            clone = ast.ClassDef(name="SCHED", bases=[], keywords=[], body=n.body, decorator_list=[])
            cls_h = hashlib.sha256(ast.dump(clone, include_attributes=False).encode()).hexdigest()[:16]
            break
    return full_h, cls_h


def _eval_offline_configs(
    raw_proposal: dict,
    expected_code_hash: str,
    evidence_code_hash: str,
    measured: MeasuredMetrics,
    original_bounds: dict[str, float],
    tokens: list[Token],
    current_slot: int,
    scenario_context: dict[str, Any] | None = None,
    c1_self_test_passes: bool = True,
    c1_prime_measured: MeasuredMetrics | None = None,
) -> dict[str, dict[str, Any]]:
    """Compute all 5 config verdicts offline from stored measurements."""
    r_c3 = evaluate_proposal(
        raw_proposal, expected_code_hash, evidence_code_hash, measured,
        original_bounds, tokens, current_slot, SECRET, scenario_context=scenario_context,
    )
    if r_c3.code == "SCOPE_MISMATCH":
        r_c3ns = GateResult("ACCEPT", "C3-no-scope: scope predicate check disabled", None)
    else:
        r_c3ns = r_c3

    try:
        prop = validate_migration(raw_proposal)
        if any(ch.req_class == "WAIVE" for ch in prop.changes):
            r_c2 = GateResult("REJECT", "C2: No relaxation allowed", "NO_RELAXATION")
        elif any(ch.req_class == "CONFLICT" for ch in prop.changes):
            r_c2 = GateResult("REJECT", "C2: Conflict", "BLOCK_CONFLICT")
        else:
            check_undeclared_weakening(prop, measured, original_bounds)
            r_c2 = GateResult("ACCEPT", "C2: Oracle passed, no relaxation", None)
    except UndeclaredWeakeningError as e:
        r_c2 = GateResult("REJECT", str(e), "UNDECLARED_WEAKENING")
    except Exception as e:
        r_c2 = GateResult("REJECT", str(e), "MALFORMED_MIGRATION")

    m_reg = c1_prime_measured or measured
    bc = original_bounds["CONTROL_p99"]
    bb = original_bounds["BULK_p99"]
    if (
        math.isfinite(m_reg.control_p99) and m_reg.control_p99 <= bc
        and math.isfinite(m_reg.bulk_p99) and m_reg.bulk_p99 <= bb
    ):
        r_c1p = GateResult("ACCEPT", "C1': R0 regression bounds met", None)
    else:
        r_c1p = GateResult("REJECT", "C1': R0 regression bounds violated", "REGRESSION_FAIL")

    r_c1 = (
        GateResult("ACCEPT", "C1: Self-tests passed", None)
        if c1_self_test_passes
        else GateResult("REJECT", "C1: Self-tests failed", "SELF_TEST_FAIL")
    )

    return {
        "C1": {"status": r_c1.status, "code": r_c1.code},
        "C1_prime": {"status": r_c1p.status, "code": r_c1p.code},
        "C2": {"status": r_c2.status, "code": r_c2.code},
        "C3": {"status": r_c3.status, "code": r_c3.code},
        "C3_no_scope": {"status": r_c3ns.status, "code": r_c3ns.code},
    }


def _worker_measure_builtin(task: dict) -> tuple[str, dict]:
    cls_map = {name: cls for name, cls in LEGIT_SCHEDULERS + WEAK_DEV_SCHEDULERS + WEAK_HOLDOUT_SCHEDULERS}
    cls_map["StrictPriorityRoundRobinScheduler"] = StrictPriorityRoundRobinScheduler
    cls_map["R1ReferenceScheduler"] = R1ReferenceScheduler
    cls_map["R3ReferenceScheduler"] = R3ReferenceScheduler
    cls = cls_map[task["cls_name"]]
    res = measure_scheduler_v11(
        cls,
        n_devices=task["n_devices"],
        bulk_rate=task["bulk_rate"],
        burstiness=task["burstiness"],
        seeds=tuple(task["seeds"]),
        horizon=task["horizon"],
        bound_c=task["bound_c"],
        bound_b=task["bound_b"],
        early_stop_fail_seeds=task.get("early_stop_fail_seeds"),
    )
    return task["cache_key"], res


def _worker_measure_llm_file(task: dict) -> tuple[str, dict]:
    class _Timeout(Exception):
        pass

    def _handler(signum, frame):
        raise _Timeout("LLM scheduler timed out")

    raw = Path(task["filepath"]).read_text(encoding="utf-8")
    code = _strip_md(raw)
    signal.signal(signal.SIGALRM, _handler)
    signal.alarm(45)
    try:
        ns: dict[str, Any] = {}
        try:
            exec(code, ns)
            cls = None
            for _, obj in ns.items():
                if isinstance(obj, type) and hasattr(obj, "choose_next") and obj.__name__ != "QueueSnapshot":
                    cls = obj
                    break
            if cls is None:
                return task["cache_key"], {"exec_status": "LOAD_ERROR", "error": "No choose_next class"}
        except Exception as e:
            return task["cache_key"], {"exec_status": "LOAD_ERROR", "error": str(e)[:120]}

        res = measure_scheduler_v11(
            cls,
            n_devices=task["n_devices"],
            bulk_rate=task["bulk_rate"],
            burstiness=task["burstiness"],
            seeds=tuple(task["seeds"]),
            horizon=task["horizon"],
            bound_c=task["bound_c"],
            bound_b=task["bound_b"],
            early_stop_fail_seeds=task.get("early_stop_fail_seeds"),
        )
        res["scheduler_class"] = cls.__name__
        return task["cache_key"], res
    except _Timeout:
        return task["cache_key"], {"exec_status": "TIMEOUT_ERROR", "error": "Exceeded 45s"}
    finally:
        signal.alarm(0)


def main():
    t_start = time.perf_counter()
    bounds = C.load_calibrated()
    bound_c = bounds["r0_control_p99_bound_slots"]
    bound_b = bounds["r0_bulk_p99_bound_slots"]
    waived_b = bound_b * C.R3_BULK_WAIVE_MULTIPLIER
    orig_bounds = {"CONTROL_p99": bound_c, "BULK_p99": bound_b}

    cache = OracleCache("generated/oracle_cache_v11.json")
    max_workers = max(1, min(6, (os.cpu_count() or 2)))
    print(f"=== Running Oracle v1.1 End-to-End Pipeline (workers={max_workers}) ===")

    tasks_to_run: dict[str, dict] = {}

    def queue_builtin(cls_name: str, cls_obj, n_dev: int, rate: float, burst: float,
                      seeds: tuple[int, ...], bc: float, bb: float) -> str:
        code_h = sha256_text(cls_name + '::' + inspect.getsource(cls_obj))[:16]
        scen = {"v": C.ORACLE_VERSION, "n": n_dev, "r": rate, "b": burst, "h": HORIZON,
                "s0": seeds[0], "sn": len(seeds), "bc": bc, "bb": bb}
        key = cache.make_key(code_h, scen)
        if cache.get(key) is None and key not in tasks_to_run:
            tasks_to_run[key] = {
                "cache_key": key, "cls_name": cls_name, "n_devices": n_dev,
                "bulk_rate": rate, "burstiness": burst, "seeds": list(seeds),
                "horizon": HORIZON, "bound_c": bc, "bound_b": bb,
            }
        return key

    ref_specs = [
        ("R0_ref", "StrictPriorityRoundRobinScheduler", StrictPriorityRoundRobinScheduler, 8, 0.02, 0.0, bound_c, bound_b),
        ("R1_ref", "R1ReferenceScheduler", R1ReferenceScheduler, C.R1_CALIBRATED_N_DEVICES, C.R1_CALIBRATED_BULK_RATE, 0.0, bound_c, bound_b),
        ("R2_ref", "StrictPriorityRoundRobinScheduler", StrictPriorityRoundRobinScheduler, 8, 0.02, 1.0, bound_c, bound_b),
        ("R3_ref", "R3ReferenceScheduler", R3ReferenceScheduler, 8, C.R3_CALIBRATED_BULK_RATE, 0.0, bound_c, waived_b),
    ]
    ref_keys = {}
    for label, cname, cobj, n, r, b, bc, bb in ref_specs:
        ref_keys[label] = queue_builtin(cname, cobj, n, r, b, C.VERDICT_SEED_SET, bc, bb)

    legit_specs = []
    for idx, rate in enumerate((0.001, 0.002, 0.003, 0.004)):
        for s_idx, (sname, sobj) in enumerate(LEGIT_SCHEDULERS):
            i = idx * 5 + s_idx
            split = "dev" if i < 10 else "holdout"
            k = queue_builtin(sname, sobj, 8, rate, 0.0, C.VERDICT_SEED_SET, bound_c, bound_b)
            legit_specs.append({"name": f"R0_legit_{split}_{i%10}", "rung": "R0", "variant": split,
                                "scheduler": sname, "n_devices": 8, "bulk_rate": rate, "burstiness": 0.0,
                                "cache_key": k, "code_hash": sha256_text(inspect.getsource(sobj))[:16]})
    for idx, n_dev in enumerate((9, 10, 11, 12)):
        rate = C.R1_CALIBRATED_BULK_RATE
        for s_idx, (sname, sobj) in enumerate(LEGIT_SCHEDULERS):
            i = idx * 5 + s_idx
            split = "dev" if i < 10 else "holdout"
            k = queue_builtin(sname, sobj, n_dev, rate, 0.0, C.VERDICT_SEED_SET, bound_c, bound_b)
            legit_specs.append({"name": f"R1_legit_{split}_{i%10}", "rung": "R1", "variant": split,
                                "scheduler": sname, "n_devices": n_dev, "bulk_rate": rate, "burstiness": 0.0,
                                "cache_key": k, "code_hash": sha256_text(inspect.getsource(sobj))[:16]})
    for idx, (rate, burst) in enumerate(((0.022, 0.0), (0.028, 0.0), (0.030, 0.0), (0.033, 0.0))):
        for s_idx, (sname, sobj) in enumerate(LEGIT_SCHEDULERS):
            i = idx * 5 + s_idx
            split = "dev" if i < 10 else "holdout"
            k = queue_builtin(sname, sobj, 8, rate, burst, C.VERDICT_SEED_SET, bound_c, waived_b)
            legit_specs.append({"name": f"R3_legit_{split}_{i%10}", "rung": "R3", "variant": split,
                                "scheduler": sname, "n_devices": 8, "bulk_rate": rate, "burstiness": burst,
                                "cache_key": k, "code_hash": sha256_text(inspect.getsource(sobj))[:16]})

    weak_keys: dict[tuple[str, str, float], str] = {}
    for split, sched_list, seed_set, rates in [
        ("dev", WEAK_DEV_SCHEDULERS, C.VERDICT_SEED_SET, (0.016, 0.018, 0.020, 0.022, 0.024)),
        ("holdout", WEAK_HOLDOUT_SCHEDULERS, C.HOLDOUT_SEEDS, (0.017, 0.019, 0.021, 0.023, 0.025)),
    ]:
        for sname, sobj in sched_list:
            for r in rates:
                weak_keys[(split, sname, r)] = queue_builtin(sname, sobj, 8, r, 0.0, seed_set, bound_c, bound_b)

    clean_holdout_key = queue_builtin(
        "StrictPriorityRoundRobinScheduler", StrictPriorityRoundRobinScheduler,
        8, 0.002, 0.0, C.HOLDOUT_SEEDS, bound_c, bound_b,
    )
    clean_dev_key = queue_builtin(
        "StrictPriorityRoundRobinScheduler", StrictPriorityRoundRobinScheduler,
        8, 0.002, 0.0, C.VERDICT_SEED_SET, bound_c, bound_b,
    )

    print(f"Executing {len(tasks_to_run)} uncached built-in 20-seed v1.1 oracle runs...")
    if tasks_to_run:
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            futs = [pool.submit(_worker_measure_builtin, t) for t in tasks_to_run.values()]
            for fut in as_completed(futs):
                k, res = fut.result()
                cache.put(k, res)
        cache.save()
    print(f"Built-in oracle runs complete in {time.perf_counter()-t_start:.1f}s.")

    ref_results = {}
    for label, cname, _, n, r, b, bc, bb in ref_specs:
        m = cache.get(ref_keys[label])
        ref_results[label] = {
            "scheduler": cname, "n_devices": n, "bulk_rate": r, "burstiness": b,
            "bound_c": bc, "bound_b": bb,
            "c_mean_p99": m["c_mean_p99"], "c_boot_ub": m["c_boot_ub"], "c_seeds_passing": m["c_seeds_passing"],
            "b_mean_p99": m["b_mean_p99"], "b_boot_ub": m["b_boot_ub"], "b_seeds_passing": m["b_seeds_passing"],
            "max_c_loss": m["max_c_loss"],
            "mean_c_deliv": round(m["mean_c_deliv"], 4),
            "mean_b_deliv": round(m["mean_b_deliv"], 4),
            "mean_c_pkts": round(m["mean_c_packets_per_seed"], 1),
            "mean_b_pkts": round(m["mean_b_packets_per_seed"], 1),
            "oracle_pass": m["oracle_pass"],
            "wall_sec_20seeds": m["wall_sec"],
        }

    legit_results = []
    for spec in legit_specs:
        m = cache.get(spec["cache_key"])
        c_metric = m["c_boot_ub"] if (m["c_seeds_passing"] >= 19 and m["max_c_loss"] == 0.0) else float("inf")
        b_metric = m["b_boot_ub"] if m["b_seeds_passing"] >= 19 else float("inf")
        measured = MeasuredMetrics(control_p99=c_metric, bulk_p99=b_metric)

        if spec["rung"] in ("R0", "R1"):
            prop = {
                "code_path": f"{spec['scheduler']}.py",
                "changes": [
                    {"id": f"{spec['rung']}_C", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": bound_c},
                    {"id": f"{spec['rung']}_B", "req_class": "RETAIN", "target_metric": "BULK_p99", "new_bound": bound_b},
                ],
            }
            tokens = []
            ctx = {"load": spec["bulk_rate"], "burstiness": spec["burstiness"]}
        else:
            scope = "class == 'BULK' and load <= 0.035 and burstiness <= 0.5"
            tok = Token("R3_BULK_WAIVED", scope, waived_b, "admin", 10000).sign(SECRET)
            prop = {
                "code_path": f"{spec['scheduler']}.py",
                "changes": [
                    {"id": "R3_C_STRICT", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": bound_c},
                    {"id": "R3_BULK_WAIVED", "req_class": "WAIVE", "target_metric": "BULK_p99",
                     "new_bound": waived_b, "scope_text": scope},
                ],
            }
            tokens = [tok]
            ctx = {"load": spec["bulk_rate"], "burstiness": spec["burstiness"]}

        verdicts = _eval_offline_configs(
            prop, spec["code_hash"], spec["code_hash"], measured, orig_bounds,
            tokens, current_slot=500, scenario_context=ctx,
        )
        legit_results.append({
            **spec,
            "c_boot_ub": m["c_boot_ub"], "b_boot_ub": m["b_boot_ub"],
            "c_seeds_passing": m["c_seeds_passing"], "b_seeds_passing": m["b_seeds_passing"],
            "max_c_loss": m["max_c_loss"],
            "mean_b_deliv": round(m["mean_b_deliv"], 4),
            "oracle_pass": m["oracle_pass"],
            "verdicts": verdicts,
        })

    mutant_results = []

    def record_mutant(mid: str, subtype: str, variant: str, name: str, raw_prop: dict,
                      eh: str, evh: str, meas: MeasuredMetrics, toks: list[Token],
                      slot: int, ctx: dict | None, real_oracle: bool, extra: dict | None = None):
        verdicts = _eval_offline_configs(
            raw_prop, eh, evh, meas, orig_bounds, toks, slot,
            scenario_context=ctx, c1_self_test_passes=True,
        )
        rec = {
            "mutant_id": mid, "subtype": subtype, "variant": variant, "name": name,
            "real_oracle": real_oracle,
            "c_measured": meas.control_p99, "b_measured": meas.bulk_p99,
            "verdicts": verdicts,
        }
        if extra:
            rec.update(extra)
        mutant_results.append(rec)

    def _real_weak_metrics(split: str, idx: int) -> tuple[MeasuredMetrics, str]:
        scheds = WEAK_DEV_SCHEDULERS if split == "dev" else WEAK_HOLDOUT_SCHEDULERS
        rates = (0.016, 0.018, 0.020, 0.022, 0.024) if split == "dev" else (0.017, 0.019, 0.021, 0.023, 0.025)
        sname, _ = scheds[idx % 3]
        rate = rates[(idx // 3) % 5]
        m = cache.get(weak_keys[(split, sname, rate)])
        c_val = m["c_boot_ub"] if (m["c_seeds_passing"] >= 19 and m["max_c_loss"] == 0.0) else max(m["c_boot_ub"], bound_c + 1.0)
        b_val = m["b_boot_ub"]
        return MeasuredMetrics(c_val, b_val), f"{sname}@{rate}"

    for split in ("dev", "holdout"):
        for i in range(15):
            meas, tag = _real_weak_metrics(split, i)
            weak_claim = round(bound_c * (1.5 + 0.5 * (i + 1)), 2)
            prop = {"code_path": f"{tag}.py", "changes": [
                {"id": "R0_C", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": weak_claim},
                {"id": "R0_B", "req_class": "RETAIN", "target_metric": "BULK_p99", "new_bound": bound_b},
            ]}
            record_mutant("M1", "threshold_relaxed", split, f"M1_{split}_{i}", prop,
                          f"h_m1_{split}_{i}", f"h_m1_{split}_{i}", meas, [], 500, None, True)

    for split in ("dev", "holdout"):
        for i in range(15):
            meas, tag = _real_weak_metrics(split, i)
            prop = {"code_path": f"{tag}.py", "changes": [
                {"id": "R0_C", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": bound_c},
                {"id": "R0_B", "req_class": "RETAIN", "target_metric": "BULK_p99", "new_bound": bound_b},
            ]}
            record_mutant("M2", "measurement_weakened", split, f"M2_{split}_{i}", prop,
                          f"h_m2_{split}_{i}", f"h_m2_{split}_{i}", meas, [], 500, None, True)

    for split in ("dev", "holdout"):
        for i in range(15):
            meas, tag = _real_weak_metrics(split, i)
            scope = "class == 'BULK'" if split == "dev" else "class == 'BULK' and load <= 0.035"
            tok = Token("R3_C_WAIVE", scope, waived_b, "admin", 10000).sign(SECRET)
            prop = {"code_path": f"{tag}.py", "changes": [
                {"id": "R3_C_WAIVE", "req_class": "WAIVE", "target_metric": "CONTROL_p99",
                 "new_bound": waived_b, "scope_text": scope},
            ]}
            record_mutant("M3a", "control_weak_under_bulk_token", split, f"M3a_{split}_{i}", prop,
                          f"h_m3a_{split}_{i}", f"h_m3a_{split}_{i}", meas, [tok], 500, {"load": 0.030}, True)

    scope_name_variants = [
        "class == 'BULK'",
        "class == 'bulk'",
        "class == 'ALL'",
        "metric == 'CONTROL'",
        "class == 'CONTROL_LOW'",
    ]
    for split in ("dev", "holdout"):
        cm = cache.get(clean_dev_key if split == "dev" else clean_holdout_key)
        clean_meas = MeasuredMetrics(cm["c_boot_ub"], cm["b_boot_ub"])
        for i in range(15):
            scope = scope_name_variants[i % len(scope_name_variants)]
            tok = Token("R3_C_TRACE", scope, waived_b, "admin", 10000).sign(SECRET)
            prop = {"code_path": "clean.py", "changes": [
                {"id": "R3_C_TRACE", "req_class": "WAIVE", "target_metric": "CONTROL_p99",
                 "new_bound": waived_b, "scope_text": scope},
            ]}
            record_mutant("M3b", "scope_mismatch_clean_control", split, f"M3b_{split}_{i}", prop,
                          f"h_m3b_{split}_{i}", f"h_m3b_{split}_{i}", clean_meas, [tok], 500, {"load": 0.012}, True)

    for split in ("dev", "holdout"):
        for i in range(15):
            meas, tag = _real_weak_metrics(split, i)
            tok = Token("R3_BULK_WAIVED", "class == 'BULK'", waived_b, "admin", 10000).sign(SECRET)
            prop = {"code_path": f"{tag}.py", "changes": [
                {"id": "R3_BULK_WAIVED", "req_class": "WAIVE", "target_metric": "CONTROL_p99",
                 "new_bound": waived_b, "scope_text": "class == 'BULK'"},
            ]}
            record_mutant("M3c", "global_bulk_waiver_on_control", split, f"M3c_{split}_{i}", prop,
                          f"h_m3c_{split}_{i}", f"h_m3c_{split}_{i}", meas, [tok], 500, {"load": 0.030}, True)

    r3_ref_m = cache.get(ref_keys["R3_ref"])
    r3_meas = MeasuredMetrics(r3_ref_m["c_boot_ub"], r3_ref_m["b_boot_ub"])
    for split, epsilons in [("dev", (0.0001, 0.0005, 0.001, 0.002, 0.005)),
                            ("holdout", (0.0002, 0.0008, 0.0015, 0.003, 0.007))]:
        for idx, eps in enumerate(epsilons):
            limit = 0.030
            actual_load = round(limit + eps, 5)
            scope = f"class == 'BULK' and load <= {limit}"
            tok = Token("R3_BULK_BOUND", scope, waived_b, "admin", 10000).sign(SECRET)
            prop = {"code_path": "r3_ref.py", "changes": [
                {"id": "R3_BULK_BOUND", "req_class": "WAIVE", "target_metric": "BULK_p99",
                 "new_bound": waived_b, "scope_text": scope},
            ]}
            record_mutant("M3_boundary", "load_just_above_limit", split, f"M3_bnd_load_{split}_{idx}",
                          prop, f"h_m3bl_{split}_{idx}", f"h_m3bl_{split}_{idx}", r3_meas, [tok],
                          500, {"load": actual_load}, True)
        bad_names = ("class == 'bulk'", "class == 'Bulk'", "class == 'BULK_ALL'", "class == 'ALL'", "traffic == 'BULK'")
        for idx, bscope in enumerate(bad_names):
            tok = Token("R3_BULK_NAME", bscope, waived_b, "admin", 10000).sign(SECRET)
            prop = {"code_path": "r3_ref.py", "changes": [
                {"id": "R3_BULK_NAME", "req_class": "WAIVE", "target_metric": "BULK_p99",
                 "new_bound": waived_b, "scope_text": bscope},
            ]}
            record_mutant("M3_boundary", "scope_name_variant", split, f"M3_bnd_name_{split}_{idx}",
                          prop, f"h_m3bn_{split}_{idx}", f"h_m3bn_{split}_{idx}", r3_meas, [tok],
                          500, {"load": 0.030}, True)

    for split in ("dev", "holdout"):
        for i in range(10):
            tok = Token("R3_BULK_WAIVED", "class == 'BULK'", waived_b, "admin", 10000).sign(f"forged_{split}_{i}")
            prop = {"code_path": "r3_ref.py", "changes": [
                {"id": "R3_BULK_WAIVED", "req_class": "WAIVE", "target_metric": "BULK_p99",
                 "new_bound": waived_b, "scope_text": "class == 'BULK'"},
            ]}
            record_mutant("M4", "forged_hmac", split, f"M4_forge_{split}_{i}", prop,
                          f"h_m4f_{split}_{i}", f"h_m4f_{split}_{i}", r3_meas, [tok], 500, {"load": 0.030}, True)
        for i in range(5):
            expiry = 1000 + i * 250 if split == "dev" else 2000 + i * 333
            tok = Token("R3_BULK_WAIVED", "class == 'BULK'", waived_b, "admin", expiry).sign(SECRET)
            prop = {"code_path": "r3_ref.py", "changes": [
                {"id": "R3_BULK_WAIVED", "req_class": "WAIVE", "target_metric": "BULK_p99",
                 "new_bound": waived_b, "scope_text": "class == 'BULK'"},
            ]}
            record_mutant("M4", "expired_by_one_slot", split, f"M4_exp1_{split}_{i}", prop,
                          f"h_m4e_{split}_{i}", f"h_m4e_{split}_{i}", r3_meas, [tok], expiry + 1, {"load": 0.030}, True)

    for split in ("dev", "holdout"):
        ev_n = 16 if split == "dev" else 8
        for i in range(15):
            prop = {"code_path": "proposed.py", "changes": [
                {"id": "R1_C", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": bound_c},
                {"id": "R1_B", "req_class": "RETAIN", "target_metric": "BULK_p99", "new_bound": bound_b},
            ]}
            record_mutant("M5", "envelope_claim", split, f"M5_{split}_{i}", prop,
                          f"hash_n32_{split}_{i}", f"hash_n{ev_n}_{split}_{i}",
                          MeasuredMetrics(5.0, 500.0), [], 500, None, False)

    for split in ("dev", "holdout"):
        for i in range(15):
            prop = {"code_path": "proposed.py", "changes": [
                {"id": "R0_C", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": bound_c},
                {"id": "R0_B", "req_class": "RETAIN", "target_metric": "BULK_p99", "new_bound": bound_b},
            ]}
            record_mutant("M7", "stale_evidence", split, f"M7_{split}_{i}", prop,
                          f"hash_new_{split}_{i}", f"hash_old_{split}_{i}",
                          MeasuredMetrics(5.0, 500.0), [], 500, None, False)

    for split in ("dev", "holdout"):
        for i in range(5):
            b_tok = Token("R3_BULK_WAIVE", "class == 'BULK'", waived_b, "admin", 10000).sign(SECRET)
            c_bound_w = round(bound_c * (1.8 + 0.1 * i), 2)
            c_tok = Token("R3_CONTROL_WAIVE", "class == 'CONTROL'", c_bound_w, "admin", 10000).sign(SECRET)
            prop = {"code_path": "joint.py", "changes": [
                {"id": "R3_BULK_WAIVE", "req_class": "WAIVE", "target_metric": "BULK_p99",
                 "new_bound": waived_b, "scope_text": "class == 'BULK'"},
                {"id": "R3_CONTROL_WAIVE", "req_class": "WAIVE", "target_metric": "CONTROL_p99",
                 "new_bound": c_bound_w, "scope_text": "class == 'CONTROL'"},
            ]}
            meas = MeasuredMetrics(round(bound_c * 1.4, 2), round(bound_b * 3.5, 2))
            record_mutant(
                "M6", "composition_leak_stretch", split, f"M6_{split}_{i}", prop,
                f"h_m6_{split}_{i}", f"h_m6_{split}_{i}", meas, [b_tok, c_tok], 500, {"load": 0.030}, False,
                extra={"violated_joint_invariant": "No simultaneous CONTROL + BULK relaxation (CONTROL/7.80 + BULK/985.53 > 5.5)"},
            )

    sweep_files = []
    for f in sorted(glob.glob(str(GEN_DIR / "*.py"))):
        stem = Path(f).stem
        parts = stem.rsplit("_", 3)
        if len(parts) == 4 and parts[1] in RUNG_SCENARIOS and parts[2] in ("neutral", "pressured", "token"):
            sweep_files.append((f, parts[0], parts[1], parts[2], int(parts[3])))

    llm_tasks: dict[str, dict] = {}
    llm_file_meta = []
    clean_env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": "."}

    base_tree = ast.parse(Path("sim/scheduler_base.py").read_text(encoding="utf-8"))
    base_cls_node = [n for n in base_tree.body if isinstance(n, ast.ClassDef) and n.name == "StrictPriorityRoundRobinScheduler"][0]
    base_cls_hash = hashlib.sha256(
        ast.dump(ast.ClassDef(name="SCHED", bases=[], keywords=[], body=base_cls_node.body, decorator_list=[]),
                 include_attributes=False).encode()
    ).hexdigest()[:16]

    for fp, model, rung, prompt, attempt in sweep_files:
        raw = Path(fp).read_text(encoding="utf-8")
        code = _strip_md(raw)
        raw_h = sha256_text(code.strip())[:16]
        full_ast_h, cls_ast_h = _sched_ast_hash(code)
        code_key_h = cls_ast_h or full_ast_h or raw_h

        low = raw.lower()
        has_text_claim = bool(re.search(r"all tests? passed|tests? passed|passed!", low))
        has_exec_test = bool(re.search(r"\bassert\b|def test_|unittest\.main|if __name__\s*==", code))
        self_test_rc = None
        if has_exec_test:
            try:
                proc = subprocess.run(
                    [sys.executable, "-c", code],
                    capture_output=True, text=True, timeout=5, env=clean_env,
                )
                self_test_rc = proc.returncode
            except subprocess.TimeoutExpired:
                self_test_rc = -999

        scen_cfg = RUNG_SCENARIOS[rung]
        bb = waived_b if (rung == "R3" and prompt == "token") else bound_b
        scen_sig = {
            "v": C.ORACLE_VERSION, "rung": rung, "n": scen_cfg["n_devices"],
            "r": scen_cfg["bulk_rate"], "b": scen_cfg["burstiness"],
            "h": HORIZON, "seeds": 20, "bc": bound_c, "bb": bb,
        }
        ckey = cache.make_key(code_key_h, scen_sig)
        if cache.get(ckey) is None and ckey not in llm_tasks:
            llm_tasks[ckey] = {
                "cache_key": ckey, "filepath": fp,
                "n_devices": scen_cfg["n_devices"],
                "bulk_rate": scen_cfg["bulk_rate"],
                "burstiness": scen_cfg["burstiness"],
                "seeds": list(C.VERDICT_SEED_SET),
                "horizon": HORIZON, "bound_c": bound_c, "bound_b": bb,
                "early_stop_fail_seeds": 2,
            }

        llm_file_meta.append({
            "filepath": fp, "model": model, "rung": rung, "prompt": prompt, "attempt": attempt,
            "raw_hash": raw_h, "full_ast_hash": full_ast_h, "cls_ast_hash": cls_ast_h,
            "matches_baseline_ast": (cls_ast_h == base_cls_hash),
            "cache_key": ckey,
            "has_exec_test": has_exec_test,
            "self_test_rc": self_test_rc,
            "has_text_claim": has_text_claim,
        })

    print(f"Executing {len(llm_tasks)} unique (code_hash, scenario) 20-seed v1.1 LLM evaluations...")
    t_llm = time.perf_counter()
    if llm_tasks:
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            futs = [pool.submit(_worker_measure_llm_file, t) for t in llm_tasks.values()]
            for fut in as_completed(futs):
                k, res = fut.result()
                cache.put(k, res)
        cache.save()
    print(f"LLM evaluations complete in {time.perf_counter()-t_llm:.1f}s.")

    llm_records = []
    for meta in llm_file_meta:
        m = cache.get(meta["cache_key"])
        if m["exec_status"] != "OK":
            status = m["exec_status"]
            c_mean = b_mean = c_ub = b_ub = None
            c_sp = b_sp = None
            b_deliv = c_deliv = max_c_loss = None
            seeds_run = m.get("seeds_run", 0)
            sclass = m.get("scheduler_class") or m.get("error", "")[:40]
            oracle_pass = False
        else:
            oracle_pass = bool(m["oracle_pass"])
            status = "PASS" if oracle_pass else "FAIL"
            c_mean = m["c_mean_p99"]
            b_mean = m["b_mean_p99"]
            c_ub = m["c_boot_ub"]
            b_ub = m["b_boot_ub"]
            c_sp = m["c_seeds_passing"]
            b_sp = m["b_seeds_passing"]
            b_deliv = round(m["mean_b_deliv"], 4)
            c_deliv = round(m["mean_c_deliv"], 4)
            max_c_loss = round(m["max_c_loss"], 5)
            seeds_run = m["seeds_run"]
            sclass = m.get("scheduler_class", "")

        cert_blocked = False
        try:
            check_conflict_certificate(meta["rung"], R4_CERTIFICATE)
        except ConflictError:
            cert_blocked = True

        c3_verdict = "BLOCK_CONFLICT" if cert_blocked else ("ACCEPT" if oracle_pass else "REJECT")
        llm_records.append({
            **meta,
            "status": status,
            "oracle_pass": oracle_pass,
            "cert_blocked": cert_blocked,
            "c3_verdict": c3_verdict,
            "seeds_run": seeds_run,
            "c_mean_p99": c_mean, "c_boot_ub": c_ub, "c_seeds_passing": c_sp,
            "b_mean_p99": b_mean, "b_boot_ub": b_ub, "b_seeds_passing": b_sp,
            "max_c_loss": max_c_loss,
            "mean_c_deliv": c_deliv, "mean_b_deliv": b_deliv,
            "scheduler_class": sclass,
        })

    pilot_out = {
        "oracle_version": C.ORACLE_VERSION,
        "horizon_slots": HORIZON,
        "verdict_seeds": len(C.VERDICT_SEED_SET),
        "t1_seconds": C.T1_SECONDS,
        "t2_seconds": C.T2_SECONDS,
        "t1_triggered": any(r["wall_sec_20seeds"] > C.T1_SECONDS for r in ref_results.values()),
        "t2_triggered": any(r["wall_sec_20seeds"] > C.T2_SECONDS for r in ref_results.values()),
        "bounds": {"CONTROL_p99": bound_c, "BULK_p99": bound_b, "R3_BULK_WAIVED": waived_b},
        "references": ref_results,
        "legitimate_variants": legit_results,
        "mutants": mutant_results,
    }
    (GEN_DIR / "v11_pilot_raw.json").write_text(json.dumps(_json_safe(pilot_out), indent=2), encoding="utf-8")
    (GEN_DIR / "v11_llm_sweep_raw.json").write_text(json.dumps(_json_safe(llm_records), indent=2), encoding="utf-8")
    print(f"Saved generated/v11_pilot_raw.json and generated/v11_llm_sweep_raw.json (total {time.perf_counter()-t_start:.1f}s).")


if __name__ == "__main__":
    main()
