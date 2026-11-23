from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.poltergeist.const import DOMAIN


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
