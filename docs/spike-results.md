# Slice 01 spike results

Run on 2026-11-23 against the Home Assistant Core container `ghcr.io/home-assistant/home-assistant:2026.11.2` (amd64, Python 3.14.10), with the integration mounted read-only into `/config/custom_components/poltergeist`. Nothing here was run on a Raspberry Pi or HA Green.

These answer the open items of `planning/spec.md` section 16.

| Item | Result | How it was checked |
|---|---|---|
| numpy in the Core image | **Yes, 2.3.2** | `import numpy` inside the container, no integration involved |
| scipy in the Core image | **Yes, 1.18.1** (pandas 2.3.3 too) | `import scipy` inside the container. This **contradicts** `planning/research/custom-integration.md`, which inferred from `requirements_all.txt` that scipy was absent. At the time the integration declared no `requirements`; it now declares `numpy>=2.3.2` (see the rerun below). |
| `recorder.history` from an integration | **Works** on a real SQLite recorder | A throwaway component (not in this repo) called `history.get_significant_states(..., significant_changes_only=False)` through `get_instance(hass).async_add_executor_job` and got the full `unknown, off, on, off, off, off` sequence of a test motion sensor. State objects carry a `context` attribute; whether it holds the user and parent ids was not inspected. |
| What remains after removing the config entry | **Nothing** | Deleted the entry over the REST API. The `.storage/poltergeist` file, all four entities, both devices and the sidebar panel were gone (live registries over WebSocket, and the registry files after their write delay). |
| Static panel file authentication | **Served without a login** | `curl` of `/poltergeist_static/panel.js` without a token returned 200. The bundle therefore holds no secrets. |
| `require_admin` | Hides the panel from non-admins; the WebSocket command refuses non-admins | The unit test `test_subscription_is_refused_for_non_admins` against the test harness. Direct URL navigation by a non-admin was not tried in a browser. |
| State survives a restart | **Yes** | After `docker restart`, the kitchen room came back at 97.9 % from a saved belief of 98.9 %. The store is written at shutdown (Home Assistant's final write). |
| Panel in the real frontend | **Works** | Headless Chromium logged into the dev instance: the Overview listed both rooms, the Hall room went from 17 % to 100 % within 1.5 s of a motion event while the panel was open, and on a 420 px wide screen the menu button opened Home Assistant's sidebar. |

## Rerun on 2026.11.3 (2026-11-26)

With rooms as config subentries and the trigger/state sensor model, in a new `ghcr.io/home-assistant/home-assistant:2026.11.3` container (amd64):

- **Sensors:** held on for 5 minutes, an occupancy room read 95.0 % (53.5 % 6 s after off) and a motion room 90.0 %.
- **Rename:** sensors were chosen in Home Assistant's room screen, one moved by hand to another room and one removed. After both entity ids were renamed, the first stayed in its chosen room and was still heard (21.3 % to 100.0 %), and the removed one stayed removed.
- **Restart after a quiet period:** before the stop, the store held the estimate from the delayed save (79.1 %, 605 s old) while the live room read 24.3 %. The stop wrote 24.3 %; after the restart the room read 23.0 %.
- **Panel:** in a headless browser the four tabs opened without page errors. No errors or tracebacks in the log.

An earlier run the same day showed the delayed save writing the store 302 s after a sensor change, and an open panel subscription receiving a room's new name. numpy is declared because Home Assistant's core requirements do not include it. Removing the integration was not repeated.

## Cost measurement (desktop only)

The current single-room filter, measured on the development machine, not on target hardware:

| Work | Time |
|---|---|
| One event update, one room | 43 µs |
| Advancing all rooms at one 5 s tick, 10 rooms | 0.32 ms |
| Advancing all rooms at one 5 s tick, 40 rooms | 1.3 ms |

This is the independent-room model of this slice only. It says nothing about the zone clusters of later slices, and the event-loop stall test (spec section 16, item 1) on a Pi or HA Green is still to do.

## Go/no-go

**Provisional go** (2026-11-25).

- **Passed:** numpy in the image (amd64), removal behaviour, persistence across restarts, panel delivery.
- **Partly checked:** scipy (amd64 only; 2026.11.2 and 2026.11.3) and `recorder.history` (a short test sequence, not the weeks the spec asks for).
- **Not decided:** the event-loop stall on target hardware (item 1) and the Supervisor watchdog (item 7). Neither was measured. The timings above predate the current sensor model.

Ticket 02 closes the open points on a Home Assistant Yellow, and the final decision is made before ticket 03.

## Test harness gap

`pytest-homeassistant-custom-component` (latest 0.13.375, 2026-10-25) pins `homeassistant==2026.10.4`. Installing 2026.11.2 next to it fails at import (`httpx was already imported`). The automated tests therefore run against 2026.10.4, and the runtime checks above against 2026.11.2. `hacs.json` names 2026.11.0 as the minimum, which the unit tests do not exercise.

**Later (2026-11-25):** the tests now run on 2026.11.3. The import error came from the harness loading `respx`, and with it `httpx`, before Home Assistant could substitute `httpx2`. `tests/ha_compat.py` handles that and one function the harness imports from its old place. The section above describes the state when slice 01 was first run.
