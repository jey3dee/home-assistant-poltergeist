"""Holds one belief per room, feeds it with what its sensors do and tells listeners about it."""

import logging
from collections.abc import Callable
from datetime import timedelta

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SAVE_DELAY, TICK_INTERVAL
from .discovery import RoomSpec
from .model import Reading, RoomBelief, RoomParams

_LOGGER = logging.getLogger(__name__)

Listener = Callable[[float], None]

_VALUES = {STATE_ON: True, STATE_OFF: False}


def _value(state: State | None) -> bool | None:
    """On, off, or None when the sensor is not heard (missing, unavailable, unknown)."""
    return None if state is None else _VALUES.get(state.state)


class UpdateListeners:
    """Who wants to hear that room values changed, and which estimator is current.

    Outlives the config entry, so a panel that is connected keeps receiving updates when the
    entry reloads and a new estimator takes over.
    """

    def __init__(self) -> None:
        self._listeners: list[Callable[[], None]] = []
        self.estimator: Estimator | None = None
        self._reload_requested = False

    def request_reload(self, hass: HomeAssistant) -> None:
        """Reload the entry once, however many changes arrive before it has started."""
        if self._reload_requested:
            return
        self._reload_requested = True
        for entry in hass.config_entries.async_entries(DOMAIN):
            hass.config_entries.async_schedule_reload(entry.entry_id)

    def reload_started(self) -> None:
        self._reload_requested = False

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
        # What each sensor has said last. Nothing is heard until the estimator starts listening.
        self.states: dict[str, bool | None] = dict.fromkeys(spec.kinds)
        self._listeners: list[Listener] = []

    def readings(self) -> list[Reading]:
        return [(kind, self.states[entity_id]) for entity_id, kind in self.spec.kinds.items()]

    def advance(self, t: float) -> None:
        """Move the belief to t, with the sensors as they have been since the last step."""
        # The tick may have advanced the belief a few milliseconds past an event's own timestamp.
        self.belief.advance(self.belief.latest(t), self.readings())

    def add_listener(self, listener: Listener) -> CALLBACK_TYPE:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def notify(self, now: float) -> None:
        for listener in list(self._listeners):
            listener(now)

    @property
    def probability(self) -> float | None:
        """None for a room no sensor watches: there is nothing to say about it."""
        return round(100.0 * self.belief.p_occupied, 1) if self.spec.sensors else None

    @property
    def expected_count(self) -> float | None:
        return round(self.belief.expected_count, 2) if self.spec.sensors else None


class Estimator:
    def __init__(
        self,
        hass: HomeAssistant,
        specs: dict[str, RoomSpec],
        store: Store,
        saved: dict[str, dict],
        now: float,
        update_listeners: UpdateListeners,
        params: RoomParams,
    ):
        self.hass = hass
        self._store = store
        self._save_pending = False
        self._update_listeners = update_listeners
        self._params = params
        self.rooms: dict[str, TrackedRoom] = {}
        for area_id, spec in specs.items():
            if area_id in saved:
                belief = RoomBelief.from_snapshot(self._params, saved[area_id])
                # Nobody watched while Home Assistant was down, so that gap is not silence.
                belief.advance(belief.latest(now))
            else:
                belief = RoomBelief(self._params, t=now)
            self.rooms[area_id] = TrackedRoom(spec, belief)
        self._room_of_sensor = {
            sensor: room for room in self.rooms.values() for sensor in room.spec.sensors
        }

    @callback
    def async_start(self) -> list[CALLBACK_TYPE]:
        """Begin listening. Returns the callbacks that undo it."""
        now = dt_util.utcnow().timestamp()
        for room in self.rooms.values():
            room.advance(now)  # nothing was heard until now
            # How a sensor stands when first seen is no change; from here on it is listened to.
            for entity_id in room.states:
                room.states[entity_id] = _value(self.hass.states.get(entity_id))
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

    def specs(self) -> dict[str, RoomSpec]:
        return {area_id: room.spec for area_id, room in self.rooms.items()}

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
        entity_id = event.data["entity_id"]
        room = self._room_of_sensor[entity_id]
        old, new = room.states[entity_id], _value(event.data["new_state"])
        if new == old:
            return  # only attributes changed, or it is still not heard
        room.advance(event.time_fired.timestamp())  # with the sensors as they were until now
        room.belief.observe_change(room.spec.kinds[entity_id], old, new)
        room.states[entity_id] = new
        _LOGGER.debug("%s in %s went from %s to %s", entity_id, room.spec.name, old, new)
        self._after_change(room)

    @callback
    def _tick(self, _now) -> None:
        now = dt_util.utcnow().timestamp()
        for room in self.rooms.values():
            room.advance(now)
            room.notify(now)
        self._update_listeners.notify()

    def _after_change(self, room: TrackedRoom) -> None:
        room.notify(dt_util.utcnow().timestamp())
        self._update_listeners.notify()
        self._save_soon()

    def _save_soon(self) -> None:
        # Home Assistant restarts the wait on every call, so ask only once per write: otherwise
        # sensors that keep changing would put the save off for as long as they do.
        if not self._save_pending:
            self._save_pending = True
            self._store.async_delay_save(self._stored_data, SAVE_DELAY)

    def _stored_data(self) -> dict:
        """What is written. Every write, delayed or not, asks for it here."""
        self._save_pending = False
        return {"rooms": {a: r.belief.snapshot() for a, r in self.rooms.items()}}

    async def async_save(self) -> None:
        await self._store.async_save(self._stored_data())
