"""The actual list of rules (obligations) for each rung of the ladder."""
from __future__ import annotations
from constitution import constants as C
from requirements_model.classes import Requirement, RequirementClass

def get_r0_obligations() -> list[Requirement]:
    """The baseline rules. CONTROL and BULK must meet the frozen bounds."""
    bounds = C.load_calibrated()
    
    return [
        Requirement(
            id="R0_CONTROL",
            req_class=RequirementClass.RETAIN,
            target_metric="CONTROL_p99",
            bound=bounds["r0_control_p99_bound_slots"]
        ),
        Requirement(
            id="R0_BULK",
            req_class=RequirementClass.RETAIN,
            target_metric="BULK_p99",
            bound=bounds["r0_bulk_p99_bound_slots"]
        )
    ]

def get_r3_obligations() -> list[Requirement]:
    """R3 adds a WAIVE rule: BULK is allowed to be slower if it has a scoped token."""
    bounds = C.load_calibrated()
    waived_bulk_bound = bounds["r0_bulk_p99_bound_slots"] * C.R3_BULK_WAIVE_MULTIPLIER
    
    return [
        Requirement(
            id="R3_CONTROL_STRICT",
            req_class=RequirementClass.RETAIN,
            target_metric="CONTROL_p99",
            bound=bounds["r0_control_p99_bound_slots"]
        ),
        Requirement(
            id="R3_BULK_WAIVED",
            req_class=RequirementClass.WAIVE,
            target_metric="BULK_p99",
            bound=waived_bulk_bound,
            scope_text="class == 'BULK'" # Only applies to BULK!
        )
    ]
