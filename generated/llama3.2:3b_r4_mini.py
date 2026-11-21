```python
class ExtendedStrictPriorityRoundRobinScheduler:
    def __init__(self) -> None:
        self._last_control: int = -1
        self._last_bulk: int = -1
        self._min_control_slots: int = 7
        self._max_bulk_slots: int = 985

    def choose_next(self, snapshot: QueueSnapshot) -> Optional[int]:
        control_devices = snapshot.pending_control_devices()
        if control_devices:
            devices = control_devices.copy()
            while len(devices) > self._min_control_slots:
                device = self._next_after(self._last_control, devices)
                self._last_control = device
                devices.remove(device)
                if devices:
                    next_device = self._next_after(self._last_control, devices)
                    devices.remove(next_device)
                    self._last_control = next_device

            if devices:
                device = devices[0]
                self._last_control = device
                return snapshot.front_control[device]

        bulk_devices = snapshot.pending_bulk_devices()
        if bulk_devices:
            devices = bulk_devices.copy()
            while len(devices) > self._max_bulk_slots:
                device = self._next_after(self._last_bulk, devices)
                self._last_bulk = device
                devices.remove(device)
                if devices:
                    next_device = self._next_after(self._last_bulk, devices)
                    devices.remove(next_device)
                    self._last_bulk = next_device

            if devices:
                device = devices[0]
                self._last_bulk = device
                return snapshot.front_bulk[device]

        return None

    @staticmethod
    def _next_after(last: int, candidates: tuple[int, ...]) -> int:
        ordered = sorted(candidates)
        for c in ordered:
            if c > last:
                return c
        return ordered[0]


# Example usage:
scheduler = ExtendedStrictPriorityRoundRobinScheduler()
snapshot = QueueSnapshot(0, {}, {})
device1 = 1
device2 = 2
device3 = 3
control_devices = {device1, device2, device3}
bulk_devices = {device1, device2, device3, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000}

snapshot.front_control[device1] = 1
snapshot.front_control[device2] = 2
snapshot.front_control[device3] = 3
snapshot.front_bulk[device1] = 1
snapshot.front_bulk[device2] = 2
snapshot.front_bulk[device3] = 3
snapshot.front_bulk[100] = 1
snapshot.front_bulk[200] = 2
snapshot.front_bulk[300] = 3
snapshot.front_bulk[400] = 4
snapshot.front_bulk[500] = 5
snapshot.front_bulk[600] = 6
snapshot.front_bulk[700] = 7
snapshot.front_bulk[800] = 8
snapshot.front_bulk[900] = 9
snapshot.front_bulk[1000] = 10

control_devices = control_devices.copy()
bulk_devices = bulk_devices.copy()

next_device = scheduler.choose_next(snapshot)
print(next_device)
```