"""R4 Conflict Certificate (Spec §3.6).

A capacity argument (offered load vs link capacity) frozen in the ledger
before any LLM run. If the certificate says R4 is a conflict, the gate
blocks with BLOCK_CONFLICT before running the oracle.
"""
from __future__ import annotations
from dataclasses import dataclass
from constitution.hashing import sha256_canonical


@dataclass(frozen=True)
class ConflictCertificate:
    rung: str
    offered_load_per_slot: float
    link_capacity_per_slot: float
    is_conflict: bool
    frozen_hash: str = ""

    def compute_hash(self) -> str:
        payload = {"rung": self.rung, "offered": self.offered_load_per_slot,
                    "capacity": self.link_capacity_per_slot, "conflict": self.is_conflict}
        return sha256_canonical(payload)


# Frozen R4 certificate: N=8, bulk_rate=0.30
# CONTROL rate = 0.4/slot, BULK rate = 2.4/slot, total = 2.8/slot > 1.0/slot
R4_CERTIFICATE = ConflictCertificate(
    rung="R4",
    offered_load_per_slot=2.8,
    link_capacity_per_slot=1.0,
    is_conflict=True,
)
R4_CERTIFICATE_FROZEN_HASH = R4_CERTIFICATE.compute_hash()


class ConflictError(RuntimeError):
    pass


def check_conflict_certificate(rung: str, cert: ConflictCertificate = R4_CERTIFICATE) -> None:
    """If the rung matches a conflict certificate, raise ConflictError."""
    if cert.is_conflict and cert.rung == rung:
        raise ConflictError(
            f"BLOCK_CONFLICT: Rung {rung} is a capacity conflict "
            f"(offered {cert.offered_load_per_slot}/slot > capacity {cert.link_capacity_per_slot}/slot)."
        )


def verify_certificate_integrity(cert: ConflictCertificate, expected_hash: str) -> bool:
    """Check the certificate hasn't been tampered with."""
    return cert.compute_hash() == expected_hash
