"""Head-count belief for one room, filtered in continuous time from motion events.

State: head count 0, 1, 2, 3+ (the last state stands for three or more people).
Dynamics: a birth-death chain. One more person arrives at `arrival_rate`; each person present
leaves at `leave_rate`.
Evidence: motion events form a Poisson process whose rate depends on the room being empty
(false events) or occupied. Between events the belief is propagated with the dynamics *and* the
probability of seeing no event, so silence slowly argues for an empty room. At an event the belief
is multiplied by the event rate of each state. The belief is renormalised after every step.

The defaults are priors for a typical room; later slices learn them.
"""

from dataclasses import dataclass

import numpy as np

N_STATES = 4


@dataclass(frozen=True)
class RoomParams:
    arrival_rate: float = 1.0 / 7200.0  # per second, an empty-or-not room gains one person
    leave_rate: float = 1.0 / 1800.0  # per second and person present
    event_rate_present: float = 1.0 / 300.0  # motion events per second while occupied
    event_rate_empty: float = 1.0 / 2_592_000.0  # false motion events per second while empty

    def __post_init__(self):
        if self.arrival_rate <= 0 or self.leave_rate <= 0:
            raise ValueError("arrival_rate and leave_rate must be positive")
        if self.event_rate_present < 0 or self.event_rate_empty < 0:
            raise ValueError("event rates must not be negative")

    @property
    def event_rates(self) -> np.ndarray:
        return np.array([self.event_rate_empty] + [self.event_rate_present] * (N_STATES - 1))

    @property
    def generator(self) -> np.ndarray:
        q = np.zeros((N_STATES, N_STATES))
        for k in range(N_STATES):
            if k < N_STATES - 1:
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
        # The sub-generator A = Q - diag(rates) has real, distinct eigenvalues (it is similar to a
        # symmetric tridiagonal matrix), so exp(A dt) comes from one eigendecomposition.
        self._observed = _Propagator(params.generator - np.diag(params.event_rates))
        self._blind = _Propagator(params.generator)
        self.probabilities = (
            self._stationary() if probabilities is None else np.asarray(probabilities, float)
        )
        self.t = t

    def _stationary(self) -> np.ndarray:
        w = [1.0]
        for k in range(1, N_STATES):
            w.append(w[-1] * self.params.arrival_rate / (k * self.params.leave_rate))
        w = np.array(w)
        return w / w.sum()

    @property
    def p_occupied(self) -> float:
        return float(1.0 - self.probabilities[0])

    @property
    def expected_count(self) -> float:
        return float(np.dot(np.arange(N_STATES), self.probabilities))

    def latest(self, t: float) -> float:
        """`t`, or this belief's own time if that is later.

        Wall-clock ticks and event timestamps can differ by a few milliseconds; the belief itself
        never moves backwards (`advance` refuses), so callers clamp with this first.
        """
        return t if self.t is None else max(t, self.t)

    def advance(self, t: float, observed: bool = True) -> None:
        """Move the belief to time t.

        With `observed=True` nobody saw a motion event in between, which is itself evidence.
        With `observed=False` nobody was listening (for example Home Assistant was down), so the
        gap says nothing about events and the belief only follows the dynamics.
        """
        if self.t is None:
            self.t = t
            return
        dt = t - self.t
        if dt < 0:
            raise ValueError(f"time went backwards by {-dt} s")
        if dt > 0:
            propagator = self._observed if observed else self._blind
            self.probabilities = self._normalised(propagator.apply(self.probabilities, dt))
        self.t = t

    def observe_event(self, t: float) -> None:
        """A motion event at time t."""
        self.advance(t)
        self.probabilities = self._normalised(self.probabilities * self.params.event_rates)

    def _normalised(self, vector: np.ndarray) -> np.ndarray:
        vector = np.clip(vector, 0.0, None)
        total = vector.sum()
        if not np.isfinite(total) or total <= 0.0:
            return self._stationary()
        return vector / total

    def snapshot(self) -> dict:
        return {"probabilities": [float(p) for p in self.probabilities], "t": self.t}

    @classmethod
    def from_snapshot(cls, params: RoomParams, data: dict) -> RoomBelief:
        return cls(params, probabilities=data["probabilities"], t=data["t"])
