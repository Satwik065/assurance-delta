"""Gate G4: Detects undeclared weakening of obligations."""
from __future__ import annotations
import math
from dataclasses import dataclass
from proposer.schema import MigrationProposal


class UndeclaredWeakeningError(RuntimeError):
    pass


@dataclass(frozen=True)
class MeasuredMetrics:
    control_p99: float
    bulk_p99: float


def check_undeclared_weakening(
    proposal: MigrationProposal,
    measured: MeasuredMetrics,
    original_bounds: dict[str, float],
) -> None:
    """Verifies that any RETAIN requirement still meets its original bound."""
    for change in proposal.changes:
        if change.req_class == "RETAIN":
            if change.target_metric == "CONTROL_p99":
                actual_value = measured.control_p99
            elif change.target_metric == "BULK_p99":
                actual_value = measured.bulk_p99
            else:
                raise ValueError(f"Unknown target metric: {change.target_metric}")

            original_bound = original_bounds.get(change.target_metric)
            if original_bound is None:
                raise ValueError(f"No original bound for {change.target_metric}")

            if (not math.isfinite(actual_value)) or actual_value > original_bound:
                raise UndeclaredWeakeningError(
                    f"UNDECLARED_WEAKENING: {change.target_metric} measured at {actual_value}, "
                    f"which exceeds the RETAIN bound of {original_bound}."
                )
