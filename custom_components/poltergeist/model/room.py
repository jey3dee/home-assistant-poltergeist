"""Head-count belief for one room, filtered in continuous time from its sensors.

State: head count 0, 1, ... `max_people`. The calculation treats the top state as exactly that
many (nobody else arrives), so reading it as "that many or more" is an approximation.
Dynamics: a birth-death Markov chain. One more person arrives at `arrival_rate`; each person
present leaves at `leave_rate`.
Evidence: each sensor changes state at rates that differ between an empty and an occupied room.
While a sensor stays as it is, the rate of the change that has not happened (the dwell rate)
counts against the head counts that would have caused it by now. When it changes, the belief is
multiplied by the rate of that change. Between changes the belief follows
exp((Q - D) dt), with D the summed dwell rates of the sensors; it is renormalised after every step.

Two kinds of sensor:
- motion, a trigger: switching on happens at `motion_rate_*`. While it is on it cannot trigger,
  so that time says nothing, and neither does switching off. This is exact only if the time it
  stays on does not depend on who is in the room.
- occupancy, a state: it switches on at `occupancy_on_rate_*` and off at `occupancy_off_rate_*`.
A sensor that is not heard (unavailable, unknown) says nothing, and neither does a change from
or to that state.

The defaults are assumed starting values; later slices learn them.
"""

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

import numpy as np

_LOGGER = logging.getLogger(__name__)

MAX_PEOPLE_LIMIT = 15
# The matrix exponential comes from an eigendecomposition whose accuracy falls quickly with size
# (measured worst error in a probability: 3e-11 at 16 states, 2e-7 at 24, 3e-3 at 32), so the
# range is capped where the error is still far below anything visible.


class SensorKind(StrEnum):
    MOTION = "motion"
    OCCUPANCY = "occupancy"


# What a sensor says: its kind, and on (True), off (False) or not heard (None).
type Reading = tuple[SensorKind, bool | None]


@dataclass(frozen=True)
class RoomParams:
    """All rates are per second. `*_empty` applies to nobody, `*_present` to one or more."""

    arrival_rate: float = 1.0 / 7200.0  # one more person comes in
    leave_rate: float = 1.0 / 1800.0  # per person present
    motion_rate_empty: float = 1.0 / 2_592_000.0  # false triggers
    motion_rate_present: float = 1.0 / 300.0
    occupancy_on_rate_empty: float = 1.0 / 2_592_000.0  # false switch-ons, while off
    occupancy_on_rate_present: float = 1.0 / 300.0
    occupancy_off_rate_empty: float = 1.0 / 120.0  # while on
    occupancy_off_rate_present: float = 1.0 / 1800.0
    max_people: int = 4  # highest head count tracked

    def __post_init__(self):
        if self.arrival_rate <= 0 or self.leave_rate <= 0:
            raise ValueError("arrival_rate and leave_rate must be positive")
        sensor_rates = (
            self.motion_rate_empty,
            self.motion_rate_present,
            self.occupancy_on_rate_empty,
            self.occupancy_on_rate_present,
            self.occupancy_off_rate_empty,
            self.occupancy_off_rate_present,
        )
        if min(sensor_rates) < 0:
            raise ValueError("sensor rates must not be negative")
        if not 1 <= self.max_people <= MAX_PEOPLE_LIMIT:
            raise ValueError(f"max_people must be between 1 and {MAX_PEOPLE_LIMIT}")

    @property
    def n_states(self) -> int:
        return self.max_people + 1

    def _per_state(self, empty: float, present: float) -> np.ndarray:
        return np.array([empty] + [present] * self.max_people)

    def _next_change_rate(self, kind: SensorKind, on: bool) -> np.ndarray | None:
        """The rate at which a sensor in this state changes by itself, per head count.

        None for a motion sensor that is on: when it goes off says nothing about the room.
        """
        if kind is SensorKind.MOTION:
            if on:
                return None
            return self._per_state(self.motion_rate_empty, self.motion_rate_present)
        if on:
            return self._per_state(self.occupancy_off_rate_empty, self.occupancy_off_rate_present)
        return self._per_state(self.occupancy_on_rate_empty, self.occupancy_on_rate_present)

    def dwell_rates(self, readings: Iterable[Reading]) -> np.ndarray:
        """The diagonal of D: the summed rates of the changes that have not happened."""
        total = np.zeros(self.n_states)
        for kind, on in readings:
            rate = None if on is None else self._next_change_rate(kind, on)
            if rate is not None:
                total += rate
        return total

    def change_weight(self, kind: SensorKind, old: bool | None, new: bool | None):
        """What to multiply the belief by when a sensor changes, or None for no evidence."""
        if old is None or new is None or old == new:
            return None
        return self._next_change_rate(kind, old)

    @property
    def generator(self) -> np.ndarray:
        q = np.zeros((self.n_states, self.n_states))
        for k in range(self.n_states):
            if k < self.max_people:
                q[k, k + 1] = self.arrival_rate
            if k > 0:
                q[k, k - 1] = k * self.leave_rate
            q[k, k] = -q[k].sum()
        return q


class _Propagator:
    """exp(A dt) for a fixed matrix A, from one eigendecomposition.

    A is a sub-generator of a birth-death chain: it is similar to a symmetric tridiagonal
    matrix, so its eigenvalues are real and it is diagonalisable.
    """

    def __init__(self, a: np.ndarray):
        self._eigenvalues, self._vectors = np.linalg.eig(a)
        self._vectors_inv = np.linalg.inv(self._vectors)
        # Subtracting the largest eigenvalue only rescales the result, which is renormalised by
        # the caller. It stops very long gaps from underflowing to an all-zero vector.
        self._shift = float(self._eigenvalues.max())

    def apply(self, row: np.ndarray, dt: float) -> np.ndarray:
        decay = np.exp((self._eigenvalues - self._shift) * dt)
        return row @ self._vectors @ np.diag(decay) @ self._vectors_inv


class RoomBelief:
    def __init__(self, params: RoomParams, probabilities=None, t: float | None = None):
        self.params = params
        # Rows are the "from" state, so a belief row vector moves as `belief @ propagator`.
        # One propagator per combination of dwell rates, made when it is first needed.
        self._propagators: dict[bytes, _Propagator] = {}
        self.probabilities = (
            self._stationary() if probabilities is None else np.asarray(probabilities, float)
        )
        self.t = t

    def _propagator(self, dwell: np.ndarray) -> _Propagator:
        key = dwell.tobytes()
        if key not in self._propagators:
            # A = Q - D has real, distinct eigenvalues for any diagonal D (it is similar to a
            # symmetric tridiagonal matrix), so exp(A dt) comes from one eigendecomposition.
            self._propagators[key] = _Propagator(self.params.generator - np.diag(dwell))
        return self._propagators[key]

    def _stationary(self) -> np.ndarray:
        w = [1.0]
        for k in range(1, self.params.n_states):
            w.append(w[-1] * self.params.arrival_rate / (k * self.params.leave_rate))
        w = np.array(w)
        return w / w.sum()

    @property
    def p_occupied(self) -> float:
        return float(1.0 - self.probabilities[0])

    @property
    def expected_count(self) -> float:
        return float(np.dot(np.arange(self.params.n_states), self.probabilities))

    def latest(self, t: float) -> float:
        """`t`, or this belief's own time if that is later.

        Wall-clock ticks and event timestamps can differ by a few milliseconds; the belief itself
        never moves backwards (`advance` refuses), so callers clamp with this first.
        """
        return t if self.t is None else max(t, self.t)

    def advance(self, t: float, readings: Iterable[Reading] = ()) -> None:
        """Move the belief to time t, with the sensors as they were during that time.

        Each listening sensor that did not change is itself evidence. Without readings nobody was
        listening (for example Home Assistant was down), so the belief only follows the dynamics.
        """
        if self.t is None:
            self.t = t
            return
        dt = t - self.t
        if dt < 0:
            raise ValueError(f"time went backwards by {-dt} s")
        if dt > 0:
            propagator = self._propagator(self.params.dwell_rates(readings))
            self.probabilities = self._normalised(propagator.apply(self.probabilities, dt))
        self.t = t

    def observe_change(self, kind: SensorKind, old: bool | None, new: bool | None) -> None:
        """A sensor changed now. `advance` to the time of the change first."""
        weight = self.params.change_weight(kind, old, new)
        if weight is not None:
            self.probabilities = self._normalised(self.probabilities * weight)

    def _normalised(self, vector: np.ndarray) -> np.ndarray:
        vector = np.clip(vector, 0.0, None)
        total = vector.sum()
        if not np.isfinite(total) or total <= 0.0:
            _LOGGER.warning(
                "The observations are impossible under the model; the room estimate is reset"
            )
            return self._stationary()
        return vector / total

    def snapshot(self) -> dict:
        return {"probabilities": [float(p) for p in self.probabilities], "t": self.t}

    @classmethod
    def from_snapshot(cls, params: RoomParams, data: dict) -> RoomBelief:
        stored = np.asarray(data["probabilities"], float)
        n = params.n_states
        # The room size may have changed since the belief was saved: widen with zeros, or fold the
        # probability of the removed head counts into the new top state ("or more").
        fitted = np.zeros(n)
        fitted[: min(n, len(stored))] = stored[:n]
        if len(stored) > n:
            fitted[n - 1] += stored[n:].sum()
        return cls(params, probabilities=fitted, t=data["t"])
