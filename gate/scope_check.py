"""Gate G5: Verifies WAIVE tokens, signatures, and scope predicates."""
from __future__ import annotations
from ledger.tokens import Token
from requirements_model.scope import ScopePredicate
from proposer.schema import RequirementChange

class TokenInvalidError(RuntimeError):
    pass

class ScopeMismatchError(RuntimeError):
    pass

def verify_waive(change: RequirementChange, token: Token, measured_val: float, current_slot: int, secret_key: str) -> None:
    # 1. Forgery check
    if not token.verify(secret_key):
        raise TokenInvalidError("TOKEN_INVALID: Signature is forged or key is wrong.")
        
    # 2. Expiration check
    if current_slot > token.expiry_slot:
        raise TokenInvalidError("TOKEN_INVALID: Token has expired.")
        
    # 3. Speed check: The measured value must fit under the token's bound
    if measured_val > token.new_bound:
        raise TokenInvalidError(f"TOKEN_INVALID: Measured {measured_val} exceeds token bound {token.new_bound}.")
        
    # 4. Scope check: Does the token's scope cover the metric being changed?
    # We map the target_metric to a context for the parser
    context = {}
    if change.target_metric == "CONTROL_p99":
        context = {"class": "CONTROL"}
    elif change.target_metric == "BULK_p99":
        context = {"class": "BULK"}
    else:
        raise ScopeMismatchError(f"Unknown metric for scope: {change.target_metric}")
        
    predicate = ScopePredicate(token.scope_text)
    if not predicate.evaluate(context):
        raise ScopeMismatchError(
            f"SCOPE_MISMATCH: Token scope '{token.scope_text}' does not cover "
            f"the change to {change.target_metric} (context: {context})."
        )
