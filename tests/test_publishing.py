from custom_components.poltergeist.publishing import Publisher


def make():
    return Publisher(step=5.0, min_interval=5.0, heartbeat=300.0)


def test_first_value_is_always_due():
    assert make().due(0.0, 12.0)


def test_small_change_is_not_due():
    p = make()
    p.mark(0.0, 50.0)
    assert not p.due(60.0, 54.9)


def test_change_of_a_full_step_is_due():
    p = make()
    p.mark(0.0, 50.0)
    assert p.due(60.0, 55.0)
    assert p.due(60.0, 45.0)


def test_big_change_inside_the_minimum_interval_waits():
    p = make()
    p.mark(100.0, 50.0)
    assert not p.due(102.0, 90.0)
    assert p.due(105.0, 90.0)  # still pending at the next chance, not dropped


def test_heartbeat_republishes_an_unchanged_value():
    p = make()
    p.mark(0.0, 50.0)
    assert not p.due(299.0, 50.0)
    assert p.due(300.0, 50.0)


def test_mark_resets_the_reference():
    p = make()
    p.mark(0.0, 50.0)
    p.mark(10.0, 70.0)
    assert not p.due(20.0, 72.0)


def test_a_value_that_appears_or_disappears_is_due_at_once():
    p = make()
    p.mark(100.0, None)
    assert p.due(101.0, 20.0)
    p.mark(101.0, 20.0)
    assert p.due(102.0, None)


def test_a_value_that_stays_absent_is_never_republished():
    p = make()
    p.mark(0.0, None)
    assert not p.due(10_000.0, None)
