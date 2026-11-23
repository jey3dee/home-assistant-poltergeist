from collections.abc import Callable

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import PoltergeistConfigEntry
from .const import DOMAIN, HEAD_COUNT_STEP, HEARTBEAT, MIN_PUBLISH_INTERVAL, PROBABILITY_STEP
from .estimator import Room
from .publishing import Publisher


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PoltergeistConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    entities: list[SensorEntity] = []
    for area_id, room in entry.runtime_data.rooms.items():
        entities.append(
            _RoomSensor(
                area_id, room, "occupancy_probability", lambda r: r.probability, PROBABILITY_STEP
            )
        )
        entities.append(
            _RoomSensor(
                area_id, room, "expected_head_count", lambda r: r.expected_count, HEAD_COUNT_STEP
            )
        )
    async_add_entities(entities)


class _RoomSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        area_id: str,
        room: Room,
        key: str,
        value: Callable[[Room], float],
        step: float,
    ):
        self._room = room
        self._value = value
        self._publisher = Publisher(step, MIN_PUBLISH_INTERVAL, HEARTBEAT)
        self._attr_unique_id = f"{area_id}_{key}"
        self._attr_translation_key = key
        if key == "occupancy_probability":
            self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, area_id)},
            name="Occupancy",
            suggested_area=room.spec.name,
        )

    @property
    def native_value(self) -> float:
        return self._value(self._room)

    async def async_added_to_hass(self) -> None:
        self._publisher.mark(dt_util.utcnow().timestamp(), self.native_value)
        self.async_on_remove(self._room.add_listener(self._on_update))

    def _on_update(self, now: float) -> None:
        value = self.native_value
        if self._publisher.due(now, value):
            self._publisher.mark(now, value)
            self.async_write_ha_state()
