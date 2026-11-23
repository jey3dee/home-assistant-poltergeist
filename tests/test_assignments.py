from custom_components.poltergeist.discovery import reconcile_assignments

from .helpers import add_area, add_binary_sensor


async def test_first_run_takes_the_proposals(hass):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    assert reconcile_assignments(hass, {}) == {pir: kitchen.id}


async def test_a_new_sensor_is_added_and_known_ones_are_kept(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    old = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    new = add_binary_sensor(hass, "hall_pir", area_id=hall.id)
    assert reconcile_assignments(hass, {old: kitchen.id}) == {old: kitchen.id, new: hall.id}


async def test_an_assignment_survives_a_change_of_the_home_assistant_area(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    pir = add_binary_sensor(hass, "pir", area_id=hall.id)  # Home Assistant says Hall now
    assert reconcile_assignments(hass, {pir: kitchen.id}) == {pir: kitchen.id}


async def test_an_excluded_sensor_stays_excluded(hass):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "pir", area_id=kitchen.id)
    assert reconcile_assignments(hass, {pir: None}) == {pir: None}


async def test_a_deleted_sensor_is_dropped(hass):
    kitchen = add_area(hass, "Kitchen")
    assert reconcile_assignments(hass, {"binary_sensor.gone": kitchen.id}) == {}


async def test_a_deleted_area_leaves_its_sensors_without_a_room(hass):
    pir = add_binary_sensor(hass, "pir")
    assert reconcile_assignments(hass, {pir: "deleted_area"}) == {pir: None}


async def test_the_stored_map_is_not_modified(hass):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "pir", area_id=kitchen.id)
    stored: dict = {}
    reconcile_assignments(hass, stored)
    assert stored == {}
    assert pir not in stored


async def test_reload_requests_are_merged_until_a_reload_has_started(hass):
    from unittest.mock import patch

    from custom_components.poltergeist.estimator import UpdateListeners
    from tests.helpers import setup_poltergeist

    await setup_poltergeist(hass)
    listeners = UpdateListeners()
    with patch.object(hass.config_entries, "async_schedule_reload") as schedule:
        for _ in range(10):
            listeners.request_reload(hass)
        assert schedule.call_count == 1  # ten changes before the reload started: one reload
        listeners.reload_started()
        listeners.request_reload(hass)
        assert schedule.call_count == 2  # a change after the reload began needs its own
