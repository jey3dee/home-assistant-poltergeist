// The small part of Home Assistant's `hass` object this panel uses. Home Assistant does not publish
// a stable type package for panels, so the shape is declared here instead of imported.
export interface Hass {
  connection: {
    subscribeMessage<T>(
      callback: (message: T) => void,
      message: { type: string },
    ): Promise<() => void | Promise<void>>;
  };
  callWS<T>(message: { type: string; [key: string]: unknown }): Promise<T>;
  states: Record<string, { state: string } | undefined>;
}

export interface Room {
  area_id: string;
  name: string;
  sensors: string[];
  probability: number | null; // percent; null while no sensor watches the room
  expected_count: number | null;
}

export interface RoomsMessage {
  rooms: Room[];
}

export interface RoomChoice {
  area_id: string;
  name: string;
}

export interface SensorRow {
  entity_id: string;
  name: string;
  device_class: string | null;
  ha_area_id: string | null; // the area Home Assistant puts the sensor in
  room: string | null; // the room it is assigned to here; null means no room
}

export interface Candidate {
  entity_id: string;
  name: string;
  ha_area_id: string | null;
}

export interface SensorsResult {
  rooms: RoomChoice[];
  sensors: SensorRow[];
  candidates: Candidate[];
}
