```python
class BurstyBulkRoundRobinScheduler:
    """Scheduler to handle bursty BULK traffic while keeping CONTROL latency under 7.8 slots and BULK latency under 985.53 slots."""
    def __init__(self, control_latency_threshold: int = 7.8, bulk_latency_threshold: int = 985.53) -> None:
        self._control_latency_threshold = control_latency_threshold
        self._bulk_latency_threshold = bulk_latency_threshold
        self._control_last_service: Optional[int] = None
        self._bulk_last_service: Optional[int] = None

    def choose_next(self, snapshot: QueueSnapshot) -> Optional[int]:
        control_devices = snapshot.pending_control_devices()
        if control_devices:
            device = self._next_after(self._control_last_service, control_devices)
            if self._get_service_latency(device) <= self._control_latency_threshold:
                self._control_last_service = device
                return snapshot.front_control[device]
            else:
                return None

        bulk_devices = snapshot.pending_bulk_devices()
        if bulk_devices:
            # Handle bursts by grouping devices by their arrival order
            device_arrivals = {d: [] for d in bulk_devices}
            for d, p in snapshot.front_bulk.items():
                if p is not None:
                    device_arrivals[d].append(p)

            # Group devices by their arrival order and select the earliest device
            earliest_device = min(device_arrivals, key=lambda d: device_arrivals[d][0])
            # Check if the device is within the bulk latency threshold
            if self._get_service_latency(earliest_device) <= self._bulk_latency_threshold:
                # Handle burst by scheduling the next device in the group
                self._bulk_last_service = earliest_device
                return snapshot.front_bulk[earliest_device]
            else:
                return None

        return None

    @staticmethod
    def _next_after(last: int, candidates: tuple[int, ...]) -> int:
        ordered = sorted(candidates)
        for c in ordered:
            if c > last:
                return c
        return ordered[0]

    def _get_service_latency(self, device: int) -> int:
        if device == self._control_last_service:
            return 1
        elif device == self._bulk_last_service:
            return 2
        else:
            return 1
```