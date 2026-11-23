from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.poltergeist.discovery import discover_rooms

from .helpers import add_area, add_binary_sensor


async def test_groups_motion_sensors_by_area(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    a = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    b = add_binary_sensor(hass, "kitchen_pir_2", area_id=kitchen.id)
    c = add_binary_sensor(hass, "hall_pir", device_area_id=hall.id)  # area comes from the device
    rooms = discover_rooms(hass)
    assert set(rooms) == {kitchen.id, hall.id}
    assert rooms[kitchen.id].name == "Kitchen"
    assert sorted(rooms[kitchen.id].sensors) == sorted([a, b])
    assert rooms[hall.id].sensors == [c]


async def test_accepts_motion_and_occupancy_only(hass):
    area = add_area(hass, "Study")
    motion = add_binary_sensor(hass, "m", area_id=area.id)
    occupancy = add_binary_sensor(
        hass, "o", area_id=area.id, device_class=BinarySensorDeviceClass.OCCUPANCY
    )
    add_binary_sensor(hass, "door", area_id=area.id, device_class=BinarySensorDeviceClass.DOOR)
    add_binary_sensor(hass, "plain", area_id=area.id, device_class=None)
    rooms = discover_rooms(hass)
    assert sorted(rooms[area.id].sensors) == sorted([motion, occupancy])


async def test_ignores_sensors_without_area_and_disabled_ones(hass):
    area = add_area(hass, "Study")
    add_binary_sensor(hass, "nowhere")
    add_binary_sensor(hass, "off", area_id=area.id, disabled=True)
    assert discover_rooms(hass) == {}


async def test_entity_area_overrides_device_area(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    entity = add_binary_sensor(hass, "pir", area_id=hall.id, device_area_id=kitchen.id)
    rooms = discover_rooms(hass)
    assert set(rooms) == {hall.id}
    assert rooms[hall.id].sensors == [entity]
