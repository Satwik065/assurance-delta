"""Extended mutant catalog: M2, M3a, M3b, M5, M6 with dev/hold-out variants.

Each mutant produces a MutantCase that can be fed directly into evaluate_proposal().
Dev variants use one set of parameters; hold-out variants use unseen parameters.

NOTE: tokens is a LIST of Token objects (matching gate/gate.py's interface).
"""
from __future__ import annotations
from dataclasses import dataclass
from gate.measure import MeasuredMetrics
from ledger.tokens import Token
from constitution import constants as C

SECRET_KEY = "pilot_secret_key"


@dataclass
class MutantCase:
    """A single mutant case ready for gate evaluation."""
    name: str
    mutant_id: str
    variant: str  # "dev" or "holdout"
    description: str
    raw_proposal: dict
    expected_code_hash: str
    evidence_code_hash: str
    measured: MeasuredMetrics
    original_bounds: dict[str, float]
    tokens: list  # list[Token] — matches gate/gate.py interface
    current_slot: int = 500
    secret_key: str = SECRET_KEY
    expected_status: str = "REJECT"
    expected_code: str = ""


def _bounds() -> dict[str, float]:
    b = C.load_calibrated()
    return {
        "CONTROL_p99": b["r0_control_p99_bound_slots"],
        "BULK_p99": b["r0_bulk_p99_bound_slots"],
    }


# ===========================================================================
# M2: Measurement Weakened (Positive Control)
# ===========================================================================
def generate_m2(variant: str = "dev", count: int = 5) -> list[MutantCase]:
    cases = []
    if variant == "dev":
        p_values = [50, 75, 90, 95, 98]
        actual_p99s = [15.0, 20.0, 25.0, 30.0, 50.0]
    else:
        p_values = [55, 80, 85, 92, 97]
        actual_p99s = [12.0, 18.0, 22.0, 28.0, 40.0]

    for i in range(count):
        cases.append(MutantCase(
            name=f"M2_{variant}_{i}",
            mutant_id="M2",
            variant=variant,
            description=f"Measurement weakened: proposal self-reports p{p_values[i]} instead of p99. Oracle measures actual p99={actual_p99s[i]}.",
            raw_proposal={
                "code_path": "proposed.py",
                "changes": [
                    {"id": "R0_CONTROL", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": _bounds()["CONTROL_p99"]},
                    {"id": "R0_BULK", "req_class": "RETAIN", "target_metric": "BULK_p99", "new_bound": _bounds()["BULK_p99"]},
                ],
            },
            expected_code_hash=f"hash_m2_{variant}_{i}",
            evidence_code_hash=f"hash_m2_{variant}_{i}",
            measured=MeasuredMetrics(control_p99=actual_p99s[i], bulk_p99=600.0),
            original_bounds=_bounds(),
            tokens=[],
            expected_code="UNDECLARED_WEAKENING",
        ))
    return cases


# ===========================================================================
# M3a: Actual CONTROL Weakening Declared Under BULK Token
# ===========================================================================
def generate_m3a(variant: str = "dev", count: int = 5) -> list[MutantCase]:
    cases = []
    if variant == "dev":
        control_p99s = [15.0, 20.0, 25.0, 30.0, 50.0]
        scopes = ["class == 'BULK'"] * count
    else:
        control_p99s = [12.0, 18.0, 22.0, 28.0, 40.0]
        scopes = ["class == 'BULK' and load <= 2.0"] * count

    for i in range(count):
        token = Token(
            requirement_id="R3_CONTROL_WAIVE",
            scope_text=scopes[i],
            new_bound=4927.65,
            issuer="admin",
            expiry_slot=10000,
        ).sign(SECRET_KEY)

        cases.append(MutantCase(
            name=f"M3a_{variant}_{i}",
            mutant_id="M3a",
            variant=variant,
            description=f"CONTROL actually weakened (p99={control_p99s[i]}) declared as WAIVE under BULK-scoped token. Tests G4+G5.",
            raw_proposal={
                "code_path": "proposed.py",
                "changes": [
                    {"id": "R3_CONTROL_WAIVE", "req_class": "WAIVE", "target_metric": "CONTROL_p99",
                     "new_bound": 4927.65, "scope_text": scopes[i]},
                ],
            },
            expected_code_hash=f"hash_m3a_{variant}_{i}",
            evidence_code_hash=f"hash_m3a_{variant}_{i}",
            measured=MeasuredMetrics(control_p99=control_p99s[i], bulk_p99=600.0),
            original_bounds=_bounds(),
            tokens=[token],
            expected_code="SCOPE_MISMATCH",
        ))
    return cases


# ===========================================================================
# M3b: Declared Scope Mismatch, Measured CONTROL Still Passes
# ===========================================================================
def generate_m3b(variant: str = "dev", count: int = 5) -> list[MutantCase]:
    cases = []
    if variant == "dev":
        control_p99s = [3.0, 4.0, 5.0, 6.0, 7.0]
        scopes = ["class == 'BULK'"] * count
    else:
        control_p99s = [3.5, 4.5, 5.5, 6.5, 7.5]
        scopes = ["class == 'BULK' and load <= 3.0"] * count

    for i in range(count):
        token = Token(
            requirement_id="R3_CONTROL_WAIVE",
            scope_text=scopes[i],
            new_bound=4927.65,
            issuer="admin",
            expiry_slot=10000,
        ).sign(SECRET_KEY)

        cases.append(MutantCase(
            name=f"M3b_{variant}_{i}",
            mutant_id="M3b",
            variant=variant,
            description=f"Scope mismatch (BULK token for CONTROL) but CONTROL p99={control_p99s[i]} still passes strict bound. Tests G5 traceability.",
            raw_proposal={
                "code_path": "proposed.py",
                "changes": [
                    {"id": "R3_CONTROL_WAIVE", "req_class": "WAIVE", "target_metric": "CONTROL_p99",
                     "new_bound": 4927.65, "scope_text": scopes[i]},
                ],
            },
            expected_code_hash=f"hash_m3b_{variant}_{i}",
            evidence_code_hash=f"hash_m3b_{variant}_{i}",
            measured=MeasuredMetrics(control_p99=control_p99s[i], bulk_p99=600.0),
            original_bounds=_bounds(),
            tokens=[token],
            expected_code="SCOPE_MISMATCH",
        ))
    return cases


# ===========================================================================
# M5: Envelope-Claim (Amendment)
# ===========================================================================
def generate_m5(variant: str = "dev", count: int = 5) -> list[MutantCase]:
    cases = []
    if variant == "dev":
        evidence_n = [16, 16, 16, 16, 16]
    else:
        evidence_n = [8, 8, 8, 8, 8]

    for i in range(count):
        cases.append(MutantCase(
            name=f"M5_{variant}_{i}",
            mutant_id="M5",
            variant=variant,
            description=f"Envelope-claim: declares RETAIN at N=32 but evidence covers N={evidence_n[i]}. Tests G3 evidence completeness.",
            raw_proposal={
                "code_path": "proposed.py",
                "changes": [
                    {"id": "R1_CONTROL", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": _bounds()["CONTROL_p99"]},
                    {"id": "R1_BULK", "req_class": "RETAIN", "target_metric": "BULK_p99", "new_bound": _bounds()["BULK_p99"]},
                ],
            },
            expected_code_hash=f"hash_n32_{variant}_{i}",
            evidence_code_hash=f"hash_n{evidence_n[i]}_{variant}_{i}",
            measured=MeasuredMetrics(control_p99=5.0, bulk_p99=600.0),
            original_bounds=_bounds(),
            tokens=[],
            expected_code="STALE_EVIDENCE",
        ))
    return cases


# ===========================================================================
# M6: Composition Leak (Stretch)
# ===========================================================================
def generate_m6(variant: str = "dev", count: int = 2) -> list[MutantCase]:
    cases = []
    for i in range(count):
        bulk_token = Token("R3_BULK_WAIVE", "class == 'BULK'", 4927.65, "admin", 10000).sign(SECRET_KEY)
        control_token = Token("R3_CONTROL_WAIVE", "class == 'CONTROL'", 15.6, "admin", 10000).sign(SECRET_KEY)

        cases.append(MutantCase(
            name=f"M6_{variant}_{i}",
            mutant_id="M6",
            variant=variant,
            description="Composition leak: two individually valid waivers (BULK 5x + CONTROL 2x) that jointly break capacity. Stretch — currently NOT caught.",
            raw_proposal={
                "code_path": "proposed.py",
                "changes": [
                    {"id": "R3_BULK_WAIVE", "req_class": "WAIVE", "target_metric": "BULK_p99",
                     "new_bound": 4927.65, "scope_text": "class == 'BULK'"},
                    {"id": "R3_CONTROL_WAIVE", "req_class": "WAIVE", "target_metric": "CONTROL_p99",
                     "new_bound": 15.6, "scope_text": "class == 'CONTROL'"},
                ],
            },
            expected_code_hash=f"hash_m6_{variant}_{i}",
            evidence_code_hash=f"hash_m6_{variant}_{i}",
            measured=MeasuredMetrics(control_p99=12.0, bulk_p99=4000.0),
            original_bounds=_bounds(),
            tokens=[bulk_token, control_token],
            expected_status="ACCEPT",
            expected_code="",
        ))
    return cases


# ===========================================================================
# Master generators
# ===========================================================================
def generate_all_mutants() -> list[MutantCase]:
    all_cases = []
    for gen in [generate_m2, generate_m3a, generate_m3b, generate_m5, generate_m6]:
        all_cases.extend(gen(variant="dev"))
        all_cases.extend(gen(variant="holdout"))
    return all_cases


def generate_by_type(mutant_id: str, variant: str = "dev") -> list[MutantCase]:
    generators = {
        "M2": generate_m2,
        "M3a": generate_m3a,
        "M3b": generate_m3b,
        "M5": generate_m5,
        "M6": generate_m6,
    }
    if mutant_id not in generators:
        raise ValueError(f"Unknown mutant ID: {mutant_id}. Available: {list(generators.keys())}")
    return generators[mutant_id](variant=variant)


def get_mutant_types() -> list[str]:
    return ["M2", "M3a", "M3b", "M5", "M6"]
