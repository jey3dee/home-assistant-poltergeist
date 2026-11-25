import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers.selector import (
    EntityFilterSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import CONF_MAX_PEOPLE, CONF_SENSORS, DEFAULT_MAX_PEOPLE, DOMAIN, SUBENTRY_ROOM
from .discovery import SENSOR_KINDS, proposals_for_area, room_entries
from .model import MAX_PEOPLE_LIMIT


class PoltergeistConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PoltergeistOptionsFlow:
        return PoltergeistOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_ROOM: RoomSubentryFlow}

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        # manifest.json has `single_config_entry`, so Home Assistant aborts a second flow itself.
        if user_input is not None:
            return self.async_create_entry(title="Poltergeist", data={})
        return self.async_show_form(step_id="user")


class PoltergeistOptionsFlow(OptionsFlow):
    """The entry reloads itself when its options change (see `_reload_on_change`)."""

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


class RoomSubentryFlow(ConfigSubentryFlow):
    """A room: Add (an area that has none), and Configure (its sensors)."""

    async def async_step_user(self, user_input=None) -> SubentryFlowResult:
        entry = self._get_entry()
        taken = room_entries(entry)
        free = sorted(
            (a for a in ar.async_get(self.hass).areas.values() if a.id not in taken),
            key=lambda a: a.name,
        )
        if not free:
            return self.async_abort(reason="all_areas_are_rooms")
        if user_input is not None:
            area = ar.async_get(self.hass).async_get_area(user_input["area"])
            return self.async_create_entry(
                title=area.name,
                data={CONF_SENSORS: proposals_for_area(self.hass, entry, area.id)},
                unique_id=area.id,
            )
        schema = vol.Schema(
            {
                vol.Required("area"): SelectSelector(
                    SelectSelectorConfig(
                        options=[SelectOptionDict(value=a.id, label=a.name) for a in free]
                    )
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_reconfigure(self, user_input=None) -> SubentryFlowResult:
        entry = self._get_entry()
        subentry = self._get_reconfigure_subentry()
        if user_input is not None:
            chosen = list(dict.fromkeys(user_input[CONF_SENSORS]))
            # A sensor watches one room: choosing it here takes it out of the room it was in.
            for other in room_entries(entry).values():
                kept = [e for e in other.data[CONF_SENSORS] if e not in chosen]
                if other.subentry_id != subentry.subentry_id and kept != list(
                    other.data[CONF_SENSORS]
                ):
                    self.hass.config_entries.async_update_subentry(
                        entry, other, data={CONF_SENSORS: kept}
                    )
            return self.async_update_and_abort(entry, subentry, data={CONF_SENSORS: chosen})
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SENSORS, default=list(subentry.data[CONF_SENSORS])
                ): EntitySelector(
                    EntitySelectorConfig(
                        filter=EntityFilterSelectorConfig(
                            domain="binary_sensor", device_class=list(SENSOR_KINDS)
                        ),
                        multiple=True,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            description_placeholders={"room": subentry.title},
        )
