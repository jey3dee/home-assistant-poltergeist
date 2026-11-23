import numpy as np
import pytest

from custom_components.poltergeist.model import RoomBelief, RoomParams

PARAMS = RoomParams()


def stationary(params):
    """Closed-form stationary head count distribution of the birth-death chain (top = or more)."""
    weights = [1.0]
    for k in range(1, params.max_people + 1):
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
    expected = float(np.dot(np.arange(len(belief.probabilities)), belief.probabilities))
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
    belief.probabilities = np.array([0.0, 1.0] + [0.0] * (silent.max_people - 1))
    belief_start = belief.probabilities.copy()
    belief.advance(1200.0, observed=False)
    oracle = forward_oracle(silent, [], 0.0, 1200.0, belief_start)
    assert belief.probabilities == pytest.approx(oracle, abs=1e-3)


def test_latest_never_goes_backwards_and_treats_zero_as_a_time():
    belief = RoomBelief(PARAMS, t=0.0)
    assert belief.latest(-5.0) == 0.0  # zero is a real time, not "unset"
    assert belief.latest(7.0) == 7.0
    assert RoomBelief(PARAMS).latest(3.0) == 3.0  # no time yet: take the given one


def test_default_tracks_up_to_four_people():
    assert RoomParams().max_people == 4
    assert len(RoomBelief(RoomParams()).probabilities) == 5


@pytest.mark.parametrize("bad", [0, -1, 16, 100])
def test_max_people_outside_the_checked_range_is_refused(bad):
    with pytest.raises(ValueError):
        RoomParams(max_people=bad)


@pytest.mark.parametrize("ok", [1, 15])
def test_max_people_range_ends_are_accepted(ok):
    assert len(RoomBelief(RoomParams(max_people=ok)).probabilities) == ok + 1


def test_a_busy_room_is_counted_above_the_default_top_state():
    busy = RoomParams(arrival_rate=1 / 60, leave_rate=1 / 3600, max_people=8)
    belief = RoomBelief(busy, t=0.0)
    belief.observe_event(10.0)
    belief.advance(610.0)
    assert belief.expected_count > 5.0


@pytest.mark.parametrize("max_people", [4, 8, 15])
def test_matrix_exponential_is_accurate_up_to_the_largest_allowed_size(max_people):
    """The eigendecomposition loses accuracy as the matrix grows; this is what limits the range."""
    from tests.oracle import expm_reference

    params = RoomParams(max_people=max_people)
    belief = RoomBelief(params, t=0.0)
    start = np.zeros(max_people + 1)
    start[1] = 1.0
    a = params.generator - np.diag(params.event_rates)
    for dt in (10.0, 300.0, 3600.0, 86400.0):
        reference = np.clip(start @ expm_reference(a, dt), 0.0, None)
        reference /= reference.sum()
        got = belief._normalised(belief._observed.apply(start, dt))
        assert got == pytest.approx(reference, abs=1e-8), (max_people, dt)


def test_a_stored_belief_is_widened_with_zero_probability():
    small = RoomBelief(RoomParams(max_people=2), t=5.0)
    restored = RoomBelief.from_snapshot(RoomParams(max_people=5), small.snapshot())
    assert len(restored.probabilities) == 6
    assert restored.probabilities[:3] == pytest.approx(small.probabilities)
    assert restored.probabilities[3:] == pytest.approx(0.0)
    assert restored.t == 5.0


def test_a_stored_belief_is_narrowed_by_folding_the_rest_into_the_top_state():
    big = RoomBelief(RoomParams(max_people=5), t=5.0)
    stored = big.probabilities.copy()
    restored = RoomBelief.from_snapshot(RoomParams(max_people=2), big.snapshot())
    assert len(restored.probabilities) == 3
    assert restored.probabilities[:2] == pytest.approx(stored[:2])
    assert restored.probabilities[2] == pytest.approx(stored[2:].sum())
    assert restored.probabilities.sum() == pytest.approx(1.0)
