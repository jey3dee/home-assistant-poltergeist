import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode

from .const import CONF_MAX_PEOPLE, DEFAULT_MAX_PEOPLE, DOMAIN
from .model import MAX_PEOPLE_LIMIT


class PoltergeistConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PoltergeistOptionsFlow:
        return PoltergeistOptionsFlow()

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        # manifest.json has `single_config_entry`, so Home Assistant aborts a second flow itself.
        if user_input is not None:
            return self.async_create_entry(title="Poltergeist", data={})
        return self.async_show_form(step_id="user")


class PoltergeistOptionsFlow(OptionsFlowWithReload):
    """Changing an option reloads the integration, so the new room size takes effect."""

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_MAX_PEOPLE, DEFAULT_MAX_PEOPLE)
        schema = vol.Schema(
            {
                vol.Required(CONF_MAX_PEOPLE, default=current): vol.All(
                    NumberSelector(
                        NumberSelectorConfig(
                            min=1, max=MAX_PEOPLE_LIMIT, step=1, mode=NumberSelectorMode.BOX
                        )
                    ),
                    vol.Coerce(int),
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
