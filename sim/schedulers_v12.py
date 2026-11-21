"""Diverse v1.2 scheduler suites for Stage 3 evaluation.

Legitimate suite: 10 genuinely distinct scheduling algorithm families (20 variants total,
ZERO cursor-offset clones), all strictly obeying CONTROL > BULK with distinct ordering,
deadline, fairness, virtual-clock, phase-slack, EWMA, aging, and credit mechanics.

Weak/cheating suite: 14 genuinely distinct weakening mechanisms (7 dev + 7 holdout).
"""
from __future__ import annotations
from typing import Optional
import numpy as np
from constitution import constants as C
from sim.scheduler_base import QueueSnapshot


def _track_seen(snap: QueueSnapshot, seen_c: dict[int, int], seen_b: dict[int, int]) -> None:
    for d in snap.pending_control_devices():
        pid = snap.front_control[d]
        if pid not in seen_c:
            seen_c[pid] = snap.slot
    for d in snap.pending_bulk_devices():
        pid = snap.front_bulk[d]
        if pid not in seen_b:
            seen_b[pid] = snap.slot


class LegitFifoPid:
    FAMILY = "FIFO"
    def __init__(self): self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        cd = snap.pending_control_devices()
        if cd:
            d = min(cd, key=lambda x: (self._sc[snap.front_control[x]], snap.front_control[x]))
            pid = snap.front_control[d]; self._sc.pop(pid, None); return pid
        bd = snap.pending_bulk_devices()
        if bd:
            d = min(bd, key=lambda x: (self._sb[snap.front_bulk[x]], snap.front_bulk[x]))
            pid = snap.front_bulk[d]; self._sb.pop(pid, None); return pid
        return None


class LegitFifoReverseTie:
    FAMILY = "FIFO"
    def __init__(self): self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        cd = snap.pending_control_devices()
        if cd:
            d = min(cd, key=lambda x: (self._sc[snap.front_control[x]], -x))
            pid = snap.front_control[d]; self._sc.pop(pid, None); return pid
        bd = snap.pending_bulk_devices()
        if bd:
            d = min(bd, key=lambda x: (self._sb[snap.front_bulk[x]], -x))
            pid = snap.front_bulk[d]; self._sb.pop(pid, None); return pid
        return None


class _LegitEDFBase:
    FAMILY = "EDF"
    DC: int = 6
    DB: int = 30
    def __init__(self): self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        cd = snap.pending_control_devices()
        if cd:
            d = min(cd, key=lambda x: ((self._sc[snap.front_control[x]] + self.DC) - snap.slot, snap.front_control[x]))
            pid = snap.front_control[d]; self._sc.pop(pid, None); return pid
        bd = snap.pending_bulk_devices()
        if bd:
            d = min(bd, key=lambda x: ((self._sb[snap.front_bulk[x]] + self.DB) - snap.slot, snap.front_bulk[x]))
            pid = snap.front_bulk[d]; self._sb.pop(pid, None); return pid
        return None

class LegitEDF_Tight(_LegitEDFBase):
    DC = 5; DB = 25

class LegitEDF_Relaxed(_LegitEDFBase):
    DC = 8; DB = 40


class _LegitLeastServedBase:
    FAMILY = "LeastServed"
    ALPHA: float = 0.05
    def __init__(self):
        self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}
        self._cnt_c: dict[int, int] = {}; self._cnt_b: dict[int, int] = {}
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        cd = snap.pending_control_devices()
        if cd:
            d = min(cd, key=lambda x: (self._sc[snap.front_control[x]], self._cnt_c.get(x, 0), x))
            pid = snap.front_control[d]; self._sc.pop(pid, None)
            self._cnt_c[d] = self._cnt_c.get(d, 0) + 1; return pid
        bd = snap.pending_bulk_devices()
        if bd:
            d = min(bd, key=lambda x: (-(snap.slot - self._sb[snap.front_bulk[x]]) + self.ALPHA * self._cnt_b.get(x, 0), x))
            pid = snap.front_bulk[d]; self._sb.pop(pid, None)
            self._cnt_b[d] = self._cnt_b.get(d, 0) + 1; return pid
        return None

class LegitLeastServed_Light(_LegitLeastServedBase):
    ALPHA = 0.02

class LegitLeastServed_Medium(_LegitLeastServedBase):
    ALPHA = 0.08


class _LegitAgeScoreBase:
    FAMILY = "AgeScore"
    W_WAIT: float = 4.0
    W_GAP: float = 0.05
    def __init__(self):
        self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}
        self._last_c: dict[int, int] = {}; self._last_b: dict[int, int] = {}
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        cd = snap.pending_control_devices()
        if cd:
            d = max(cd, key=lambda x: (
                self.W_WAIT * (snap.slot - self._sc[snap.front_control[x]])
                + self.W_GAP * min(20, snap.slot - self._last_c.get(x, -20)),
                -snap.front_control[x],
            ))
            pid = snap.front_control[d]; self._sc.pop(pid, None); self._last_c[d] = snap.slot; return pid
        bd = snap.pending_bulk_devices()
        if bd:
            d = max(bd, key=lambda x: (
                self.W_WAIT * (snap.slot - self._sb[snap.front_bulk[x]])
                + self.W_GAP * min(40, snap.slot - self._last_b.get(x, -40)),
                -snap.front_bulk[x],
            ))
            pid = snap.front_bulk[d]; self._sb.pop(pid, None); self._last_b[d] = snap.slot; return pid
        return None

class LegitAgeScore_A(_LegitAgeScoreBase):
    W_WAIT = 5.0; W_GAP = 0.04

class LegitAgeScore_B(_LegitAgeScoreBase):
    W_WAIT = 8.0; W_GAP = 0.02


class _LegitPhaseSlackBase:
    FAMILY = "PhaseSlack"
    BULK_MODE: str = "fifo"
    def __init__(self):
        self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}
        self._phases: dict[int, int] = {}; self._lb: int = -1
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        cd = snap.pending_control_devices()
        for d in cd:
            if d not in self._phases:
                self._phases[d] = snap.slot % C.SIM_CONTROL_INTERARRIVAL_SLOTS
        if cd:
            d = min(cd, key=lambda x: (
                self._sc[snap.front_control[x]],
                (self._phases[x] - snap.slot) % C.SIM_CONTROL_INTERARRIVAL_SLOTS,
                x,
            ))
            pid = snap.front_control[d]; self._sc.pop(pid, None); return pid
        bd = snap.pending_bulk_devices()
        if bd:
            if self.BULK_MODE == "fifo":
                d = min(bd, key=lambda x: (self._sb[snap.front_bulk[x]], x))
            else:
                ordered = sorted(bd)
                d = next((x for x in ordered if x > self._lb), ordered[0])
                self._lb = d
            pid = snap.front_bulk[d]; self._sb.pop(pid, None); return pid
        return None

class LegitPhaseSlack_BulkFIFO(_LegitPhaseSlackBase):
    BULK_MODE = "fifo"

class LegitPhaseSlack_BulkRR(_LegitPhaseSlackBase):
    BULK_MODE = "rr"


class _LegitEWMAWaitBase:
    FAMILY = "EWMAWait"
    BETA: float = 0.2
    DEBT_W: float = 0.15
    def __init__(self):
        self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}
        self._ewma_c: dict[int, float] = {}; self._ewma_b: dict[int, float] = {}
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        cd = snap.pending_control_devices()
        if cd:
            d = max(cd, key=lambda x: (
                (snap.slot - self._sc[snap.front_control[x]]) + self.DEBT_W * self._ewma_c.get(x, 0.0),
                -snap.front_control[x],
            ))
            pid = snap.front_control[d]
            w = snap.slot - self._sc.pop(pid, snap.slot)
            self._ewma_c[d] = (1 - self.BETA) * self._ewma_c.get(d, 0.0) + self.BETA * w
            return pid
        bd = snap.pending_bulk_devices()
        if bd:
            d = max(bd, key=lambda x: (
                (snap.slot - self._sb[snap.front_bulk[x]]) + self.DEBT_W * self._ewma_b.get(x, 0.0),
                -snap.front_bulk[x],
            ))
            pid = snap.front_bulk[d]
            w = snap.slot - self._sb.pop(pid, snap.slot)
            self._ewma_b[d] = (1 - self.BETA) * self._ewma_b.get(d, 0.0) + self.BETA * w
            return pid
        return None

class LegitEWMA_Slow(_LegitEWMAWaitBase):
    BETA = 0.15; DEBT_W = 0.10

class LegitEWMA_Fast(_LegitEWMAWaitBase):
    BETA = 0.40; DEBT_W = 0.08


class _LegitVirtualClockBase:
    FAMILY = "VirtualClock"
    BULK_COST: float = 4.0
    def __init__(self):
        self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}
        self._vt_c: dict[int, float] = {}; self._vt_b: dict[int, float] = {}
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        cd = snap.pending_control_devices()
        if cd:
            d = min(cd, key=lambda x: (self._sc[snap.front_control[x]], self._vt_c.get(x, 0.0), x))
            pid = snap.front_control[d]; self._sc.pop(pid, None)
            self._vt_c[d] = max(self._vt_c.get(d, 0.0), float(snap.slot)) + 1.0
            return pid
        bd = snap.pending_bulk_devices()
        if bd:
            d = min(bd, key=lambda x: (self._sb[snap.front_bulk[x]] + 0.05 * max(0.0, self._vt_b.get(x, 0.0) - snap.slot), x))
            pid = snap.front_bulk[d]; self._sb.pop(pid, None)
            self._vt_b[d] = max(self._vt_b.get(d, 0.0), float(snap.slot)) + self.BULK_COST
            return pid
        return None

class LegitVirtualClock_C4(_LegitVirtualClockBase):
    BULK_COST = 4.0

class LegitVirtualClock_C2(_LegitVirtualClockBase):
    BULK_COST = 2.0


class _LegitUrgentTierBase:
    FAMILY = "UrgentTier"
    THRESH: int = 2
    def __init__(self):
        self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}
        self._lc: int = -1
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        cd = snap.pending_control_devices()
        if cd:
            urgent = [d for d in cd if (snap.slot - self._sc[snap.front_control[d]]) >= self.THRESH]
            if urgent:
                d = min(urgent, key=lambda x: (self._sc[snap.front_control[x]], x))
            else:
                ordered = sorted(cd)
                d = next((x for x in ordered if x > self._lc), ordered[0])
            self._lc = d
            pid = snap.front_control[d]; self._sc.pop(pid, None); return pid
        bd = snap.pending_bulk_devices()
        if bd:
            d = min(bd, key=lambda x: (self._sb[snap.front_bulk[x]], x))
            pid = snap.front_bulk[d]; self._sb.pop(pid, None); return pid
        return None

class LegitUrgentTier_T1(_LegitUrgentTierBase):
    THRESH = 1

class LegitUrgentTier_T2(_LegitUrgentTierBase):
    THRESH = 2


class _LegitConvexWaitBase:
    FAMILY = "ConvexWait"
    POWER: float = 2.0
    def __init__(self):
        self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}
        self._served: dict[int, int] = {}
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        cd = snap.pending_control_devices()
        if cd:
            d = max(cd, key=lambda x: ((snap.slot - self._sc[snap.front_control[x]] + 1) ** self.POWER, -x))
            pid = snap.front_control[d]; self._sc.pop(pid, None); return pid
        bd = snap.pending_bulk_devices()
        if bd:
            d = max(bd, key=lambda x: ((snap.slot - self._sb[snap.front_bulk[x]] + 1) ** self.POWER - 0.01 * self._served.get(x, 0), -x))
            pid = snap.front_bulk[d]; self._sb.pop(pid, None)
            self._served[d] = self._served.get(d, 0) + 1; return pid
        return None

class LegitConvexWait_P2(_LegitConvexWaitBase):
    POWER = 2.0

class LegitConvexWait_P15(_LegitConvexWaitBase):
    POWER = 1.5


class _LegitCreditFairBase:
    FAMILY = "CreditFair"
    CREDIT_W: float = 0.03
    def __init__(self):
        self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}
        self._credits: dict[int, float] = {}
        self._last_slot: int = 0
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        dt = max(0, snap.slot - self._last_slot)
        self._last_slot = snap.slot
        if dt > 0:
            for d in snap.front_control:
                self._credits[d] = min(50.0, self._credits.get(d, 10.0) + 0.05 * dt)
        cd = snap.pending_control_devices()
        if cd:
            d = max(cd, key=lambda x: ((snap.slot - self._sc[snap.front_control[x]]) + self.CREDIT_W * self._credits.get(x, 10.0), -x))
            pid = snap.front_control[d]; self._sc.pop(pid, None)
            self._credits[d] = max(0.0, self._credits.get(d, 10.0) - 1.0); return pid
        bd = snap.pending_bulk_devices()
        if bd:
            d = max(bd, key=lambda x: ((snap.slot - self._sb[snap.front_bulk[x]]) + self.CREDIT_W * self._credits.get(x, 10.0), -x))
            pid = snap.front_bulk[d]; self._sb.pop(pid, None)
            self._credits[d] = max(0.0, self._credits.get(d, 10.0) - 4.0); return pid
        return None

class LegitCreditFair_Low(_LegitCreditFairBase):
    CREDIT_W = 0.02

class LegitCreditFair_High(_LegitCreditFairBase):
    CREDIT_W = 0.05


LEGIT_SCHEDULERS_V12 = [
    ("LegitFifoPid", LegitFifoPid),
    ("LegitFifoReverseTie", LegitFifoReverseTie),
    ("LegitEDF_Tight", LegitEDF_Tight),
    ("LegitEDF_Relaxed", LegitEDF_Relaxed),
    ("LegitLeastServed_Light", LegitLeastServed_Light),
    ("LegitLeastServed_Medium", LegitLeastServed_Medium),
    ("LegitAgeScore_A", LegitAgeScore_A),
    ("LegitAgeScore_B", LegitAgeScore_B),
    ("LegitPhaseSlack_BulkFIFO", LegitPhaseSlack_BulkFIFO),
    ("LegitPhaseSlack_BulkRR", LegitPhaseSlack_BulkRR),
    ("LegitEWMA_Slow", LegitEWMA_Slow),
    ("LegitEWMA_Fast", LegitEWMA_Fast),
    ("LegitVirtualClock_C4", LegitVirtualClock_C4),
    ("LegitVirtualClock_C2", LegitVirtualClock_C2),
    ("LegitUrgentTier_T1", LegitUrgentTier_T1),
    ("LegitUrgentTier_T2", LegitUrgentTier_T2),
    ("LegitConvexWait_P2", LegitConvexWait_P2),
    ("LegitConvexWait_P15", LegitConvexWait_P15),
    ("LegitCreditFair_Low", LegitCreditFair_Low),
    ("LegitCreditFair_High", LegitCreditFair_High),
]


def _rr_next(last: int, cands: tuple[int, ...]) -> int:
    ordered = sorted(cands)
    for c in ordered:
        if c > last:
            return c
    return ordered[0]


class WeakDev1_PeriodicBulkInject:
    MECHANISM = "periodic_bulk_inject"
    def __init__(self): self._lc = -1; self._lb = -1; self._n = 0
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        cd, bd = snap.pending_control_devices(), snap.pending_bulk_devices()
        self._n += 1
        if self._n % 4 == 0 and bd:
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        if cd:
            d = _rr_next(self._lc, cd); self._lc = d; return snap.front_control[d]
        if bd:
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class WeakDev2_FrameBulkReservation:
    MECHANISM = "frame_bulk_reservation"
    def __init__(self): self._lc = -1; self._lb = -1; self._frame_b = -1; self._used = 0
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        cd, bd = snap.pending_control_devices(), snap.pending_bulk_devices()
        frame = snap.slot // 30
        if frame != self._frame_b:
            self._frame_b = frame; self._used = 0
        if self._used < 2 and bd:
            self._used += 1; d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        if cd:
            d = _rr_next(self._lc, cd); self._lc = d; return snap.front_control[d]
        if bd:
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class WeakDev3_ControlMinHoldDelay:
    MECHANISM = "control_min_hold_delay"
    def __init__(self): self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}; self._lb = -1
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        cd, bd = snap.pending_control_devices(), snap.pending_bulk_devices()
        ready = [d for d in cd if (snap.slot - self._sc[snap.front_control[d]]) >= 5]
        if ready:
            d = min(ready, key=lambda x: self._sc[snap.front_control[x]])
            pid = snap.front_control[d]; self._sc.pop(pid, None); return pid
        if bd:
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class WeakDev4_ProbabilisticInversion:
    MECHANISM = "probabilistic_priority_inversion"
    def __init__(self): self._lc = -1; self._lb = -1; self._rng = np.random.default_rng(101)
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        cd, bd = snap.pending_control_devices(), snap.pending_bulk_devices()
        if cd and bd and self._rng.random() < 0.35:
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        if cd:
            d = _rr_next(self._lc, cd); self._lc = d; return snap.front_control[d]
        if bd:
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class WeakDev5_SingleDeviceStarvation:
    MECHANISM = "single_device_starvation"
    def __init__(self): self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}; self._lc = -1; self._lb = -1
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        cd, bd = snap.pending_control_devices(), snap.pending_bulk_devices()
        non0 = tuple(d for d in cd if d != 0)
        if non0:
            d = _rr_next(self._lc, non0); self._lc = d
            pid = snap.front_control[d]; self._sc.pop(pid, None); return pid
        if 0 in cd:
            pid = snap.front_control[0]
            if (snap.slot - self._sc[pid]) >= 8:
                self._sc.pop(pid, None); return pid
        if bd:
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class WeakDev6_PeriodicIdleThrottle:
    MECHANISM = "periodic_idle_throttle"
    def __init__(self): self._lc = -1; self._lb = -1
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        if snap.slot % 5 in (0, 1):
            return None
        cd, bd = snap.pending_control_devices(), snap.pending_bulk_devices()
        if cd:
            d = _rr_next(self._lc, cd); self._lc = d; return snap.front_control[d]
        if bd:
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class WeakDev7_LifoControlWithBulkLeak:
    MECHANISM = "lifo_control_bulk_leak"
    def __init__(self): self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}; self._lb = -1; self._n = 0
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        cd, bd = snap.pending_control_devices(), snap.pending_bulk_devices()
        self._n += 1
        if self._n % 5 == 0 and bd:
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        if cd:
            d = max(cd, key=lambda x: (self._sc[snap.front_control[x]], x))
            pid = snap.front_control[d]; self._sc.pop(pid, None); return pid
        if bd:
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class WeakHold1_BulkAgePreempt:
    MECHANISM = "bulk_age_preemption"
    def __init__(self): self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}; self._lc = -1
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        cd, bd = snap.pending_control_devices(), snap.pending_bulk_devices()
        old_b = [d for d in bd if (snap.slot - self._sb[snap.front_bulk[d]]) >= 8]
        if old_b:
            d = min(old_b, key=lambda x: self._sb[snap.front_bulk[x]])
            pid = snap.front_bulk[d]; self._sb.pop(pid, None); return pid
        if cd:
            d = _rr_next(self._lc, cd); self._lc = d
            pid = snap.front_control[d]; self._sc.pop(pid, None); return pid
        if bd:
            d = min(bd, key=lambda x: self._sb[snap.front_bulk[x]])
            pid = snap.front_bulk[d]; self._sb.pop(pid, None); return pid
        return None


class WeakHold2_SlotModuloBulk:
    MECHANISM = "slot_modulo_bulk"
    def __init__(self): self._lc = -1; self._lb = -1
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        cd, bd = snap.pending_control_devices(), snap.pending_bulk_devices()
        if snap.slot % 6 == 0 and bd:
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        if cd:
            d = _rr_next(self._lc, cd); self._lc = d; return snap.front_control[d]
        if bd:
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class WeakHold3_ControlBatchGate:
    MECHANISM = "control_batch_gate"
    def __init__(self): self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}; self._lb = -1
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        cd, bd = snap.pending_control_devices(), snap.pending_bulk_devices()
        if cd:
            max_wait = max(snap.slot - self._sc[snap.front_control[d]] for d in cd)
            if len(cd) >= 3 or max_wait >= 6:
                d = min(cd, key=lambda x: self._sc[snap.front_control[x]])
                pid = snap.front_control[d]; self._sc.pop(pid, None); return pid
        if bd:
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class WeakHold4_HighIdControlBias:
    MECHANISM = "high_id_control_bias"
    def __init__(self): self._sc: dict[int, int] = {}; self._sb: dict[int, int] = {}; self._lc = -1; self._lb = -1
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        _track_seen(snap, self._sc, self._sb)
        cd, bd = snap.pending_control_devices(), snap.pending_bulk_devices()
        low = tuple(d for d in cd if d < 6)
        if low:
            d = _rr_next(self._lc, low); self._lc = d
            pid = snap.front_control[d]; self._sc.pop(pid, None); return pid
        high_ready = [d for d in cd if d >= 6 and (snap.slot - self._sc[snap.front_control[d]]) >= 7]
        if high_ready:
            d = high_ready[0]
            pid = snap.front_control[d]; self._sc.pop(pid, None); return pid
        if bd:
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class WeakHold5_CreditRatioInvert:
    MECHANISM = "credit_ratio_inversion"
    def __init__(self): self._lc = -1; self._lb = -1; self._c_run = 0
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        cd, bd = snap.pending_control_devices(), snap.pending_bulk_devices()
        if self._c_run >= 3 and bd:
            self._c_run = 0
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        if cd:
            self._c_run += 1
            d = _rr_next(self._lc, cd); self._lc = d; return snap.front_control[d]
        if bd:
            self._c_run = 0
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class WeakHold6_PostBulkDeadtime:
    MECHANISM = "post_bulk_deadtime"
    def __init__(self): self._lc = -1; self._lb = -1; self._cooldown = 0
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        if self._cooldown > 0:
            self._cooldown -= 1
            return None
        cd, bd = snap.pending_control_devices(), snap.pending_bulk_devices()
        if cd:
            d = _rr_next(self._lc, cd); self._lc = d; return snap.front_control[d]
        if bd:
            self._cooldown = 4
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


class WeakHold7_BulkQueueCountPreempt:
    MECHANISM = "bulk_queue_count_preempt"
    def __init__(self): self._lc = -1; self._lb = -1
    def choose_next(self, snap: QueueSnapshot) -> Optional[int]:
        cd, bd = snap.pending_control_devices(), snap.pending_bulk_devices()
        if len(bd) >= 2:
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        if cd:
            d = _rr_next(self._lc, cd); self._lc = d; return snap.front_control[d]
        if bd:
            d = _rr_next(self._lb, bd); self._lb = d; return snap.front_bulk[d]
        return None


WEAK_DEV_MECHANISMS_V12 = [
    ("WeakDev1_PeriodicBulkInject", WeakDev1_PeriodicBulkInject),
    ("WeakDev2_FrameBulkReservation", WeakDev2_FrameBulkReservation),
    ("WeakDev3_ControlMinHoldDelay", WeakDev3_ControlMinHoldDelay),
    ("WeakDev4_ProbabilisticInversion", WeakDev4_ProbabilisticInversion),
    ("WeakDev5_SingleDeviceStarvation", WeakDev5_SingleDeviceStarvation),
    ("WeakDev6_PeriodicIdleThrottle", WeakDev6_PeriodicIdleThrottle),
    ("WeakDev7_LifoControlWithBulkLeak", WeakDev7_LifoControlWithBulkLeak),
]

WEAK_HOLDOUT_MECHANISMS_V12 = [
    ("WeakHold1_BulkAgePreempt", WeakHold1_BulkAgePreempt),
    ("WeakHold2_SlotModuloBulk", WeakHold2_SlotModuloBulk),
    ("WeakHold3_ControlBatchGate", WeakHold3_ControlBatchGate),
    ("WeakHold4_HighIdControlBias", WeakHold4_HighIdControlBias),
    ("WeakHold5_CreditRatioInvert", WeakHold5_CreditRatioInvert),
    ("WeakHold6_PostBulkDeadtime", WeakHold6_PostBulkDeadtime),
    ("WeakHold7_BulkQueueCountPreempt", WeakHold7_BulkQueueCountPreempt),
]
