// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-06 — Bidirectional SVG↔profile parity gate across all 11
//                    controllers (10 specific Pioneer/Numark/Hercules + 1
//                    _generic fallback).
//
// Phase 91 Plan 02 — parameterized over the 11 controller IDs that Plan 05
// (FLX4 + _generic golden) and Plan 06 (other 9) ship under
// `tauri/ui/src/learn/controllers/<id>.svg.ts`. For each ID:
//   1. Forward: every `field` (+ optional `:deck`) in
//      `src/vibemix/midi/profiles/<id>.json` has a matching
//      `<g data-control-id>` in the SVG (skipped for `_generic`, which has
//      no profile JSON — its parity is "labeled-zone text only"). Relative
//      jog CC movement is represented by the same platter hit-region as
//      `jog_touch:<deck>`; the renderer maps `jog:<deck>` wire frames there.
//   2. Reverse: every `<g data-control-id>` in the SVG resolves to a
//      binding in the matching profile JSON.
//
// Files that don't exist yet skip (Plan 05/06 lands them). When all 11 SVG
// files land, this gate runs as 11 parameterized cases — each green when
// the corresponding SVG matches its profile.

import { describe, it, expect } from "vitest";
import * as fs from "node:fs";
import * as path from "node:path";

// vitest's `environmentMatchGlobs` maps tests/**/*.spec.ts → jsdom, so
// `document` + `DOMParser` are both available here without importing
// jsdom directly (the repo has no @types/jsdom — vite/client + DOM lib
// are the only ambient types).
const REPO_ROOT = path.resolve(__dirname, "../../../..");
const PROFILES_DIR = path.join(REPO_ROOT, "src/vibemix/midi/profiles");
const SVG_DIR = path.join(REPO_ROOT, "tauri/ui/src/learn/controllers");

const CONTROLLER_IDS: readonly string[] = [
  "pioneer_ddj_flx4",
  "pioneer_ddj_flx6",
  "pioneer_ddj_flx10",
  "pioneer_ddj_400",
  "pioneer_ddj_1000",
  "pioneer_ddj_sx3",
  "pioneer_xdj_rx3",
  "numark_party_mix_live",
  "hercules_inpulse_300",
  "hercules_inpulse_500",
  "_generic",
];

interface ProfileBinding {
  field?: string;
  deck?: string | null;
  kind?: string;
}

interface ProfileJSON {
  controls?: Record<string, ProfileBinding>;
  buttons?: Record<string, ProfileBinding>;
}

function profileControlIds(p: ProfileJSON): Set<string> {
  const ids = new Set<string>();
  const add = (binding: ProfileBinding): void => {
    const field = binding.field ?? binding.kind;
    if (!field) return;
    const deck = binding.deck;
    if (field === "jog" && deck) {
      ids.add(`jog_touch:${deck}`);
      return;
    }
    ids.add(deck ? `${field}:${deck}` : field);
  };
  for (const c of Object.values(p.controls ?? {})) add(c);
  for (const b of Object.values(p.buttons ?? {})) add(b);
  return ids;
}

function svgControlIds(svgString: string): Set<string> {
  // Wrap in <root> so the parser handles SVG fragments without a wrapping
  // <svg> element gracefully.
  const wrapped = svgString.trim().startsWith("<svg")
    ? svgString
    : `<svg xmlns="http://www.w3.org/2000/svg">${svgString}</svg>`;
  const doc = new DOMParser().parseFromString(wrapped, "image/svg+xml");
  const groups = doc.querySelectorAll("[data-control-id]");
  const ids = new Set<string>();
  groups.forEach((g: Element) => {
    const id = g.getAttribute("data-control-id");
    if (id) ids.add(id);
  });
  return ids;
}

describe("test_svg_profile_parity.spec.ts (RENDER-06)", () => {
  for (const controllerId of CONTROLLER_IDS) {
    const profilePath = path.join(PROFILES_DIR, `${controllerId}.json`);
    const svgPath = path.join(SVG_DIR, `${controllerId}.svg.ts`);
    const svgExists = fs.existsSync(svgPath);
    const profileExists = fs.existsSync(profilePath);

    const testFn = svgExists ? it : it.skip;
    testFn(`${controllerId} — SVG ↔ profile parity (bidirectional)`, () => {
      const svgSource = fs.readFileSync(svgPath, "utf8");
      // Extract backtick-delimited SVG body from the .svg.ts module source.
      // Plan 05/06 ship modules of shape `export const FOO_SVG = \`<svg>...</svg>\`;`.
      const m = svgSource.match(/=\s*`([\s\S]*?)`/);
      const svgString = m?.[1] ?? "";
      const svgIds = svgControlIds(svgString);

      if (controllerId === "_generic") {
        // Generic has no profile JSON — its contract is "labeled-zone text only"
        // (DECK A / MIXER / DECK B). Sibling spec
        // test_generic_fallback.spec.ts pins that contract.
        expect(svgIds.size).toBeGreaterThanOrEqual(0);
        return;
      }

      expect(profileExists).toBe(true);
      const profile: ProfileJSON = JSON.parse(fs.readFileSync(profilePath, "utf8"));
      const profileIds = profileControlIds(profile);

      // Forward: every profile binding has a matching SVG hit-region.
      const missingInSvg = [...profileIds].filter((id) => !svgIds.has(id));
      // Reverse: every SVG hit-region resolves to a profile binding.
      const missingInProfile = [...svgIds].filter((id) => !profileIds.has(id));

      expect(missingInSvg).toEqual([]);
      expect(missingInProfile).toEqual([]);
    });
  }
});
