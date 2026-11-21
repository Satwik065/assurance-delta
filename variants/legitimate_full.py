"""Full legitimate variant suite: 20 per rung (R0, R1, R3) = 60 total.

Each variant stays within 80% of the applicable bound (Amendment: safety margin).
R1 uses N=16 (feasible — N=32 was infeasible because CONTROL rate 1.6/slot exceeds
the 1/slot uplink capacity; documented in RESEARCH_LOG).
"""
from __future__ import annotations
from dataclasses import dataclass
from gate.measure import MeasuredMetrics
from ledger.tokens import Token
from constitution import constants as C

SECRET_KEY = "pilot_secret_key"


@dataclass
class LegitimateCase:
    name: str
    rung: str
    variant: str  # "dev" or "holdout"
    description: str
    raw_proposal: dict
    expected_code_hash: str
    evidence_code_hash: str
    measured: MeasuredMetrics
    original_bounds: dict[str, float]
    tokens: list
    current_slot: int = 500
    secret_key: str = SECRET_KEY
    expected_status: str = "ACCEPT"
    expected_code: str = ""


def _bounds() -> dict[str, float]:
    b = C.load_calibrated()
    return {"CONTROL_p99": b["r0_control_p99_bound_slots"], "BULK_p99": b["r0_bulk_p99_bound_slots"]}


def _within_80pct(value: float, bound: float) -> bool:
    return value <= bound * C.LEGIT_VARIANT_MAX_BOUND_FRACTION


# ===========================================================================
# R0: Baseline, N=8, both bounds RETAIN
# ===========================================================================
def generate_r0(count: int = 20) -> list[LegitimateCase]:
    cases = []
    bound_c = _bounds()["CONTROL_p99"]  # 7.8
    bound_b = _bounds()["BULK_p99"]     # 985.53
    max_c = bound_c * 0.8  # 6.24
    max_b = bound_b * 0.8  # 788.42

    for i in range(count):
        # Parameter sweep: spread metrics across 80% of the bound
        c_p99 = 2.0 + (i / max(count - 1, 1)) * (max_c - 2.0)  # 2.0 to 6.24
        b_p99 = 300.0 + (i / max(count - 1, 1)) * (max_b - 300.0)  # 300 to 788.42
        variant = "dev" if i < 10 else "holdout"

        cases.append(LegitimateCase(
            name=f"R0_legit_{variant}_{i % 10}",
            rung="R0",
            variant=variant,
            description=f"R0 legitimate variant: CONTROL p99={c_p99:.2f}, BULK p99={b_p99:.2f}. Both under 80% of bound.",
            raw_proposal={
                "code_path": "proposed.py",
                "changes": [
                    {"id": "R0_CONTROL", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": bound_c},
                    {"id": "R0_BULK", "req_class": "RETAIN", "target_metric": "BULK_p99", "new_bound": bound_b},
                ],
            },
            expected_code_hash=f"hash_r0_legit_{i}",
            evidence_code_hash=f"hash_r0_legit_{i}",
            measured=MeasuredMetrics(control_p99=round(c_p99, 2), bulk_p99=round(b_p99, 2)),
            original_bounds=_bounds(),
            tokens=[],
        ))
    return cases


# ===========================================================================
# R1: Scale-out, N=16 (feasible), both bounds RETAIN
# ===========================================================================
def generate_r1(count: int = 20) -> list[LegitimateCase]:
    cases = []
    bound_c = _bounds()["CONTROL_p99"]
    bound_b = _bounds()["BULK_p99"]
    max_c = bound_c * 0.8
    max_b = bound_b * 0.8

    for i in range(count):
        c_p99 = 3.0 + (i / max(count - 1, 1)) * (max_c - 3.0)  # 3.0 to 6.24
        b_p99 = 350.0 + (i / max(count - 1, 1)) * (max_b - 350.0)
        variant = "dev" if i < 10 else "holdout"

        cases.append(LegitimateCase(
            name=f"R1_legit_{variant}_{i % 10}",
            rung="R1",
            variant=variant,
            description=f"R1 legitimate variant (N=16): CONTROL p99={c_p99:.2f}, BULK p99={b_p99:.2f}. Both under 80% of bound.",
            raw_proposal={
                "code_path": "proposed.py",
                "changes": [
                    {"id": "R1_CONTROL", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": bound_c},
                    {"id": "R1_BULK", "req_class": "RETAIN", "target_metric": "BULK_p99", "new_bound": bound_b},
                ],
            },
            expected_code_hash=f"hash_r1_legit_{i}",
            evidence_code_hash=f"hash_r1_legit_{i}",
            measured=MeasuredMetrics(control_p99=round(c_p99, 2), bulk_p99=round(b_p99, 2)),
            original_bounds=_bounds(),
            tokens=[],
        ))
    return cases


# ===========================================================================
# R3: Higher BULK load, CONTROL RETAIN, BULK WAIVE (scoped token)
# ===========================================================================
def generate_r3(count: int = 20) -> list[LegitimateCase]:
    cases = []
    bound_c = _bounds()["CONTROL_p99"]
    waived_bulk = _bounds()["BULK_p99"] * C.R3_BULK_WAIVE_MULTIPLIER  # 4927.65
    max_c = bound_c * 0.8  # 6.24
    max_b = waived_bulk * 0.8  # 3942.12

    for i in range(count):
        c_p99 = 2.0 + (i / max(count - 1, 1)) * (max_c - 2.0)
        b_p99 = 1000.0 + (i / max(count - 1, 1)) * (max_b - 1000.0)
        variant = "dev" if i < 10 else "holdout"

        token = Token(
            requirement_id="R3_BULK_WAIVED",
            scope_text="class == 'BULK'",
            new_bound=waived_bulk,
            issuer="admin",
            expiry_slot=10000,
        ).sign(SECRET_KEY)

        cases.append(LegitimateCase(
            name=f"R3_legit_{variant}_{i % 10}",
            rung="R3",
            variant=variant,
            description=f"R3 legitimate variant: CONTROL p99={c_p99:.2f} (strict), BULK p99={b_p99:.2f} (waived, under {waived_bulk:.0f}).",
            raw_proposal={
                "code_path": "proposed.py",
                "changes": [
                    {"id": "R3_CONTROL_STRICT", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": bound_c},
                    {"id": "R3_BULK_WAIVED", "req_class": "WAIVE", "target_metric": "BULK_p99",
                     "new_bound": waived_bulk, "scope_text": "class == 'BULK'"},
                ],
            },
            expected_code_hash=f"hash_r3_legit_{i}",
            evidence_code_hash=f"hash_r3_legit_{i}",
            measured=MeasuredMetrics(control_p99=round(c_p99, 2), bulk_p99=round(b_p99, 2)),
            original_bounds=_bounds(),
            tokens=[token],
        ))
    return cases


# ===========================================================================
# Master generators
# ===========================================================================
def generate_all_legitimate() -> list[LegitimateCase]:
    return generate_r0() + generate_r1() + generate_r3()


def generate_by_rung(rung: str, count: int = 20) -> list[LegitimateCase]:
    generators = {"R0": generate_r0, "R1": generate_r1, "R3": generate_r3}
    if rung not in generators:
        raise ValueError(f"Unknown rung: {rung}. Available: {list(generators.keys())}")
    return generators[rung](count=count)


def get_rungs() -> list[str]:
    return ["R0", "R1", "R3"]
