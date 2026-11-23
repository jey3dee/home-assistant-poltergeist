from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class PoltergeistConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        # manifest.json has `single_config_entry`, so Home Assistant aborts a second flow itself.
        if user_input is not None:
            return self.async_create_entry(title="Poltergeist", data={})
        return self.async_show_form(step_id="user")
