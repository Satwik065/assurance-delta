from requirements_model.classes import RequirementClass
from requirements_model.obligations import get_r0_obligations, get_r3_obligations
from constitution import constants as C

def test_r0_obligations_loaded_from_constitution():
    rules = get_r0_obligations()
    bounds = C.load_calibrated()
    
    assert len(rules) == 2
    # Check that it pulled the exact frozen number (7.8) from constitution.json
    assert rules[0].bound == bounds["r0_control_p99_bound_slots"]
    assert rules[0].req_class == RequirementClass.RETAIN

def test_r3_obligations_have_waived_bulk():
    rules = get_r3_obligations()
    bounds = C.load_calibrated()
    
    assert len(rules) == 2
    control_rule = [r for r in rules if r.id == "R3_CONTROL_STRICT"][0]
    bulk_rule = [r for r in rules if r.id == "R3_BULK_WAIVED"][0]
    
    # CONTROL stays strict at 7.8
    assert control_rule.bound == bounds["r0_control_p99_bound_slots"]
    
    # BULK is waived at 5x (985.53 * 5 = 4927.65)
    expected_bulk_bound = bounds["r0_bulk_p99_bound_slots"] * C.R3_BULK_WAIVE_MULTIPLIER
    assert bulk_rule.bound == expected_bulk_bound
    assert bulk_rule.req_class == RequirementClass.WAIVE
    assert bulk_rule.scope_text == "class == 'BULK'"
