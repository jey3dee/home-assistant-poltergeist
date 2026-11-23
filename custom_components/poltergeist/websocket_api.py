import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, UPDATE_LISTENERS_KEY
from .discovery import device_class_of, home_assistant_area, reconcile_assignments
from .estimator import Estimator


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_sensors)
    websocket_api.async_register_command(hass, ws_assign)
    websocket_api.async_register_command(hass, ws_restore_proposals)


def _loaded_estimator(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> Estimator | None:
    estimator = hass.data[UPDATE_LISTENERS_KEY].estimator
    if estimator is None:
        connection.send_error(msg["id"], "not_loaded", "Poltergeist is not set up")
    return estimator


def _name(entry: er.RegistryEntry) -> str:
    return entry.name or entry.original_name or entry.entity_id


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/sensors"})
@websocket_api.require_admin
@callback
def ws_sensors(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict):
    """Every room, the sensors with their assignment, and the sensors that could be added."""
    if (estimator := _loaded_estimator(hass, connection, msg)) is None:
        return
    entities = er.async_get(hass).entities
    assigned = estimator.assignments
    connection.send_result(
        msg["id"],
        {
            "rooms": [{"area_id": a.id, "name": a.name} for a in ar.async_get(hass).areas.values()],
            "sensors": [
                {
                    "entity_id": entity_id,
                    "name": _name(entities[entity_id]),
                    "device_class": device_class_of(entities[entity_id]),
                    "ha_area_id": home_assistant_area(hass, entities[entity_id]),
                    "room": assigned[entity_id],
                }
                for entity_id in sorted(assigned)
            ],
            "candidates": [
                {
                    "entity_id": e.entity_id,
                    "name": _name(e),
                    "ha_area_id": home_assistant_area(hass, e),
                }
                for e in sorted(entities.values(), key=lambda e: e.entity_id)
                if e.domain == "binary_sensor" and not e.disabled and e.entity_id not in assigned
            ],
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/assign",
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("area_id"): vol.Any(None, str),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_assign(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict):
    """Put a sensor in a room, or in no room (area_id null)."""
    if (estimator := _loaded_estimator(hass, connection, msg)) is None:
        return
    entity_id, area_id = msg["entity_id"], msg["area_id"]
    if not entity_id.startswith("binary_sensor."):
        connection.send_error(msg["id"], "invalid_format", "Only binary sensors can be assigned")
        return
    if er.async_get(hass).async_get(entity_id) is None:
        connection.send_error(msg["id"], "not_found", f"{entity_id} does not exist")
        return
    if area_id is not None and ar.async_get(hass).async_get_area(area_id) is None:
        connection.send_error(msg["id"], "not_found", f"Area {area_id} does not exist")
        return
    estimator.assignments[entity_id] = area_id
    await estimator.async_save()
    hass.data[UPDATE_LISTENERS_KEY].request_reload(hass)
    connection.send_result(msg["id"])


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/restore_proposals"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_restore_proposals(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
):
    """Forget every edit: the assignments become what Home Assistant's areas propose."""
    if (estimator := _loaded_estimator(hass, connection, msg)) is None:
        return
    estimator.assignments = reconcile_assignments(hass, {})
    await estimator.async_save()
    hass.data[UPDATE_LISTENERS_KEY].request_reload(hass)
    connection.send_result(msg["id"])


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@websocket_api.require_admin
@callback
def ws_subscribe(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict):
    """Send the rooms now and again whenever a displayed value changes."""
    listeners = hass.data[UPDATE_LISTENERS_KEY]
    if _loaded_estimator(hass, connection, msg) is None:
        return
    last: list = []

    @callback
    def send(force: bool = False) -> None:
        # The entry may have been reloaded since the subscription started, so ask for the
        # estimator that is current now.
        if listeners.estimator is None:
            return
        rooms = listeners.estimator.snapshot()
        signature = [(r["area_id"], r["probability"], r["expected_count"]) for r in rooms]
        if force or signature != last:
            last[:] = signature
            connection.send_message(websocket_api.event_message(msg["id"], {"rooms": rooms}))

    connection.subscriptions[msg["id"]] = listeners.add(send)
    connection.send_result(msg["id"])
    send(force=True)
