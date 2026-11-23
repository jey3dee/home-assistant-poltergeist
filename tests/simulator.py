"""Minimal synthetic household: one room, residents arriving and leaving, a motion sensor.

Generates the data the model is supposed to explain, with the truth attached.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class Scenario:
    events: list[float]  # motion event times in seconds
    changes: list[tuple[float, int]]  # (time, head count after change); starts with (0, n0)
    duration: float

    def truth_at(self, t: float) -> int:
        count = self.changes[0][1]
        for ts, n in self.changes:
            if ts <= t:
                count = n
            else:
                break
        return count


def simulate(params, duration: float, seed: int, initial_count: int = 0):
    rng = np.random.default_rng(seed)
    t, n = 0.0, initial_count
    changes = [(0.0, n)]
    events: list[float] = []
    while t < duration:
        up = params.arrival_rate if n < params.max_people else 0.0
        down = n * params.leave_rate
        event = params.event_rate_empty if n == 0 else params.event_rate_present
        total = up + down + event
        t += rng.exponential(1.0 / total)
        if t >= duration:
            break
        u = rng.random() * total
        if u < up:
            n += 1
            changes.append((t, n))
        elif u < up + down:
            n -= 1
            changes.append((t, n))
        else:
            events.append(t)
    return Scenario(events=events, changes=changes, duration=duration)
