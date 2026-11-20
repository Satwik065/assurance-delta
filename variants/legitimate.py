"""Generates legitimate upgrade proposals (the good guys) to test false rejection."""
from __future__ import annotations
from typing import Any
import numpy as np

def generate_legit_r0_variant(seed: int) -> dict[str, Any]:
    """Generates a perfectly legal R0 upgrade with slight parameter noise."""
    rng = np.random.default_rng(seed)
    
    # The AI proposes a scheduler that is slightly faster or slower, 
    # but still well within the 80% safe margin (Amendment D5)
    # Control bound is 7.8, so we test between 4.0 and 6.24 (80% of bound).
    simulated_control_p99 = rng.uniform(4.0, 6.24)
    simulated_bulk_p99 = rng.uniform(500.0, 788.0) # 80% of 985.53
    
    return {
        "code_path": f"legit_r0_{seed}.py",
        "changes": [
            {"id": "R0_CONTROL", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": 7.8},
            {"id": "R0_BULK", "req_class": "RETAIN", "target_metric": "BULK_p99", "new_bound": 985.53}
        ],
        # We attach the simulated metrics so the test harness knows what to feed the oracle
        "_simulated_metrics": {"control": simulated_control_p99, "bulk": simulated_bulk_p99}
    }

def generate_legit_r3_variant(seed: int) -> dict[str, Any]:
    """Generates a legal R3 upgrade that uses a valid BULK waiver."""
    rng = np.random.default_rng(seed)
    
    # R3 waives BULK up to 4927.65. We test between 2000 and 3942 (80% of waived bound).
    simulated_control_p99 = rng.uniform(4.0, 6.24)
    simulated_bulk_p99 = rng.uniform(2000.0, 3942.0) 
    
    return {
        "code_path": f"legit_r3_{seed}.py",
        "changes": [
            {"id": "R3_CONTROL_STRICT", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": 7.8},
            {"id": "R3_BULK_WAIVED", "req_class": "WAIVE", "target_metric": "BULK_p99", "new_bound": 4927.65, "scope_text": "class == 'BULK'"}
        ],
        "_simulated_metrics": {"control": simulated_control_p99, "bulk": simulated_bulk_p99}
    }
