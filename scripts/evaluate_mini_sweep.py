"""Evaluate the 3 mini-sweep generated files through the Oracle."""
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

def evaluate(rung_name, filepath, n_devices, bulk_rate, bound_c, bound_b, seeds=5):
    print(f"\n--- {rung_name} ---")
    print(f"  File: {Path(filepath).name}")

    try:
        SchedulerClass = load_scheduler_class(filepath)
        print(f"  Scheduler class: {SchedulerClass.__name__}")
    except Exception as e:
        print(f"  LOAD FAILED: {str(e)[:100]}")
        return {"rung": rung_name, "status": "LOAD_ERROR", "c_p99": "N/A", "b_p99": "N/A"}

    c_p99s, b_p99s = [], []

    for seed in list(C.VERDICT_SEED_SET)[:seeds]:
        cfg = TrafficConfig(n_devices, 5000, bulk_rate, 0.0, seed)
        arrivals = generate_arrivals(cfg)

        try:
            scheduler = SchedulerClass()
            log = run(arrivals, scheduler, n_devices, 5000)
        except Exception as e:
            print(f"  Seed {seed}: ENGINE ERROR: {str(e)[:80]}")
            return {"rung": rung_name, "status": "ENGINE_ERROR", "c_p99": "N/A", "b_p99": "N/A"}

        violations = audit_departure_log(arrivals, log)
        if violations:
            print(f"  Seed {seed}: AUDIT VIOLATIONS: {violations}")
            return {"rung": rung_name, "status": "AUDIT_FAIL", "c_p99": "N/A", "b_p99": "N/A"}

        c_p99s.append(compute_per_seed_p99(arrivals, log, "CONTROL"))
        b_p99s.append(compute_per_seed_p99(arrivals, log, "BULK"))

    mean_c = sum(c_p99s) / len(c_p99s)
    mean_b = sum(b_p99s) / len(b_p99s)
    status = "PASS" if (mean_c <= bound_c and mean_b <= bound_b) else "FAIL"

    print(f"  CONTROL p99: {mean_c:.2f} (bound: {bound_c}) -> {'PASS' if mean_c <= bound_c else 'FAIL'}")
    print(f"  BULK p99:    {mean_b:.2f} (bound: {bound_b}) -> {'PASS' if mean_b <= bound_b else 'FAIL'}")
    print(f"  VERDICT: {status}")
    return {"rung": rung_name, "status": status, "c_p99": round(mean_c, 2), "b_p99": round(mean_b, 2)}

def main():
    gen_dir = Path("generated")
    bounds = C.load_calibrated()
    waived_bulk = bounds["r0_bulk_p99_bound_slots"] * C.R3_BULK_WAIVE_MULTIPLIER

    results = []

    r0 = glob.glob(str(gen_dir / "*_r0_mini.py"))
    r1 = glob.glob(str(gen_dir / "*_r1_mini.py"))
    r3 = glob.glob(str(gen_dir / "*_r3_mini.py"))

    if r0:
        results.append(evaluate("R0 (Baseline N=8)", r0[0], 8, 0.02,
            bounds["r0_control_p99_bound_slots"], bounds["r0_bulk_p99_bound_slots"]))
    if r1:
        results.append(evaluate("R1 (Scale-out N=32)", r1[0], 32, 0.02,
            bounds["r0_control_p99_bound_slots"], bounds["r0_bulk_p99_bound_slots"]))
    if r3:
        results.append(evaluate("R3 (High BULK + WAIVE)", r3[0], 8, 0.10,
            bounds["r0_control_p99_bound_slots"], waived_bulk))

    print("\n" + "=" * 65)
    print("MINI-SWEEP EVALUATION SUMMARY (Qwen 2.5 Coder 3B)")
    print("=" * 65)
    print(f"{'Rung':<28} {'Status':<14} {'C_p99':<10} {'B_p99':<10}")
    print("-" * 65)
    for r in results:
        print(f"{r['rung']:<28} {r['status']:<14} {str(r['c_p99']):<10} {str(r['b_p99']):<10}")
    print("=" * 65)

if __name__ == "__main__":
    main()
