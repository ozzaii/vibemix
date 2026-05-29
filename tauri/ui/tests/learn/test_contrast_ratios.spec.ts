// SPDX-License-Identifier: Apache-2.0
// REQ-ID: N/A - A11Y contrast - Learn window palette tokens keep WCAG
//               contrast before the browser axe pass.

import { describe, expect, it } from "vitest";

import { contrastTokens } from "./contrast-helpers";

const AA_NORMAL = 4.5;
const AAA_NORMAL = 7;
const NON_TEXT = 3;

describe("test_contrast_ratios.spec.ts (A11Y contrast)", () => {
  it("keeps primary Learn text tokens readable on the void", () => {
    expect(contrastTokens("silk")).toBeGreaterThanOrEqual(AAA_NORMAL);
    expect(contrastTokens("silk-65")).toBeGreaterThanOrEqual(AA_NORMAL);
  });

  it("keeps the amber accent and status LEDs visible as meaningful graphics", () => {
    for (const token of ["amber", "led-ok", "led-warn", "led-fault"]) {
      expect(contrastTokens(token)).toBeGreaterThanOrEqual(NON_TEXT);
    }
  });

  it("keeps the citation chip foreground readable on amber glass", () => {
    expect(contrastTokens("amber-pale", "amber-22")).toBeGreaterThanOrEqual(AA_NORMAL);
  });
});
