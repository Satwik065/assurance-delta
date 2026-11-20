import pytest
from requirements_model.scope import ScopePredicate

def test_simple_equality():
    scope = ScopePredicate("class == 'BULK'")
    assert scope.evaluate({"class": "BULK"}) is True
    assert scope.evaluate({"class": "CONTROL"}) is False

def test_numeric_comparison():
    scope = ScopePredicate("load <= 2.5")
    assert scope.evaluate({"load": 1.0}) is True
    assert scope.evaluate({"load": 2.5}) is True
    assert scope.evaluate({"load": 2.6}) is False

def test_compound_and():
    scope = ScopePredicate("class == 'BULK' and load <= 2.0")
    assert scope.evaluate({"class": "BULK", "load": 1.0}) is True
    assert scope.evaluate({"class": "BULK", "load": 3.0}) is False
    assert scope.evaluate({"class": "CONTROL", "load": 1.0}) is False

def test_missing_variable_fails_safe():
    scope = ScopePredicate("class == 'BULK'")
    assert scope.evaluate({}) is False

def test_invalid_syntax_raises():
    with pytest.raises(ValueError, match="Invalid scope syntax"):
        ScopePredicate("class is BULK")
