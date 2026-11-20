"""Canonical JSON and SHA-256 helpers.

Used everywhere a value must be hash-pinned: Constitution v0 itself, the
authorization ledger hash chain, sandbox before/after hashes, and G2
tamper detection.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json_dumps(obj: Any) -> str:
    """Serialize to canonical JSON: sorted keys, no whitespace, UTF-8.

    Two dicts with the same entries always produce the same string,
    regardless of insertion order. This is what makes hash pinning
    meaningful.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_canonical(obj: Any) -> str:
    return sha256_text(canonical_json_dumps(obj))
