import pytest
from gate.measure import check_undeclared_weakening, UndeclaredWeakeningError, MeasuredMetrics
from proposer.schema import MigrationProposal, RequirementChange

def test_retain_passes_when_under_bound():
    prop = MigrationProposal("code.py", [
        RequirementChange("R0_CONTROL", "RETAIN", "CONTROL_p99", 7.8, None)
    ])
    measured = MeasuredMetrics(control_p99=5.0, bulk_p99=500.0)
    bounds = {"CONTROL_p99": 7.8, "BULK_p99": 985.53}
    
    # Should not raise
    check_undeclared_weakening(prop, measured, bounds)

def test_retain_fails_when_over_bound():
    prop = MigrationProposal("code.py", [
        RequirementChange("R0_CONTROL", "RETAIN", "CONTROL_p99", 7.8, None)
    ])
    # Oracle measured 9.0, which is > 7.8
    measured = MeasuredMetrics(control_p99=9.0, bulk_p99=500.0)
    bounds = {"CONTROL_p99": 7.8, "BULK_p99": 985.53}
    
    with pytest.raises(UndeclaredWeakeningError, match="UNDECLARED_WEAKENING"):
        check_undeclared_weakening(prop, measured, bounds)

def test_waive_ignored_by_g4():
    # If it's a WAIVE, G4 doesn't check it (G5 handles scope/tokens)
    prop = MigrationProposal("code.py", [
        RequirementChange("R3_BULK", "WAIVE", "BULK_p99", 4927.65, "class == 'BULK'")
    ])
    # Oracle measured 4000, which is > 985.53 (original bound) but G4 should ignore it
    measured = MeasuredMetrics(control_p99=5.0, bulk_p99=4000.0)
    bounds = {"CONTROL_p99": 7.8, "BULK_p99": 985.53}
    
    # Should not raise
    check_undeclared_weakening(prop, measured, bounds)
