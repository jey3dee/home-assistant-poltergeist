// The shipped panel.js contains other people's code. Their licences ask for their notices to travel
// with it, and the integration folder is all that gets installed, so they have to be in the file.
import { describe, expect, it } from "vitest";
import panel from "../../custom_components/poltergeist/panel.js?raw";

const files = import.meta.glob<string>(
  ["../node_modules/{*,@*/*}/LICENSE", "../node_modules/{*,@*/*}/package.json"],
  { query: "?raw", import: "default" },
);
const read = (name: string, file: string) => files[`../node_modules/${name}/${file}`]!();

// The packages Lit's code comes from. Named here on purpose: the build works its own list out from
// the bundler, and this test must not take that list's word for it.
const bundled = ["@lit/reactive-element", "lit-element", "lit-html"];
const flat = (text: string) => text.replace(/^ \* ?/gm, "").replace(/\s+/g, " ").trim();

describe("third-party notices in panel.js", () => {
  it("names every bundled package with its version and carries its licence text", async () => {
    const notice = flat(panel.slice(0, panel.indexOf("*/")));
    expect(panel.startsWith("/*!")).toBe(true);
    for (const name of bundled) {
      const { version } = JSON.parse(await read(name, "package.json"));
      expect(notice).toContain(`${name} ${version}`);
      expect(notice).toContain(flat(await read(name, "LICENSE")));
    }
  });
});
