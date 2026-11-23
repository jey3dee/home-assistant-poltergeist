"""When a value is worth writing to Home Assistant.

Every state write ends up in the recorder database, so a value is written only when it moved by
a meaningful step, no sooner than a minimum interval after the last write, and at the latest
after a heartbeat so that quiet entities do not look dead.
"""


class Publisher:
    def __init__(self, step: float, min_interval: float, heartbeat: float):
        self.step = step
        self.min_interval = min_interval
        self.heartbeat = heartbeat
        self._time: float | None = None
        self._value: float | None = None

    def due(self, now: float, value: float | None) -> bool:
        if self._time is None or (value is None) != (self._value is None):
            return True  # first value, or the value appeared or disappeared
        if value is None:
            return False  # still no value: nothing to republish
        elapsed = now - self._time
        if elapsed < self.min_interval:
            return False
        return abs(value - self._value) >= self.step or elapsed >= self.heartbeat

    def mark(self, now: float, value: float | None) -> None:
        self._time = now
        self._value = value
