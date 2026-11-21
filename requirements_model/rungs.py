"""Defines the R1 and R4 obligations."""
from __future__ import annotations
from constitution import constants as C
from requirements_model.classes import Requirement, RequirementClass

def get_r1_obligations() -> list[Requirement]:
    """R1: Scale-out to N=32. The bounds are identical to R0 (RETAIN)."""
    bounds = C.load_calibrated()
    return [
        Requirement("R1_CONTROL", RequirementClass.RETAIN, "CONTROL_p99", bounds["r0_control_p99_bound_slots"]),
        Requirement("R1_BULK", RequirementClass.RETAIN, "BULK_p99", bounds["r0_bulk_p99_bound_slots"])
    ]

def get_r4_obligations() -> list[Requirement]:
    """R4: Genuine CONFLICT. Load exceeds capacity, bounds cannot be met."""
    # By definition, R4 cannot be satisfied without a waiver (which is not allowed).
    return [
        Requirement("R4_CONFLICT", RequirementClass.CONFLICT, "CONTROL_p99", 7.8)
    ]
