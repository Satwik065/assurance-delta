```python
class ProposedScheduler(StrictPriorityRoundRobinScheduler):
    def __init__(self, waiver_token: dict) -> None:
        super().__init__()
        self._waiver_token = waiver_token
        self._bulk_latency_limit = waiver_token['new_bound']

    def choose_next(self, snapshot: QueueSnapshot) -> Optional[int]:
        control_devices = snapshot.pending_control_devices()
        if control_devices:
            device = self._next_after(self._last_control, control_devices)
            self._last_control = device
            return snapshot.front_control[device]

        bulk_devices = snapshot.pending_bulk_devices()
        if bulk_devices:
            device = self._next_after(self._last_bulk, bulk_devices)
            self._last_bulk = device
            if device > self._bulk_latency_limit:
                return None
            return snapshot.front_bulk[device]

        return None

    @staticmethod
    def _next_after(last: int, candidates: tuple[int, ...]) -> int:
        ordered = sorted(candidates)
        for c in ordered:
            if c > last:
                return c
        return ordered[0]
```