// astro.config.mjs — ACT-3A dashboard shell.
//
// Notes:
// - We use `output: 'static'` so the build is purely pre-rendered.
// - `srcDir` stays at default 'src'.
// - No integrations: no @astrojs/react, no @astrojs/tailwind. ACT-3A is
//   deliberately minimal. The whole point is "vanilla Astro + plain CSS".
// - The dashboard reads ../../generated/index.json at build time, which
//   means `npm run build` MUST be preceded by `make build` (which calls
//   scripts/tower.py build). The Makefile wires this together.

import { defineConfig } from "astro/config";

export default defineConfig({
  output: "static",
  build: {
    // Output to apps/dashboard/dist/ by default
  },
  // Make the repo root resolvable as '@/' if we want it later.
  vite: {
    resolve: {
      alias: {
        "@": new URL("./src", import.meta.url).pathname,
      },
    },
  },
});
