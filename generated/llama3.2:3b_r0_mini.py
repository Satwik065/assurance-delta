class ProposedScheduler:
    """Proposed scheduler with control over bulk packet selection."""
    def __init__(self) -> None:
        pass

    def choose_next(self, snapshot: QueueSnapshot) -> Optional[int]:
        control_devices = snapshot.pending_control_devices()
        if control_devices:
            device = self._next_after(snapshot._last_control, control_devices)
            snapshot._last_control = device
            return snapshot.front_control[device]

        bulk_devices = snapshot.pending_bulk_devices()
        if bulk_devices:
            device = self._next_after(snapshot._last_bulk, bulk_devices)
            snapshot._last_bulk = device
            return snapshot.front_bulk[device]

        return None

    @staticmethod
    def _next_after(last: int, candidates: tuple[int, ...]) -> int:
        ordered = sorted(candidates)
        for c in ordered:
            if c > last:
                return c
        return ordered[0]