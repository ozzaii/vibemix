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
      // Phase 31 Plan 02 — per-channel layer files live under
      // src/mascot/layers/{base,emotion,reaction}.ts. base layer is
      // pure-state but emotion/reaction layer tests may touch DOM
      // helpers (matches existing src/mascot/*.test.ts policy).
      ["src/mascot/layers/*.test.ts", "jsdom"],
      // Phase 31 Plan 05 — v2.0 test name port-verbatim suite. Lives
      // under src/mascot/__tests__/*.spec.ts per Pitfall P47 evidence
      // anchors. Uses real AnimationMixer + AnimationClip fixtures.
      ["src/mascot/__tests__/*.spec.ts", "jsdom"],
      ["src/mascot/__tests__/*.test.ts", "jsdom"],
      // Phase 15 Plan 04 — Recording browser specs live alongside their
      // components per plan §files_modified; they construct HTMLElement
      // instances + poke data-attrs and need jsdom (rather than the
      // default node env for src/**/*.spec.ts).
      ["src/settings/components/recording-*.spec.ts", "jsdom"],
      // Phase 20 Plan 04 — citation-diagnostics renderer; same DOM-API
      // pattern as recording-row and friends, needs jsdom for textContent /
      // title-attr / dataset assertions.
      ["src/settings/components/citation-diagnostics.spec.ts", "jsdom"],
      // Phase 29 Plans 05+06 — all debrief specs (component renders +
      // recording-row debrief button) need jsdom for HTMLElement APIs.
      ["src/debrief/__tests__/*.spec.ts", "jsdom"],
      // Phase 32 Plan 05 — Settings → Profile panel renderer (vanilla TS
      // DOM construction + dataset assertions). Same env as recording-*.
      ["src/settings/components/profile-panel.spec.ts", "jsdom"],
    ],
  },
});
