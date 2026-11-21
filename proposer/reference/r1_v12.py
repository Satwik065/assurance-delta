"""R1 v1.2 Reference Upgrade: Work-conserving Oldest-First Strict Priority Scheduler.

At R1 (N=13, bulk_rate=0.0020, H=200,000, rho=0.754), the frozen baseline
StrictPriorityRoundRobinScheduler fails the 19/20 guard on CALIBRATION_SEEDS
(18/20 <= 8.77) because device-ID round-robin lets newly arrived CONTROL
packets jump ahead of CONTROL packets that waited during a 4-slot BULK slot.
Tracking earliest-seen slot + packet_id from QueueSnapshot eliminates tail
inversion with zero idle waste (20/20 pass, C_ub=6.20, B_ub=28.08).
"""
from __future__ import annotations
from typing import Optional
from sim.scheduler_base import QueueSnapshot


class OldestFirstStrictScheduler:
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
