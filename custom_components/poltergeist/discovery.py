"""Rooms and their sensors.

A room is a config subentry of the integration, tied to one Home Assistant area and holding the
sensors that watch it. Rooms and sensors are proposed from Home Assistant's areas, but each only
once: what the user then deletes or removes is not proposed again.

What is stored names a sensor by its entity registry id ("sensor id" below), because the user can
rename an entity id. The estimator and the panel work with entity ids.
"""

from dataclasses import dataclass, field
from types import MappingProxyType

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_SEEN_AREAS, CONF_SEEN_SENSORS, CONF_SENSORS, SUBENTRY_ROOM
from .model import SensorKind

# The sensors the model can interpret, and how each of them counts.
SENSOR_KINDS: dict[str, SensorKind] = {
    BinarySensorDeviceClass.MOTION: SensorKind.MOTION,
    BinarySensorDeviceClass.OCCUPANCY: SensorKind.OCCUPANCY,
}


@dataclass
class RoomSpec:
    area_id: str
    name: str
    subentry_id: str | None = None
    kinds: dict[str, SensorKind] = field(default_factory=dict)  # the watched sensors
    ignored: list[str] = field(default_factory=list)  # in the room, but of a kind we cannot read

    @property
    def sensors(self) -> list[str]:
        return list(self.kinds)


@dataclass
class SyncPlan:
    """What bringing the rooms in line with Home Assistant would change."""

    add: dict[str, tuple[str, list[str]]] = field(default_factory=dict)  # area -> (title, sensors)
    remove: list[str] = field(default_factory=list)  # subentry ids
    update: dict[str, tuple[str, list[str]]] = field(
        default_factory=dict
    )  # subentry -> (title, sensors)
    seen_areas: list[str] = field(default_factory=list)
    seen_sensors: list[str] = field(default_factory=list)

    @property
    def changes_rooms(self) -> bool:
        return bool(self.add or self.remove or self.update)


def home_assistant_area(hass: HomeAssistant, entry: er.RegistryEntry) -> str | None:
    """The area Home Assistant puts an entity in: its own, else its device's."""
    area_id = entry.area_id
    if area_id is None and entry.device_id is not None:
        device = dr.async_get(hass).async_get(entry.device_id)
        area_id = device.area_id if device else None
    return area_id if area_id and ar.async_get(hass).async_get_area(area_id) else None


def sensor_kind(entry: er.RegistryEntry) -> SensorKind | None:
    """By the device class, where the user's "show as" wins over the integration's."""
    device_class = entry.device_class or entry.original_device_class
    return None if device_class is None else SENSOR_KINDS.get(device_class)


def sensor_ids(hass: HomeAssistant, entity_ids: list[str]) -> list[str]:
    """The sensor ids to store. An entity without a registry entry has none and is left out."""
    registry = er.async_get(hass)
    return [found.id for e in entity_ids if (found := registry.async_get(e)) is not None]


def sensor_entity_ids(hass: HomeAssistant, ids: list[str]) -> list[str]:
    """What the stored sensors are called now. Sensors that no longer exist are left out."""
    entities = er.async_get(hass).entities
    return [found.entity_id for i in ids if (found := entities.get_entry(i)) is not None]


def propose_sensors(hass: HomeAssistant) -> dict[str, str]:
    """Enabled motion and occupancy sensors by id, each with the area Home Assistant puts it in.

    In the order of their entity ids, which is the order they are added to a room in.
    """
    proposals: dict[str, str] = {}
    for entry in sorted(er.async_get(hass).entities.values(), key=lambda e: e.entity_id):
        if entry.domain != "binary_sensor" or entry.disabled:
            continue
        if sensor_kind(entry) is None:
            continue
        area_id = home_assistant_area(hass, entry)
        if area_id is not None:
            proposals[entry.id] = area_id
    return proposals


def room_entries(entry: ConfigEntry) -> dict[str, ConfigSubentry]:
    """The room entries by area id."""
    return {
        sub.unique_id: sub
        for sub in entry.subentries.values()
        if sub.subentry_type == SUBENTRY_ROOM and sub.unique_id
    }


def sensors_of_rooms(entry: ConfigEntry) -> set[str]:
    return {e for sub in room_entries(entry).values() for e in sub.data[CONF_SENSORS]}


def proposals_for_area(hass: HomeAssistant, entry: ConfigEntry, area_id: str) -> list[str]:
    """The sensors to start a room of this area with: its own, not watching another room yet."""
    taken = sensors_of_rooms(entry)
    return [i for i, a in propose_sensors(hass).items() if a == area_id and i not in taken]


def plan_room_sync(hass: HomeAssistant, entry: ConfigEntry) -> SyncPlan:
    areas = {a.id: a for a in ar.async_get(hass).areas.values()}
    entities = er.async_get(hass).entities
    proposals = propose_sensors(hass)
    rooms = room_entries(entry)
    seen_areas = set(entry.data.get(CONF_SEEN_AREAS, []))
    seen_sensors = set(entry.data.get(CONF_SEEN_SENSORS, []))
    plan = SyncPlan()

    # Rooms of areas that are gone go; the others keep the sensors that still exist.
    plan.remove = [sub.subentry_id for area_id, sub in rooms.items() if area_id not in areas]
    lists = {
        area_id: [i for i in sub.data[CONF_SENSORS] if entities.get_entry(i) is not None]
        for area_id, sub in rooms.items()
        if area_id in areas
    }
    assigned = {e for sensors in lists.values() for e in sensors}

    # An area that was never offered becomes a room, with the sensors it holds.
    for area in areas.values():
        if area.id not in rooms and area.id not in seen_areas:
            sensors = [
                i
                for i, a in proposals.items()
                if a == area.id and i not in assigned and i not in seen_sensors
            ]
            plan.add[area.id] = (area.name, sensors)
            lists[area.id] = sensors
            assigned.update(sensors)

    # A sensor that was never offered joins the room of its area, if that area has one.
    for sensor_id, area_id in proposals.items():
        if sensor_id not in seen_sensors and sensor_id not in assigned and area_id in lists:
            lists[area_id].append(sensor_id)
            assigned.add(sensor_id)

    for area_id, sub in rooms.items():
        if area_id in areas:
            title, sensors = areas[area_id].name, lists[area_id]
            if title != sub.title or sensors != list(sub.data[CONF_SENSORS]):
                plan.update[sub.subentry_id] = (title, sensors)

    plan.seen_areas = sorted((seen_areas | set(lists)) & set(areas))
    plan.seen_sensors = sorted(
        i for i in seen_sensors | assigned if entities.get_entry(i) is not None
    )
    return plan


def apply_room_sync(hass: HomeAssistant, entry: ConfigEntry, plan: SyncPlan) -> None:
    for area_id, (title, sensors) in plan.add.items():
        hass.config_entries.async_add_subentry(
            entry,
            ConfigSubentry(
                data=MappingProxyType({CONF_SENSORS: sensors}),
                subentry_type=SUBENTRY_ROOM,
                title=title,
                unique_id=area_id,
            ),
        )
    for subentry_id in plan.remove:
        hass.config_entries.async_remove_subentry(entry, subentry_id)
    for subentry_id, (title, sensors) in plan.update.items():
        hass.config_entries.async_update_subentry(
            entry, entry.subentries[subentry_id], title=title, data={CONF_SENSORS: sensors}
        )
    seen = {CONF_SEEN_AREAS: plan.seen_areas, CONF_SEEN_SENSORS: plan.seen_sensors}
    if any(entry.data.get(key) != value for key, value in seen.items()):
        hass.config_entries.async_update_entry(entry, data={**entry.data, **seen})


def build_rooms(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, RoomSpec]:
    """The rooms as the estimator needs them: the enabled sensors of each room entry."""
    entities = er.async_get(hass).entities
    rooms: dict[str, RoomSpec] = {}
    for area_id, sub in room_entries(entry).items():
        spec = RoomSpec(area_id, sub.title, sub.subentry_id)
        for sensor_id in sub.data[CONF_SENSORS]:
            found = entities.get_entry(sensor_id)
            if found is None or found.disabled:
                continue
            kind = sensor_kind(found)
            if kind is None:
                spec.ignored.append(found.entity_id)
            else:
                spec.kinds[found.entity_id] = kind
        rooms[area_id] = spec
    return rooms
