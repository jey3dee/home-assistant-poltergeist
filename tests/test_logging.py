"""The log should be able to tell what happened."""

import logging

from custom_components.poltergeist.model import RoomBelief, RoomParams, SensorKind

from .helpers import add_area, add_binary_sensor, setup_poltergeist


def messages(caplog, level):
    return [
        r.getMessage()
        for r in caplog.records
        if r.name.startswith("custom_components.poltergeist") and r.levelno == level
    ]


def test_a_reset_estimate_is_reported_with_its_room(caplog):
    never = RoomParams(motion_rate_present=0.0, motion_rate_empty=0.0)
    belief = RoomBelief(never, t=0.0, name="Kitchen")
    belief.observe_change(SensorKind.MOTION, False, True)
    [warning] = messages(caplog, logging.WARNING)
    assert "Kitchen" in warning and "reset" in warning


async def test_setup_says_at_debug_level_what_each_room_watches(hass, caplog):
    caplog.set_level(logging.DEBUG)
    kitchen = add_area(hass, "Kitchen")
    add_area(hass, "Bedroom")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    await setup_poltergeist(hass)
    assert f"Kitchen watches {pir} (motion)" in messages(caplog, logging.DEBUG)
    assert "Bedroom watches no sensors" in messages(caplog, logging.DEBUG)


async def test_a_sensor_change_is_logged_in_its_own_words_with_what_it_did(hass, caplog):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    await setup_poltergeist(hass)
    caplog.set_level(logging.DEBUG)
    for state in ("on", "unavailable"):
        hass.states.async_set(pir, state)
        await hass.async_block_till_done()
    on, gone = [m for m in messages(caplog, logging.DEBUG) if "went from" in m]
    assert on.startswith(f"Kitchen: {pir} went from off to on; occupied 22.1 % before")
    assert on.endswith("99.9 % after") or on.endswith("100.0 % after")
    assert "went from on to unavailable" in gone


async def test_a_reload_after_saved_settings_or_rooms_says_why(hass, caplog):
    kitchen = add_area(hass, "Kitchen")
    add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    entry = await setup_poltergeist(hass)
    caplog.set_level(logging.INFO)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(result["flow_id"], {"max_people": 6})
    await hass.async_block_till_done()
    assert "Settings or rooms were saved, reloading" in messages(caplog, logging.INFO)


async def test_the_startup_summary_does_not_say_every_room_has_sensors(hass, caplog):
    caplog.set_level(logging.INFO)
    kitchen = add_area(hass, "Kitchen")
    add_area(hass, "Bedroom")
    add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    await setup_poltergeist(hass)
    assert "Tracking 2 rooms (Kitchen, Bedroom); 1 with sensors" in messages(caplog, logging.INFO)
