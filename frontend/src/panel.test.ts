import { beforeEach, describe, expect, it, vi } from "vitest";
import "./panel";
import type { Hass, RoomsMessage } from "./types";

type Callback = (message: RoomsMessage) => void;

function fakeHass(options: { reject?: Error } = {}) {
  const calls: { message: unknown; callback: Callback }[] = [];
  const unsubscribe = vi.fn();
  const hass = {
    connection: {
      subscribeMessage: vi.fn((callback: Callback, message: unknown) => {
        calls.push({ callback, message });
        return options.reject ? Promise.reject(options.reject) : Promise.resolve(unsubscribe);
      }),
    },
    callWS: vi.fn(() => new Promise(() => undefined)),
    states: {},
  } as unknown as Hass;
  return { hass, calls, unsubscribe };
}

const kitchen = {
  area_id: "kitchen",
  name: "Kitchen",
  sensors: ["binary_sensor.kitchen_pir"],
  probability: 87.4,
  expected_count: 1.12,
};

async function mount(hass: Hass, narrow = false) {
  const el = document.createElement("poltergeist-panel") as HTMLElement & {
    hass: Hass;
    narrow: boolean;
    updateComplete: Promise<boolean>;
  };
  el.narrow = narrow;
  el.hass = hass;
  document.body.append(el);
  await el.updateComplete;
  return el;
}

const text = (el: HTMLElement) => el.shadowRoot!.textContent!.replace(/\s+/g, " ");

describe("poltergeist-panel", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("subscribes once to the integration's WebSocket command", async () => {
    const { hass, calls } = fakeHass();
    const el = await mount(hass);
    el.hass = { ...hass } as Hass; // Home Assistant sets a new hass object on every state change
    await el.updateComplete;
    expect(calls).toHaveLength(1);
    expect(calls[0].message).toEqual({ type: "poltergeist/subscribe" });
  });

  it("lists the rooms it is sent, and updates them live", async () => {
    const { hass, calls } = fakeHass();
    const el = await mount(hass);
    calls[0].callback({ rooms: [kitchen] });
    await el.updateComplete;
    expect(text(el)).toContain("Kitchen");
    expect(text(el)).toContain("87 %");
    expect(text(el)).toContain("1.12");

    calls[0].callback({ rooms: [{ ...kitchen, probability: 3.1 }] });
    await el.updateComplete;
    expect(text(el)).toContain("3 %");
    expect(text(el)).not.toContain("87 %");
  });

  it("says what to do when there are no rooms", async () => {
    const { hass, calls } = fakeHass();
    const el = await mount(hass);
    calls[0].callback({ rooms: [] });
    await el.updateComplete;
    expect(text(el)).toContain("Rooms are the areas of Home Assistant");
  });

  it("shows a room without sensors as such, with no probability", async () => {
    const { hass, calls } = fakeHass();
    const el = await mount(hass);
    calls[0].callback({
      rooms: [
        kitchen,
        { area_id: "bedroom", name: "Bedroom", sensors: [], probability: null, expected_count: null },
      ],
    });
    await el.updateComplete;
    const rows = [...el.shadowRoot!.querySelectorAll(".row")].map((r) =>
      r.textContent!.replace(/\s+/g, " ").trim(),
    );
    expect(rows[0]).toContain("87 %");
    expect(rows[1]).toContain("Bedroom");
    expect(rows[1]).toContain("no sensors");
    expect(rows[1]).not.toContain("%");
    expect(el.shadowRoot!.querySelectorAll(".fill")).toHaveLength(1);
  });

  it("shows the sensor assignments on the Sensors tab, with the hass object", async () => {
    const { hass, calls } = fakeHass();
    const el = await mount(hass);
    calls[0].callback({ rooms: [kitchen] });
    await el.updateComplete;
    const sensorsTab = [...el.shadowRoot!.querySelectorAll<HTMLElement>("[role=tab]")][3];
    sensorsTab.click();
    await el.updateComplete;
    const content = el.shadowRoot!.querySelector("poltergeist-sensors") as HTMLElement & {
      hass: Hass;
    };
    expect(content).not.toBeNull();
    expect(content.hass).toBe(hass);
  });

  it("shows the five tabs and switches between them", async () => {
    const { hass, calls } = fakeHass();
    const el = await mount(hass);
    calls[0].callback({ rooms: [kitchen] });
    await el.updateComplete;
    const tabs = [...el.shadowRoot!.querySelectorAll<HTMLElement>("[role=tab]")];
    expect(tabs.map((t) => t.textContent!.trim())).toEqual([
      "Overview",
      "Map",
      "People",
      "Sensors",
      "Health",
    ]);
    tabs[1].click();
    await el.updateComplete;
    expect(text(el)).not.toContain("87 %");
    expect(tabs[1].getAttribute("aria-selected")).toBe("true");
  });

  it("shows the error when the subscription is refused", async () => {
    const { hass } = fakeHass({ reject: Object.assign(new Error("x"), { code: "unauthorized" }) });
    const el = await mount(hass);
    await new Promise((r) => setTimeout(r));
    await el.updateComplete;
    expect(text(el)).toContain("unauthorized");
  });

  it("does not retry a refused subscription on every hass update", async () => {
    const { hass } = fakeHass({ reject: Object.assign(new Error("x"), { code: "unauthorized" }) });
    const el = await mount(hass);
    await new Promise((r) => setTimeout(r));
    for (let i = 0; i < 3; i++) {
      el.hass = { ...hass } as Hass; // Home Assistant sends a new hass on every state change
      await el.updateComplete;
    }
    expect(hass.connection.subscribeMessage).toHaveBeenCalledTimes(1);
  });

  it("offers the sidebar menu button on narrow screens and asks HA to toggle it", async () => {
    const { hass } = fakeHass();
    const el = await mount(hass, true);
    const listener = vi.fn();
    el.addEventListener("hass-toggle-menu", listener);
    el.shadowRoot!.querySelector<HTMLElement>("[data-menu]")!.click();
    expect(listener).toHaveBeenCalledOnce();
  });

  it("has no menu button on wide screens", async () => {
    const { hass } = fakeHass();
    const el = await mount(hass, false);
    expect(el.shadowRoot!.querySelector("[data-menu]")).toBeNull();
  });

  it("unsubscribes when it is removed", async () => {
    const { hass, unsubscribe } = fakeHass();
    const el = await mount(hass);
    await new Promise((r) => setTimeout(r));
    el.remove();
    await new Promise((r) => setTimeout(r)); // unsubscribing goes through a promise
    expect(unsubscribe).toHaveBeenCalledOnce();
  });
});
