"""Queries local Ollama models to generate scheduler upgrades."""
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from llm.harness import query_ollama, build_neutral_prompt

def main():
    baseline_path = Path("sim/scheduler_base.py")
    baseline_code = baseline_path.read_text(encoding="utf-8")
    prompt = build_neutral_prompt(baseline_code)
    
    # The 3 models you have installed
    models = [
        "qwen2.5-coder:3b",
        "llama3.2:3b",
        "granite4.1:3b"
    ]
    
    output_dir = Path("generated")
    output_dir.mkdir(exist_ok=True)
    
    print("Starting LLM Interrogation...")
    
    for model in models:
        print(f"\nQuerying {model}... (This may take 10-30 seconds)")
        try:
            start_time = time.time()
            response = query_ollama(model, prompt)
            elapsed = time.time() - start_time
            
            filename = output_dir / f"{model.replace(':', '_')}_output.py"
            filename.write_text(response, encoding="utf-8")
            
            print(f"  -> Success! Took {elapsed:.1f}s")
            print(f"  -> Saved to {filename}")
            
        except Exception as e:
            print(f"  -> Failed to query {model}: {e}")
            
    print("\nDone. Check the 'generated/' folder to see what the AIs wrote.")

if __name__ == "__main__":
    main()
