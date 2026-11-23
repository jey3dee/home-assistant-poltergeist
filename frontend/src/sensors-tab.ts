import { LitElement, css, html, nothing } from "lit";
import { live } from "lit/directives/live.js";
import type { Candidate, Hass, SensorRow, SensorsResult } from "./types";

// While the integration reloads after an edit its commands answer "not_loaded" for a moment.
const RETRY_MS = 1000;
const MAX_ATTEMPTS = 8;

const errorText = (error: unknown) => {
  const e = error as { code?: string; message?: string };
  return e.code ?? e.message ?? "unknown error";
};

export class SensorsTab extends LitElement {
  static properties = {
    hass: { attribute: false },
    _data: { state: true },
    _error: { state: true },
    _addSensor: { state: true },
    _addRoom: { state: true },
  };

  declare hass?: Hass;
  declare private _data: SensorsResult | undefined;
  declare private _error: string | undefined;
  declare private _addSensor: string;
  declare private _addRoom: string;
  private _started = false;

  constructor() {
    super();
    this._addSensor = "";
    this._addRoom = "";
  }

  protected willUpdate(changed: Map<string, unknown>): void {
    // `hass` is replaced on every state change; load the assignments once.
    if (changed.has("hass") && this.hass && !this._started) {
      this._started = true;
      void this._load();
    }
  }

  private async _load(): Promise<void> {
    for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
      try {
        this._data = await this.hass!.callWS<SensorsResult>({ type: "poltergeist/sensors" });
        this._error = undefined;
        return;
      } catch (error) {
        const code = (error as { code?: string }).code;
        if (code !== "not_loaded" || attempt === MAX_ATTEMPTS) {
          this._error = errorText(error);
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, RETRY_MS));
      }
    }
  }

  private async _assign(entityId: string, areaId: string | null): Promise<void> {
    this._error = undefined;
    try {
      await this.hass!.callWS({
        type: "poltergeist/assign",
        entity_id: entityId,
        area_id: areaId,
      });
    } catch (error) {
      this._error = errorText(error);
      await this._load(); // show what the server really has
      this._error = errorText(error);
      return;
    }
    const data = this._data!;
    const known = data.sensors.some((s) => s.entity_id === entityId);
    const candidate = data.candidates.find((c) => c.entity_id === entityId);
    this._data = {
      ...data,
      sensors: known
        ? data.sensors.map((s) => (s.entity_id === entityId ? { ...s, room: areaId } : s))
        : [...data.sensors, this._rowFor(candidate!, areaId)].sort((a, b) =>
            a.entity_id.localeCompare(b.entity_id),
          ),
      candidates: data.candidates.filter((c) => c.entity_id !== entityId),
    };
  }

  private _rowFor(candidate: Candidate, room: string | null): SensorRow {
    return {
      entity_id: candidate.entity_id,
      name: candidate.name,
      device_class: null,
      ha_area_id: candidate.ha_area_id,
      room,
    };
  }

  private async _add(): Promise<void> {
    await this._assign(this._addSensor, this._addRoom);
    this._addSensor = "";
    this._addRoom = "";
  }

  private async _restore(): Promise<void> {
    const message =
      "Forget every change you made and use the areas of Home Assistant for all sensors?";
    if (!window.confirm(message)) return;
    this._error = undefined;
    try {
      await this.hass!.callWS({ type: "poltergeist/restore_proposals" });
    } catch (error) {
      this._error = errorText(error);
      return;
    }
    await this._load();
  }

  protected render() {
    if (this._error && !this._data) {
      return html`<p class="note error">Could not load the sensors: ${this._error}</p>`;
    }
    const data = this._data;
    if (!data) return html`<p class="note">Loading…</p>`;
    const roomName = (id: string | null) =>
      data.rooms.find((room) => room.area_id === id)?.name ?? "none";
    const watched = new Set(data.sensors.map((s) => s.room));
    const unwatched = data.rooms.filter((room) => !watched.has(room.area_id));
    return html`
      ${this._error ? html`<p class="note error">${this._error}</p>` : nothing}
      <table>
        <thead>
          <tr>
            <th>Sensor</th>
            <th>Class</th>
            <th>State</th>
            <th>Room</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${data.sensors.map(
            (sensor) => html`<tr>
              <td>${sensor.name}<div class="id">${sensor.entity_id}</div></td>
              <td>${sensor.device_class ?? ""}</td>
              <td data-state>${this.hass?.states[sensor.entity_id]?.state ?? ""}</td>
              <td>
                <select
                  aria-label="Room of ${sensor.name}"
                  @change=${(event: Event) =>
                    this._assign(
                      sensor.entity_id,
                      (event.target as HTMLSelectElement).value || null,
                    )}
                >
                  <option value="" .selected=${live(sensor.room === null)}>No room</option>
                  ${data.rooms.map(
                    (room) =>
                      html`<option
                        value=${room.area_id}
                        .selected=${live(sensor.room === room.area_id)}
                      >
                        ${room.name}
                      </option>`,
                  )}
                </select>
              </td>
              <td class="marker">
                ${sensor.room === sensor.ha_area_id
                  ? "as proposed"
                  : html`changed<span class="id">
                        (Home Assistant: ${roomName(sensor.ha_area_id)})</span
                      >`}
              </td>
            </tr>`,
          )}
        </tbody>
      </table>
      <div class="actions">
        <select
          data-add-sensor
          aria-label="Sensor to add"
          @change=${(e: Event) => (this._addSensor = (e.target as HTMLSelectElement).value)}
        >
          <option value="">Add a sensor…</option>
          ${data.candidates.map(
            (c) => html`<option value=${c.entity_id}>${c.name} (${c.entity_id})</option>`,
          )}
        </select>
        <select
          data-add-room
          aria-label="Room for the new sensor"
          @change=${(e: Event) => (this._addRoom = (e.target as HTMLSelectElement).value)}
        >
          <option value="">in room…</option>
          ${data.rooms.map((room) => html`<option value=${room.area_id}>${room.name}</option>`)}
        </select>
        <button data-add ?disabled=${!this._addSensor || !this._addRoom} @click=${this._add}>
          Add
        </button>
        <button data-restore @click=${this._restore}>Restore proposals</button>
      </div>
      ${unwatched.length
        ? html`<p class="note">
            Rooms without sensors: ${unwatched.map((room) => room.name).join(", ")}
          </p>`
        : nothing}
    `;
  }

  static styles = css`
    :host {
      display: block;
      padding: 16px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background: var(--card-background-color, #fff);
      border-radius: 12px;
      overflow: hidden;
    }
    th,
    td {
      text-align: left;
      padding: 8px 12px;
      border-bottom: 1px solid var(--divider-color, #e0e0e0);
    }
    th {
      color: var(--secondary-text-color);
      font-weight: 500;
    }
    .id {
      color: var(--secondary-text-color);
      font-size: 12px;
    }
    .marker {
      color: var(--secondary-text-color);
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 16px 0;
    }
    select,
    button {
      font: inherit;
      padding: 6px 10px;
    }
    .note {
      color: var(--secondary-text-color);
    }
    .error {
      color: var(--error-color);
    }
  `;
}

customElements.define("poltergeist-sensors", SensorsTab);
