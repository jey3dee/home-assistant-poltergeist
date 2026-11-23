"""Independent reference for the single-room model.

A discrete-time hidden Markov model forward pass on a fine time grid. It shares no code with the
production model: no matrix exponential, no eigendecomposition. It is the "exact oracle" of the
spec for a one-room house, up to the grid step.
"""

import numpy as np


def forward_oracle(params, events, t_start, t_end, initial, step=0.25):
    """Belief over head count at t_end, given motion events (seconds) in [t_start, t_end]."""
    n_states = params.max_people + 1
    n = np.arange(n_states)
    rates = np.where(n == 0, params.event_rate_empty, params.event_rate_present)
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
    event_steps: dict[int, int] = {}
    for t in events:
        idx = min(int((t - t_start) / step), steps - 1)
        event_steps[idx] = event_steps.get(idx, 0) + 1
    belief = np.array(initial, dtype=float)
    for i in range(steps):
        belief = belief @ trans
        count = event_steps.get(i, 0)
        if count:
            belief = belief * (rates * step) ** count
        else:
            belief = belief * (1.0 - rates * step)
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
