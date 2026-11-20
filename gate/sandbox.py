"""Secure execution environment for untrusted LLM code (Amendment D2)."""
from __future__ import annotations
import os
import subprocess
import sys
import resource
from pathlib import Path

def _limit_resources():
    """Enforces memory and CPU limits inside the child process."""
    # Limit to 1 GB of memory
    limit_bytes = 1 * 1024 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
    # Limit CPU time to 5 seconds
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))

def run_in_sandbox(script_path: str, timeout_seconds: int = 10) -> str:
    """Runs a script securely and returns its stdout or raises an exception."""
    if not Path(script_path).exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    # Amendment D5: Scrub the environment so the child can't steal the key
    safe_env = {}
    for k, v in os.environ.items():
        if k != "AD_TOKEN_KEY":
            safe_env[k] = v

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            env=safe_env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            preexec_fn=_limit_resources
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Sandboxed code failed with exit code {result.returncode}:\n{result.stderr}")
            
        return result.stdout

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Sandboxed code exceeded {timeout_seconds} seconds.")
