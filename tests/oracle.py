"""Independent reference for the single-room model.

A discrete-time hidden Markov model forward pass on a fine time grid. It shares no code with the
production model: no matrix exponential, no eigendecomposition. It is the "exact oracle" of the
spec for a one-room house, up to the grid step.
"""

import numpy as np


def forward_oracle(params, sensors, changes, t_start, t_end, initial, step=0.25):
    """Belief over head count at t_end.

    `sensors` is a list of (kind, state at t_start), kind "motion" or "occupancy" and state True
    (on), False (off) or None (not heard). `changes` is a time-ordered list of
    (seconds, sensor index, new state). The sensor rules are written out here a second time on
    purpose, instead of asking the production model for them.
    """
    n_states = params.max_people + 1
    empty = np.arange(n_states) == 0

    def per_state(when_empty, when_occupied):
        return np.where(empty, when_empty, when_occupied)

    motion = per_state(params.motion_rate_empty, params.motion_rate_present)
    switch_on = per_state(params.occupancy_on_rate_empty, params.occupancy_on_rate_present)
    switch_off = per_state(params.occupancy_off_rate_empty, params.occupancy_off_rate_present)

    def pending_rate(kind, state):
        """Rate of the change that may happen next. A motion sensor that is on has none."""
        if state is None or (kind == "motion" and state):
            return np.zeros(n_states)
        if kind == "motion":
            return motion
        return switch_off if state else switch_on

    trans = np.zeros((n_states, n_states))
    for k in range(n_states):
        up = params.arrival_rate if k < n_states - 1 else 0.0
        down = k * params.leave_rate
        trans[k, k] = 1.0 - (up + down) * step
        if k < n_states - 1:
            trans[k, k + 1] = up * step
        if k > 0:
            trans[k, k - 1] = down * step

    steps = int(round((t_end - t_start) / step))
    by_step: dict[int, list] = {}
    for t, index, new in changes:
        by_step.setdefault(min(int((t - t_start) / step), steps - 1), []).append((index, new))

    kinds = [kind for kind, _ in sensors]
    states = [state for _, state in sensors]
    belief = np.array(initial, dtype=float)
    for i in range(steps):
        belief = belief @ trans
        happening = by_step.get(i, [])
        changed = {index for index, _ in happening}
        for index, kind in enumerate(kinds):
            if index not in changed:
                belief = belief * (1.0 - pending_rate(kind, states[index]) * step)
        for index, new in happening:
            old = states[index]
            if old is not None and new is not None and old != new:
                # a motion sensor going off is its hold time running out: no evidence
                if not (kinds[index] == "motion" and old):
                    belief = belief * pending_rate(kinds[index], old) * step
            states[index] = new
        belief = belief / belief.sum()
    return belief


def expm_reference(matrix, t, terms=24):
    """exp(matrix * t) by scaling and squaring with a Taylor series: no eigendecomposition."""
    a = matrix * t
    squarings = max(0, int(np.ceil(np.log2(max(np.abs(a).sum(axis=1).max(), 1e-300)))) + 1)
    a = a / 2**squarings
    result = term = np.eye(len(a))
    for k in range(1, terms):
        term = term @ a / k
        result = result + term
    for _ in range(squarings):
        result = result @ result
    return result
