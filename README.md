# Poltergeist

A Home Assistant custom integration that estimates where people are in the house from indirect sensor evidence. The planning, spec and tickets live in the sibling `planning/` repository (`spec.md`).

## What it does today (slice 01)

- **Rooms** are entries under Settings > Devices & services > Poltergeist, one per Home Assistant area. They are created automatically, once: every area at first, and every area you add later. A room you delete stays deleted. The **+** button adds one back, from the areas that have no room. A room that no sensor watches reports `unknown`.
- **Sensors:** each room's gear icon opens a picker with the sensors that watch it, any `binary_sensor`. They are proposed once, from Home Assistant's own areas (enabled `motion` and `occupancy` sensors; a sensor's own area wins over its device's). After that the list is yours: a sensor you remove is not proposed again, and moving a sensor to another area in Home Assistant does not move it here. A sensor watches one room: choosing it in another room moves it. Sensors deleted from Home Assistant are dropped. Renaming an area renames its room.
- Each room gets one device named *Occupancy* with two sensors: the occupancy probability in percent and the expected head count.
- A motion sensor switching to `on` is evidence that someone is there; silence slowly argues for an empty room. Each room is filtered separately, in continuous time, over a head count of 0 up to a highest value (see below). The default rates are priors, nothing is learned yet.
- The beliefs are stored in `.storage/poltergeist`. Time while Home Assistant was down is not counted as silence, and neither is time while all of a room's sensors are unavailable.
- An admin-only sidebar panel lists the rooms live. Its Map, People, Sensors and Health tabs are empty.

The head count is tracked from 0 up to a highest value you can change under Settings > Devices & services > Poltergeist > the gear of the integration itself (default 4, range 1 to 15; the top count means "this many or more"). A motion sensor cannot tell these counts apart, so a higher value only matters once sensors that count people are added. Changing it reloads the integration and keeps the saved beliefs.

Values are written to Home Assistant only when they move by 5 percentage points (0.1 persons for the head count), at most every 5 s, and at least every 5 minutes.

Not there yet: persons, other sensor kinds, learning, movement between rooms, the intruder hypothesis, alerts. See `planning/tickets/implementation/`.

## Install by hand

Requires Home Assistant 2026.11 or newer.

1. Build the panel (see below). `custom_components/poltergeist/panel.js` is committed, so this is only needed after changing the front end.
2. Copy `custom_components/poltergeist` into the `custom_components` folder of your Home Assistant configuration and restart Home Assistant.
3. Settings → Devices & services → Add integration → *Poltergeist*.

Put your motion sensors into areas first; rooms follow the registry and the integration reloads itself when areas or sensors change.

## Develop

```sh
uv sync                      # Python 3.14 and the Home Assistant test tools
uv run pytest                # model, oracle comparison and integration tests
uv run ruff check .
uv run ruff format --check .

cd frontend
npm ci
npm test                     # panel tests
npm run typecheck
npm run build                # writes ../custom_components/poltergeist/panel.js
```

The model is checked against an independent reference, a discrete-time forward pass in `tests/oracle.py`, on households simulated by `tests/simulator.py`.

### Try it in a throwaway Home Assistant

The automated tests use `pytest-homeassistant-custom-component`, which currently pins Home Assistant 2026.10.4. To try the integration on a current release, run the official image with a scratch configuration directory and the integration mounted:

```sh
docker run -d --name poltergeist-dev -p 18123:8123 \
  -v "$PWD/dev-config:/config" \
  -v "$PWD/custom_components/poltergeist:/config/custom_components/poltergeist:ro" \
  ghcr.io/home-assistant/home-assistant:2026.11.2
```

`dev-config/` is ignored by git. Results of the first runs against 2026.11.2 are in `docs/spike-results.md`.
