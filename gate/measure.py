"""Gate G4: Detects undeclared weakening of obligations."""
from __future__ import annotations
from dataclasses import dataclass
from requirements_model.classes import RequirementClass
from proposer.schema import MigrationProposal

class UndeclaredWeakeningError(RuntimeError):
    pass

@dataclass(frozen=True)
class MeasuredMetrics:
    control_p99: float
    bulk_p99: float

def check_undeclared_weakening(proposal: MigrationProposal, measured: MeasuredMetrics, original_bounds: dict[str, float]) -> None:
    """Verifies that any RETAIN requirement still meets its original bound."""
    for change in proposal.changes:
        if change.req_class == "RETAIN":
            # If it's RETAIN, the new bound must be equal to or stricter than the original
            # (For now, we just check the measured metric against the original bound)
            
            actual_value = None
            if change.target_metric == "CONTROL_p99":
                actual_value = measured.control_p99
            elif change.target_metric == "BULK_p99":
                actual_value = measured.bulk_p99
                
            if actual_value is None:
                raise ValueError(f"Unknown target metric: {change.target_metric}")
                
            # The original bound from the Constitution
            original_bound = original_bounds.get(change.target_metric)
            if original_bound is None:
                 raise ValueError(f"No original bound for {change.target_metric}")
                 
            if actual_value > original_bound:
                raise UndeclaredWeakeningError(
                    f"UNDECLARED_WEAKENING: {change.target_metric} measured at {actual_value}, "
                    f"which exceeds the RETAIN bound of {original_bound}."
                )
