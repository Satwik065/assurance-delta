"""Gate G5: Verifies WAIVE tokens, signatures, expiry, bounds, and scope predicates."""
from __future__ import annotations
import math
from typing import Any
from ledger.tokens import Token
from requirements_model.scope import ScopePredicate
from proposer.schema import RequirementChange


class TokenInvalidError(RuntimeError):
    pass


class ScopeMismatchError(RuntimeError):
    pass


def verify_waive(
    change: RequirementChange,
    token: Token,
    measured_val: float,
    current_slot: int,
    secret_key: str,
    scenario_context: dict[str, Any] | None = None,
) -> None:
    # 1. Forgery check
    if not token.verify(secret_key):
        raise TokenInvalidError("TOKEN_INVALID: Signature is forged or key is wrong.")

    # 2. Expiration check (strict: expiry_slot + 1 is expired)
    if current_slot > token.expiry_slot:
        raise TokenInvalidError(
            f"TOKEN_INVALID: Token has expired (expiry={token.expiry_slot}, current={current_slot})."
        )

    # 3. Bound check (non-finite +inf / NaN always fails)
    if (not math.isfinite(measured_val)) or measured_val > token.new_bound:
        raise TokenInvalidError(
            f"TOKEN_INVALID: Measured {measured_val} exceeds token bound {token.new_bound}."
        )

    # 4. Scope predicate check (merges class with optional scenario_context like load/burstiness)
    context: dict[str, Any] = dict(scenario_context) if scenario_context else {}
    if change.target_metric == "CONTROL_p99":
        context["class"] = "CONTROL"
    elif change.target_metric == "BULK_p99":
        context["class"] = "BULK"
    else:
        raise ScopeMismatchError(f"Unknown metric for scope: {change.target_metric}")

    try:
        predicate = ScopePredicate(token.scope_text)
    except ValueError as e:
        raise ScopeMismatchError(f"SCOPE_MISMATCH: Invalid scope grammar '{token.scope_text}': {e}")

    if not predicate.evaluate(context):
        raise ScopeMismatchError(
            f"SCOPE_MISMATCH: Token scope '{token.scope_text}' does not cover "
            f"{change.target_metric} (context: {context})."
        )
