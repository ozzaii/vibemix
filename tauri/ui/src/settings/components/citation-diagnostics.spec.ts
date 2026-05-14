/* Phase 20 Plan 04 Task 2 — citation-diagnostics.spec.ts vitest jsdom coverage.
 *
 * Pins the §behavior contract from 20-04-PLAN.md: 2-line readout with
 * percentage formatting, bypass-badge state, optional unverified-response
 * subtitle truncation + full text in title attribute, no subtitle when idle.
 *
 * Vitest env: jsdom (extended below in vitest.config.ts via the
 * src/settings/components/citation-diagnostics.spec.ts glob).
 */

import { afterEach, describe, expect, it } from "vitest";

import { renderCitationDiagnostics } from "./citation-diagnostics.js";

afterEach(() => {
  document.body.replaceChildren();
});

describe("citation-diagnostics — Test 1: renders two lines with percentages", () => {
  it("formats slopRatio + strippedRate15s as rounded percentages", () => {
    const handle = renderCitationDiagnostics({
      slopRatio: 0.123,
      strippedRate15s: 0.077,
      lastUnverifiedResponse: null,
      bypassActive: false,
    });
    document.body.append(handle.root);

    const line1 = handle.root.querySelector<HTMLElement>(
      ".vmx-citation-diag__line",
    );
    expect(line1).not.toBeNull();
    // 0.123 → 12%, 0.077 → 8% (Math.round half-up)
    expect(line1!.textContent).toContain("Slop ratio: 12%");
    expect(line1!.textContent).toContain("Stripped rate (15s): 8%");
  });
});

describe("citation-diagnostics — Test 2: bypass badge active state", () => {
  it("renders 'Bypass: ACTIVE' with data-active='true' when bypassActive", () => {
    const handle = renderCitationDiagnostics({
      slopRatio: 0.5,
      strippedRate15s: 0.4,
      lastUnverifiedResponse: "some text",
      bypassActive: true,
    });
    document.body.append(handle.root);

    const badge = handle.root.querySelector<HTMLElement>(
      ".vmx-citation-diag__badge",
    );
    expect(badge).not.toBeNull();
    expect(badge!.textContent).toContain("ACTIVE");
    expect(badge!.dataset.active).toBe("true");
  });

  it("renders 'Bypass: idle' with data-active='false' when bypassActive=false", () => {
    const handle = renderCitationDiagnostics({
      slopRatio: 0.0,
      strippedRate15s: 0.0,
      lastUnverifiedResponse: null,
      bypassActive: false,
    });
    document.body.append(handle.root);

    const badge = handle.root.querySelector<HTMLElement>(
      ".vmx-citation-diag__badge",
    );
    expect(badge!.textContent).toContain("idle");
    expect(badge!.dataset.active).toBe("false");
  });
});

describe("citation-diagnostics — Test 3: lastUnverifiedResponse truncates at 60 chars", () => {
  it("renders first 60 chars + '...' + full text in title attribute", () => {
    const fullText = "x".repeat(200);
    const handle = renderCitationDiagnostics({
      slopRatio: 0.6,
      strippedRate15s: 0.5,
      lastUnverifiedResponse: fullText,
      bypassActive: true,
    });
    document.body.append(handle.root);

    const subtitle = handle.root.querySelector<HTMLElement>(
      ".citation-diag-last-unverified",
    );
    expect(subtitle).not.toBeNull();
    expect(subtitle!.textContent).toBe(`${"x".repeat(60)}...`);
    expect(subtitle!.title).toBe(fullText);
  });

  it("renders the full text without '...' when length <= 60", () => {
    const shortText = "Short unverified claim under 60 chars.";
    const handle = renderCitationDiagnostics({
      slopRatio: 0.6,
      strippedRate15s: 0.5,
      lastUnverifiedResponse: shortText,
      bypassActive: true,
    });
    document.body.append(handle.root);

    const subtitle = handle.root.querySelector<HTMLElement>(
      ".citation-diag-last-unverified",
    );
    expect(subtitle).not.toBeNull();
    expect(subtitle!.textContent).toBe(shortText);
    expect(subtitle!.textContent).not.toContain("...");
    expect(subtitle!.title).toBe(shortText);
  });
});

describe("citation-diagnostics — Test 4: no subtitle when idle or null", () => {
  it("omits the subtitle when lastUnverifiedResponse is null", () => {
    const handle = renderCitationDiagnostics({
      slopRatio: 0.1,
      strippedRate15s: 0.05,
      lastUnverifiedResponse: null,
      bypassActive: true,
    });
    document.body.append(handle.root);

    const subtitle = handle.root.querySelector(".citation-diag-last-unverified");
    expect(subtitle).toBeNull();
  });

  it("omits the subtitle when bypassActive=false even if text is present", () => {
    const handle = renderCitationDiagnostics({
      slopRatio: 0.1,
      strippedRate15s: 0.05,
      lastUnverifiedResponse: "stripped earlier — idle now",
      bypassActive: false,
    });
    document.body.append(handle.root);

    const subtitle = handle.root.querySelector(".citation-diag-last-unverified");
    expect(subtitle).toBeNull();
  });
});

describe("citation-diagnostics — Test 5: update() refreshes without rebuilding root", () => {
  it("preserves the root element identity across updates and toggles the subtitle", () => {
    const handle = renderCitationDiagnostics({
      slopRatio: 0.0,
      strippedRate15s: 0.0,
      lastUnverifiedResponse: null,
      bypassActive: false,
    });
    document.body.append(handle.root);
    const rootRef = handle.root;

    handle.update({
      slopRatio: 0.42,
      strippedRate15s: 0.31,
      lastUnverifiedResponse: "nope no evidence here",
      bypassActive: true,
    });

    expect(handle.root).toBe(rootRef);
    const line1 = handle.root.querySelector<HTMLElement>(
      ".vmx-citation-diag__line",
    );
    expect(line1!.textContent).toContain("42%");
    expect(line1!.textContent).toContain("31%");

    const badge = handle.root.querySelector<HTMLElement>(
      ".vmx-citation-diag__badge",
    );
    expect(badge!.dataset.active).toBe("true");

    const subtitle = handle.root.querySelector<HTMLElement>(
      ".citation-diag-last-unverified",
    );
    expect(subtitle).not.toBeNull();
    expect(subtitle!.title).toBe("nope no evidence here");

    // Toggle back to idle — subtitle should detach.
    handle.update({
      slopRatio: 0.42,
      strippedRate15s: 0.31,
      lastUnverifiedResponse: null,
      bypassActive: false,
    });
    expect(
      handle.root.querySelector(".citation-diag-last-unverified"),
    ).toBeNull();
    expect(badge.dataset.active).toBe("false");
  });
});

describe("citation-diagnostics — Test 6: XSS-safe via textContent + title", () => {
  it("renders <script> as literal text without injecting a <script> element", () => {
    const handle = renderCitationDiagnostics({
      slopRatio: 0.5,
      strippedRate15s: 0.4,
      lastUnverifiedResponse: "<script>alert(1)</script>",
      bypassActive: true,
    });
    document.body.append(handle.root);

    expect(handle.root.querySelectorAll("script").length).toBe(0);
    const subtitle = handle.root.querySelector<HTMLElement>(
      ".citation-diag-last-unverified",
    );
    expect(subtitle!.textContent).toBe("<script>alert(1)</script>");
    expect(subtitle!.title).toBe("<script>alert(1)</script>");
  });
});

describe("citation-diagnostics — Test 7: defensive clamp on out-of-range values", () => {
  it("clamps slopRatio > 1 to 100% rather than rendering 150%", () => {
    const handle = renderCitationDiagnostics({
      slopRatio: 1.5,
      strippedRate15s: -0.1,
      lastUnverifiedResponse: null,
      bypassActive: false,
    });
    document.body.append(handle.root);
    const line1 = handle.root.querySelector<HTMLElement>(
      ".vmx-citation-diag__line",
    );
    expect(line1!.textContent).toContain("Slop ratio: 100%");
    expect(line1!.textContent).toContain("Stripped rate (15s): 0%");
  });
});
