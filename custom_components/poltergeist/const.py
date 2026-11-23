DOMAIN = "poltergeist"

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
SAVE_DELAY = 60.0  # seconds before changed beliefs are written to the store

UPDATE_LISTENERS_KEY = f"{DOMAIN}_update_listeners"
