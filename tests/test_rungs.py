from requirements_model.rungs import get_r1_obligations, get_r4_obligations
from requirements_model.classes import RequirementClass

def test_r1_has_same_bounds_as_r0():
    rules = get_r1_obligations()
    assert len(rules) == 2
    assert rules[0].req_class == RequirementClass.RETAIN
    assert rules[1].req_class == RequirementClass.RETAIN

def test_r4_is_conflict():
    rules = get_r4_obligations()
    assert len(rules) == 1
    assert rules[0].req_class == RequirementClass.CONFLICT
