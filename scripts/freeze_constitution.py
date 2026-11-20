"""Freeze the calibrated bounds into constitution.json."""
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from constitution import constants as C
from oracle.verdict import compute_per_seed_p99
from sim.engine import run
from sim.scheduler_base import StrictPriorityRoundRobinScheduler
from sim.traffic import TrafficConfig, generate_arrivals
import numpy as np

def main():
    print("Calculating R0 bounds for freeze...")
    control_p99s = []
    bulk_p99s = []
    
    # Same traffic config as calibrate.py
    for seed in C.VERDICT_SEED_SET:
        cfg = TrafficConfig(
            n_devices=C.R0_N_DEVICES,
            total_slots=5000,
            bulk_rate_per_device_per_slot=0.02,
            bulk_burstiness=0.0,
            seed=seed
        )
        arrivals = generate_arrivals(cfg)
        log = run(arrivals, StrictPriorityRoundRobinScheduler(), n_devices=cfg.n_devices, max_slot=cfg.total_slots)
        
        control_p99s.append(compute_per_seed_p99(arrivals, log, "CONTROL"))
        bulk_p99s.append(compute_per_seed_p99(arrivals, log, "BULK"))
        
    bound_control = np.mean(control_p99s) * C.R0_BOUND_MULTIPLIER
    bound_bulk = np.mean(bulk_p99s) * C.R0_BOUND_MULTIPLIER
    
    calibrated_data = {
        "r0_control_p99_bound_slots": round(float(bound_control), 2),
        "r0_bulk_p99_bound_slots": round(float(bound_bulk), 2),
        "r1_n_devices": 32,
        "r3_bulk_load_multiplier": 5.0,
        "r3_bulk_burstiness": 1.0
    }
    
    output = {
        "calibrated": calibrated_data,
        "frozen_at": "2026-11-20"
    }
    
    out_path = Path(__file__).parent.parent / C.CONSTITUTION_JSON_PATH
    out_path.write_text(json.dumps(output, indent=4), encoding="utf-8")
    print(f"Successfully wrote {out_path}")
    print(json.dumps(output, indent=4))

if __name__ == "__main__":
    main()
