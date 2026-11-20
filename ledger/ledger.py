"""Append-only hash chain ledger (Amendment D6)."""
from __future__ import annotations
import json
import hashlib
from dataclasses import dataclass, asdict
from typing import Optional
from ledger.tokens import Token

@dataclass(frozen=True)
class LedgerEntry:
    action: str
    token: Token
    prev_hash: str
    entry_hash: str = ""

    def compute_hash(self) -> str:
        payload = asdict(self)
        del payload["entry_hash"]
        # Convert token to dict for serialization
        payload["token"] = asdict(self.token)
        payload_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()

class Ledger:
    def __init__(self):
        self.entries: list[LedgerEntry] = []
        self.head_hash = "GENESIS"

    def append(self, action: str, token: Token) -> LedgerEntry:
        entry = LedgerEntry(action=action, token=token, prev_hash=self.head_hash)
        # Create a new entry with the computed hash
        entry = LedgerEntry(action=entry.action, token=entry.token, prev_hash=entry.prev_hash, entry_hash=entry.compute_hash())
        self.entries.append(entry)
        self.head_hash = entry.entry_hash
        return entry

    def verify_chain(self) -> bool:
        expected_prev = "GENESIS"
        for entry in self.entries:
            if entry.prev_hash != expected_prev:
                return False
            if entry.entry_hash != entry.compute_hash():
                return False
            expected_prev = entry.entry_hash
        return True
