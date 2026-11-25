// A Vite plugin: put the name, version and licence text of every bundled npm package at the top of
// the built file. The licences ask for that, and the integration folder is all that gets installed.
import { readFileSync } from "node:fs";

const PACKAGE_DIR = /^(.*\/node_modules\/((?:@[^/]+\/)?[^/]+))\//;

export default function thirdPartyNotices() {
  return {
    name: "third-party-notices",
    renderChunk(code, chunk) {
      const packages = new Map();
      for (const id of chunk.moduleIds) {
        const match = id.match(PACKAGE_DIR);
        if (match) packages.set(match[2], match[1]);
      }
      if (packages.size === 0) return null;
      // Packages that share a licence text are listed together above it.
      const licences = new Map();
      for (const [name, dir] of [...packages].sort(([a], [b]) => a.localeCompare(b))) {
        const { version } = JSON.parse(readFileSync(`${dir}/package.json`, "utf8"));
        // A package without a licence file stops the build: someone has to look at it.
        const text = readFileSync(`${dir}/LICENSE`, "utf8").trim();
        if (text.includes("*/")) throw new Error(`The licence of ${name} would end the comment`);
        licences.set(text, [...(licences.get(text) ?? []), `${name} ${version}`]);
      }
      const sections = [...licences].map(([text, names]) => `${names.join("\n")}\n\n${text}`);
      const notice = `This file includes code of the following packages.\n\n${sections.join("\n\n----\n\n")}`;
      return { code: `/*!\n${notice}\n*/\n${code}`, map: null };
    },
  };
}
