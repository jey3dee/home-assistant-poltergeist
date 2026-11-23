import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_subscribe)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@websocket_api.require_admin
@callback
def ws_subscribe(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict):
    """Send the rooms now and again whenever a displayed value changes."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        connection.send_error(msg["id"], "not_loaded", "Poltergeist is not set up")
        return
    estimator = entries[0].runtime_data
    last: list = []

    @callback
    def send(force: bool = False) -> None:
        rooms = estimator.snapshot()
        signature = [(r["area_id"], r["probability"], r["expected_count"]) for r in rooms]
        if force or signature != last:
            last[:] = signature
            connection.send_message(websocket_api.event_message(msg["id"], {"rooms": rooms}))

    connection.subscriptions[msg["id"]] = estimator.add_update_listener(send)
    connection.send_result(msg["id"])
    send(force=True)
