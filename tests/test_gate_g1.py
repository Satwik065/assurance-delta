import pytest
from gate.migration import validate_migration, MalformedMigrationError

def test_valid_migration():
    data = {
        "code_path": "scheduler.py",
        "changes": [
            {"id": "R0_CONTROL", "req_class": "RETAIN", "target_metric": "CONTROL_p99", "new_bound": 7.8}
        ]
    }
    proposal = validate_migration(data)
    assert proposal.code_path == "scheduler.py"
    assert len(proposal.changes) == 1
    assert proposal.changes[0].id == "R0_CONTROL"
    assert proposal.changes[0].new_bound == 7.8
    assert proposal.changes[0].scope_text is None

def test_missing_code_path():
    data = {"changes": [{"id": "R1", "req_class": "RETAIN", "target_metric": "X", "new_bound": 1.0}]}
    with pytest.raises(MalformedMigrationError, match="Missing required field: 'code_path'"):
        validate_migration(data)

def test_empty_changes():
    data = {"code_path": "scheduler.py", "changes": []}
    with pytest.raises(MalformedMigrationError, match="changes must be a non-empty list"):
        validate_migration(data)

def test_invalid_bound_type():
    data = {
        "code_path": "scheduler.py",
        "changes": [
            {"id": "R1", "req_class": "RETAIN", "target_metric": "X", "new_bound": "not a number"}
        ]
    }
    with pytest.raises(MalformedMigrationError, match="Invalid field type"):
        validate_migration(data)
