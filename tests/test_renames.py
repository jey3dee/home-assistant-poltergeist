"""Renaming a sensor's entity id must not change which room it watches."""

import pytest
from homeassistant.helpers import entity_registry as er

from .helpers import (
    add_area,
    add_binary_sensor,
    room,
    room_sensors,
    set_room_sensors,
    setup_poltergeist,
)


async def rename(hass, old):
    new = f"{old}_renamed"
    er.async_get(hass).async_update_entity(old, new_entity_id=new)
    hass.states.async_remove(old)
    hass.states.async_set(new, "off")
    await hass.async_block_till_done()
    return new


@pytest.mark.parametrize("own_area", [True, False])
async def test_a_sensor_placed_by_hand_stays_in_its_room(hass, own_area):
    kitchen, hall = add_area(hass, "Kitchen"), add_area(hass, "Hall")
    pir = add_binary_sensor(hass, "pir", area_id=kitchen.id if own_area else None)
    entry = await setup_poltergeist(hass)
    set_room_sensors(hass, entry, kitchen.id, [])
    set_room_sensors(hass, entry, hall.id, [pir])
    await hass.async_block_till_done()

    new = await rename(hass, pir)

    assert room_sensors(entry, hall.id) == [new]
    assert room_sensors(entry, kitchen.id) == []
    # and the room listens to it under its new name
    before = entry.runtime_data.rooms[hall.id].probability
    hass.states.async_set(new, "on")
    await hass.async_block_till_done()
    assert entry.runtime_data.rooms[hall.id].probability > before + 50


async def test_a_removed_sensor_is_not_added_again_when_renamed(hass):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "pir", area_id=kitchen.id)
    entry = await setup_poltergeist(hass)
    set_room_sensors(hass, entry, kitchen.id, [])
    await hass.async_block_till_done()

    await rename(hass, pir)

    assert room(entry, kitchen.id) is not None
    assert room_sensors(entry, kitchen.id) == []


async def test_a_rename_while_poltergeist_is_not_loaded_is_followed(hass):
    kitchen, hall = add_area(hass, "Kitchen"), add_area(hass, "Hall")
    pir = add_binary_sensor(hass, "pir", area_id=kitchen.id)
    entry = await setup_poltergeist(hass)
    set_room_sensors(hass, entry, kitchen.id, [])
    set_room_sensors(hass, entry, hall.id, [pir])
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)

    new = await rename(hass, pir)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert room_sensors(entry, hall.id) == [new]
    assert room_sensors(entry, kitchen.id) == []
