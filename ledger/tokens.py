"""Cryptographically signed authorization tokens (Amendment D5)."""
from __future__ import annotations
import hmac
import hashlib
import json
import os
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass(frozen=True)
class Token:
    requirement_id: str
    scope_text: str
    new_bound: float
    issuer: str
    expiry_slot: int
    signature: str = ""

    def sign(self, secret_key: str) -> "Token":
        payload = asdict(self)
        del payload["signature"] # Don't sign the signature itself
        payload_str = json.dumps(payload, sort_keys=True)
        sig = hmac.new(secret_key.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
        return Token(**{**payload, "signature": sig})

    def verify(self, secret_key: str) -> bool:
        if not self.signature:
            return False
        expected = self.sign(secret_key)
        return hmac.compare_digest(self.signature, expected.signature)

def get_signing_key() -> str:
    """Fetches the key from the environment. Sandbox scrubs this (D5)."""
    key = os.environ.get("AD_TOKEN_KEY")
    if not key:
        raise ValueError("AD_TOKEN_KEY environment variable is not set.")
    return key
