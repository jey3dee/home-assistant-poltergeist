import { LitElement, css, html, nothing } from "lit";
import { formatCount, formatPercent } from "./format";
import type { Hass, Room, RoomsMessage } from "./types";

const MENU_ICON = "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z";
const TABS = ["Overview", "Map", "People", "Health"] as const;
type Tab = (typeof TABS)[number];

export class PoltergeistPanel extends LitElement {
  static properties = {
    hass: { attribute: false },
    narrow: { type: Boolean },
    _rooms: { state: true },
    _error: { state: true },
    _tab: { state: true },
  };

  // `declare` keeps these as Lit reactive properties; a plain class field would shadow Lit's
  // accessors and updates would silently stop.
  declare hass?: Hass;
  declare narrow: boolean;
  declare private _rooms: Room[] | undefined;
  declare private _error: string | undefined;
  declare private _tab: Tab;
  private _unsubscribe: Promise<() => void | Promise<void>> | undefined;

  constructor() {
    super();
    this.narrow = false;
    this._tab = "Overview";
  }

  protected willUpdate(changed: Map<string, unknown>): void {
    // Home Assistant hands over a new `hass` object on every state change; subscribe only once.
    if (changed.has("hass") && this.hass && !this._unsubscribe) {
      this._subscribe(this.hass);
    }
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    const unsubscribe = this._unsubscribe;
    this._unsubscribe = undefined;
    unsubscribe?.then((fn) => fn()).catch(() => undefined);
  }

  private _subscribe(hass: Hass): void {
    this._unsubscribe = hass.connection.subscribeMessage<RoomsMessage>(
      (message) => {
        this._rooms = message.rooms;
        this._error = undefined;
      },
      { type: "poltergeist/subscribe" },
    );
    // A refused subscription is not retried: `hass` changes on every state change, so retrying
    // from willUpdate would ask again, and be refused again, many times a second.
    this._unsubscribe.catch((error: { code?: string; message?: string }) => {
      this._error = error.code ?? error.message ?? "unknown error";
    });
  }

  protected render() {
    return html`
      <header>
        ${this.narrow
          ? html`<button data-menu aria-label="Open sidebar" @click=${this._toggleMenu}>
              <svg viewBox="0 0 24 24" width="24" height="24"><path d=${MENU_ICON} /></svg>
            </button>`
          : nothing}
        <h1>Poltergeist</h1>
      </header>
      <nav role="tablist">
        ${TABS.map(
          (tab) => html`<button
            role="tab"
            aria-selected=${tab === this._tab}
            @click=${() => (this._tab = tab)}
          >
            ${tab}
          </button>`,
        )}
      </nav>
      <main>${this._tab === "Overview" ? this._renderOverview() : this._renderEmpty()}</main>
    `;
  }

  private _toggleMenu = () =>
    this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }));

  private _renderEmpty() {
    return html`<p class="note">Nothing here yet.</p>`;
  }

  private _renderOverview() {
    if (this._error) {
      return html`<p class="note error">Could not load the rooms: ${this._error}</p>`;
    }
    if (!this._rooms) return html`<p class="note">Loading…</p>`;
    if (this._rooms.length === 0) {
      return html`<p class="note">
        No rooms yet. Add one under Settings > Devices & services > Poltergeist.
      </p>`;
    }
    return html`<div class="card">
      ${this._rooms.map((room) =>
        room.probability === null
          ? html`<div class="row">
              <div class="name">${room.name}</div>
              <div class="none">no sensors</div>
            </div>`
          : html`<div class="row">
              <div class="name">${room.name}</div>
              <div class="bar" title=${room.sensors.join(", ")}>
                <div
                  class="fill"
                  style="width: ${Math.min(100, Math.max(0, room.probability))}%"
                ></div>
              </div>
              <div class="value">${formatPercent(room.probability)}</div>
              <div class="count">${formatCount(room.expected_count ?? 0)}</div>
            </div>`,
      )}
    </div>`;
  }

  static styles = css`
    :host {
      display: block;
      min-height: 100%;
      background: var(--primary-background-color);
      color: var(--primary-text-color);
      font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
    }
    header {
      display: flex;
      align-items: center;
      gap: 8px;
      height: var(--header-height, 56px);
      padding: 0 16px;
      background: var(--app-header-background-color, var(--primary-color));
      color: var(--app-header-text-color, var(--text-primary-color, #fff));
    }
    header h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 400;
    }
    header button {
      background: none;
      border: none;
      color: inherit;
      cursor: pointer;
      padding: 8px;
    }
    header svg {
      fill: currentColor;
    }
    nav {
      display: flex;
      overflow-x: auto;
      background: var(--app-header-background-color, var(--primary-color));
      color: var(--app-header-text-color, var(--text-primary-color, #fff));
    }
    nav button {
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      color: inherit;
      cursor: pointer;
      font: inherit;
      opacity: 0.75;
      padding: 12px 16px;
    }
    nav button[aria-selected="true"] {
      border-bottom-color: currentColor;
      opacity: 1;
    }
    main {
      max-width: 960px;
      margin: 0 auto;
      padding: 16px;
    }
    .card {
      background: var(--card-background-color);
      border-radius: var(--ha-card-border-radius, 12px);
      box-shadow: var(--ha-card-box-shadow, none);
      border: 1px solid var(--divider-color);
      overflow: hidden;
    }
    .row {
      display: grid;
      grid-template-columns: minmax(80px, 1fr) minmax(80px, 2fr) 56px 48px;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--divider-color);
    }
    .row:last-child {
      border-bottom: none;
    }
    .bar {
      height: 8px;
      border-radius: 4px;
      background: var(--divider-color);
      overflow: hidden;
    }
    .fill {
      height: 100%;
      background: var(--primary-color);
    }
    .value {
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .count {
      text-align: right;
      color: var(--secondary-text-color);
      font-variant-numeric: tabular-nums;
    }
    .none {
      grid-column: 2 / -1;
      color: var(--secondary-text-color);
    }
    .note {
      color: var(--secondary-text-color);
    }
    .error {
      color: var(--error-color);
    }
  `;
}

customElements.define("poltergeist-panel", PoltergeistPanel);
