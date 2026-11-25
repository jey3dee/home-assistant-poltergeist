"""Poltergeist: probabilistic presence tracking."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import config_validation as cv
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
from .discovery import RoomSpec, apply_room_sync, build_rooms, plan_room_sync
from .estimator import Estimator, UpdateListeners
from .model import RoomParams

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)  # nothing to set in YAML

type PoltergeistConfigEntry = ConfigEntry[Estimator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data[UPDATE_LISTENERS_KEY] = UpdateListeners()
    websocket_api.async_register(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: PoltergeistConfigEntry) -> bool:
    listeners: UpdateListeners = hass.data[UPDATE_LISTENERS_KEY]
    listeners.reload_started()  # changes from here on are not covered by this setup

    apply_room_sync(hass, entry, plan_room_sync(hass, entry))
    specs = build_rooms(hass, entry)
    for spec in specs.values():
        if spec.ignored:
            _LOGGER.warning(
                "%s: not watching %s. Only motion and occupancy sensors can be used so far",
                spec.name,
                ", ".join(spec.ignored),
            )

    store: Store = Store(hass, STORE_VERSION, STORE_KEY)
    saved = (await store.async_load() or {}).get("rooms", {})
    params = RoomParams(max_people=entry.options.get(CONF_MAX_PEOPLE, DEFAULT_MAX_PEOPLE))
    estimator = Estimator(
        hass, specs, store, saved, dt_util.utcnow().timestamp(), listeners, params
    )
    entry.runtime_data = estimator
    # Watch from here on: a change made while the rest of the setup awaits must not be missed.
    entry.async_on_unload(_watch_registries(hass, entry, listeners, estimator))
    entry.async_on_unload(entry.add_update_listener(_reload_on_change))
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

    version = async_get_loaded_integration(hass, DOMAIN).version
    await panel.async_register_panel(hass, str(version))
    _LOGGER.info(
        "Tracking %d rooms, %d with sensors: %s",
        len(specs),
        sum(1 for s in specs.values() if s.sensors),
        ", ".join(s.name for s in specs.values()),
    )
    return True


async def _reload_on_change(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Options, rooms and their sensors all take effect by reloading, once per burst."""
    hass.data[UPDATE_LISTENERS_KEY].request_reload(hass)


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


def _watch_registries(
    hass: HomeAssistant, entry: ConfigEntry, listeners: UpdateListeners, estimator: Estimator
):
    """Reload when Home Assistant changes something the rooms are built from."""

    def fingerprint(rooms: dict[str, RoomSpec]) -> dict:
        return {a: (r.name, sorted(r.kinds.items())) for a, r in rooms.items()}

    current = fingerprint(estimator.specs())

    @callback
    def changed(_event: Event[Any]) -> None:
        if (
            plan_room_sync(hass, entry).changes_rooms
            or fingerprint(build_rooms(hass, entry)) != current
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
