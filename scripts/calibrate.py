"""Calibrate the R0 baseline bounds."""
import sys
from pathlib import Path
# Tell Python to look in the parent directory (the project root) for imports
sys.path.append(str(Path(__file__).parent.parent))

import numpy as np
from constitution import constants as C
from oracle.verdict import compute_per_seed_p99
from sim.engine import run
from sim.scheduler_base import StrictPriorityRoundRobinScheduler
from sim.traffic import TrafficConfig, generate_arrivals

def main():
    print("Starting R0 Calibration...")
    
    # We need a reasonable baseline traffic load to calibrate against.
    cfg = TrafficConfig(
        n_devices=C.R0_N_DEVICES,
        total_slots=5000,
        bulk_rate_per_device_per_slot=0.02,
        bulk_burstiness=0.0,
        seed=0 # The seed is overridden in the loop below
    )
    
    control_p99s = []
    bulk_p99s = []
    
    for seed in C.VERDICT_SEED_SET:
        cfg = TrafficConfig(cfg.n_devices, cfg.total_slots, cfg.bulk_rate_per_device_per_slot, cfg.bulk_burstiness, seed)
        arrivals = generate_arrivals(cfg)
        
        log = run(arrivals, StrictPriorityRoundRobinScheduler(), n_devices=cfg.n_devices, max_slot=cfg.total_slots)
        
        control_p99 = compute_per_seed_p99(arrivals, log, "CONTROL")
        bulk_p99 = compute_per_seed_p99(arrivals, log, "BULK")
        
        control_p99s.append(control_p99)
        bulk_p99s.append(bulk_p99)
        
        print(f"Seed {seed:02d} | CONTROL p99: {control_p99:6.2f} | BULK p99: {bulk_p99:6.2f}")
        
    mean_control = np.mean(control_p99s)
    mean_bulk = np.mean(bulk_p99s)
    
    print("\n--- Calibration Results ---")
    print(f"Baseline Mean CONTROL p99: {mean_control:.2f} slots")
    print(f"Baseline Mean BULK p99:    {mean_bulk:.2f} slots")
    
    # Spec 4.3: R0 bound = 1.5 * measured R0 reference p99
    bound_control = mean_control * C.R0_BOUND_MULTIPLIER
    bound_bulk = mean_bulk * C.R0_BOUND_MULTIPLIER
    
    print("\n--- Derived R0 Bounds (1.5x) ---")
    print(f"CONTROL Bound: {bound_control:.2f} slots")
    print(f"BULK Bound:    {bound_bulk:.2f} slots")
    print("\n(Note: These numbers will eventually be written to constitution.json)")

if __name__ == "__main__":
    main()
