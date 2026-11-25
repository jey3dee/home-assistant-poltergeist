"""Minimal synthetic household: one room, people arriving and leaving, a few sensors.

Generates the data the model is supposed to explain, with the truth attached.
"""

from dataclasses import dataclass

import numpy as np

MOTION_HOLD = 90.0  # seconds a motion sensor stays on; it must not depend on the head count


@dataclass
class Scenario:
    sensors: list[tuple[str, bool]]  # (kind, state at time 0)
    changes: list[tuple[float, int, bool | None]]  # (time, sensor index, new state)
    counts: list[tuple[float, int]]  # (time, head count after change); starts with (0, n0)
    duration: float

    def truth_at(self, t: float) -> int:
        count = self.counts[0][1]
        for ts, n in self.counts:
            if ts <= t:
                count = n
            else:
                break
        return count


def simulate(params, duration: float, seed: int, kinds=("motion",), initial_count: int = 0):
    rng = np.random.default_rng(seed)
    t, n = 0.0, initial_count
    state = [False] * len(kinds)
    rearm = [np.inf] * len(kinds)  # when a motion sensor that is on goes off again
    counts = [(0.0, n)]
    changes: list[tuple[float, int, bool | None]] = []
    while True:
        options = []  # (rate, what happens)
        if n < params.max_people:
            options.append((params.arrival_rate, "arrive"))
        if n > 0:
            options.append((n * params.leave_rate, "leave"))
        for i, kind in enumerate(kinds):
            if kind == "motion":
                if not state[i]:
                    rate = params.motion_rate_present if n else params.motion_rate_empty
                    options.append((rate, i))
            elif state[i]:
                rate = params.occupancy_off_rate_present if n else params.occupancy_off_rate_empty
                options.append((rate, i))
            else:
                rate = params.occupancy_on_rate_present if n else params.occupancy_on_rate_empty
                options.append((rate, i))
        total = sum(rate for rate, _ in options)
        next_random = t + rng.exponential(1.0 / total)
        next_rearm = min(rearm, default=np.inf)
        if min(next_random, next_rearm) >= duration:
            break
        if next_rearm < next_random:  # all other waiting times are memoryless, so redraw them
            t, i = next_rearm, rearm.index(next_rearm)
            state[i], rearm[i] = False, np.inf
            changes.append((t, i, False))
            continue
        t = next_random
        weights = np.array([rate for rate, _ in options]) / total
        what = options[rng.choice(len(options), p=weights)][1]
        if what == "arrive" or what == "leave":
            n += 1 if what == "arrive" else -1
            counts.append((t, n))
        else:
            state[what] = not state[what]
            if kinds[what] == "motion":
                rearm[what] = t + MOTION_HOLD
            changes.append((t, what, state[what]))
    return Scenario([(kind, False) for kind in kinds], changes, counts, duration)


def with_outage(scenario: Scenario, index: int, start: float, end: float) -> Scenario:
    """The same household, with one sensor not heard between start and end."""
    state, kept = scenario.sensors[index][1], []
    resumed = None
    for t, i, new in scenario.changes:
        if i == index and t < end:
            resumed = new
        if i != index or not start <= t < end:
            kept.append((t, i, new))
    for t, i, new in scenario.changes:
        if i == index and t < start:
            state = new
    resumed = state if resumed is None else resumed
    kept += [(start, index, None), (end, index, resumed)]
    kept.sort(key=lambda c: c[0])
    return Scenario(scenario.sensors, kept, scenario.counts, scenario.duration)
