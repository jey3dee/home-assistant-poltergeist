import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "./sensors-tab";
import type { Hass, SensorsResult } from "./types";

const rooms = [
  { area_id: "kitchen", name: "Kitchen" },
  { area_id: "hall", name: "Hall" },
  { area_id: "bedroom", name: "Bedroom" },
];

function listing(overrides: Partial<SensorsResult> = {}): SensorsResult {
  return {
    rooms,
    sensors: [
      {
        entity_id: "binary_sensor.kitchen_pir",
        name: "Kitchen PIR",
        device_class: "motion",
        ha_area_id: "kitchen",
        room: "kitchen",
      },
      {
        entity_id: "binary_sensor.hall_pir",
        name: "Hall PIR",
        device_class: "motion",
        ha_area_id: "kitchen",
        room: "hall",
      },
    ],
    candidates: [{ entity_id: "binary_sensor.front_door", name: "Front door", ha_area_id: "hall" }],
    ...overrides,
  };
}

type Call = { type: string; [key: string]: unknown };

function fakeHass(initial: SensorsResult = listing(), failures: Record<string, Error> = {}) {
  const calls: Call[] = [];
  let current = initial;
  const hass = {
    states: {
      "binary_sensor.kitchen_pir": { state: "on" },
      "binary_sensor.hall_pir": { state: "off" },
    },
    callWS: vi.fn((message: Call) => {
      calls.push(message);
      if (failures[message.type]) return Promise.reject(failures[message.type]);
      return Promise.resolve(message.type === "poltergeist/sensors" ? current : undefined);
    }),
    connection: { subscribeMessage: vi.fn() },
  } as unknown as Hass;
  return { hass, calls, setListing: (next: SensorsResult) => (current = next) };
}

async function mount(hass: Hass) {
  const el = document.createElement("poltergeist-sensors") as HTMLElement & {
    hass: Hass;
    updateComplete: Promise<boolean>;
  };
  el.hass = hass;
  document.body.append(el);
  await settle(el);
  return el;
}

async function settle(el: { updateComplete: Promise<boolean> }) {
  for (let i = 0; i < 4; i++) {
    await Promise.resolve();
    await el.updateComplete;
  }
}

const text = (el: HTMLElement) => el.shadowRoot!.textContent!.replace(/\s+/g, " ");
const q = <T extends Element>(el: HTMLElement, selector: string) =>
  el.shadowRoot!.querySelector<T>(selector)!;
const qa = <T extends Element>(el: HTMLElement, selector: string) =>
  [...el.shadowRoot!.querySelectorAll<T>(selector)];

async function choose(el: HTMLElement, select: HTMLSelectElement, value: string) {
  select.value = value;
  select.dispatchEvent(new Event("change", { bubbles: true }));
  await settle(el as never);
}

describe("poltergeist-sensors", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("loads the assignments once and shows one row per sensor with its live state", async () => {
    const { hass, calls } = fakeHass();
    const el = await mount(hass);
    expect(calls).toEqual([{ type: "poltergeist/sensors" }]);
    expect(qa(el, "tbody tr")).toHaveLength(2);
    expect(text(el)).toContain("Kitchen PIR");
    expect(text(el)).toContain("motion");
    const states = qa(el, "tbody tr").map((row) => row.querySelector("[data-state]")!.textContent);
    expect(states).toEqual(["on", "off"]);
  });

  it("offers every room and 'No room', with the assigned room selected", async () => {
    const { hass } = fakeHass();
    const el = await mount(hass);
    const select = qa<HTMLSelectElement>(el, "tbody select")[1];
    expect([...select.options].map((o) => o.textContent!.trim())).toEqual([
      "No room",
      "Kitchen",
      "Hall",
      "Bedroom",
    ]);
    expect(select.value).toBe("hall");
  });

  it("says whether a sensor is where Home Assistant puts it", async () => {
    const { hass } = fakeHass();
    const el = await mount(hass);
    const [kitchenRow, hallRow] = qa(el, "tbody tr").map((r) => r.textContent!.replace(/\s+/g, " "));
    expect(kitchenRow).toContain("as proposed");
    expect(hallRow).toContain("changed");
    expect(hallRow).toContain("Home Assistant: Kitchen");
  });

  it("sends an assignment when a room is chosen, and shows it at once", async () => {
    const { hass, calls } = fakeHass();
    const el = await mount(hass);
    await choose(el, qa<HTMLSelectElement>(el, "tbody select")[0], "bedroom");
    expect(calls.at(-1)).toEqual({
      type: "poltergeist/assign",
      entity_id: "binary_sensor.kitchen_pir",
      area_id: "bedroom",
    });
    expect(qa<HTMLSelectElement>(el, "tbody select")[0].value).toBe("bedroom");
  });

  it("sends null for 'No room'", async () => {
    const { hass, calls } = fakeHass();
    const el = await mount(hass);
    await choose(el, qa<HTMLSelectElement>(el, "tbody select")[0], "");
    expect(calls.at(-1)).toMatchObject({ type: "poltergeist/assign", area_id: null });
  });

  it("shows the error and the server's truth when an assignment is refused", async () => {
    const { hass } = fakeHass(listing(), {
      "poltergeist/assign": Object.assign(new Error("x"), { code: "not_found" }),
    });
    const el = await mount(hass);
    await choose(el, qa<HTMLSelectElement>(el, "tbody select")[0], "bedroom");
    expect(text(el)).toContain("not_found");
    expect(qa<HTMLSelectElement>(el, "tbody select")[0].value).toBe("kitchen");
  });

  it("lists rooms that no sensor watches", async () => {
    const { hass } = fakeHass();
    const el = await mount(hass);
    expect(text(el)).toContain("Rooms without sensors: Bedroom");
    await choose(el, qa<HTMLSelectElement>(el, "tbody select")[0], "bedroom");
    expect(text(el)).toContain("Rooms without sensors: Kitchen");
  });

  it("adds any other binary sensor to a room", async () => {
    const { hass, calls } = fakeHass();
    const el = await mount(hass);
    await choose(el, q<HTMLSelectElement>(el, "[data-add-sensor]"), "binary_sensor.front_door");
    await choose(el, q<HTMLSelectElement>(el, "[data-add-room]"), "hall");
    q<HTMLButtonElement>(el, "[data-add]").click();
    await settle(el as never);
    expect(calls.at(-1)).toEqual({
      type: "poltergeist/assign",
      entity_id: "binary_sensor.front_door",
      area_id: "hall",
    });
    expect(qa(el, "tbody tr")).toHaveLength(3);
    expect(q<HTMLSelectElement>(el, "[data-add-sensor]").options.length).toBe(1); // placeholder only
  });

  it("restores the proposals only after confirmation, then reloads the list", async () => {
    const { hass, calls, setListing } = fakeHass();
    const el = await mount(hass);
    const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false);
    q<HTMLButtonElement>(el, "[data-restore]").click();
    await settle(el as never);
    expect(calls.map((c) => c.type)).toEqual(["poltergeist/sensors"]);

    confirm.mockReturnValueOnce(true);
    setListing(listing({ sensors: [] }));
    q<HTMLButtonElement>(el, "[data-restore]").click();
    await settle(el as never);
    expect(calls.map((c) => c.type)).toContain("poltergeist/restore_proposals");
    expect(qa(el, "tbody tr")).toHaveLength(0);
  });

  it("keeps asking while the integration is reloading", async () => {
    vi.useFakeTimers();
    const { hass, calls } = fakeHass();
    let attempts = 0;
    (hass.callWS as unknown as ReturnType<typeof vi.fn>).mockImplementation((m: Call) => {
      calls.push(m);
      attempts += 1;
      return attempts < 3
        ? Promise.reject(Object.assign(new Error("not loaded"), { code: "not_loaded" }))
        : Promise.resolve(listing());
    });
    const el = document.createElement("poltergeist-sensors") as HTMLElement & {
      hass: Hass;
      updateComplete: Promise<boolean>;
    };
    el.hass = hass;
    document.body.append(el);
    await vi.advanceTimersByTimeAsync(3000);
    await settle(el);
    expect(attempts).toBe(3);
    expect(qa(el, "tbody tr")).toHaveLength(2);
  });

  it("gives up with a message when the list never loads", async () => {
    vi.useFakeTimers();
    const { hass } = fakeHass();
    (hass.callWS as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(
      Object.assign(new Error("nope"), { code: "unauthorized" }),
    );
    const el = document.createElement("poltergeist-sensors") as HTMLElement & {
      hass: Hass;
      updateComplete: Promise<boolean>;
    };
    el.hass = hass;
    document.body.append(el);
    await vi.advanceTimersByTimeAsync(30_000);
    await settle(el);
    expect(text(el)).toContain("unauthorized");
  });
});
