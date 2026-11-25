"""The version we state, the version we test and the frontend we test with must agree."""

import json
from importlib.metadata import version
from pathlib import Path

import homeassistant
from homeassistant.const import __version__

ROOT = Path(__file__).parent.parent


def test_the_stated_minimum_is_the_tested_home_assistant():
    hacs = json.loads((ROOT / "hacs.json").read_text())
    assert hacs["homeassistant"] == __version__


def test_the_installed_frontend_is_the_one_home_assistant_asks_for():
    manifest = Path(homeassistant.__file__).parent / "components/frontend/manifest.json"
    assert json.loads(manifest.read_text())["requirements"] == [
        f"home-assistant-frontend=={version('home-assistant-frontend')}"
    ]
