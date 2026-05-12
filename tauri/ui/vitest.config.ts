// Phase 11 Wave 0 + Phase 12 Wave 2 — Vitest config.
//
// validator.spec.ts (Phase 11) runs in node env; DOM-touching spec files
// in src/**/*.dom.spec.ts and tests/**/*.spec.ts run under jsdom. Phase 12
// Wave 2 (session components) is the first consumer of the jsdom env —
// every component constructs HTMLElement instances and pokes data-attrs.
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.spec.ts", "tests/**/*.spec.ts"],
    environmentMatchGlobs: [
      ["tests/**/*.spec.ts", "jsdom"],
      ["src/**/*.dom.spec.ts", "jsdom"],
    ],
  },
});
