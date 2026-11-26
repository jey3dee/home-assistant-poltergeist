"""Adding a room and choosing its sensors, through Home Assistant's own flows."""

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import area_registry as ar

from custom_components.poltergeist.const import DOMAIN, SUBENTRY_ROOM

from .helpers import add_area, add_binary_sensor, room, room_sensors, setup_poltergeist


async def start_add(hass, entry):
    return await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_ROOM), context={"source": config_entries.SOURCE_USER}
    )


async def start_configure(hass, entry, area_id):
    return await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_ROOM),
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "subentry_id": room(entry, area_id).subentry_id,
        },
    )


async def test_add_offers_only_areas_without_a_room(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    entry = await setup_poltergeist(hass)
    hass.config_entries.async_remove_subentry(entry, room(entry, hall.id).subentry_id)
    await hass.async_block_till_done()
    result = await start_add(hass, entry)
    assert result["type"] is FlowResultType.FORM
    options = result["data_schema"].schema["area"].config["options"]
    assert options == [{"value": hall.id, "label": "Hall"}]
    assert kitchen.id not in [o["value"] for o in options]


async def test_add_brings_a_deleted_room_back_with_its_proposed_sensors(hass):
    hall = add_area(hass, "Hall")
    pir = add_binary_sensor(hass, "hall_pir", area_id=hall.id)
    entry = await setup_poltergeist(hass)
    hass.config_entries.async_remove_subentry(entry, room(entry, hall.id).subentry_id)
    await hass.async_block_till_done()
    assert room(entry, hall.id) is None

    result = await start_add(hass, entry)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"area": hall.id}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert room(entry, hall.id).title == "Hall"
    assert room_sensors(entry, hall.id) == [pir]
    assert entry.runtime_data.rooms[hall.id].spec.sensors == [pir]


async def test_add_does_not_take_sensors_that_watch_another_room(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    pir = add_binary_sensor(hass, "pir", area_id=hall.id)
    entry = await setup_poltergeist(hass)
    hass.config_entries.async_remove_subentry(entry, room(entry, hall.id).subentry_id)
    await hass.async_block_till_done()
    result = await start_configure(hass, entry, kitchen.id)
    await hass.config_entries.subentries.async_configure(result["flow_id"], {"sensors": [pir]})
    await hass.async_block_till_done()
    assert room_sensors(entry, kitchen.id) == [pir]

    result = await start_add(hass, entry)
    await hass.config_entries.subentries.async_configure(result["flow_id"], {"area": hall.id})
    await hass.async_block_till_done()
    assert room_sensors(entry, hall.id) == []  # it already watches the kitchen


async def test_add_says_so_when_every_area_is_a_room(hass):
    add_area(hass, "Kitchen")
    entry = await setup_poltergeist(hass)
    result = await start_add(hass, entry)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "all_areas_are_rooms"


async def test_configure_shows_the_rooms_sensors_and_offers_motion_and_occupancy_only(hass):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    entry = await setup_poltergeist(hass)
    result = await start_configure(hass, entry, kitchen.id)
    assert result["type"] is FlowResultType.FORM
    schema = result["data_schema"]
    assert schema({})["sensors"] == [pir]
    [offered] = schema.schema["sensors"].config["filter"]
    assert offered["domain"] == ["binary_sensor"]
    assert sorted(offered["device_class"]) == ["motion", "occupancy"]
    assert result["description_placeholders"] == {"room": "Kitchen"}


async def test_configure_saves_the_sensors_and_the_room_watches_them_after_the_reload(hass):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    radar = add_binary_sensor(hass, "radar", device_class="occupancy")
    entry = await setup_poltergeist(hass)
    result = await start_configure(hass, entry, kitchen.id)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"sensors": [pir, radar]}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert room_sensors(entry, kitchen.id) == [pir, radar]
    assert entry.runtime_data.rooms[kitchen.id].spec.sensors == [pir, radar]


async def test_choosing_a_sensor_of_another_room_moves_it(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    entry = await setup_poltergeist(hass)
    result = await start_configure(hass, entry, hall.id)
    await hass.config_entries.subentries.async_configure(result["flow_id"], {"sensors": [pir]})
    await hass.async_block_till_done()
    assert room_sensors(entry, hall.id) == [pir]
    assert room_sensors(entry, kitchen.id) == []
    assert hass.states.get("sensor.kitchen_occupancy_probability").state == "unknown"


async def test_moving_a_sensor_between_rooms_causes_at_most_two_reloads(hass):
    from unittest.mock import patch

    import custom_components.poltergeist as integration

    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    entry = await setup_poltergeist(hass)
    real = integration.Estimator
    built = []
    with patch.object(
        integration, "Estimator", side_effect=lambda *a, **k: built.append(1) or real(*a, **k)
    ):
        result = await start_configure(hass, entry, hall.id)
        await hass.config_entries.subentries.async_configure(result["flow_id"], {"sensors": [pir]})
        await hass.async_block_till_done()
    # one change moves a sensor between two rooms; the test harness finishes a reload inside the
    # call that asks for it, so what counts is that it is not more than one per room entry
    assert 1 <= len(built) <= 2
    assert DOMAIN in hass.config.components


async def test_add_ends_cleanly_if_the_area_is_deleted_while_the_form_is_open(hass):
    hall = add_area(hass, "Hall")
    attic = add_area(hass, "Attic")  # still free afterwards, so the form has something to offer
    entry = await setup_poltergeist(hass)
    for area in (hall, attic):
        hass.config_entries.async_remove_subentry(entry, room(entry, area.id).subentry_id)
        await hass.async_block_till_done()
    result = await start_add(hass, entry)

    ar.async_get(hass).async_delete(hall.id)
    await hass.async_block_till_done()
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"area": hall.id}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "area_gone"
