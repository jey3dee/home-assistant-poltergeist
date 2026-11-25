DOMAIN = "poltergeist"

SUBENTRY_ROOM = "room"
# Sensors are stored by entity registry id, which stays the same when the entity id is renamed.
CONF_SENSORS = "sensors"  # in a room: the sensors that watch it
CONF_SEEN_AREAS = "seen_areas"  # areas already offered as rooms, so a deleted room stays deleted
CONF_SEEN_SENSORS = "seen_sensors"  # sensors already offered, so a removed one stays removed

CONF_MAX_PEOPLE = "max_people"
DEFAULT_MAX_PEOPLE = 4

STORE_VERSION = 1
STORE_KEY = DOMAIN

# Publishing defaults (spec section 11).
PROBABILITY_STEP = 5.0  # percentage points
HEAD_COUNT_STEP = 0.1  # persons
MIN_PUBLISH_INTERVAL = 5.0  # seconds
HEARTBEAT = 300.0  # seconds
TICK_INTERVAL = 5.0  # seconds between belief updates while no event arrives
SAVE_DELAY = 300.0  # seconds from the first unsaved change to writing the beliefs

UPDATE_LISTENERS_KEY = f"{DOMAIN}_update_listeners"
