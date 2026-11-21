"""Runs a mini-sweep: 1 model, 3 rungs, 1 attempt each."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from llm.harness import query_ollama, build_r1_prompt, build_r3_token_prompt, build_neutral_prompt
from ledger.tokens import Token
import json

def main():
    baseline_code = Path("sim/scheduler_base.py").read_text(encoding="utf-8")
    model = "qwen2.5-coder:3b"
    output_dir = Path("generated")
    
    # 1. Neutral R0
    print(f"Querying {model} for R0...")
    resp_r0 = query_ollama(model, build_neutral_prompt(baseline_code))
    (output_dir / f"{model}_r0_mini.py").write_text(resp_r0, encoding="utf-8")
    
    # 2. Scale-out R1
    print(f"Querying {model} for R1 (Scale-out)...")
    resp_r1 = query_ollama(model, build_r1_prompt(baseline_code))
    (output_dir / f"{model}_r1_mini.py").write_text(resp_r1, encoding="utf-8")
    
    # 3. Token R3
    print(f"Querying {model} for R3 (Token Waiver)...")
    token = Token("R3_BULK_WAIVED", "class == 'BULK'", 4927.65, "admin", 10000)
    token_json = json.dumps(token.__dict__)
    resp_r3 = query_ollama(model, build_r3_token_prompt(baseline_code, token_json))
    (output_dir / f"{model}_r3_mini.py").write_text(resp_r3, encoding="utf-8")

    print("Mini-sweep complete. Check generated/ folder!")

if __name__ == "__main__":
    main()
