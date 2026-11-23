"""The production filter against the independent grid oracle on simulated households."""

import numpy as np
import pytest

from custom_components.poltergeist.model import RoomBelief, RoomParams
from tests.oracle import forward_oracle
from tests.simulator import simulate

PARAMS = RoomParams()
SEEDS = [1, 2, 3, 4, 5]


def run_model(params, scenario, checkpoints):
    belief = RoomBelief(params, t=0.0)
    out = {}
    pending = sorted(checkpoints)
    for t in scenario.events:
        while pending and pending[0] < t:
            belief.advance(pending[0])
            out[pending[0]] = belief.probabilities.copy()
            pending.pop(0)
        belief.observe_event(t)
    for c in pending:
        belief.advance(c)
        out[c] = belief.probabilities.copy()
    return out


@pytest.mark.parametrize("seed", SEEDS)
def test_matches_oracle_at_checkpoints(seed):
    scenario = simulate(PARAMS, duration=6 * 3600.0, seed=seed)
    checkpoints = [1800.0, 7200.0, 14400.0, 6 * 3600.0]
    model = run_model(PARAMS, scenario, checkpoints)
    prior = RoomBelief(PARAMS).probabilities
    for c in checkpoints:
        events = [t for t in scenario.events if t <= c]
        oracle = forward_oracle(PARAMS, events, 0.0, c, prior)
        assert model[c] == pytest.approx(oracle, abs=ORACLE_TOLERANCE), (seed, c)


# Measured worst case over 20 seeds x 4 checkpoints: 2e-4 (grid step 0.25 s).
ORACLE_TOLERANCE = 1e-3


@pytest.mark.parametrize("max_people", [1, 2, 8, 15])
def test_matches_oracle_for_other_room_sizes(max_people):
    params = RoomParams(arrival_rate=1 / 1800, max_people=max_people)
    scenario = simulate(params, duration=2 * 3600.0, seed=7)
    checkpoints = [900.0, 3600.0, 2 * 3600.0]
    model = run_model(params, scenario, checkpoints)
    prior = RoomBelief(params).probabilities
    for c in checkpoints:
        events = [t for t in scenario.events if t <= c]
        oracle = forward_oracle(params, events, 0.0, c, prior)
        assert model[c] == pytest.approx(oracle, abs=ORACLE_TOLERANCE), (max_people, c)


def test_posterior_beats_prior_on_simulated_truth():
    log_post, log_prior = [], []
    prior = RoomBelief(PARAMS).probabilities
    for seed in range(10, 20):
        scenario = simulate(PARAMS, duration=4 * 3600.0, seed=seed)
        checkpoints = [float(c) for c in range(600, 4 * 3600, 600)]
        model = run_model(PARAMS, scenario, checkpoints)
        for c in checkpoints:
            truth = scenario.truth_at(c)
            log_post.append(np.log(max(model[c][truth], 1e-12)))
            log_prior.append(np.log(prior[truth]))
    assert np.mean(log_post) > np.mean(log_prior) + MIN_GAIN_NATS


# Measured gain over the prior on seeds 10-19: 0.23 nats.
MIN_GAIN_NATS = 0.1
