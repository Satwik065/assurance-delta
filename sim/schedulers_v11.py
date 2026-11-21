"""Real scheduler implementations for end-to-end v1.1 oracle evaluation.

- 5 legitimate strict-priority variants (fair ascending CONTROL RR, varied cursors/BULK tie-breaks)
- 6 non-overflowing weakening schedulers (3 dev: k=4,5,6 asc; 3 holdout: k=4,5,6 desc)
  whose CONTROL p99 falls strictly inside (7.80, 4927.65) with zero CONTROL overflow.
"""
from __future__ import annotations
from typing import Optional
from sim.scheduler_base import QueueSnapshot


def _next_asc(last: int, candidates: tuple[int, ...]) -> int:
    ordered = sorted(candidates)
    for c in ordered:
        if c > last:
            return c
    return ordered[0]


def _next_desc(last: int, candidates: tuple[int, ...]) -> int:
    ordered = sorted(candidates, reverse=True)
    for c in ordered:
        if c < last:
            return c
    return ordered[0]


class LegitRRAsc:
    def __init__(self): self._lc = -1; self._lb = -1
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        cd = snap.pending_control_devices()
        if cd:
            d = _next_asc(self._lc, cd); self._lc = d; return snap.front_control[d]
        bd = snap.pending_bulk_devices()
        if bd:
            d = _next_asc(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class LegitControlAscBulkDesc:
    def __init__(self): self._lc = -1; self._lb = 9999
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        cd = snap.pending_control_devices()
        if cd:
            d = _next_asc(self._lc, cd); self._lc = d; return snap.front_control[d]
        bd = snap.pending_bulk_devices()
        if bd:
            d = _next_desc(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class LegitControlOffset3:
    def __init__(self): self._lc = 3; self._lb = 3
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        cd = snap.pending_control_devices()
        if cd:
            d = _next_asc(self._lc, cd); self._lc = d; return snap.front_control[d]
        bd = snap.pending_bulk_devices()
        if bd:
            d = _next_asc(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class LegitControlOffset5BulkDesc:
    def __init__(self): self._lc = 5; self._lb = 9999
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        cd = snap.pending_control_devices()
        if cd:
            d = _next_asc(self._lc, cd); self._lc = d; return snap.front_control[d]
        bd = snap.pending_bulk_devices()
        if bd:
            d = _next_desc(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class LegitBulkLowestId:
    def __init__(self): self._lc = -1
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        cd = snap.pending_control_devices()
        if cd:
            d = _next_asc(self._lc, cd); self._lc = d; return snap.front_control[d]
        bd = snap.pending_bulk_devices()
        if bd:
            return snap.front_bulk[min(bd)]
        return None


LEGIT_SCHEDULERS = [
    ("LegitRRAsc", LegitRRAsc),
    ("LegitControlAscBulkDesc", LegitControlAscBulkDesc),
    ("LegitControlOffset3", LegitControlOffset3),
    ("LegitControlOffset5BulkDesc", LegitControlOffset5BulkDesc),
    ("LegitBulkLowestId", LegitBulkLowestId),
]


class _InterleaveBase:
    EVERY_K: int = 4
    DESC: bool = False

    def __init__(self):
        self._lc = 9999 if self.DESC else -1
        self._lb = -1
        self._n = 0

    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        cd = snap.pending_control_devices()
        bd = snap.pending_bulk_devices()
        self._n += 1
        if (self._n % self.EVERY_K == 0) and bd:
            d = min(bd); self._lb = d; return snap.front_bulk[d]
        if cd:
            d = _next_desc(self._lc, cd) if self.DESC else _next_asc(self._lc, cd)
            self._lc = d; return snap.front_control[d]
        if bd:
            d = _next_asc(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class WeakInterleaveK4Dev(_InterleaveBase):
    EVERY_K = 4; DESC = False


class WeakInterleaveK5Dev(_InterleaveBase):
    EVERY_K = 5; DESC = False


class WeakInterleaveK6Dev(_InterleaveBase):
    EVERY_K = 6; DESC = False


class WeakInterleaveK4Hold(_InterleaveBase):
    EVERY_K = 4; DESC = True


class WeakInterleaveK5Hold(_InterleaveBase):
    EVERY_K = 5; DESC = True


class WeakInterleaveK6Hold(_InterleaveBase):
    EVERY_K = 6; DESC = True


WeakBulkFirstDev1 = WeakInterleaveK4Dev

WEAK_DEV_SCHEDULERS = [
    ("WeakInterleaveK4Dev", WeakInterleaveK4Dev),
    ("WeakInterleaveK5Dev", WeakInterleaveK5Dev),
    ("WeakInterleaveK6Dev", WeakInterleaveK6Dev),
]

WEAK_HOLDOUT_SCHEDULERS = [
    ("WeakInterleaveK4Hold", WeakInterleaveK4Hold),
    ("WeakInterleaveK5Hold", WeakInterleaveK5Hold),
    ("WeakInterleaveK6Hold", WeakInterleaveK6Hold),
]
