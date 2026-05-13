// Phase 11 Wave 0 + Phase 12 Wave 2 — Vitest config.
//
// validator.spec.ts (Phase 11) runs in node env; DOM-touching spec files
// in src/**/*.dom.spec.ts and tests/**/*.spec.ts run under jsdom. Phase 12
// Wave 2 (session components) is the first consumer of the jsdom env —
// every component constructs HTMLElement instances and pokes data-attrs.
//
// Phase 13 Plan 04 adds src/mascot/*.test.ts. The plan's verify contract
// hard-codes the .test.ts extension AND the src/mascot/ path; we extend
// `include` so `vitest run` (no args) picks them up alongside existing
// *.spec.ts files. asset-loader.test.ts mocks fetch + GLTFLoader and
// needs jsdom; state-machine.test.ts is pure-function and works in either
// env. The glob below routes both under jsdom for simplicity.
//
// Phase 14 Plan 14-01 adds tests/**/*.test.ts (token migration specs).
// `tokens.legacy-detect.test.ts` is pure-function and works in node env;
// the per-surface specs (wizard|session|settings.tokens + mascot.chrome)
// render components / parse HTML and need jsdom. The `tests/**/*.test.ts`
// extension is added to `include` and routed under jsdom for simplicity.
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: [
      "src/**/*.spec.ts",
      "src/**/*.test.ts",
      "tests/**/*.spec.ts",
      "tests/**/*.test.ts",
    ],
    environmentMatchGlobs: [
      ["tests/**/*.spec.ts", "jsdom"],
      ["tests/**/*.test.ts", "jsdom"],
      ["src/**/*.dom.spec.ts", "jsdom"],
      ["src/mascot/*.test.ts", "jsdom"],
      // Phase 15 Plan 04 — Recording browser specs live alongside their
      // components per plan §files_modified; they construct HTMLElement
      // instances + poke data-attrs and need jsdom (rather than the
      // default node env for src/**/*.spec.ts).
      ["src/settings/components/recording-*.spec.ts", "jsdom"],
    ],
  },
});
