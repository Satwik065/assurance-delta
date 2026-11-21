class LoadAwareStrictPriorityScheduler:
    """Scheduler with load constraints for CONTROL and BULK queues."""
    def __init__(self, control_max_slots: float = 7.8, bulk_max_slots: float = 985.53):
        self._last_control: int = -1
        self._last_bulk: int = -1
        self._control_slots_used: float = 0.0
        self._bulk_slots_used: float = 0.0
        self.control_max_slots = control_max_slots
        self.bulk_max_slots = bulk_max_slots

    def choose_next(self, snapshot: QueueSnapshot) -> Optional[int]:
        control_devices = snapshot.pending_control_devices()
        if control_devices:
            if self._control_slots_used >= self.control_max_slots:
                return None

            device = self._next_after(self._last_control, control_devices)
            self._last_control = device
            self._control_slots_used += 1
            return snapshot.front_control[device]

        bulk_devices = snapshot.pending_bulk_devices()
        if bulk_devices:
            if self._bulk_slots_used >= self.bulk_max_slots:
                return None

            device = self._next_after(self._last_bulk, bulk_devices)
            self._last_bulk = device
            self._bulk_slots_used += 1
            return snapshot.front_bulk[device]

        return None

    @staticmethod
    def _next_after(last: int, candidates: tuple[int, ...]) -> int:
        ordered = sorted(candidates)
        for c in ordered:
            if c > last:
                return c
        return ordered[0]