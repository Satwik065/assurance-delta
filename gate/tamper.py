"""Gate G2: Detects if frozen files or the ledger have been tampered with."""
from __future__ import annotations
import json
from pathlib import Path
from constitution.hashing import sha256_file
from constitution import constants as C

class TamperError(RuntimeError):
    pass

def verify_frozen_files(expected_hashes: dict[str, str]) -> None:
    """Checks if any frozen file has been modified since the hash was recorded."""
    for file_path, expected_hash in expected_hashes.items():
        p = Path(file_path)
        if not p.exists():
            raise TamperError(f"TAMPER: Frozen file missing: {file_path}")
            
        actual_hash = sha256_file(p)
        if actual_hash != expected_hash:
            raise TamperError(f"TAMPER: File modified: {file_path}\nExpected: {expected_hash}\nActual:   {actual_hash}")

def verify_ledger_head(expected_head: str) -> None:
    """Checks if the ledger's head hash has been modified."""
    p = Path(C.LEDGER_HEAD_PATH)
    if not p.exists():
        raise TamperError(f"TAMPER: Ledger head file missing: {p}")
        
    actual_head = p.read_text(encoding="utf-8").strip()
    if actual_head != expected_head:
        raise TamperError(f"TAMPER: Ledger head modified.\nExpected: {expected_head}\nActual:   {actual_head}")
