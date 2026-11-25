# Poltergeist

A Home Assistant custom integration that estimates where people are in the house from indirect sensor evidence. The planning, spec and tickets live in the sibling `planning/` repository (`spec.md`).

## What it does today (slice 01)

- **Rooms** are entries under Settings > Devices & services > Poltergeist, one per Home Assistant area. They are created automatically, once: every area at first, and every area you add later. A room you delete stays deleted. The **+** button adds one back, from the areas that have no room. A room that no sensor watches reports `unknown`.
- **Sensors:** each room's gear icon opens a picker with the sensors that watch it. Only `binary_sensor`s of the type `motion` or `occupancy` can be used so far (Home Assistant's "show as" setting counts); another type left in a room is not watched, and the log says so. They are proposed once, from Home Assistant's own areas (enabled `motion` and `occupancy` sensors; a sensor's own area wins over its device's). After that the list is yours: a sensor you remove is not proposed again, and moving a sensor to another area in Home Assistant does not move it here. A sensor watches one room: choosing it in another room moves it. Sensors deleted from Home Assistant are dropped. Renaming an area renames its room.
- Each room gets one device named *Occupancy* with two sensors: the occupancy probability in percent and the expected head count.
- **How sensors count.** Each room is filtered separately, in continuous time, over a head count of 0 up to a highest value (see below). What a sensor does, and what it fails to do, moves the estimate:
  - *Motion* is a trigger. Switching `on` is strong evidence that someone is there; while it is `off`, silence slowly argues for an empty room. While it is `on` it cannot trigger, so that time says nothing.
  - *Occupancy* is a state. Switching `on` argues for someone, and so does staying `on`; switching `off` and staying `off` argue for an empty room.
  - An `unavailable` or `unknown` sensor says nothing, and neither does coming back from it. A sensor already `on` when it is first seen counts from then on, not as a new switch.
  - With several sensors in a room, each one adds its evidence. Two that see the same movement are counted as independent, which makes the estimate too sure.
- All rates are assumed starting values; nothing is learned yet. Known limits: a motion sensor whose `on` time stretches with further movement loses that information; one that triggers as someone leaves reads as someone there; a sensor stuck `on` keeps an occupancy room occupied.
- The beliefs are stored in `.storage/poltergeist`. Time while Home Assistant was down counts as evidence from no sensor: only the possibility that people moved.
- An admin-only sidebar panel lists the rooms live. Its Map, People and Health tabs are empty.

The head count is tracked from 0 up to a highest value you can change under Settings > Devices & services > Poltergeist > the gear of the integration itself (default 4, range 1 to 15; read the top count roughly as "this many or more"; the calculation treats it as exactly that many). Motion and occupancy sensors cannot tell these counts apart, so a higher value only matters once sensors that count people are added. Changing it reloads the integration and keeps the saved beliefs.

Values are written to Home Assistant only when they move by 5 percentage points (0.1 persons for the head count), at most every 5 s, and at least every 5 minutes.

Not there yet: persons, other sensor kinds, learning, movement between rooms, the intruder hypothesis, alerts. See `planning/tickets/implementation/`.

## Install by hand

Requires Home Assistant 2026.11.3 or newer. Development and the automated tests use exactly 2026.11.3; newer versions are not tested until the pin moves.

1. Build the panel (see below). `custom_components/poltergeist/panel.js` is committed, so this is only needed after changing the front end.
2. Copy `custom_components/poltergeist` into the `custom_components` folder of your Home Assistant configuration and restart Home Assistant.
3. Settings → Devices & services → Add integration → *Poltergeist*.

Put your motion and occupancy sensors into areas first; rooms follow the registry and the integration reloads itself when areas or sensors change.

## Develop

```sh
uv sync                      # Python 3.14.2 or newer and the Home Assistant test tools
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

### The Home Assistant version

`pyproject.toml` pins Home Assistant. The test harness, `pytest-homeassistant-custom-component`, declares an older one, so `uv` is told to override it and `tests/ha_compat.py` bridges the two differences. This is not a combination the harness supports.

To move to a new release, change the two `homeassistant==` pins and the frontend pin in `pyproject.toml` (the frontend version is in Home Assistant's `components/frontend/manifest.json`) and the minimum in `hacs.json`, then run `uv lock`, `uv sync` and the tests. `tests/test_versions.py` fails if the stated minimum or the frontend does not match. Drop the override and `tests/ha_compat.py` once the harness supports the pinned release.

### Try it in a throwaway Home Assistant

Run the official image of the pinned release with a scratch configuration directory and the integration mounted:

```sh
docker run -d --name poltergeist-dev -p 18123:8123 \
  -v "$PWD/dev-config:/config" \
  -v "$PWD/custom_components/poltergeist:/config/custom_components/poltergeist:ro" \
  ghcr.io/home-assistant/home-assistant:2026.11.3
```

`dev-config/` is ignored by git. Results of the first runs against 2026.11.2 are in `docs/spike-results.md`.
