"""Holds one belief per room, feeds it with motion events and tells listeners about changes."""

import logging
from collections.abc import Callable
from datetime import timedelta

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import SAVE_DELAY, TICK_INTERVAL
from .discovery import RoomSpec
from .model import RoomBelief, RoomParams

_LOGGER = logging.getLogger(__name__)

Listener = Callable[[float], None]


class UpdateListeners:
    """Who wants to hear that room values changed, and which estimator is current.

    Outlives the config entry, so a panel that is connected keeps receiving updates when the
    entry reloads and a new estimator takes over.
    """

    def __init__(self) -> None:
        self._listeners: list[Callable[[], None]] = []
        self.estimator: Estimator | None = None

    def add(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def notify(self) -> None:
        for listener in list(self._listeners):
            listener()


class TrackedRoom:
    def __init__(self, spec: RoomSpec, belief: RoomBelief):
        self.spec = spec
        self.belief = belief
        self._listeners: list[Listener] = []

    def add_listener(self, listener: Listener) -> CALLBACK_TYPE:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def notify(self, now: float) -> None:
        for listener in list(self._listeners):
            listener(now)

    @property
    def probability(self) -> float:
        return round(100.0 * self.belief.p_occupied, 1)

    @property
    def expected_count(self) -> float:
        return round(self.belief.expected_count, 2)


class Estimator:
    def __init__(
        self,
        hass: HomeAssistant,
        specs: dict[str, RoomSpec],
        store: Store,
        saved: dict[str, dict],
        now: float,
        update_listeners: UpdateListeners,
    ):
        self.hass = hass
        self._store = store
        self._update_listeners = update_listeners
        self._params = RoomParams()
        self.rooms: dict[str, TrackedRoom] = {}
        for area_id, spec in specs.items():
            if area_id in saved:
                belief = RoomBelief.from_snapshot(self._params, saved[area_id])
                # Nobody watched while Home Assistant was down, so that gap is not silence.
                belief.advance(belief.latest(now), observed=False)
            else:
                belief = RoomBelief(self._params, t=now)
            self.rooms[area_id] = TrackedRoom(spec, belief)
        self._room_of_sensor = {
            sensor: room for room in self.rooms.values() for sensor in room.spec.sensors
        }

    @callback
    def async_start(self) -> list[CALLBACK_TYPE]:
        """Begin listening. Returns the callbacks that undo it."""
        undo = [
            async_track_time_interval(self.hass, self._tick, timedelta(seconds=TICK_INTERVAL)),
        ]
        if self._room_of_sensor:
            undo.append(
                async_track_state_change_event(
                    self.hass, list(self._room_of_sensor), self._handle_state_change
                )
            )
        return undo

    def snapshot(self) -> list[dict]:
        return [
            {
                "area_id": area_id,
                "name": room.spec.name,
                "sensors": list(room.spec.sensors),
                "probability": room.probability,
                "expected_count": room.expected_count,
            }
            for area_id, room in self.rooms.items()
        ]

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        new, old = event.data["new_state"], event.data["old_state"]
        if new is None or new.state != "on":
            return
        if old is not None and old.state == "on":
            return  # attribute change only, the sensor did not fire again
        room = self._room_of_sensor[event.data["entity_id"]]
        # The tick may have advanced the belief a few milliseconds past the event's own timestamp.
        room.belief.observe_event(room.belief.latest(event.time_fired.timestamp()))
        _LOGGER.debug("Motion in %s from %s", room.spec.name, event.data["entity_id"])
        self._after_change(room)

    @callback
    def _tick(self, _now) -> None:
        now = dt_util.utcnow().timestamp()
        for room in self.rooms.values():
            # A sensor that is unavailable says nothing, so silence is only evidence while at
            # least one of the room's sensors is actually reporting.
            room.belief.advance(room.belief.latest(now), observed=self._is_reporting(room))
            room.notify(now)
        self._update_listeners.notify()

    def _is_reporting(self, room: TrackedRoom) -> bool:
        for entity_id in room.spec.sensors:
            state = self.hass.states.get(entity_id)
            if state is not None and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                return True
        return False

    def _after_change(self, room: TrackedRoom) -> None:
        room.notify(dt_util.utcnow().timestamp())
        self._update_listeners.notify()
        self._store.async_delay_save(self._stored_data, SAVE_DELAY)

    def _stored_data(self) -> dict:
        return {"rooms": {a: r.belief.snapshot() for a, r in self.rooms.items()}}

    async def async_save(self) -> None:
        await self._store.async_save(self._stored_data())
