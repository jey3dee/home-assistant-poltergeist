from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import PoltergeistConfigEntry
from .const import DOMAIN, HEAD_COUNT_STEP, HEARTBEAT, MIN_PUBLISH_INTERVAL, PROBABILITY_STEP
from .estimator import TrackedRoom
from .publishing import Publisher


@dataclass(frozen=True, kw_only=True)
class RoomSensorDescription(SensorEntityDescription):
    value_fn: Callable[[TrackedRoom], float | None]
    step: float  # smallest change worth writing, in the sensor's own unit


DESCRIPTIONS = (
    RoomSensorDescription(
        key="occupancy_probability",
        translation_key="occupancy_probability",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda room: room.probability,
        step=PROBABILITY_STEP,
    ),
    RoomSensorDescription(
        key="expected_head_count",
        translation_key="expected_head_count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda room: room.expected_count,
        step=HEAD_COUNT_STEP,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PoltergeistConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    for room in entry.runtime_data.rooms.values():
        async_add_entities(
            [RoomSensor(room, description) for description in DESCRIPTIONS],
            config_subentry_id=room.spec.subentry_id,
        )


class RoomSensor(SensorEntity):
    entity_description: RoomSensorDescription
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, room: TrackedRoom, description: RoomSensorDescription):
        self.entity_description = description
        self._room = room
        self._publisher = Publisher(description.step, MIN_PUBLISH_INTERVAL, HEARTBEAT)
        self._attr_unique_id = f"{room.spec.area_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, room.spec.area_id)},
            name="Occupancy",
            suggested_area=room.spec.name,
        )

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self._room)

    async def async_added_to_hass(self) -> None:
        self._publisher.mark(dt_util.utcnow().timestamp(), self.native_value)
        self.async_on_remove(self._room.add_listener(self._on_update))

    def _on_update(self, now: float) -> None:
        value = self.native_value
        if self._publisher.due(now, value):
            self._publisher.mark(now, value)
            self.async_write_ha_state()
