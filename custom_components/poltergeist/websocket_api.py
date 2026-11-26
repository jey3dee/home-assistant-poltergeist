import probatio as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, UPDATE_LISTENERS_KEY


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_subscribe)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@websocket_api.require_admin
@callback
def ws_subscribe(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict):
    """Send the rooms now and again whenever anything about them changes."""
    listeners = hass.data[UPDATE_LISTENERS_KEY]
    if listeners.estimator is None:
        connection.send_error(msg["id"], "not_loaded", "Poltergeist is not set up")
        return
    last: list = []

    @callback
    def send(force: bool = False) -> None:
        # The entry may have been reloaded since the subscription started, so ask for the
        # estimator that is current now.
        if listeners.estimator is None:
            return
        rooms = listeners.estimator.snapshot()
        if force or rooms != last:
            last[:] = rooms
            connection.send_message(websocket_api.event_message(msg["id"], {"rooms": rooms}))

    connection.subscriptions[msg["id"]] = listeners.add(send)
    connection.send_result(msg["id"])
    send(force=True)
