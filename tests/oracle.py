"""Independent reference for the single-room model.

A discrete-time hidden Markov model forward pass on a fine time grid. It shares no code with the
production model: no matrix exponential, no eigendecomposition. It is the "exact oracle" of the
spec for a one-room house, up to the grid step.
"""

import numpy as np

N_STATES = 4


def forward_oracle(params, events, t_start, t_end, initial, step=0.25):
    """Belief over head count at t_end, given motion events (seconds) in [t_start, t_end]."""
    n = np.arange(N_STATES)
    rates = np.where(n == 0, params.event_rate_empty, params.event_rate_present)
    trans = np.zeros((N_STATES, N_STATES))
    for k in range(N_STATES):
        up = params.arrival_rate if k < N_STATES - 1 else 0.0
        down = k * params.leave_rate
        trans[k, k] = 1.0 - (up + down) * step
        if k < N_STATES - 1:
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
