import { defineConfig } from "vite";

// One ES module, written next to the integration so Home Assistant can serve it.
export default defineConfig({
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
  test: {
    environment: "jsdom",
  },
});
