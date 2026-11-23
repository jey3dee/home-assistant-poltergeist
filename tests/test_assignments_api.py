import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er

from custom_components.poltergeist.const import DOMAIN

from .helpers import add_area, add_binary_sensor, setup_poltergeist


async def call(client, type_, **payload):
    client.last_id = getattr(client, "last_id", 0) + 1  # Home Assistant refuses reused ids
    await client.send_json({"id": client.last_id, "type": f"{DOMAIN}/{type_}", **payload})
    return await client.receive_json()


async def house(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    bedroom = add_area(hass, "Bedroom")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    door = add_binary_sensor(
        hass, "front_door", area_id=hall.id, device_class=BinarySensorDeviceClass.DOOR
    )
    entry = await setup_poltergeist(hass)
    return entry, kitchen, hall, bedroom, pir, door


async def test_sensors_lists_rooms_assignments_and_candidates(hass, hass_ws_client):
    _, kitchen, hall, bedroom, pir, door = await house(hass)
    client = await hass_ws_client(hass)
    result = (await call(client, "sensors"))["result"]
    assert {r["area_id"]: r["name"] for r in result["rooms"]} == {
        kitchen.id: "Kitchen",
        hall.id: "Hall",
        bedroom.id: "Bedroom",
    }
    assert result["sensors"] == [
        {
            "entity_id": pir,
            "name": "kitchen_pir",
            "device_class": "motion",
            "ha_area_id": kitchen.id,
            "room": kitchen.id,
        }
    ]
    assert result["candidates"] == [
        {"entity_id": door, "name": "front_door", "ha_area_id": hall.id}
    ]


async def test_assigning_moves_the_sensor_and_survives_a_restart(hass, hass_ws_client):
    entry, kitchen, hall, bedroom, pir, _ = await house(hass)
    client = await hass_ws_client(hass)
    response = await call(client, "assign", entity_id=pir, area_id=bedroom.id)
    assert response["success"]
    await hass.async_block_till_done()
    rooms = entry.runtime_data.rooms
    assert rooms[bedroom.id].spec.sensors == [pir]
    assert rooms[kitchen.id].spec.sensors == []

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.rooms[bedroom.id].spec.sensors == [pir]


async def test_an_edit_wins_over_a_later_change_of_the_home_assistant_area(hass, hass_ws_client):
    entry, kitchen, hall, bedroom, pir, _ = await house(hass)
    client = await hass_ws_client(hass)
    await call(client, "assign", entity_id=pir, area_id=bedroom.id)
    await hass.async_block_till_done()
    er.async_get(hass).async_update_entity(pir, area_id=hall.id)  # Home Assistant now says Hall
    await hass.async_block_till_done()
    assert entry.runtime_data.rooms[bedroom.id].spec.sensors == [pir]
    listing = (await call(client, "sensors"))["result"]["sensors"][0]
    assert (listing["ha_area_id"], listing["room"]) == (hall.id, bedroom.id)


async def test_a_sensor_can_be_taken_out_of_every_room(hass, hass_ws_client):
    entry, kitchen, *_, pir, _ = await house(hass)
    client = await hass_ws_client(hass)
    assert (await call(client, "assign", entity_id=pir, area_id=None))["success"]
    await hass.async_block_till_done()
    assert entry.runtime_data.rooms[kitchen.id].spec.sensors == []
    assert hass.states.get("sensor.kitchen_occupancy_probability").state == "unknown"
    listing = (await call(client, "sensors"))["result"]["sensors"][0]
    assert listing["room"] is None


async def test_any_binary_sensor_can_be_added_to_a_room(hass, hass_ws_client):
    entry, kitchen, hall, bedroom, pir, door = await house(hass)
    client = await hass_ws_client(hass)
    assert (await call(client, "assign", entity_id=door, area_id=hall.id))["success"]
    await hass.async_block_till_done()
    assert entry.runtime_data.rooms[hall.id].spec.sensors == [door]
    result = (await call(client, "sensors"))["result"]
    assert door in [s["entity_id"] for s in result["sensors"]]
    assert result["candidates"] == []


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"entity_id": "binary_sensor.ghost", "area_id": None}, "not_found"),
        ({"entity_id": "light.kitchen", "area_id": None}, "invalid_format"),
        ({"entity_id": "{pir}", "area_id": "no_such_area"}, "not_found"),
    ],
)
async def test_assign_refuses_bad_input_and_changes_nothing(hass, hass_ws_client, payload, code):
    entry, kitchen, hall, bedroom, pir, _ = await house(hass)
    er.async_get(hass).async_get_or_create(
        "light", "test", "kitchen", suggested_object_id="kitchen"
    )
    payload = {k: (pir if v == "{pir}" else v) for k, v in payload.items()}
    client = await hass_ws_client(hass)
    response = await call(client, "assign", **payload)
    assert not response["success"]
    assert response["error"]["code"] == code
    assert entry.runtime_data.assignments == {pir: kitchen.id}


async def test_restore_proposals_resets_every_edit(hass, hass_ws_client):
    entry, kitchen, hall, bedroom, pir, door = await house(hass)
    client = await hass_ws_client(hass)
    await call(client, "assign", entity_id=pir, area_id=bedroom.id)
    await call(client, "assign", entity_id=door, area_id=hall.id)
    await hass.async_block_till_done()
    assert (await call(client, "restore_proposals"))["success"]
    await hass.async_block_till_done()
    assert entry.runtime_data.assignments == {pir: kitchen.id}


@pytest.mark.parametrize(
    ("type_", "payload"),
    [
        ("sensors", {}),
        ("assign", {"entity_id": "binary_sensor.x", "area_id": None}),
        ("restore_proposals", {}),
    ],
)
async def test_the_commands_are_for_admins_only(
    hass, hass_ws_client, hass_read_only_access_token, type_, payload
):
    await setup_poltergeist(hass)
    client = await hass_ws_client(hass, hass_read_only_access_token)
    response = await call(client, type_, **payload)
    assert not response["success"]
    assert response["error"]["code"] == "unauthorized"


async def test_edits_are_refused_while_the_entry_is_not_loaded(hass, hass_ws_client):
    entry, *_ = await house(hass)
    client = await hass_ws_client(hass)
    await hass.config_entries.async_unload(entry.entry_id)
    response = await call(client, "assign", entity_id="binary_sensor.x", area_id=None)
    assert not response["success"]
    assert response["error"]["code"] == "not_loaded"
    assert ar.async_get(hass).async_get_area_by_name("Kitchen")  # nothing else was touched
