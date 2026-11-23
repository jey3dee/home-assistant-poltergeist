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
from .const import (
    CONF_MAX_PEOPLE,
    DEFAULT_MAX_PEOPLE,
    DOMAIN,
    STORE_KEY,
    STORE_VERSION,
    UPDATE_LISTENERS_KEY,
)
from .discovery import RoomSpec, build_rooms, reconcile_assignments
from .estimator import Estimator, UpdateListeners
from .model import RoomParams

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

type PoltergeistConfigEntry = ConfigEntry[Estimator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data[UPDATE_LISTENERS_KEY] = UpdateListeners()
    websocket_api.async_register(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: PoltergeistConfigEntry) -> bool:
    listeners: UpdateListeners = hass.data[UPDATE_LISTENERS_KEY]
    listeners.reload_started()  # changes from here on are not covered by this setup

    store: Store = Store(hass, STORE_VERSION, STORE_KEY)
    data = await store.async_load() or {}
    saved = data.get("rooms", {})
    assignments = reconcile_assignments(hass, data.get("sensors", {}))
    specs = build_rooms(hass, assignments)
    _remove_stale_devices(hass, entry, specs)

    params = RoomParams(max_people=entry.options.get(CONF_MAX_PEOPLE, DEFAULT_MAX_PEOPLE))
    estimator = Estimator(
        hass, specs, store, saved, dt_util.utcnow().timestamp(), listeners, params, assignments
    )
    entry.runtime_data = estimator
    # Watch from here on: a change made while the rest of the setup awaits must not be missed.
    entry.async_on_unload(_watch_registries(hass, listeners, estimator))
    _LOGGER.info(
        "Restored the belief of %d of %d rooms from the store",
        len(saved.keys() & specs.keys()),
        len(specs),
    )
    if assignments != data.get("sensors"):
        await estimator.async_save()  # the first run, or sensors that were added or removed

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    for undo in estimator.async_start():
        entry.async_on_unload(undo)
    listeners.estimator = estimator
    listeners.notify()  # connected panels learn about the new rooms after a reload

    version = async_get_loaded_integration(hass, DOMAIN).version
    await panel.async_register_panel(hass, str(version))
    _LOGGER.info(
        "Tracking %d rooms, %d with sensors: %s",
        len(specs),
        sum(1 for s in specs.values() if s.sensors),
        ", ".join(s.name for s in specs.values()),
    )
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


def _watch_registries(hass: HomeAssistant, listeners: UpdateListeners, estimator: Estimator):
    """Reload when the rooms or the assignments Home Assistant would add change."""

    def fingerprint(rooms: dict[str, RoomSpec]) -> dict:
        return {a: (r.name, sorted(r.sensors)) for a, r in rooms.items()}

    current = fingerprint(estimator.specs())

    @callback
    def changed(_event: Event) -> None:
        # Stored assignments win, so only new sensors, deleted ones and room changes show up here.
        assignments = reconcile_assignments(hass, estimator.assignments)
        if (
            assignments != estimator.assignments
            or fingerprint(build_rooms(hass, assignments)) != current
        ):
            _LOGGER.info("Rooms or sensors changed, reloading")
            listeners.request_reload(hass)

    undo = [
        hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, changed),
        hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, changed),
        hass.bus.async_listen(ar.EVENT_AREA_REGISTRY_UPDATED, changed),
    ]

    def cancel() -> None:
        for fn in undo:
            fn()

    return cancel
