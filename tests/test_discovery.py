from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.poltergeist.discovery import build_rooms, propose_assignments

from .helpers import add_area, add_binary_sensor


async def test_proposes_motion_sensors_by_their_area(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    a = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    b = add_binary_sensor(hass, "kitchen_pir_2", area_id=kitchen.id)
    c = add_binary_sensor(hass, "hall_pir", device_area_id=hall.id)  # area comes from the device
    assert propose_assignments(hass) == {a: kitchen.id, b: kitchen.id, c: hall.id}


async def test_proposes_motion_and_occupancy_only(hass):
    area = add_area(hass, "Study")
    motion = add_binary_sensor(hass, "m", area_id=area.id)
    occupancy = add_binary_sensor(
        hass, "o", area_id=area.id, device_class=BinarySensorDeviceClass.OCCUPANCY
    )
    add_binary_sensor(hass, "door", area_id=area.id, device_class=BinarySensorDeviceClass.DOOR)
    add_binary_sensor(hass, "plain", area_id=area.id, device_class=None)
    assert propose_assignments(hass) == {motion: area.id, occupancy: area.id}


async def test_proposes_nothing_for_sensors_without_area_or_disabled_ones(hass):
    area = add_area(hass, "Study")
    add_binary_sensor(hass, "nowhere")
    add_binary_sensor(hass, "off", area_id=area.id, disabled=True)
    assert propose_assignments(hass) == {}


async def test_entity_area_overrides_device_area(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    sensor = add_binary_sensor(hass, "pir", area_id=hall.id, device_area_id=kitchen.id)
    assert propose_assignments(hass) == {sensor: hall.id}


async def test_every_area_is_a_room_even_without_sensors(hass):
    kitchen = add_area(hass, "Kitchen")
    bedroom = add_area(hass, "Bedroom")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    rooms = build_rooms(hass, {pir: kitchen.id})
    assert set(rooms) == {kitchen.id, bedroom.id}
    assert rooms[kitchen.id].name == "Kitchen"
    assert rooms[kitchen.id].sensors == [pir]
    assert rooms[bedroom.id].sensors == []


async def test_a_room_gets_the_sensors_assigned_to_it_not_those_in_its_area(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    rooms = build_rooms(hass, {pir: hall.id})
    assert rooms[kitchen.id].sensors == []
    assert rooms[hall.id].sensors == [pir]


async def test_excluded_and_disabled_sensors_belong_to_no_room(hass):
    kitchen = add_area(hass, "Kitchen")
    excluded = add_binary_sensor(hass, "excluded", area_id=kitchen.id)
    disabled = add_binary_sensor(hass, "disabled", area_id=kitchen.id, disabled=True)
    rooms = build_rooms(hass, {excluded: None, disabled: kitchen.id})
    assert rooms[kitchen.id].sensors == []


async def test_a_sensor_of_any_class_can_be_assigned(hass):
    hall = add_area(hass, "Hall")
    door = add_binary_sensor(hass, "front_door", device_class=BinarySensorDeviceClass.DOOR)
    assert build_rooms(hass, {door: hall.id})[hall.id].sensors == [door]


async def test_assignments_to_missing_areas_or_entities_are_ignored_when_building(hass):
    kitchen = add_area(hass, "Kitchen")
    rooms = build_rooms(hass, {"binary_sensor.ghost": kitchen.id, "binary_sensor.x": "nope"})
    assert rooms[kitchen.id].sensors == []
