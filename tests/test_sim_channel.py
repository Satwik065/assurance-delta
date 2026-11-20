import pytest
from constitution import constants as C
from sim.channel import service_time_slots

def test_control_service_time():
    assert service_time_slots("CONTROL") == 1

def test_bulk_service_time():
    assert service_time_slots("BULK") == 4

def test_unknown_class_raises():
    with pytest.raises(ValueError, match="Unknown packet class"):
        service_time_slots("VIDEO")
