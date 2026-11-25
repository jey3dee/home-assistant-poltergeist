"""Let the test harness, built for an older Home Assistant, run on the pinned one.

pytest loads this file before the harness (see `addopts` in pyproject.toml). Remove it,
and the version override, once the harness supports the pinned version itself.
"""

# isort: off
# Importing Home Assistant first lets it put httpx2 in place of httpx. The harness imports
# respx, and with it httpx, before it imports Home Assistant.
import homeassistant  # noqa: F401

# The harness's own patches must come before any other Home Assistant import, in its order.
from pytest_homeassistant_custom_component import patch_json, patch_recorder, patch_time  # noqa: F401

from homeassistant.components import logger
from homeassistant.components.logger import helpers as logger_helpers
# isort: on

# The harness imports this from its old place.
logger._clear_logger_overwrites = logger_helpers._clear_logger_overwrites
