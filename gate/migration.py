"""Gate G1: Validates that a Migration Proposal is well-formed."""
from __future__ import annotations
from typing import Any
from proposer.schema import MigrationProposal, RequirementChange

class MalformedMigrationError(ValueError):
    pass

def validate_migration(data: dict[str, Any]) -> MigrationProposal:
    """Parses a dict into a MigrationProposal, raising MalformedMigrationError if invalid."""
    try:
        code_path = data["code_path"]
        changes_data = data["changes"]
        
        if not isinstance(code_path, str):
            raise MalformedMigrationError("code_path must be a string")
        if not isinstance(changes_data, list) or not changes_data:
            raise MalformedMigrationError("changes must be a non-empty list")
            
        changes = []
        for c in changes_data:
            scope = c.get("scope_text")
            change = RequirementChange(
                id=str(c["id"]),
                req_class=str(c["req_class"]),
                target_metric=str(c["target_metric"]),
                new_bound=float(c["new_bound"]),
                scope_text=str(scope) if scope else None
            )
            changes.append(change)
            
        return MigrationProposal(code_path=code_path, changes=changes)
        
    except KeyError as e:
        raise MalformedMigrationError(f"Missing required field: {e}")
    except (TypeError, ValueError) as e:
        raise MalformedMigrationError(f"Invalid field type: {e}")
