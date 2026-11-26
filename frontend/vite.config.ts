import { defineConfig } from "vite";
import thirdPartyNotices from "./third-party-notices.js";

// One ES module, written next to the integration so Home Assistant can serve it.
export default defineConfig({
  plugins: [thirdPartyNotices()],
  build: {
    lib: {
      entry: "src/panel.ts",
      formats: ["es"],
      fileName: () => "panel.js",
    },
    outDir: "../custom_components/poltergeist",
    emptyOutDir: false,
    target: "es2022",
  },
  // The notices test reads the built panel.js, which lies next to this folder.
  server: { fs: { allow: [".."] } },
  test: {
    environment: "jsdom",
  },
});
