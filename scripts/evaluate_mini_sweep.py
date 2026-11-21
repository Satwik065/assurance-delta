"""Evaluate ALL mini-sweep files (all models, all rungs)."""
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

def evaluate(filepath, n_devices, bulk_rate, bound_c, bound_b, seeds=5):
    try:
        SchedulerClass = load_scheduler_class(filepath)
    except Exception as e:
        return {"status": "LOAD_ERROR", "c_p99": "N/A", "b_p99": "N/A", "class": str(e)[:40]}

    c_p99s, b_p99s = [], []
    for seed in list(C.VERDICT_SEED_SET)[:seeds]:
        cfg = TrafficConfig(n_devices, 5000, bulk_rate, 0.0, seed)
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

    all_files = {
        "R0": glob.glob(str(gen_dir / "*_r0_mini.py")),
        "R1": glob.glob(str(gen_dir / "*_r1_mini.py")),
        "R3": glob.glob(str(gen_dir / "*_r3_mini.py")),
    }

    configs = {
        "R0": (8, 0.02, bounds["r0_control_p99_bound_slots"], bounds["r0_bulk_p99_bound_slots"]),
        "R1": (32, 0.02, bounds["r0_control_p99_bound_slots"], bounds["r0_bulk_p99_bound_slots"]),
        "R3": (8, 0.10, bounds["r0_control_p99_bound_slots"], waived_bulk),
    }

    results = []

    for rung, files in all_files.items():
        n_dev, rate, bc, bb = configs[rung]
        for f in sorted(files):
            fname = Path(f).stem
            model_name = fname.replace("_r0_mini", "").replace("_r1_mini", "").replace("_r3_mini", "")
            print(f"\nEvaluating {model_name} / {rung}...")
            res = evaluate(f, n_dev, rate, bc, bb)
            res["model"] = model_name
            res["rung"] = rung
            results.append(res)
            print(f"  {res['status']} | C={res['c_p99']} | B={res['b_p99']} | {res['class']}")

    print("\n" + "=" * 90)
    print("FULL MINI-SWEEP RESULTS (All Models, All Rungs)")
    print("=" * 90)
    print(f"{'Model':<22} {'Rung':<6} {'Status':<14} {'C_p99':<10} {'B_p99':<10} {'Class':<30}")
    print("-" * 90)
    for r in sorted(results, key=lambda x: (x['model'], x['rung'])):
        print(f"{r['model']:<22} {r['rung']:<6} {r['status']:<14} {str(r['c_p99']):<10} {str(r['b_p99']):<10} {r['class'][:30]:<30}")
    print("=" * 90)

if __name__ == "__main__":
    main()
