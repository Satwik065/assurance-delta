"""R3 v1.2 Reference Upgrade (ERRATA E8): Work-conserving Oldest-First Strict Priority.

Replaces the legacy baseline round-robin copy (proposer/reference/r3.py), which
failed the 19/20 guard on VERDICT_SEED_SET at v1.2 R3 load (N=8, rate=0.0155,
rho=0.896: 18/20 <= 8.77). Uses global earliest-seen FIFO within each class
under strict CONTROL > BULK priority (identical algorithm to R1 v1.2 reference).
"""
from __future__ import annotations
from typing import Optional
from sim.scheduler_base import QueueSnapshot


class R3ReferenceV12Scheduler:
    """Strict priority (CONTROL > BULK), global earliest-seen FIFO within each class."""

    def __init__(self) -> None:
        self._seen_c: dict[int, int] = {}
        self._seen_b: dict[int, int] = {}

    def choose_next(self, snapshot: QueueSnapshot) -> Optional[int]:
        cd = snapshot.pending_control_devices()
        for d in cd:
            pid = snapshot.front_control[d]
            if pid not in self._seen_c:
                self._seen_c[pid] = snapshot.slot
        bd = snapshot.pending_bulk_devices()
        for d in bd:
            pid = snapshot.front_bulk[d]
            if pid not in self._seen_b:
                self._seen_b[pid] = snapshot.slot

        if cd:
            d = min(cd, key=lambda x: (self._seen_c[snapshot.front_control[x]], snapshot.front_control[x]))
            pid = snapshot.front_control[d]
            self._seen_c.pop(pid, None)
            return pid

        if bd:
            d = min(bd, key=lambda x: (self._seen_b[snapshot.front_bulk[x]], snapshot.front_bulk[x]))
            pid = snapshot.front_bulk[d]
            self._seen_b.pop(pid, None)
            return pid

        return None
