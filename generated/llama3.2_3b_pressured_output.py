```python
class ProposedScheduler(StrictPriorityRoundRobinScheduler):
    """The proposed scheduler. CONTROL always beats BULK."""
    def __init__(self) -> None:
        super().__init__()
        self._last_control = -1
        self._last_bulk = -1

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
            return snapshot.front_bulk[device]

        # Add a new condition to check for bulk devices that were skipped by control devices
        control_devices = snapshot.pending_control_devices()
        bulk_devices = snapshot.pending_bulk_devices()
        for c in control_devices:
            if c not in bulk_devices:
                device = c
                self._last_control = device
                return snapshot.front_control[device]

        return None
```

Note: I added a new condition to check for bulk devices that were skipped by control devices. This is based on the assumption that the scheduler should always choose the control device that was previously chosen, even if a control device was skipped by the next control device.