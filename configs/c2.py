"""C2: Oracle-only. Strict enforcement of original bounds. No WAIVE allowed."""
from gate.measure import MeasuredMetrics

def evaluate_c2(measured: MeasuredMetrics, original_bounds: dict[str, float]) -> str:
    # C2 ignores tokens entirely. If it violates the original bound, it fails.
    if measured.control_p99 > original_bounds["CONTROL_p99"]:
        return "REJECT"
    if measured.bulk_p99 > original_bounds["BULK_p99"]:
        return "REJECT"
    return "ACCEPT"
