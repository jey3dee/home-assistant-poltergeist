import asyncio

from homeassistant.helpers import area_registry as ar

from custom_components.poltergeist.const import DOMAIN

from .helpers import add_area, add_binary_sensor, setup_poltergeist


async def test_panel_is_registered_for_admins_and_removed_on_unload(hass):
    entry = await setup_poltergeist(hass)
    panel = hass.data["frontend_panels"][DOMAIN]
    assert panel.require_admin is True
    assert panel.sidebar_title == "Poltergeist"
    await hass.config_entries.async_unload(entry.entry_id)
    assert DOMAIN not in hass.data["frontend_panels"]


async def test_subscription_sends_the_rooms_and_then_updates(hass, hass_ws_client):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    await setup_poltergeist(hass)
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "poltergeist/subscribe"})
    assert (await client.receive_json())["success"]
    first = (await client.receive_json())["event"]
    assert first["rooms"][0]["area_id"] == kitchen.id
    assert first["rooms"][0]["name"] == "Kitchen"
    assert first["rooms"][0]["sensors"] == [pir]
    low = first["rooms"][0]["probability"]

    hass.states.async_set(pir, "on")
    await hass.async_block_till_done()
    update = (await client.receive_json())["event"]
    assert update["rooms"][0]["probability"] > 99.0 > low


async def test_subscription_is_refused_for_non_admins(
    hass, hass_ws_client, hass_read_only_access_token
):
    await setup_poltergeist(hass)
    client = await hass_ws_client(hass, hass_read_only_access_token)
    await client.send_json({"id": 1, "type": "poltergeist/subscribe"})
    response = await client.receive_json()
    assert not response["success"]
    assert response["error"]["code"] == "unauthorized"


async def _next_event_where(client, condition):
    """The next pushed event that satisfies the condition; fails if none arrives in time."""
    async with asyncio.timeout(3):  # without the fix nothing ever arrives
        while True:
            event = (await client.receive_json())["event"]
            if condition(event):
                return event


async def test_subscription_survives_a_reload_of_the_entry(hass, hass_ws_client):
    kitchen = add_area(hass, "Kitchen")
    add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    await setup_poltergeist(hass)
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "poltergeist/subscribe"})
    await client.receive_json()
    assert len((await client.receive_json())["event"]["rooms"]) == 1

    hall = add_area(hass, "Hall")  # the entry reloads for the new room
    hall_pir = add_binary_sensor(hass, "hall_pir", area_id=hall.id)
    await hass.async_block_till_done()
    update = await _next_event_where(
        client,
        lambda e: any(r["name"] == "Hall" and r["probability"] is not None for r in e["rooms"]),
    )
    assert sorted(r["name"] for r in update["rooms"]) == ["Hall", "Kitchen"]

    hass.states.async_set(hall_pir, "on")  # and the new estimator keeps feeding it
    await hass.async_block_till_done()
    update = await _next_event_where(
        client,
        lambda e: any(r["name"] == "Hall" and (r["probability"] or 0) > 99.0 for r in e["rooms"]),
    )
    assert update


async def test_an_open_panel_learns_a_rooms_new_name(hass, hass_ws_client):
    bedroom = add_area(hass, "Bedroom")  # no sensors: no value will ever change
    await setup_poltergeist(hass)
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "poltergeist/subscribe"})
    await client.receive_json()
    await client.receive_json()

    ar.async_get(hass).async_update(bedroom.id, name="Study")
    await hass.async_block_till_done()
    await _next_event_where(client, lambda e: [r["name"] for r in e["rooms"]] == ["Study"])
