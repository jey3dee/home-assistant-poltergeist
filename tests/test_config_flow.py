import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType, InvalidData

from custom_components.poltergeist.const import DOMAIN

from .helpers import setup_poltergeist


async def test_user_flow_creates_the_entry(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Poltergeist"


async def test_only_one_instance(hass):
    first = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    await hass.config_entries.flow.async_configure(first["flow_id"], {})
    second = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert second["type"] is FlowResultType.ABORT
    assert second["reason"] == "single_instance_allowed"


async def test_options_form_offers_four_as_the_default(hass):
    entry = await setup_poltergeist(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["data_schema"]({})["max_people"] == 4


@pytest.mark.parametrize("bad", [0, 16])
async def test_options_flow_refuses_values_outside_the_checked_range(hass, bad):
    entry = await setup_poltergeist(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(result["flow_id"], {"max_people": bad})
    assert entry.options == {}


async def test_options_form_uses_a_number_box_and_stores_a_whole_number(hass):
    entry = await setup_poltergeist(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    selector = result["data_schema"].schema["max_people"].validators[0]
    assert selector.config["mode"] == "box"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"max_people": 6.0}
    )
    assert entry.options == {"max_people": 6}
    assert type(entry.options["max_people"]) is int
