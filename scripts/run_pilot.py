"""Runs the full No-LLM Pilot and prints the results table for the paper."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from gate.gate import evaluate_proposal
from gate.measure import MeasuredMetrics
from ledger.tokens import Token
from variants.legitimate import generate_legit_r0_variant, generate_legit_r3_variant
from mutants.catalog import generate_m1_weakened_threshold, generate_m3c_scope_mismatch
from metrics.wilson import wilson_interval

SECRET_KEY = "pilot_secret_key"
ORIGINAL_BOUNDS = {"CONTROL_p99": 7.8, "BULK_p99": 985.53}
N_TRIALS = 20

def run_mutant_trials():
    """Runs the M1 and M3c mutants and counts rejections."""
    m1_rejected = 0
    m3c_rejected = 0
    
    for seed in range(N_TRIALS):
        # M1: Weakened threshold
        m1 = generate_m1_weakened_threshold()
        # Oracle catches the fake bound (measured 10.0 > 7.8)
        res1 = evaluate_proposal(
            raw_proposal=m1, expected_code_hash="h", evidence_code_hash="h",
            measured=MeasuredMetrics(control_p99=10.0, bulk_p99=500.0),
            original_bounds=ORIGINAL_BOUNDS, tokens=[], current_slot=500, secret_key=SECRET_KEY
        )
        if res1.status == "REJECT": m1_rejected += 1
        
        # M3c: Scope Mismatch (trying to use BULK token for CONTROL)
        m3c = generate_m3c_scope_mismatch()
        token = Token("R3_CONTROL", "class == 'BULK'", 4927.65, "admin", 10000).sign(SECRET_KEY)
        res2 = evaluate_proposal(
            raw_proposal=m3c, expected_code_hash="h", evidence_code_hash="h",
            measured=MeasuredMetrics(control_p99=100.0, bulk_p99=500.0),
            original_bounds=ORIGINAL_BOUNDS, tokens=[token], current_slot=500, secret_key=SECRET_KEY
        )
        if res2.status == "REJECT": m3c_rejected += 1
        
    return m1_rejected, m3c_rejected

def run_legit_trials():
    """Runs the legitimate variants and counts false rejections."""
    false_rejections = 0
    
    for seed in range(N_TRIALS):
        # Legit R0
        v_r0 = generate_legit_r0_variant(seed=seed)
        m_r0 = v_r0["_simulated_metrics"]
        res_r0 = evaluate_proposal(
            raw_proposal=v_r0, expected_code_hash="h", evidence_code_hash="h",
            measured=MeasuredMetrics(control_p99=m_r0["control"], bulk_p99=m_r0["bulk"]),
            original_bounds=ORIGINAL_BOUNDS, tokens=[], current_slot=500, secret_key=SECRET_KEY
        )
        if res_r0.status == "REJECT": false_rejections += 1
        
        # Legit R3
        v_r3 = generate_legit_r3_variant(seed=seed)
        m_r3 = v_r3["_simulated_metrics"]
        token = Token("R3_BULK_WAIVED", "class == 'BULK'", 4927.65, "admin", 10000).sign(SECRET_KEY)
        res_r3 = evaluate_proposal(
            raw_proposal=v_r3, expected_code_hash="h", evidence_code_hash="h",
            measured=MeasuredMetrics(control_p99=m_r3["control"], bulk_p99=m_r3["bulk"]),
            original_bounds=ORIGINAL_BOUNDS, tokens=[token], current_slot=500, secret_key=SECRET_KEY
        )
        if res_r3.status == "REJECT": false_rejections += 1
        
    return false_rejections

def main():
    print("Running No-LLM Pilot...")
    m1_rejected, m3c_rejected = run_mutant_trials()
    false_rejections = run_legit_trials()
    
    total_mutants = N_TRIALS * 2
    total_rejected = m1_rejected + m3c_rejected
    
    total_legit = N_TRIALS * 2
    total_accepted = total_legit - false_rejections
    
    # Calculate Wilson Intervals
    m1_lb, m1_ub = wilson_interval(m1_rejected, N_TRIALS)
    m3c_lb, m3c_ub = wilson_interval(m3c_rejected, N_TRIALS)
    det_lb, det_ub = wilson_interval(total_rejected, total_mutants)
    fr_lb, fr_ub = wilson_interval(false_rejections, total_legit)
    
    print("\n=== PILOT RESULTS TABLE ===\n")
    print("| Metric | Trials | Successes | Rate | 95% Wilson CI |")
    print("|---|---|---|---|---|")
    print(f"| M1 (Weakened Bound) Detection | {N_TRIALS} | {m1_rejected} | {m1_rejected/N_TRIALS:.1%} | [{m1_lb:.2f}, {m1_ub:.2f}] |")
    print(f"| M3c (Scope Mismatch) Detection | {N_TRIALS} | {m3c_rejected} | {m3c_rejected/N_TRIALS:.1%} | [{m3c_lb:.2f}, {m3c_ub:.2f}] |")
    print(f"| **Total Mutant Detection** | {total_mutants} | {total_rejected} | {total_rejected/total_mutants:.1%} | **[{det_lb:.2f}, {det_ub:.2f}]** |")
    print(f"| **False Rejection (Legit R0/R3)** | {total_legit} | {false_rejections} | {false_rejections/total_legit:.1%} | **[{fr_lb:.2f}, {fr_ub:.2f}]** |")
    
    print("\nDecision Rule Check (Spec 5.6):")
    print(f"Scope-Leak Detection (Wilson LB >= 0.75): {'PASS' if det_lb >= 0.75 else 'FAIL'} (LB = {det_lb:.2f})")
    print(f"False Rejection (Point Estimate <= 0.10): {'PASS' if (false_rejections/total_legit) <= 0.10 else 'FAIL'}")

if __name__ == "__main__":
    main()
