from datetime import timedelta

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.poltergeist.const import DOMAIN

from .helpers import add_area, add_binary_sensor, setup_poltergeist


async def settle(hass, freezer, seconds=5):
    """Let time pass so the publishing interval allows the next write."""
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()


async def test_room_gets_a_device_and_two_sensors(hass):
    kitchen = add_area(hass, "Kitchen")
    add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    entry = await setup_poltergeist(hass)

    registry = er.async_get(hass)
    probability = registry.async_get("sensor.kitchen_occupancy_probability")
    count = registry.async_get("sensor.kitchen_occupancy_expected_head_count")
    assert probability is not None and count is not None
    assert probability.unique_id == f"{kitchen.id}_occupancy_probability"
    assert count.unique_id == f"{kitchen.id}_expected_head_count"

    device = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, kitchen.id), entry.entry_id)
    assert device is not None and device.name == "Occupancy"
    assert device.area_id == kitchen.id
    assert probability.device_id == device.id == count.device_id


async def test_initial_state_is_the_prior(hass):
    kitchen = add_area(hass, "Kitchen")
    add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    await setup_poltergeist(hass)
    probability = float(hass.states.get("sensor.kitchen_occupancy_probability").state)
    count = float(hass.states.get("sensor.kitchen_occupancy_expected_head_count").state)
    assert 0.0 < probability < 50.0
    assert 0.0 < count < 1.0
    assert (
        hass.states.get("sensor.kitchen_occupancy_probability").attributes["unit_of_measurement"]
        == "%"
    )


async def test_motion_event_raises_the_probability(hass, freezer):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    await setup_poltergeist(hass)
    before = float(hass.states.get("sensor.kitchen_occupancy_probability").state)
    hass.states.async_set(pir, "on")
    await hass.async_block_till_done()
    await settle(hass, freezer)  # the minimum publish interval holds the write until the tick
    after = float(hass.states.get("sensor.kitchen_occupancy_probability").state)
    assert after > 99.0 > before


async def test_only_a_switch_to_on_counts_as_an_event(hass, freezer):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    await setup_poltergeist(hass)
    before = float(hass.states.get("sensor.kitchen_occupancy_probability").state)
    for state in ("unavailable", "unknown", "off"):
        hass.states.async_set(pir, state)
        await hass.async_block_till_done()
    await settle(hass, freezer)  # a wrongly counted event would be published at this tick
    after = float(hass.states.get("sensor.kitchen_occupancy_probability").state)
    assert after < before + 1.0


async def test_attribute_change_while_on_is_not_a_new_event(hass, freezer):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    await setup_poltergeist(hass)
    hass.states.async_set(pir, "on")
    await hass.async_block_till_done()
    freezer.tick(timedelta(hours=2))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    decayed = float(hass.states.get("sensor.kitchen_occupancy_probability").state)
    hass.states.async_set(pir, "on", {"battery": 80})  # same state, new attribute
    await hass.async_block_till_done()
    await settle(hass, freezer)  # a wrongly counted event would be published at this tick
    assert float(hass.states.get("sensor.kitchen_occupancy_probability").state) < decayed + 1.0


async def test_silence_lowers_the_probability_over_time(hass, freezer):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    await setup_poltergeist(hass)
    hass.states.async_set(pir, "on")
    await hass.async_block_till_done()
    await settle(hass, freezer)
    high = float(hass.states.get("sensor.kitchen_occupancy_probability").state)
    freezer.tick(timedelta(hours=3))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    low = float(hass.states.get("sensor.kitchen_occupancy_probability").state)
    assert high > 99.0 and low < 10.0


async def test_small_drift_does_not_write_state(hass, freezer):
    kitchen = add_area(hass, "Kitchen")
    add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    await setup_poltergeist(hass)
    reported = hass.states.get("sensor.kitchen_occupancy_probability").last_reported
    freezer.tick(timedelta(seconds=10))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get("sensor.kitchen_occupancy_probability").last_reported == reported


async def test_heartbeat_rewrites_a_quiet_entity(hass, freezer):
    kitchen = add_area(hass, "Kitchen")
    add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    await setup_poltergeist(hass)
    freezer.tick(timedelta(hours=6))  # let the belief settle so the value stops moving
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    # HA updates `last_reported` on the same state object, so keep the timestamp itself.
    reported = hass.states.get("sensor.kitchen_occupancy_probability").last_reported
    freezer.tick(timedelta(seconds=305))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get("sensor.kitchen_occupancy_probability").last_reported > reported


async def test_an_unavailable_sensor_is_not_evidence_of_an_empty_room(hass, freezer):
    kitchen = add_area(hass, "Kitchen")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    await setup_poltergeist(hass)
    hass.states.async_set(pir, "on")
    await hass.async_block_till_done()
    hass.states.async_set(pir, "unavailable")
    await hass.async_block_till_done()
    await settle(hass, freezer, seconds=3 * 3600)
    # Three hours of real silence would end below 5 %. A dead sensor says nothing, so the
    # belief only relaxes toward the prior.
    assert float(hass.states.get("sensor.kitchen_occupancy_probability").state) > 15.0


async def test_a_room_with_one_working_sensor_still_counts_silence(hass, freezer):
    kitchen = add_area(hass, "Kitchen")
    working = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    dead = add_binary_sensor(hass, "kitchen_pir_2", area_id=kitchen.id)
    await setup_poltergeist(hass)
    hass.states.async_set(working, "on")
    await hass.async_block_till_done()
    hass.states.async_set(dead, "unavailable")
    await hass.async_block_till_done()
    await settle(hass, freezer, seconds=3 * 3600)
    assert float(hass.states.get("sensor.kitchen_occupancy_probability").state) < 10.0
