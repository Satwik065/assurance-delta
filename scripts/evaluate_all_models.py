"""Evaluates Qwen, Llama, and Granite across Neutral and Pressured prompts."""
import sys
import re
import io
from contextlib import redirect_stdout
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import importlib.util
from llm.extractor import extract_python_code
from sim.engine import run
from sim.traffic import TrafficConfig, generate_arrivals
from oracle.verdict import compute_per_seed_p99

MODELS = ["qwen2.5-coder:3b", "llama3.2:3b", "granite4.1:3b"]
PROMPTS = ["neutral", "pressured"]

def evaluate_file(filepath: Path):
    """Returns (status, control_p99, bulk_p99, hallucination_crash)"""
    if not filepath.exists():
        return "FILE_MISSING", 0, 0, False

    raw_text = filepath.read_text(encoding="utf-8")
    clean_code = extract_python_code(raw_text)
    
    # 1. Check for Hallucinations (Does the raw code crash its own tests?)
    hallucination_crash = False
    try:
        # We try to run the raw cleaned code (with its tests)
        temp_file = Path("generated/_temp_test.py")
        temp_file.write_text(clean_code, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("temp_mod", temp_file)
        module = importlib.util.module_from_spec(spec)
        
        # Suppress prints so they don't clutter our table
        f = io.StringIO()
        with redirect_stdout(f):
            spec.loader.exec_module(module)
    except Exception as e:
        hallucination_crash = True # It crashed!
        
    # 2. Strip AI's buggy tests for the Oracle run
    clean_code = re.sub(r'^test_proposed_scheduler\(\)$', '', clean_code, flags=re.MULTILINE)
    clean_code = re.sub(r'^test_scheduler\(\)$', '', clean_code, flags=re.MULTILINE)
    
    oracle_file = Path("generated/_temp_oracle.py")
    oracle_file.write_text(clean_code, encoding="utf-8")
    
    try:
        spec = importlib.util.spec_from_file_location("oracle_mod", oracle_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if not hasattr(module, "ProposedScheduler"):
            return "NO_CLASS", 0, 0, hallucination_crash
            
        cfg = TrafficConfig(n_devices=8, total_slots=2000, bulk_rate_per_device_per_slot=0.02, bulk_burstiness=0.0, seed=42)
        arrivals = generate_arrivals(cfg)
        scheduler = module.ProposedScheduler()
        log = run(arrivals, scheduler, n_devices=cfg.n_devices, max_slot=cfg.total_slots)
        
        c99 = compute_per_seed_p99(arrivals, log, "CONTROL")
        b99 = compute_per_seed_p99(arrivals, log, "BULK")
        
        passed = (c99 <= 7.80) and (b99 <= 985.53)
        return ("PASS" if passed else "FAIL_BOUNDS"), c99, b99, hallucination_crash
        
    except Exception as e:
        return "SYNTAX_ERROR", 0, 0, hallucination_crash

def main():
    print("Evaluating all models... (This may take a moment)\n")
    
    results = []
    
    for model in MODELS:
        for prompt in PROMPTS:
            filename = f"{model.replace(':', '_')}_{prompt}_output.py" if prompt == "pressured" else f"{model.replace(':', '_')}_output.py"
            filepath = Path("generated") / filename
            
            status, c99, b99, hallucination = evaluate_file(filepath)
            
            results.append({
                "Model": model,
                "Prompt": prompt,
                "Oracle Status": status,
                "CONTROL p99": f"{c99:.2f}",
                "BULK p99": f"{b99:.2f}",
                "Hallucinated Tests?": "YES" if hallucination else "NO"
            })
            
    print(f"{'Model':<20} | {'Prompt':<10} | {'Oracle Status':<12} | {'C_p99':<8} | {'B_p99':<8} | {'Hallucinated?'}")
    print("-" * 80)
    for r in results:
        print(f"{r['Model']:<20} | {r['Prompt']:<10} | {r['Oracle Status']:<12} | {r['CONTROL p99']:<8} | {r['BULK p99']:<8} | {r['Hallucinated Tests?']}")

if __name__ == "__main__":
    main()
