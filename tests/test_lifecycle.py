from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.poltergeist.const import DOMAIN

from .helpers import add_area, add_binary_sensor, setup_poltergeist


async def test_beliefs_survive_a_restart(hass, hass_storage):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    entry = await setup_poltergeist(hass)
    hass.states.async_set(pir, "on")
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    saved = hass_storage[DOMAIN]["data"]
    assert saved["rooms"][kitchen.id]["probabilities"][0] < 0.01

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert float(hass.states.get("sensor.kitchen_occupancy_probability").state) > 90.0


async def test_downtime_is_not_counted_as_silence(hass, hass_storage, freezer):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    entry = await setup_poltergeist(hass)
    hass.states.async_set(pir, "on")
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    freezer.tick(timedelta(minutes=30))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # 30 minutes of observed silence would drop it near the prior; a blind gap keeps more.
    assert float(hass.states.get("sensor.kitchen_occupancy_probability").state) > 15.0


async def test_removing_the_entry_removes_the_store_and_devices(hass, hass_storage):
    kitchen = add_area(hass, "Kitchen")
    add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    entry = await setup_poltergeist(hass)
    await hass.config_entries.async_unload(entry.entry_id)
    assert DOMAIN in hass_storage
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert DOMAIN not in hass_storage
    assert dr.async_get(hass).async_get_devices(identifiers={(DOMAIN, kitchen.id)}) == []


async def test_new_room_appears_after_a_sensor_is_placed(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    await setup_poltergeist(hass)
    assert hass.states.get("sensor.hall_occupancy_probability") is None
    add_binary_sensor(hass, "hall_pir", area_id=hall.id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.hall_occupancy_probability") is not None


async def test_room_disappears_when_its_last_sensor_goes(hass):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    await setup_poltergeist(hass)
    assert hass.states.get("sensor.kitchen_occupancy_probability") is not None
    er.async_get(hass).async_remove(pir)
    await hass.async_block_till_done()
    assert er.async_get(hass).async_get("sensor.kitchen_occupancy_probability") is None
    assert dr.async_get(hass).async_get_devices(identifiers={(DOMAIN, kitchen.id)}) == []


async def test_setup_with_no_sensors_is_fine(hass):
    entry = await setup_poltergeist(hass)
    assert entry.state is ConfigEntryState.LOADED


async def test_removal_after_a_pending_delayed_save_leaves_no_store(hass, hass_storage, freezer):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    entry = await setup_poltergeist(hass)
    hass.states.async_set(pir, "on")  # schedules a delayed save
    await hass.async_block_till_done()
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert DOMAIN not in hass_storage


async def test_a_device_the_user_moved_to_another_area_stays_there(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    entry = await setup_poltergeist(hass)
    registry = dr.async_get(hass)
    device = registry.async_get_device_by_identifier((DOMAIN, kitchen.id), entry.entry_id)
    registry.async_update_device(device.id, area_id=hall.id)  # the user moves it
    await hass.async_block_till_done()

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    device = registry.async_get_device_by_identifier((DOMAIN, kitchen.id), entry.entry_id)
    assert device.area_id == hall.id
    # Entity ids are fixed at creation, so the entity is still found by its unique id.
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{kitchen.id}_occupancy_probability"
    )
    assert entity_id == "sensor.kitchen_occupancy_probability"
