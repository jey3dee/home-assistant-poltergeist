from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PANEL_FILE = Path(__file__).parent / "panel.js"
PANEL_URL = f"/{DOMAIN}_static/panel.js"
_STATIC_KEY = f"{DOMAIN}_static_registered"


async def async_register_panel(hass: HomeAssistant, version: str) -> None:
    if not hass.data.get(_STATIC_KEY):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(PANEL_URL, str(PANEL_FILE), cache_headers=False)]
        )
        hass.data[_STATIC_KEY] = True
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="poltergeist-panel",
        frontend_url_path=DOMAIN,
        sidebar_title="Poltergeist",
        sidebar_icon="mdi:ghost",
        module_url=f"{PANEL_URL}?v={version}",
        require_admin=True,
    )


def async_remove_panel(hass: HomeAssistant) -> None:
    frontend.async_remove_panel(hass, DOMAIN)
