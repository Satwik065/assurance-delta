"""Audits a DepartureLog against the original arrivals to detect cheating.

Trust contract (Amendment D1): The sandboxed process only generates the
scheduler. The engine generates the log. Before we trust the log to calculate
latency and p99, we must audit it to ensure the log hasn't been fabricated
or tampered with.
"""
from __future__ import annotations
from constitution import constants as C
from sim.engine import DepartureLog
from sim.traffic import Packet

def audit_departure_log(arrivals: list[Packet], log: DepartureLog) -> list[str]:
    """Returns a list of violation codes. If the list is empty, the log is clean."""
    violations: list[str] = []
    
    arrival_map = {p.packet_id: p for p in arrivals}
    seen_departures: set[int] = set()
    occupied_slots: set[int] = set()

    for dep in log.departures:
        # 1. Duplicate packet ID in log
        if dep.packet_id in seen_departures:
            violations.append("DUPLICATE_PACKET_ID_IN_LOG")
        seen_departures.add(dep.packet_id)

        # 2. Departure without arrival (or unknown ID)
        if dep.packet_id not in arrival_map:
            violations.append("DEPARTURE_WITHOUT_ARRIVAL")
            continue # Can't check time-travel if we don't know when it arrived

        # 3. Multiple departures per slot (we only have 1 uplink)
        if dep.departure_slot in occupied_slots:
            violations.append("MULTIPLE_DEPARTURES_PER_SLOT")
        occupied_slots.add(dep.departure_slot)

        # 4. Time travel (departure must be strictly AFTER arrival)
        actual_arrival = arrival_map[dep.packet_id].arrival_slot
        if dep.departure_slot <= actual_arrival:
            violations.append("TIME_TRAVEL_DEPARTURE_BEFORE_ARRIVAL")

    # Return unique violations sorted for deterministic tests
    return sorted(list(set(violations)))
