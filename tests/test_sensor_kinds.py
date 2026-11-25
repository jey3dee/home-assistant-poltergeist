"""Motion sensors are triggers, occupancy sensors are states: through the whole integration."""

import logging
from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from .helpers import add_area, add_binary_sensor, setup_poltergeist

OCCUPANCY = BinarySensorDeviceClass.OCCUPANCY


async def run_for(hass, freezer, seconds, step=60):
    for _ in range(int(seconds // step)):
        freezer.tick(timedelta(seconds=step))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()


def probability(entry, area):
    return entry.runtime_data.rooms[area.id].probability


async def kitchen_with(hass, *classes, state="off"):
    kitchen = add_area(hass, "Kitchen")
    sensors = [
        add_binary_sensor(hass, f"sensor_{i}", area_id=kitchen.id, device_class=cls, state=state)
        for i, cls in enumerate(classes)
    ]
    return kitchen, sensors, await setup_poltergeist(hass)


async def switch(hass, entity_id, state):
    hass.states.async_set(entity_id, state)
    await hass.async_block_till_done()


async def test_an_occupancy_sensor_that_stays_on_keeps_the_room_occupied(hass, freezer):
    kitchen, [sensor], entry = await kitchen_with(hass, OCCUPANCY)
    await switch(hass, sensor, "on")
    await run_for(hass, freezer, 1800)
    assert 93.0 < probability(entry, kitchen) < 96.0


async def test_an_occupancy_sensor_switching_off_lowers_the_estimate_at_once(hass, freezer):
    kitchen, [sensor], entry = await kitchen_with(hass, OCCUPANCY)
    await switch(hass, sensor, "on")
    await run_for(hass, freezer, 1800)
    await switch(hass, sensor, "off")
    assert 48.0 < probability(entry, kitchen) < 56.0


async def test_a_sensor_already_on_at_setup_raises_the_estimate_over_time(hass, freezer):
    kitchen, _, entry = await kitchen_with(hass, OCCUPANCY, state="on")
    assert probability(entry, kitchen) < 25.0  # first sight is no change
    await run_for(hass, freezer, 900)
    assert probability(entry, kitchen) > 90.0


async def test_a_motion_sensor_that_stays_on_is_not_counted_as_silence(hass, freezer):
    kitchen, [sensor], entry = await kitchen_with(hass, BinarySensorDeviceClass.MOTION)
    await switch(hass, sensor, "on")
    await run_for(hass, freezer, 1800)
    assert 45.0 < probability(entry, kitchen) < 52.0


async def test_silence_counts_from_the_moment_a_motion_sensor_goes_off(hass, freezer):
    kitchen, [sensor], entry = await kitchen_with(hass, BinarySensorDeviceClass.MOTION)
    await switch(hass, sensor, "on")
    freezer.tick(timedelta(seconds=600))  # no tick in between
    await switch(hass, sensor, "off")
    held = probability(entry, kitchen)
    assert held > 70.0  # the ten minutes on were not silence
    await run_for(hass, freezer, 900)
    assert probability(entry, kitchen) < 30.0


async def test_going_unavailable_takes_effect_at_that_moment(hass, freezer):
    kitchen, [sensor], entry = await kitchen_with(hass, BinarySensorDeviceClass.MOTION)
    await switch(hass, sensor, "on")
    await switch(hass, sensor, "off")
    freezer.tick(timedelta(seconds=900))  # quiet and heard, with no tick in between
    await switch(hass, sensor, "unavailable")
    assert probability(entry, kitchen) < 30.0


async def test_coming_back_as_on_is_not_a_new_trigger(hass, freezer):
    kitchen, [sensor], entry = await kitchen_with(hass, BinarySensorDeviceClass.MOTION)
    await switch(hass, sensor, "unavailable")
    await switch(hass, sensor, "on")
    assert probability(entry, kitchen) < 25.0


async def test_only_motion_and_occupancy_sensors_are_watched(hass, freezer, caplog):
    kitchen = add_area(hass, "Kitchen")
    door = add_binary_sensor(
        hass, "front_door", area_id=kitchen.id, device_class=BinarySensorDeviceClass.DOOR
    )
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    entry = await setup_poltergeist(hass)
    sub = next(iter(entry.subentries.values()))
    caplog.set_level(logging.WARNING)
    hass.config_entries.async_update_subentry(entry, sub, data={"sensors": [pir, door]})
    await hass.async_block_till_done()
    assert entry.runtime_data.rooms[kitchen.id].spec.sensors == [pir]
    assert door in caplog.text and "Kitchen" in caplog.text
    before = probability(entry, kitchen)
    await switch(hass, door, "on")
    assert probability(entry, kitchen) == before


async def test_changing_what_a_sensor_is_shown_as_changes_how_it_counts(hass, freezer):
    kitchen, [sensor], entry = await kitchen_with(hass, BinarySensorDeviceClass.MOTION)
    er.async_get(hass).async_update_entity(sensor, device_class=OCCUPANCY)
    await hass.async_block_till_done()
    await switch(hass, sensor, "on")
    await run_for(hass, freezer, 1800)
    assert probability(entry, kitchen) > 90.0  # a motion sensor would be near 48 by now
