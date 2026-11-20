import pytest
from constitution import constants as C
from sim.traffic import TrafficConfig, generate_arrivals

def _cfg(seed=0, n_devices=8, total_slots=2000, bulk_rate=0.05, burstiness=0.0):
    return TrafficConfig(n_devices, total_slots, bulk_rate, burstiness, seed)

def test_deterministic_for_same_seed():
    assert generate_arrivals(_cfg(seed=42)) == generate_arrivals(_cfg(seed=42))

def test_different_seeds_differ():
    assert generate_arrivals(_cfg(seed=1)) != generate_arrivals(_cfg(seed=2))

def test_all_packet_ids_unique():
    arrivals = generate_arrivals(_cfg(seed=7))
    ids = [p.packet_id for p in arrivals]
    assert len(ids) == len(set(ids))

def test_sorted_by_arrival_slot():
    arrivals = generate_arrivals(_cfg(seed=7))
    slots = [p.arrival_slot for p in arrivals]
    assert slots == sorted(slots)

def test_control_periodic_per_device():
    arrivals = generate_arrivals(_cfg(seed=7))
    by_device = {}
    for p in arrivals:
        if p.packet_class == "CONTROL":
            by_device.setdefault(p.device_id, []).append(p.arrival_slot)
    for slots in by_device.values():
        diffs = [b - a for a, b in zip(slots, slots[1:])]
        assert all(d == C.SIM_CONTROL_INTERARRIVAL_SLOTS for d in diffs)

def test_control_phase_offsets_randomized():
    arrivals = generate_arrivals(_cfg(seed=7))
    first_slot = {}
    for p in arrivals:
        if p.packet_class == "CONTROL":
            first_slot.setdefault(p.device_id, p.arrival_slot)
    assert len(set(first_slot.values())) > 1
    for phase in first_slot.values():
        assert 0 <= phase < C.SIM_CONTROL_INTERARRIVAL_SLOTS

def test_zero_bulk_rate_produces_no_bulk():
    arrivals = generate_arrivals(_cfg(seed=7, bulk_rate=0.0))
    assert all(p.packet_class == "CONTROL" for p in arrivals)

def test_negative_config_rejected():
    with pytest.raises(ValueError):
        generate_arrivals(_cfg(n_devices=-1))
