"""Deterministic arrival-trace generation for the wireless slot scheduler."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
import numpy as np
from constitution import constants as C

PacketClass = Literal["CONTROL", "BULK"]

@dataclass(frozen=True)
class Packet:
    packet_id: int
    device_id: int
    packet_class: PacketClass
    arrival_slot: int

@dataclass(frozen=True)
class TrafficConfig:
    n_devices: int
    total_slots: int
    bulk_rate_per_device_per_slot: float
    bulk_burstiness: float
    seed: int

def generate_arrivals(config: TrafficConfig) -> list[Packet]:
    if config.n_devices < 0 or config.total_slots < 0 or config.bulk_rate_per_device_per_slot < 0 or config.bulk_burstiness < 0:
        raise ValueError("Config values must be >= 0")

    rng = np.random.default_rng(config.seed)
    arrivals: list[Packet] = []
    next_id = 0

    # CONTROL: periodic with randomized phase per device
    for device_id in range(config.n_devices):
        phase = int(rng.integers(0, C.SIM_CONTROL_INTERARRIVAL_SLOTS))
        slot = phase
        while slot < config.total_slots:
            arrivals.append(Packet(next_id, device_id, "CONTROL", slot))
            next_id += 1
            slot += C.SIM_CONTROL_INTERARRIVAL_SLOTS

    # BULK: per-device Poisson, optional on/off burstiness
    for device_id in range(config.n_devices):
        if config.bulk_burstiness <= 0.0:
            next_id = _bulk_poisson(arrivals, next_id, device_id, config, rng)
        else:
            next_id = _bulk_onoff(arrivals, next_id, device_id, config, rng)

    arrivals.sort(key=lambda p: (p.arrival_slot, p.device_id, p.packet_class, p.packet_id))
    return arrivals

def _bulk_poisson(arrivals, current_id, device_id, config, rng) -> int:
    rate = config.bulk_rate_per_device_per_slot
    for slot in range(config.total_slots):
        n = int(rng.poisson(rate))
        for _ in range(n):
            arrivals.append(Packet(current_id, device_id, "BULK", slot))
            current_id += 1
    return current_id

def _bulk_onoff(arrivals, current_id, device_id, config, rng) -> int:
    state_on = True
    rate_on = config.bulk_rate_per_device_per_slot * 2.0
    for slot in range(config.total_slots):
        if rng.random() < config.bulk_burstiness:
            state_on = not state_on
        if state_on:
            n = int(rng.poisson(rate_on))
            for _ in range(n):
                arrivals.append(Packet(current_id, device_id, "BULK", slot))
                current_id += 1
    return current_id
