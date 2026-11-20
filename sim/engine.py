"""SimPy harness. Given a list of arrivals and a scheduler, produce a
departure log and a drop log.

Trust contract (amendment D1):
- The engine is TRUSTED code. It enforces buffer limits, service times, and the
  one-uplink-at-a-time rule.
- The scheduler is the ONLY untrusted component. It sees a QueueSnapshot
  and returns a packet_id (or None).
- The engine emits RAW departure + drop records. It does NOT compute
  latency, p99, loss, or any verdict. The parent oracle does that in a
  later stage.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from typing import Optional
import simpy
from constitution import constants as C
from sim.channel import service_time_slots
from sim.scheduler_base import QueueSnapshot
from sim.traffic import Packet

@dataclass(frozen=True)
class Departure:
    packet_id: int
    device_id: int
    packet_class: str
    arrival_slot: int
    departure_slot: int

@dataclass(frozen=True)
class Drop:
    packet_id: int
    device_id: int
    packet_class: str
    arrival_slot: int
    reason: str  # "BUFFER_OVERFLOW" or "HORIZON"

@dataclass
class DepartureLog:
    departures: list[Departure]
    drops: list[Drop]

def run(arrivals: list[Packet], scheduler, n_devices: int, max_slot: int) -> DepartureLog:
    if n_devices < 0 or max_slot < 0:
        raise ValueError("n_devices and max_slot must be >= 0")

    ids = [p.packet_id for p in arrivals]
    if len(ids) != len(set(ids)):
        raise ValueError("Arrivals contain duplicate packet_id")

    env = simpy.Environment()
    queues: dict[int, dict[str, list[Packet]]] = {d: {"CONTROL": [], "BULK": []} for d in range(n_devices)}
    pending: deque[Packet] = deque(sorted(arrivals, key=lambda p: (p.arrival_slot, p.packet_id)))
    departures: list[Departure] = []
    drops: list[Drop] = []

    def uplink_process():
        while env.now < max_slot:
            # Drain arrivals that have arrived by env.now.
            while pending and pending[0].arrival_slot <= env.now:
                packet = pending.popleft()
                q = queues[packet.device_id][packet.packet_class]
                if len(q) >= C.SIM_BUFFER_PACKETS_PER_QUEUE:
                    drops.append(Drop(packet.packet_id, packet.device_id, packet.packet_class, packet.arrival_slot, "BUFFER_OVERFLOW"))
                else:
                    q.append(packet)

            snapshot = _build_snapshot(env.now, queues)
            chosen_id = scheduler.choose_next(snapshot)

            if chosen_id is None:
                yield env.timeout(1)
                continue

            packet = _pop_packet(queues, chosen_id)
            if packet is None:
                raise RuntimeError(f"Scheduler returned packet_id {chosen_id} which is not in any queue at slot {env.now}")

            service = service_time_slots(packet.packet_class)
            yield env.timeout(service)

            departures.append(Departure(packet.packet_id, packet.device_id, packet.packet_class, packet.arrival_slot, env.now))

    env.process(uplink_process())
    env.run(until=max_slot)

    # Anything not served by the horizon is a drop.
    while pending:
        packet = pending.popleft()
        drops.append(Drop(packet.packet_id, packet.device_id, packet.packet_class, packet.arrival_slot, "HORIZON"))
    for qs in queues.values():
        for cls in ("CONTROL", "BULK"):
            for packet in qs[cls]:
                drops.append(Drop(packet.packet_id, packet.device_id, packet.packet_class, packet.arrival_slot, "HORIZON"))

    return DepartureLog(departures=departures, drops=drops)

def _build_snapshot(slot: int, queues: dict[int, dict[str, list[Packet]]]) -> QueueSnapshot:
    front_control = {d: (q["CONTROL"][0].packet_id if q["CONTROL"] else None) for d, q in queues.items()}
    front_bulk = {d: (q["BULK"][0].packet_id if q["BULK"] else None) for d, q in queues.items()}
    return QueueSnapshot(slot=slot, front_control=front_control, front_bulk=front_bulk)

def _pop_packet(queues: dict[int, dict[str, list[Packet]]], packet_id: int) -> Optional[Packet]:
    for q in queues.values():
        for cls in ("CONTROL", "BULK"):
            for i, p in enumerate(q[cls]):
                if p.packet_id == packet_id:
                    return q[cls].pop(i)
    return None
