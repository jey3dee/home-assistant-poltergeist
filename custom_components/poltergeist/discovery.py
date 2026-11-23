"""Which rooms exist and which motion sensors watch them, from the HA registries."""

from dataclasses import dataclass, field

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

MOTION_CLASSES = {BinarySensorDeviceClass.MOTION, BinarySensorDeviceClass.OCCUPANCY}


@dataclass
class RoomSpec:
    area_id: str
    name: str
    sensors: list[str] = field(default_factory=list)


def discover_rooms(hass: HomeAssistant) -> dict[str, RoomSpec]:
    """Rooms are HA areas that contain at least one enabled motion or occupancy sensor."""
    areas = ar.async_get(hass)
    devices = dr.async_get(hass)
    rooms: dict[str, RoomSpec] = {}
    for entry in er.async_get(hass).entities.values():
        if entry.domain != "binary_sensor" or entry.disabled:
            continue
        if (entry.device_class or entry.original_device_class) not in MOTION_CLASSES:
            continue
        area_id = entry.area_id
        if area_id is None and entry.device_id is not None:
            device = devices.async_get(entry.device_id)
            area_id = device.area_id if device else None
        area = areas.async_get_area(area_id) if area_id else None
        if area is None:
            continue
        room = rooms.setdefault(area.id, RoomSpec(area_id=area.id, name=area.name))
        room.sensors.append(entry.entity_id)
    return rooms
