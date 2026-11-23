"""Rooms and sensor assignments, from the Home Assistant registries.

A room is a Home Assistant area. Which sensors watch it is an assignment: proposed from the
sensor's own area the first time the sensor is seen, owned by the user after that.
"""

from dataclasses import dataclass, field

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

MOTION_CLASSES = {BinarySensorDeviceClass.MOTION, BinarySensorDeviceClass.OCCUPANCY}

# entity_id -> area_id of the room it watches, or None when it is deliberately in no room
Assignments = dict[str, str | None]


@dataclass
class RoomSpec:
    area_id: str
    name: str
    sensors: list[str] = field(default_factory=list)


def home_assistant_area(hass: HomeAssistant, entry: er.RegistryEntry) -> str | None:
    """The area Home Assistant puts an entity in: its own, else its device's."""
    area_id = entry.area_id
    if area_id is None and entry.device_id is not None:
        device = dr.async_get(hass).async_get(entry.device_id)
        area_id = device.area_id if device else None
    return area_id if area_id and ar.async_get(hass).async_get_area(area_id) else None


def device_class_of(entry: er.RegistryEntry) -> str | None:
    return entry.device_class or entry.original_device_class


def propose_assignments(hass: HomeAssistant) -> Assignments:
    """Enabled motion and occupancy sensors, each in the area Home Assistant puts it in."""
    proposals: Assignments = {}
    for entry in er.async_get(hass).entities.values():
        if entry.domain != "binary_sensor" or entry.disabled:
            continue
        if device_class_of(entry) not in MOTION_CLASSES:
            continue
        area_id = home_assistant_area(hass, entry)
        if area_id is not None:
            proposals[entry.entity_id] = area_id
    return proposals


def reconcile_assignments(hass: HomeAssistant, stored: Assignments) -> Assignments:
    """The stored assignments, plus proposals for new sensors, minus what no longer exists.

    A stored entry always wins over what Home Assistant says now: moving a sensor to another
    area in Home Assistant does not move it here.
    """
    entities = er.async_get(hass).entities
    areas = ar.async_get(hass)
    result: Assignments = {}
    for entity_id, area_id in stored.items():
        if entity_id not in entities:
            continue
        result[entity_id] = area_id if area_id and areas.async_get_area(area_id) else None
    for entity_id, area_id in propose_assignments(hass).items():
        result.setdefault(entity_id, area_id)
    return result


def build_rooms(hass: HomeAssistant, assignments: Assignments) -> dict[str, RoomSpec]:
    """Every area is a room, with the enabled sensors assigned to it."""
    entities = er.async_get(hass).entities
    rooms = {
        area.id: RoomSpec(area_id=area.id, name=area.name)
        for area in ar.async_get(hass).areas.values()
    }
    for entity_id, area_id in assignments.items():
        entry = entities.get(entity_id)
        if area_id in rooms and entry is not None and not entry.disabled:
            rooms[area_id].sensors.append(entity_id)
    return rooms
