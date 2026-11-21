"""C3-no-scope: Applies WAIVE globally. Fails to check the scope predicate."""
from gate.measure import MeasuredMetrics
from ledger.tokens import Token

def evaluate_c3_no_scope(measured: MeasuredMetrics, original_bounds: dict[str, float], tokens: list[Token]) -> str:
    # If there's a BULK waiver, it applies to EVERYTHING (even CONTROL)
    has_waiver = any(t.requirement_id == "R3_BULK_WAIVED" for t in tokens)
    
    if has_waiver:
        # Control is judged against the relaxed BULK bound!
        relaxed_bound = 4927.65
        if measured.control_p99 > relaxed_bound:
            return "REJECT"
        if measured.bulk_p99 > relaxed_bound:
            return "REJECT"
        return "ACCEPT"
    else:
        # No waiver, standard strict checks
        if measured.control_p99 > original_bounds["CONTROL_p99"] or measured.bulk_p99 > original_bounds["BULK_p99"]:
            return "REJECT"
        return "ACCEPT"
