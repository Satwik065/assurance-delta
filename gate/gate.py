"""The Gate Orchestrator. Runs a proposal through G0-G5 and the Oracle."""
from __future__ import annotations
from dataclasses import dataclass
from proposer.schema import MigrationProposal
from gate.migration import validate_migration, MalformedMigrationError
from gate.tamper import verify_frozen_files, verify_ledger_head, TamperError
from gate.evidence import verify_evidence_freshness, StaleEvidenceError
from gate.measure import check_undeclared_weakening, UndeclaredWeakeningError, MeasuredMetrics
from gate.scope_check import verify_waive, TokenInvalidError, ScopeMismatchError
from ledger.tokens import Token

@dataclass(frozen=True)
class GateResult:
    status: str  # "ACCEPT", "REJECT"
    reason: str
    code: str | None = None

def evaluate_proposal(
    raw_proposal: dict,
    expected_code_hash: str,
    evidence_code_hash: str,
    measured: MeasuredMetrics,
    original_bounds: dict[str, float],
    tokens: list[Token],
    current_slot: int,
    secret_key: str,
) -> GateResult:
    
    # G1: Validate Form
    try:
        proposal = validate_migration(raw_proposal)
    except MalformedMigrationError as e:
        return GateResult("REJECT", str(e), "MALFORMED_MIGRATION")
        
    # G3: Evidence Freshness
    try:
        verify_evidence_freshness(expected_code_hash, evidence_code_hash)
    except StaleEvidenceError as e:
        return GateResult("REJECT", str(e), "STALE_EVIDENCE")

    # G4: Undeclared Weakening
    try:
        check_undeclared_weakening(proposal, measured, original_bounds)
    except UndeclaredWeakeningError as e:
        return GateResult("REJECT", str(e), "UNDECLARED_WEAKENING")

    # G5: Token and Scope Checks
    for change in proposal.changes:
        if change.req_class == "WAIVE":
            # Find the token that matches this requirement ID
            matching_token = next((t for t in tokens if t.requirement_id == change.id), None)
            if not matching_token:
                return GateResult("REJECT", f"No token provided for WAIVE {change.id}", "TOKEN_INVALID")
                
            try:
                measured_val = measured.control_p99 if change.target_metric == "CONTROL_p99" else measured.bulk_p99
                verify_waive(change, matching_token, measured_val, current_slot, secret_key)
            except (TokenInvalidError, ScopeMismatchError) as e:
                return GateResult("REJECT", str(e), "TOKEN_INVALID")

    # If we make it here, everything passed!
    return GateResult("ACCEPT", "All gates passed.", None)
