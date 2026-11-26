"""The rooms of the integration: one room entry per area, filled with proposals, then the user's."""

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er

from custom_components.poltergeist.const import CONF_SEEN_AREAS, CONF_SEEN_SENSORS

from .helpers import (
    add_area,
    add_binary_sensor,
    add_entry,
    add_room,
    room,
    room_sensors,
    stored,
    sync,
)


async def test_the_first_sync_makes_a_room_of_every_area_with_proposed_sensors(hass):
    kitchen = add_area(hass, "Kitchen")
    bedroom = add_area(hass, "Bedroom")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    add_binary_sensor(hass, "front_door", area_id=kitchen.id, device_class="door")
    entry = add_entry(hass)
    sync(hass, entry)
    assert room_sensors(entry, kitchen.id) == [pir]
    assert room_sensors(entry, bedroom.id) == []
    assert room(entry, kitchen.id).title == "Kitchen"
    assert set(entry.data[CONF_SEEN_AREAS]) == {kitchen.id, bedroom.id}
    assert entry.data[CONF_SEEN_SENSORS] == stored(hass, [pir])


async def test_a_second_sync_changes_nothing(hass):
    kitchen = add_area(hass, "Kitchen")
    add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    entry = add_entry(hass)
    sync(hass, entry)
    plan = sync(hass, entry)
    assert not plan.changes_rooms


async def test_a_new_area_gets_a_room(hass):
    entry = add_entry(hass)
    sync(hass, entry)
    hall = add_area(hass, "Hall")
    pir = add_binary_sensor(hass, "hall_pir", area_id=hall.id)
    sync(hass, entry)
    assert room_sensors(entry, hall.id) == [pir]


async def test_a_deleted_area_takes_its_room_with_it(hass):
    kitchen = add_area(hass, "Kitchen")
    entry = add_entry(hass)
    sync(hass, entry)
    ar.async_get(hass).async_delete(kitchen.id)
    sync(hass, entry)
    assert room(entry, kitchen.id) is None
    assert kitchen.id not in entry.data[CONF_SEEN_AREAS]


async def test_a_renamed_area_renames_its_room(hass):
    kitchen = add_area(hass, "Kitchen")
    entry = add_entry(hass)
    sync(hass, entry)
    ar.async_get(hass).async_update(kitchen.id, name="Cooking")
    sync(hass, entry)
    assert room(entry, kitchen.id).title == "Cooking"


async def test_a_room_the_user_deleted_does_not_come_back(hass):
    kitchen = add_area(hass, "Kitchen")
    add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    entry = add_entry(hass)
    sync(hass, entry)
    hass.config_entries.async_remove_subentry(entry, room(entry, kitchen.id).subentry_id)
    sync(hass, entry)
    assert room(entry, kitchen.id) is None


async def test_a_new_motion_sensor_joins_the_room_of_its_area(hass):
    kitchen = add_area(hass, "Kitchen")
    entry = add_entry(hass)
    sync(hass, entry)
    pir = add_binary_sensor(hass, "late_pir", area_id=kitchen.id)
    sync(hass, entry)
    assert room_sensors(entry, kitchen.id) == [pir]


async def test_a_sensor_the_user_removed_is_not_proposed_again(hass):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    entry = add_entry(hass)
    sync(hass, entry)
    sub = room(entry, kitchen.id)
    hass.config_entries.async_update_subentry(entry, sub, data={"sensors": []})
    sync(hass, entry)
    assert room_sensors(entry, kitchen.id) == []
    assert stored(hass, [pir])[0] in entry.data[CONF_SEEN_SENSORS]


async def test_a_sensor_in_another_room_stays_there_when_its_home_assistant_area_changes(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    pir = add_binary_sensor(hass, "pir", area_id=kitchen.id)
    entry = add_entry(hass)
    sync(hass, entry)
    er.async_get(hass).async_update_entity(pir, area_id=hall.id)  # Home Assistant now says Hall
    sync(hass, entry)
    assert room_sensors(entry, kitchen.id) == [pir]
    assert room_sensors(entry, hall.id) == []


async def test_a_deleted_sensor_is_dropped_from_its_room(hass):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    entry = add_entry(hass)
    sync(hass, entry)
    [pir_id] = stored(hass, [pir])
    er.async_get(hass).async_remove(pir)
    sync(hass, entry)
    assert room_sensors(entry, kitchen.id) == []
    assert pir_id not in entry.data[CONF_SEEN_SENSORS]


async def test_new_sensors_of_a_deleted_room_are_not_added_anywhere(hass):
    kitchen = add_area(hass, "Kitchen")
    entry = add_entry(hass)
    sync(hass, entry)
    hass.config_entries.async_remove_subentry(entry, room(entry, kitchen.id).subentry_id)
    sync(hass, entry)
    add_binary_sensor(hass, "late_pir", area_id=kitchen.id)
    sync(hass, entry)
    assert room(entry, kitchen.id) is None


async def test_a_sensor_is_proposed_for_one_room_only(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    pir = add_binary_sensor(hass, "pir", area_id=hall.id)
    entry = add_entry(hass)
    add_room(hass, entry, kitchen, [pir])  # the user already put it in the kitchen
    sync(hass, entry)
    assert room_sensors(entry, kitchen.id) == [pir]
    assert room_sensors(entry, hall.id) == []
