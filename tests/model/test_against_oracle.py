"""The production filter against the independent grid oracle on simulated households."""

import numpy as np
import pytest

from custom_components.poltergeist.model import RoomBelief, RoomParams, SensorKind
from tests.oracle import forward_oracle
from tests.simulator import simulate, with_outage

PARAMS = RoomParams()
SEEDS = [1, 2]
HOUSES = {
    "motion": ("motion",),
    "occupancy": ("occupancy",),
    "mixed": ("motion", "occupancy"),
    "two_of_each": ("motion", "motion", "occupancy", "occupancy"),
}
# Measured worst case over 4 houses x 8 seeds x 3 checkpoints: 1.4e-4 (grid step 0.25 s).
ORACLE_TOLERANCE = 1e-3


def run_model(params, scenario, checkpoints):
    belief = RoomBelief(params, t=0.0)
    kinds = [SensorKind(kind) for kind, _ in scenario.sensors]
    states = [state for _, state in scenario.sensors]
    out = {}
    pending = sorted(checkpoints)

    def advance(t):
        belief.advance(t, list(zip(kinds, states, strict=True)))

    for t, index, new in scenario.changes:
        while pending and pending[0] < t:
            advance(pending[0])
            out[pending.pop(0)] = belief.probabilities.copy()
        advance(t)
        belief.observe_change(kinds[index], states[index], new)
        states[index] = new
    for c in pending:
        advance(c)
        out[c] = belief.probabilities.copy()
    return out


def assert_matches_oracle(params, scenario, checkpoints, label):
    model = run_model(params, scenario, checkpoints)
    prior = RoomBelief(params).probabilities
    for c in checkpoints:
        changes = [change for change in scenario.changes if change[0] < c]
        oracle = forward_oracle(params, scenario.sensors, changes, 0.0, c, prior)
        worst = float(np.abs(model[c] - oracle).max())
        assert worst < ORACLE_TOLERANCE, (label, c, worst)


@pytest.mark.parametrize("house", HOUSES)
@pytest.mark.parametrize("seed", SEEDS)
def test_matches_oracle_at_checkpoints(house, seed):
    scenario = simulate(PARAMS, duration=3 * 3600.0, seed=seed, kinds=HOUSES[house])
    assert_matches_oracle(PARAMS, scenario, [1800.0, 7200.0, 3 * 3600.0], (house, seed))


@pytest.mark.parametrize("house", ["motion", "occupancy"])
def test_matches_oracle_across_an_outage(house):
    kinds = HOUSES[house] * 2
    scenario = simulate(PARAMS, duration=3 * 3600.0, seed=3, kinds=kinds)
    scenario = with_outage(scenario, 0, 2000.0, 8000.0)
    assert_matches_oracle(PARAMS, scenario, [1800.0, 5000.0, 9000.0, 3 * 3600.0], house)


@pytest.mark.parametrize("max_people", [1, 2, 8, 15])
def test_matches_oracle_for_other_room_sizes(max_people):
    params = RoomParams(arrival_rate=1 / 1800, max_people=max_people)
    scenario = simulate(params, duration=2 * 3600.0, seed=7, kinds=HOUSES["mixed"])
    assert_matches_oracle(params, scenario, [900.0, 3600.0, 2 * 3600.0], max_people)


@pytest.mark.parametrize("house", HOUSES)
def test_posterior_beats_prior_on_simulated_truth(house):
    log_post, log_prior = [], []
    prior = RoomBelief(PARAMS).probabilities
    for seed in range(10, 20):
        scenario = simulate(PARAMS, duration=4 * 3600.0, seed=seed, kinds=HOUSES[house])
        checkpoints = [float(c) for c in range(600, 4 * 3600, 600)]
        model = run_model(PARAMS, scenario, checkpoints)
        for c in checkpoints:
            truth = scenario.truth_at(c)
            log_post.append(np.log(max(model[c][truth], 1e-12)))
            log_prior.append(np.log(prior[truth]))
    assert np.mean(log_post) > np.mean(log_prior) + MIN_GAIN_NATS


MIN_GAIN_NATS = 0.1
