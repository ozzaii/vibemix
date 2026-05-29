// SPDX-License-Identifier: Apache-2.0
// REQ-ID: LESSON-05 / WCAG - tutor-speak dock contrast contract.

import { describe, expect, it } from "vitest";

import { contrastTokens, readLearnCss } from "./contrast-helpers";

const AA_NORMAL = 4.5;
const AAA_NORMAL = 7;

function cssRule(css: string, selector: string): string {
  const start = css.indexOf(`${selector} {`);
  expect(start).toBeGreaterThanOrEqual(0);
  const end = css.indexOf("}", start);
  expect(end).toBeGreaterThan(start);
  return css.slice(start, end);
}

describe("test_contrast_p92.spec.ts (LESSON-05 WCAG)", () => {
  const learnCss = readLearnCss();

  it("tutor dock .now line uses fixed 28px silk text with AAA contrast", () => {
    const nowRule = cssRule(learnCss, ".tutor-dock .now");
    expect(nowRule).toContain("font-size: 28px");
    expect(nowRule).not.toContain("clamp(");
    expect(nowRule).toContain("color: var(--silk)");
    expect(contrastTokens("silk")).toBeGreaterThanOrEqual(AAA_NORMAL);
  });

  it("tutor dock hint line uses silk-65 text with normal AA contrast", () => {
    const hintRule = cssRule(learnCss, ".tutor-dock .hint-line");
    expect(hintRule).toContain("font-size: 14px");
    expect(hintRule).toContain("font-style: italic");
    expect(hintRule).toContain("color: var(--silk-65)");
    expect(contrastTokens("silk-65")).toBeGreaterThanOrEqual(AA_NORMAL);
  });

  it("highlight cue colors render through real CSS selectors with AA contrast", () => {
    const baseRule = cssRule(learnCss, ".learn-stage svg [data-control-id][data-cue-color]");
    const amberRule = cssRule(
      learnCss,
      '.learn-stage svg [data-control-id][data-cue-color="amber"]',
    );
    const warningRule = cssRule(
      learnCss,
      '.learn-stage svg [data-control-id][data-cue-color="warning"]',
    );

    expect(baseRule).toContain("color: var(--learn-highlight)");
    expect(amberRule).toContain("--learn-highlight: var(--amber)");
    expect(warningRule).toContain("--learn-highlight: var(--led-warn)");
    expect(contrastTokens("amber")).toBeGreaterThanOrEqual(AA_NORMAL);
    expect(contrastTokens("led-warn")).toBeGreaterThanOrEqual(AA_NORMAL);
  });
});
