"""Evaluate ALL mini-sweep files (all models, all 5 rungs)."""
import sys, glob, re
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sim.engine import run
from sim.traffic import TrafficConfig, generate_arrivals
from oracle.audit import audit_departure_log
from oracle.verdict import compute_per_seed_p99
from constitution import constants as C

def strip_markdown(text):
    match = re.search(r'```(?:python)?\s*\n(.*?)\n```', text, re.DOTALL)
    return match.group(1) if match else text

def load_scheduler_class(filepath):
    raw = Path(filepath).read_text(encoding="utf-8")
    code = strip_markdown(raw)
    namespace = {}
    exec(code, namespace)
    for name, obj in namespace.items():
        if isinstance(obj, type) and hasattr(obj, 'choose_next') and obj.__name__ != 'QueueSnapshot':
            return obj
    raise ValueError("No scheduler class with choose_next found")

def evaluate(filepath, n_devices, bulk_rate, burstiness, bound_c, bound_b, seeds=5):
    try:
        SchedulerClass = load_scheduler_class(filepath)
    except Exception as e:
        return {"status": "LOAD_ERROR", "c_p99": "N/A", "b_p99": "N/A", "class": str(e)[:40]}

    c_p99s, b_p99s = [], []
    for seed in list(C.VERDICT_SEED_SET)[:seeds]:
        cfg = TrafficConfig(n_devices, 5000, bulk_rate, burstiness, seed)
        arrivals = generate_arrivals(cfg)
        try:
            scheduler = SchedulerClass()
            log = run(arrivals, scheduler, n_devices, 5000)
        except Exception as e:
            return {"status": "ENGINE_ERROR", "c_p99": "N/A", "b_p99": "N/A", "class": SchedulerClass.__name__}

        violations = audit_departure_log(arrivals, log)
        if violations:
            return {"status": "AUDIT_FAIL", "c_p99": "N/A", "b_p99": "N/A", "class": SchedulerClass.__name__}

        c_p99s.append(compute_per_seed_p99(arrivals, log, "CONTROL"))
        b_p99s.append(compute_per_seed_p99(arrivals, log, "BULK"))

    mean_c = sum(c_p99s) / len(c_p99s)
    mean_b = sum(b_p99s) / len(b_p99s)
    status = "PASS" if (mean_c <= bound_c and mean_b <= bound_b) else "FAIL"
    return {"status": status, "c_p99": round(mean_c, 2), "b_p99": round(mean_b, 2), "class": SchedulerClass.__name__}

def main():
    gen_dir = Path("generated")
    bounds = C.load_calibrated()
    waived_bulk = bounds["r0_bulk_p99_bound_slots"] * C.R3_BULK_WAIVE_MULTIPLIER
    bc = bounds["r0_control_p99_bound_slots"]
    bb = bounds["r0_bulk_p99_bound_slots"]

    all_files = {}
    for rung in ("R0", "R1", "R2", "R3", "R4"):
        all_files[rung] = glob.glob(str(gen_dir / f"*_r{rung[1:]}_mini.py"))

    # (n_devices, bulk_rate, burstiness, bound_c, bound_b)
    configs = {
        "R0": (8, 0.02, 0.0, bc, bb),
        "R1": (32, 0.02, 0.0, bc, bb),
        "R2": (8, 0.02, 1.0, bc, bb),
        "R3": (8, 0.10, 0.0, bc, waived_bulk),
        "R4": (8, 0.30, 0.0, bc, bb),
    }

    results = []

    for rung, files in all_files.items():
        n_dev, rate, burst, b_c, b_b = configs[rung]
        for f in sorted(files):
            fname = Path(f).stem
            model_name = fname
            for suffix in ("_r0_mini", "_r1_mini", "_r2_mini", "_r3_mini", "_r4_mini"):
                model_name = model_name.replace(suffix, "")
            print(f"\nEvaluating {model_name} / {rung}...")
            res = evaluate(f, n_dev, rate, burst, b_c, b_b)
            res["model"] = model_name
            res["rung"] = rung
            results.append(res)
            print(f"  {res['status']} | C={res['c_p99']} | B={res['b_p99']} | {res['class']}")

    print("\n" + "=" * 95)
    print("FULL MINI-SWEEP RESULTS (All Models, All 5 Rungs)")
    print("=" * 95)
    print(f"{'Model':<22} {'Rung':<6} {'Status':<14} {'C_p99':<10} {'B_p99':<10} {'Class':<30}")
    print("-" * 95)
    for r in sorted(results, key=lambda x: (x['model'], x['rung'])):
        print(f"{r['model']:<22} {r['rung']:<6} {r['status']:<14} {str(r['c_p99']):<10} {str(r['b_p99']):<10} {r['class'][:30]:<30}")
    print("=" * 95)

    # Per-model summary
    print("\nPer-Model Summary:")
    print(f"{'Model':<22} {'R0':<10} {'R1':<10} {'R2':<10} {'R3':<10} {'R4':<10} {'Pass':<6}")
    print("-" * 75)
    for model in sorted(set(r["model"] for r in results)):
        rung_results = {r["rung"]: r["status"] for r in results if r["model"] == model}
        passes = sum(1 for s in rung_results.values() if s == "PASS")
        total = len(rung_results)
        print(f"{model:<22} {rung_results.get('R0','N/A'):<10} {rung_results.get('R1','N/A'):<10} {rung_results.get('R2','N/A'):<10} {rung_results.get('R3','N/A'):<10} {rung_results.get('R4','N/A'):<10} {passes}/{total}")
    print("=" * 75)

if __name__ == "__main__":
    main()
