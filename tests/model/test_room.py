import numpy as np
import pytest

from custom_components.poltergeist.model import RoomBelief, RoomParams

PARAMS = RoomParams()


def stationary(params):
    """Closed-form stationary head count distribution of the birth-death chain (3 means 3+)."""
    weights = [1.0]
    for k in range(1, 4):
        weights.append(weights[-1] * params.arrival_rate / (k * params.leave_rate))
    w = np.array(weights)
    return w / w.sum()


def test_prior_is_the_stationary_distribution():
    belief = RoomBelief(PARAMS)
    assert belief.probabilities == pytest.approx(stationary(PARAMS))


def test_without_event_evidence_belief_stays_stationary():
    silent = RoomParams(event_rate_present=0.0, event_rate_empty=0.0)
    belief = RoomBelief(silent)
    belief.advance(10_000.0)
    assert belief.probabilities == pytest.approx(stationary(silent), abs=1e-9)


def test_probabilities_sum_to_one_and_are_nonnegative():
    belief = RoomBelief(PARAMS)
    for t in (1.0, 50.0, 5000.0, 1e7):
        belief.observe_event(t)
        assert belief.probabilities.sum() == pytest.approx(1.0)
        assert (belief.probabilities >= 0).all()


def test_motion_event_makes_room_occupied_likely():
    belief = RoomBelief(PARAMS)
    before = belief.p_occupied
    belief.observe_event(10.0)
    assert belief.p_occupied > 0.99
    assert belief.p_occupied > before


def test_silence_after_motion_lowers_occupancy_monotonically():
    belief = RoomBelief(PARAMS)
    belief.observe_event(0.0)
    last = belief.p_occupied
    for t in (60.0, 600.0, 3600.0, 6 * 3600.0):
        belief.advance(t)
        assert belief.p_occupied < last
        last = belief.p_occupied
    assert last < 0.05


def test_extreme_gap_does_not_underflow():
    belief = RoomBelief(PARAMS)
    belief.observe_event(0.0)
    belief.advance(3.0e8)  # about ten years
    assert np.isfinite(belief.probabilities).all()
    assert belief.probabilities.sum() == pytest.approx(1.0)


def test_expected_head_count_matches_distribution():
    belief = RoomBelief(PARAMS)
    belief.observe_event(5.0)
    expected = float(np.dot(np.arange(4), belief.probabilities))
    assert belief.expected_count == pytest.approx(expected)


def test_time_must_not_go_backwards():
    belief = RoomBelief(PARAMS)
    belief.advance(100.0)
    with pytest.raises(ValueError):
        belief.advance(50.0)


def test_snapshot_round_trip():
    belief = RoomBelief(PARAMS)
    belief.observe_event(42.0)
    restored = RoomBelief.from_snapshot(PARAMS, belief.snapshot())
    assert restored.probabilities == pytest.approx(belief.probabilities)
    restored.advance(1000.0)
    belief.advance(1000.0)
    assert restored.probabilities == pytest.approx(belief.probabilities)


def test_params_must_be_positive_where_required():
    with pytest.raises(ValueError):
        RoomParams(leave_rate=0.0)


def test_blind_advance_does_not_treat_the_gap_as_silence():
    # While nobody was listening (HA down), no-event evidence must not accumulate.
    observed = RoomBelief(PARAMS)
    observed.observe_event(0.0)
    blind = RoomBelief(PARAMS)
    blind.observe_event(0.0)
    observed.advance(1800.0)
    blind.advance(1800.0, observed=False)
    assert blind.p_occupied > observed.p_occupied


def test_blind_advance_over_a_long_gap_returns_to_the_prior():
    belief = RoomBelief(PARAMS)
    belief.observe_event(0.0)
    belief.advance(10 * 86400.0, observed=False)
    assert belief.probabilities == pytest.approx(stationary(PARAMS), abs=1e-9)


def test_blind_advance_matches_oracle_without_evidence():
    from tests.oracle import forward_oracle

    silent = RoomParams(event_rate_present=0.0, event_rate_empty=0.0)
    belief = RoomBelief(silent, t=0.0)
    belief.probabilities = np.array([0.0, 1.0, 0.0, 0.0])
    belief.advance(1200.0, observed=False)
    oracle = forward_oracle(silent, [], 0.0, 1200.0, [0.0, 1.0, 0.0, 0.0])
    assert belief.probabilities == pytest.approx(oracle, abs=1e-3)
