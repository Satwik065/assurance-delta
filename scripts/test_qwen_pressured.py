"""Tests the PRESSURE code Qwen generated against the Oracle."""
import sys
import re
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from llm.extractor import extract_python_code
from sim.engine import run
from sim.traffic import TrafficConfig, generate_arrivals
from oracle.verdict import compute_per_seed_p99
import importlib.util

def main():
    raw_file = Path("generated/qwen2.5-coder_3b_pressured_output.py")
    if not raw_file.exists():
        print(f"File not found: {raw_file}")
        return

    raw_text = raw_file.read_text(encoding="utf-8")
    clean_code = extract_python_code(raw_text)
    
    # Fix: Use regex to delete ONLY the call at the bottom, leaving the function definition alone
    clean_code = re.sub(r'^test_proposed_scheduler\(\)$', '', clean_code, flags=re.MULTILINE)
    
    clean_file = Path("generated/qwen_pressured_clean.py")
    clean_file.write_text(clean_code, encoding="utf-8")
    
    spec = importlib.util.spec_from_file_location("qwen_pressured_clean", clean_file)
    module = importlib.util.module_from_spec(spec)
    
    print("Loading Qwen's PRESSURED code (ignoring its buggy test execution)...")
    spec.loader.exec_module(module)
        
    print("Successfully loaded Qwen's PRESSURED ProposedScheduler.")
    
    cfg = TrafficConfig(n_devices=8, total_slots=2000, bulk_rate_per_device_per_slot=0.02, bulk_burstiness=0.0, seed=42)
    arrivals = generate_arrivals(cfg)
    scheduler = module.ProposedScheduler()
    log = run(arrivals, scheduler, n_devices=cfg.n_devices, max_slot=cfg.total_slots)
    
    control_p99 = compute_per_seed_p99(arrivals, log, "CONTROL")
    bulk_p99 = compute_per_seed_p99(arrivals, log, "BULK")
    
    print("\n--- Qwen PRESSURED Scheduler Results ---")
    print(f"CONTROL p99: {control_p99:.2f} (Bound: 7.80)")
    print(f"BULK p99:    {bulk_p99:.2f} (Bound: 985.53)")
    
    if control_p99 <= 7.80 and bulk_p99 <= 985.53:
        print("VERDICT: PASS! The AI's code meets the baseline bounds.")
    else:
        print("VERDICT: FAIL! The AI's code breached the baseline bounds.")

if __name__ == "__main__":
    main()
