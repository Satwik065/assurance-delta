import pytest
from oracle.audit import audit_departure_log
from sim.engine import DepartureLog, Departure
from sim.traffic import Packet

def _arrival(pid, slot): return Packet(pid, 0, "CONTROL", slot)
def _dep(pid, arr_slot, dep_slot): return Departure(pid, 0, "CONTROL", arr_slot, dep_slot)

def test_clean_log_has_no_violations():
    arrivals = [_arrival(0, 0)]
    log = DepartureLog(departures=[_dep(0, 0, 1)], drops=[])
    assert audit_departure_log(arrivals, log) == []

def test_unknown_packet_id_caught():
    arrivals = [_arrival(0, 0)]
    # Cheater fabricated packet 99
    log = DepartureLog(departures=[_dep(99, 0, 1)], drops=[])
    assert "DEPARTURE_WITHOUT_ARRIVAL" in audit_departure_log(arrivals, log)

def test_multiple_departures_per_slot_caught():
    arrivals = [_arrival(0, 0), _arrival(1, 0)]
    # Cheater claimed both packets left at slot 1 (impossible, only 1 uplink)
    log = DepartureLog(departures=[_dep(0, 0, 1), _dep(1, 0, 1)], drops=[])
    assert "MULTIPLE_DEPARTURES_PER_SLOT" in audit_departure_log(arrivals, log)

def test_time_travel_caught():
    arrivals = [_arrival(0, 5)]
    # Cheater claimed packet departed at slot 4 (before it arrived!)
    log = DepartureLog(departures=[_dep(0, 5, 4)], drops=[])
    assert "TIME_TRAVEL_DEPARTURE_BEFORE_ARRIVAL" in audit_departure_log(arrivals, log)

def test_zero_latency_caught():
    arrivals = [_arrival(0, 5)]
    # Cheater claimed packet departed at the exact same slot it arrived
    log = DepartureLog(departures=[_dep(0, 5, 5)], drops=[])
    assert "TIME_TRAVEL_DEPARTURE_BEFORE_ARRIVAL" in audit_departure_log(arrivals, log)

def test_duplicate_departure_caught():
    arrivals = [_arrival(0, 0)]
    # Cheater logged the same packet departing twice
    log = DepartureLog(departures=[_dep(0, 0, 1), _dep(0, 0, 2)], drops=[])
    assert "DUPLICATE_PACKET_ID_IN_LOG" in audit_departure_log(arrivals, log)
