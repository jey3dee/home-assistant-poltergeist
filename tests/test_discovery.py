from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.poltergeist.discovery import build_rooms, propose_sensors

from .helpers import add_area, add_binary_sensor, add_entry, add_room


async def test_proposes_motion_sensors_by_their_area(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    a = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    b = add_binary_sensor(hass, "kitchen_pir_2", area_id=kitchen.id)
    c = add_binary_sensor(hass, "hall_pir", device_area_id=hall.id)  # area comes from the device
    assert propose_sensors(hass) == {a: kitchen.id, b: kitchen.id, c: hall.id}


async def test_proposes_motion_and_occupancy_only(hass):
    area = add_area(hass, "Study")
    motion = add_binary_sensor(hass, "m", area_id=area.id)
    occupancy = add_binary_sensor(
        hass, "o", area_id=area.id, device_class=BinarySensorDeviceClass.OCCUPANCY
    )
    add_binary_sensor(hass, "door", area_id=area.id, device_class=BinarySensorDeviceClass.DOOR)
    add_binary_sensor(hass, "plain", area_id=area.id, device_class=None)
    assert propose_sensors(hass) == {motion: area.id, occupancy: area.id}


async def test_proposes_nothing_for_sensors_without_area_or_disabled_ones(hass):
    area = add_area(hass, "Study")
    add_binary_sensor(hass, "nowhere")
    add_binary_sensor(hass, "off", area_id=area.id, disabled=True)
    assert propose_sensors(hass) == {}


async def test_entity_area_overrides_device_area(hass):
    kitchen = add_area(hass, "Kitchen")
    hall = add_area(hass, "Hall")
    sensor = add_binary_sensor(hass, "pir", area_id=hall.id, device_area_id=kitchen.id)
    assert propose_sensors(hass) == {sensor: hall.id}


async def test_rooms_are_built_from_the_room_entries(hass):
    kitchen = add_area(hass, "Kitchen")
    bedroom = add_area(hass, "Bedroom")
    pir = add_binary_sensor(hass, "kitchen_pir", area_id=kitchen.id)
    entry = add_entry(hass)
    add_room(hass, entry, kitchen, [pir])
    add_room(hass, entry, bedroom)
    rooms = build_rooms(hass, entry)
    assert set(rooms) == {kitchen.id, bedroom.id}
    assert rooms[kitchen.id].name == "Kitchen"
    assert rooms[kitchen.id].sensors == [pir]
    assert rooms[bedroom.id].sensors == []
    assert rooms[kitchen.id].subentry_id is not None


async def test_a_room_watches_the_sensors_of_its_entry_whatever_their_area(hass):
    hall = add_area(hass, "Hall")
    kitchen = add_area(hass, "Kitchen")
    door = add_binary_sensor(
        hass, "front_door", area_id=kitchen.id, device_class=BinarySensorDeviceClass.DOOR
    )
    entry = add_entry(hass)
    add_room(hass, entry, hall, [door])
    assert build_rooms(hass, entry)[hall.id].sensors == [door]


async def test_disabled_and_deleted_sensors_are_not_watched(hass):
    kitchen = add_area(hass, "Kitchen")
    disabled = add_binary_sensor(hass, "disabled", area_id=kitchen.id, disabled=True)
    entry = add_entry(hass)
    add_room(hass, entry, kitchen, [disabled, "binary_sensor.ghost"])
    assert build_rooms(hass, entry)[kitchen.id].sensors == []
