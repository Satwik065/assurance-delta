"""Slot-based channel model for the pilot."""
from __future__ import annotations
from constitution import constants as C

def service_time_slots(packet_class: str) -> int:
    """Return the number of slots a packet of the given class occupies."""
    if packet_class == "CONTROL":
        return C.SIM_CONTROL_PACKET_SLOTS
    if packet_class == "BULK":
        return C.SIM_BULK_PACKET_SLOTS
    raise ValueError(f"Unknown packet class: {packet_class!r}")
