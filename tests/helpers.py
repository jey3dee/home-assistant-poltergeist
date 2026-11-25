from types import MappingProxyType

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant, async_get_hass
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.poltergeist.const import CONF_SENSORS, DOMAIN, SUBENTRY_ROOM
from custom_components.poltergeist.discovery import (
    apply_room_sync,
    plan_room_sync,
    sensor_entity_ids,
    sensor_ids,
)


def add_area(hass: HomeAssistant, name: str):
    return ar.async_get(hass).async_create(name)


def add_binary_sensor(
    hass: HomeAssistant,
    object_id: str,
    *,
    area_id: str | None = None,
    device_area_id: str | None = None,
    device_class=BinarySensorDeviceClass.MOTION,
    state: str = "off",
    disabled: bool = False,
) -> str:
    """Register a binary_sensor of another integration, optionally placed in an area."""
    registry = er.async_get(hass)
    device_id = None
    config_entry = MockConfigEntry(domain="test")
    config_entry.add_to_hass(hass)
    if device_area_id is not None:
        device = dr.async_get(hass).async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers={("test", object_id)},
        )
        dr.async_get(hass).async_update_device(device.id, area_id=device_area_id)
        device_id = device.id
    entry = registry.async_get_or_create(
        "binary_sensor",
        "test",
        object_id,
        suggested_object_id=object_id,
        original_name=object_id,
        config_entry=config_entry,
        device_id=device_id,
        original_device_class=device_class,
        disabled_by=er.RegistryEntryDisabler.USER if disabled else None,
    )
    if area_id is not None:
        registry.async_update_entity(entry.entity_id, area_id=area_id)
    if not disabled:
        hass.states.async_set(entry.entity_id, state)
    return entry.entity_id


async def setup_poltergeist(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Poltergeist")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def add_entry(hass: HomeAssistant, **kwargs) -> MockConfigEntry:
    """A Poltergeist entry that is not set up, to test the room logic on its own."""
    entry = MockConfigEntry(domain=DOMAIN, title="Poltergeist", **kwargs)
    entry.add_to_hass(hass)
    return entry


def sync(hass: HomeAssistant, entry: MockConfigEntry):
    plan = plan_room_sync(hass, entry)
    apply_room_sync(hass, entry, plan)
    return plan


def room(entry: MockConfigEntry, area_id: str) -> ConfigSubentry | None:
    return next((s for s in entry.subentries.values() if s.unique_id == area_id), None)


def room_sensors(entry: MockConfigEntry, area_id: str) -> list[str] | None:
    found = room(entry, area_id)
    return None if found is None else sensor_entity_ids(async_get_hass(), found.data[CONF_SENSORS])


def stored(hass: HomeAssistant, entity_ids) -> list[str]:
    """As a room stores them. A name without a registry entry is kept, to stand for a lost one."""
    return [next(iter(sensor_ids(hass, [e])), e) for e in entity_ids]


def set_room_sensors(hass: HomeAssistant, entry: MockConfigEntry, area_id: str, sensors):
    """What the user's choice in the room's screen stores."""
    hass.config_entries.async_update_subentry(
        entry, room(entry, area_id), data={CONF_SENSORS: stored(hass, sensors)}
    )


def add_room(hass: HomeAssistant, entry: MockConfigEntry, area, sensors=()):
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data=MappingProxyType({CONF_SENSORS: stored(hass, sensors)}),
            subentry_type=SUBENTRY_ROOM,
            title=area.name,
            unique_id=area.id,
        ),
    )
