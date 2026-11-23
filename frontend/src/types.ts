// The small part of Home Assistant's `hass` object this panel uses. Home Assistant does not publish
// a stable type package for panels, so the shape is declared here instead of imported.
export interface Hass {
  connection: {
    subscribeMessage<T>(
      callback: (message: T) => void,
      subscribeMessage: { type: string },
    ): Promise<() => void | Promise<void>>;
  };
}

export interface Room {
  area_id: string;
  name: string;
  sensors: string[];
  probability: number; // percent
  expected_count: number;
}

export interface RoomsMessage {
  rooms: Room[];
}
