"""Sweep all 3 models through R2 (bursty) and R4 (conflict)."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from llm.harness import query_ollama, build_r2_prompt, build_r4_prompt

def main():
    baseline_code = Path("sim/scheduler_base.py").read_text(encoding="utf-8")
    output_dir = Path("generated")
    output_dir.mkdir(exist_ok=True)

    models = ["qwen2.5-coder:3b", "granite4.1:3b", "llama3.2:3b"]

    for model in models:
        print(f"\n=== {model} ===")

        print(f"  R2 (Bursty)...")
        resp = query_ollama(model, build_r2_prompt(baseline_code))
        (output_dir / f"{model}_r2_mini.py").write_text(resp, encoding="utf-8")

        print(f"  R4 (Conflict)...")
        resp = query_ollama(model, build_r4_prompt(baseline_code))
        (output_dir / f"{model}_r4_mini.py").write_text(resp, encoding="utf-8")

    print("\nSweep complete for R2 and R4!")

if __name__ == "__main__":
    main()
