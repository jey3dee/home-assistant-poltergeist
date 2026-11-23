"""Poltergeist: probabilistic presence tracking."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_loaded_integration
from homeassistant.util import dt as dt_util

from . import panel, websocket_api
from .const import DOMAIN, STORE_KEY, STORE_VERSION, UPDATE_LISTENERS_KEY
from .discovery import RoomSpec, discover_rooms
from .estimator import Estimator, UpdateListeners

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

type PoltergeistConfigEntry = ConfigEntry[Estimator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data[UPDATE_LISTENERS_KEY] = UpdateListeners()
    websocket_api.async_register(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: PoltergeistConfigEntry) -> bool:
    specs = discover_rooms(hass)
    _remove_stale_devices(hass, entry, specs)

    store: Store = Store(hass, STORE_VERSION, STORE_KEY)
    saved = (await store.async_load() or {}).get("rooms", {})
    listeners: UpdateListeners = hass.data[UPDATE_LISTENERS_KEY]
    estimator = Estimator(hass, specs, store, saved, dt_util.utcnow().timestamp(), listeners)
    entry.runtime_data = estimator
    _LOGGER.info(
        "Restored the belief of %d of %d rooms from the store",
        len(saved.keys() & specs.keys()),
        len(specs),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    for undo in estimator.async_start():
        entry.async_on_unload(undo)
    listeners.estimator = estimator
    listeners.notify()  # connected panels learn about the new rooms after a reload
    entry.async_on_unload(_watch_registries(hass, entry, specs))

    version = async_get_loaded_integration(hass, DOMAIN).version
    await panel.async_register_panel(hass, str(version))
    _LOGGER.info("Tracking %d rooms: %s", len(specs), ", ".join(s.name for s in specs.values()))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PoltergeistConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        listeners: UpdateListeners = hass.data[UPDATE_LISTENERS_KEY]
        if listeners.estimator is entry.runtime_data:
            listeners.estimator = None
        await entry.runtime_data.async_save()
        panel.async_remove_panel(hass)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: PoltergeistConfigEntry) -> None:
    await Store(hass, STORE_VERSION, STORE_KEY).async_remove()


def _remove_stale_devices(
    hass: HomeAssistant, entry: ConfigEntry, specs: dict[str, RoomSpec]
) -> None:
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        area_ids = {identifier[1] for identifier in device.identifiers if identifier[0] == DOMAIN}
        if not area_ids & specs.keys():
            registry.async_remove_device(device.id)


def _watch_registries(hass: HomeAssistant, entry: ConfigEntry, specs: dict[str, RoomSpec]):
    """Reload when the rooms or their sensors change, so entities follow the house."""

    def fingerprint(rooms: dict[str, RoomSpec]) -> dict:
        return {a: (r.name, sorted(r.sensors)) for a, r in rooms.items()}

    current = fingerprint(specs)

    @callback
    def changed(_event: Event) -> None:
        if fingerprint(discover_rooms(hass)) != current:
            _LOGGER.info("Rooms or motion sensors changed, reloading")
            hass.config_entries.async_schedule_reload(entry.entry_id)

    undo = [
        hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, changed),
        hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, changed),
        hass.bus.async_listen(ar.EVENT_AREA_REGISTRY_UPDATED, changed),
    ]

    def cancel() -> None:
        for fn in undo:
            fn()

    return cancel
