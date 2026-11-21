```python
class ProposedScheduler:
    """Scheduler that prioritizes CONTROL packets and allows BULK to increase up to the waivered limit."""
    def __init__(self):
        self._last_control: int = -1
        self._last_bulk: int = -1
        self._bulk_limit = 4927.65

    def choose_next(self, snapshot: QueueSnapshot) -> Optional[int]:
        control_devices = snapshot.pending_control_devices()
        if control_devices:
            device = self._next_after(self._last_control, control_devices)
            self._last_control = device
            return snapshot.front_control[device]

        bulk_devices = snapshot.pending_bulk_devices()
        if bulk_devices:
            # Check if the next bulk device respects the BULK speed limit
            if self._last_bulk is not None and self._last_bulk in bulk_devices:
                # If the last bulk device is still pending, skip to the next one
                bulk_devices = tuple(d for d in bulk_devices if d != self._last_bulk)

            if bulk_devices:
                device = self._next_after(self._last_bulk, bulk_devices)
                self._last_bulk = device
                if snapshot.front_bulk[device] > self._bulk_limit:
                    # Skip devices that would exceed the BULK limit
                    bulk_devices = tuple(d for d in bulk_devices if snapshot.front_bulk[d] <= self._bulk_limit)
                if bulk_devices:
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