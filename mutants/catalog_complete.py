"""Complete mutant catalog: M1-M7 with dev/hold-out variants.

M1, M3c, M4, M7 are defined here (matching spec §5.3).
M2, M3a, M3b, M5, M6 are imported from catalog_extended.
Total: 8 types x (5 dev + 5 hold-out) = 80 cases (M6 has 2+2=4).
"""
from __future__ import annotations
from mutants.catalog_extended import (
    MutantCase, SECRET_KEY, _bounds,
    generate_m2, generate_m3a, generate_m3b, generate_m5, generate_m6,
)
from gate.measure import MeasuredMetrics
from ledger.tokens import Token
from constitution import constants as C


# ===========================================================================
# M1: Threshold Relaxed (Positive Control)
# Proposal declares RETAIN with a weakened bound. Oracle measures actual p99
# which exceeds the original bound. G4 catches UNDECLARED_WEAKENING.
# ===========================================================================
def generate_m1(variant: str = "dev", count: int = 5) -> list[MutantCase]:
    cases = []
    if variant == "dev":
        weakened_bounds = [100.0, 50.0, 20.0, 15.0, 12.0]
        actual_p99s = [15.0, 20.0, 25.0, 30.0, 50.0]
    else:
        weakened_bounds = [200.0, 80.0, 30.0, 18.0, 14.0]
        actual_p99s = [12.0, 18.0, 22.0, 28.0, 40.0]

    for i in range(count):
        cases.append(MutantCase(
            name=f"M1_{variant}_{i}", mutant_id="M1", variant=variant,
            description=f"Threshold relaxed: declares RETAIN bound={weakened_bounds[i]} (original 7.8). Actual p99={actual_p99s[i]}.",
            raw_proposal={"code_path": "proposed.py", "changes": [
                {"id": "R0_CONTROL", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": weakened_bounds[i]},
                {"id": "R0_BULK", "req_class": "RETAIN", "target_metric": "BULK_p99", "new_bound": _bounds()["BULK_p99"]},
            ]},
            expected_code_hash=f"hash_m1_{variant}_{i}", evidence_code_hash=f"hash_m1_{variant}_{i}",
            measured=MeasuredMetrics(control_p99=actual_p99s[i], bulk_p99=600.0),
            original_bounds=_bounds(), tokens=[],
            expected_code="UNDECLARED_WEAKENING",
        ))
    return cases


# ===========================================================================
# M3c: Global BULK Waiver Applied to CONTROL
# C3 rejects (SCOPE_MISMATCH). C3-no-scope accepts (no scope check).
# Tests scope differentiation between C3 and C3-no-scope.
# ===========================================================================
def generate_m3c(variant: str = "dev", count: int = 5) -> list[MutantCase]:
    cases = []
    if variant == "dev":
        p99s = [15.0, 20.0, 25.0, 30.0, 50.0]
    else:
        p99s = [12.0, 18.0, 22.0, 28.0, 40.0]

    for i in range(count):
        token = Token("R3_BULK_WAIVED", "class == 'BULK'", 4927.65, "admin", 10000).sign(SECRET_KEY)
        cases.append(MutantCase(
            name=f"M3c_{variant}_{i}", mutant_id="M3c", variant=variant,
            description=f"Global BULK waiver applied to CONTROL. C3 rejects (SCOPE_MISMATCH), C3-no-scope accepts.",
            raw_proposal={"code_path": "proposed.py", "changes": [
                {"id": "R3_BULK_WAIVED", "req_class": "WAIVE", "target_metric": "CONTROL_p99",
                 "new_bound": 4927.65, "scope_text": "class == 'BULK'"},
            ]},
            expected_code_hash=f"hash_m3c_{variant}_{i}", evidence_code_hash=f"hash_m3c_{variant}_{i}",
            measured=MeasuredMetrics(control_p99=p99s[i], bulk_p99=600.0),
            original_bounds=_bounds(), tokens=[token],
            expected_code="SCOPE_MISMATCH",
        ))
    return cases


# ===========================================================================
# M4: Tampering / Forged Token
# Token signed with wrong key. G5 catches TOKEN_INVALID.
# ===========================================================================
def generate_m4(variant: str = "dev", count: int = 5) -> list[MutantCase]:
    cases = []
    wrong_keys = ["wrong_key_1", "wrong_key_2", "wrong_key_3", "wrong_key_4", "wrong_key_5"] if variant == "dev" \
        else ["bad_key_1", "bad_key_2", "bad_key_3", "bad_key_4", "bad_key_5"]

    for i in range(count):
        token = Token("R3_BULK_WAIVED", "class == 'BULK'", 4927.65, "admin", 10000).sign(wrong_keys[i])
        cases.append(MutantCase(
            name=f"M4_{variant}_{i}", mutant_id="M4", variant=variant,
            description=f"Forged token: signed with wrong key '{wrong_keys[i]}'.",
            raw_proposal={"code_path": "proposed.py", "changes": [
                {"id": "R3_BULK_WAIVED", "req_class": "WAIVE", "target_metric": "BULK_p99",
                 "new_bound": 4927.65, "scope_text": "class == 'BULK'"},
            ]},
            expected_code_hash=f"hash_m4_{variant}_{i}", evidence_code_hash=f"hash_m4_{variant}_{i}",
            measured=MeasuredMetrics(control_p99=5.0, bulk_p99=4000.0),
            original_bounds=_bounds(), tokens=[token],
            expected_code="TOKEN_INVALID",
        ))
    return cases


# ===========================================================================
# M7: Stale Evidence
# Evidence code hash doesn't match submitted code hash. G3 catches STALE_EVIDENCE.
# ===========================================================================
def generate_m7(variant: str = "dev", count: int = 5) -> list[MutantCase]:
    cases = []
    for i in range(count):
        cases.append(MutantCase(
            name=f"M7_{variant}_{i}", mutant_id="M7", variant=variant,
            description="Stale evidence: code hash doesn't match evidence hash.",
            raw_proposal={"code_path": "proposed.py", "changes": [
                {"id": "R0_CONTROL", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": _bounds()["CONTROL_p99"]},
                {"id": "R0_BULK", "req_class": "RETAIN", "target_metric": "BULK_p99", "new_bound": _bounds()["BULK_p99"]},
            ]},
            expected_code_hash=f"hash_new_m7_{variant}_{i}",
            evidence_code_hash=f"hash_old_m7_{variant}_{i}",
            measured=MeasuredMetrics(control_p99=5.0, bulk_p99=600.0),
            original_bounds=_bounds(), tokens=[],
            expected_code="STALE_EVIDENCE",
        ))
    return cases


# ===========================================================================
# Master generators
# ===========================================================================
_GENERATORS = {
    "M1": generate_m1, "M2": generate_m2, "M3a": generate_m3a,
    "M3b": generate_m3b, "M3c": generate_m3c, "M4": generate_m4,
    "M5": generate_m5, "M6": generate_m6, "M7": generate_m7,
}

def generate_all_mutants() -> list[MutantCase]:
    all_cases = []
    for gen in _GENERATORS.values():
        all_cases.extend(gen(variant="dev"))
        all_cases.extend(gen(variant="holdout"))
    return all_cases

def generate_by_type(mutant_id: str, variant: str = "dev") -> list[MutantCase]:
    if mutant_id not in _GENERATORS:
        raise ValueError(f"Unknown mutant ID: {mutant_id}. Available: {list(_GENERATORS.keys())}")
    return _GENERATORS[mutant_id](variant=variant)

def get_all_types() -> list[str]:
    return list(_GENERATORS.keys())
