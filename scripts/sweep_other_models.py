"""Sweep Granite and Llama through R0, R1, R3."""
import sys, json
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from llm.harness import query_ollama, build_r1_prompt, build_r3_token_prompt, build_neutral_prompt
from ledger.tokens import Token

def main():
    baseline_code = Path("sim/scheduler_base.py").read_text(encoding="utf-8")
    output_dir = Path("generated")
    output_dir.mkdir(exist_ok=True)

    token = Token("R3_BULK_WAIVED", "class == 'BULK'", 4927.65, "admin", 10000)
    token_json = json.dumps({
        "requirement_id": token.requirement_id,
        "scope_text": token.scope_text,
        "new_bound": token.new_bound,
        "issuer": token.issuer,
        "expiry_slot": token.expiry_slot
    })

    models = ["granite4.1:3b", "llama3.2:3b"]

    for model in models:
        print(f"\n=== {model} ===")

        print(f"  R0 (Baseline)...")
        resp = query_ollama(model, build_neutral_prompt(baseline_code))
        (output_dir / f"{model}_r0_mini.py").write_text(resp, encoding="utf-8")

        print(f"  R1 (Scale-out)...")
        resp = query_ollama(model, build_r1_prompt(baseline_code))
        (output_dir / f"{model}_r1_mini.py").write_text(resp, encoding="utf-8")

        print(f"  R3 (Token Waiver)...")
        resp = query_ollama(model, build_r3_token_prompt(baseline_code, token_json))
        (output_dir / f"{model}_r3_mini.py").write_text(resp, encoding="utf-8")

    print("\nSweep complete for Granite and Llama!")

if __name__ == "__main__":
    main()
