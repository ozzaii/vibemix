// SPDX-License-Identifier: Apache-2.0
// Evidence tooltip placement — the receipt opens AT the clicked chip.
//
// The production flow is async (chip click → ws request → frame returns),
// so the anchor is stashed at click time and passed when the frame lands.
// Without it the tooltip rendered at its static position: the document
// tail, potentially below the fold — an evidence receipt nobody saw.

import { afterEach, describe, expect, it } from "vitest";

import {
  hideCitationTooltip,
  showCitationTooltip,
  type CitationTooltipPayload,
} from "../components/citation-tooltip.js";

function payload(overrides: Partial<CitationTooltipPayload> = {}): CitationTooltipPayload {
  return {
    event_id: "evt:12:44",
    evidence_text: "bass swap landed three beats early",
    timestamp: 764,
    found: true,
    ...overrides,
  };
}

function host(): HTMLElement {
  const el = document.createElement("div");
  el.hidden = true;
  document.body.append(el);
  return el;
}

afterEach(() => {
  document.body.replaceChildren();
});

describe("showCitationTooltip placement", () => {
  it("anchored: opens at the click position (plus a small offset)", () => {
    const el = host();
    showCitationTooltip(el, payload(), { x: 200, y: 150 });
    expect(el.hidden).toBe(false);
    expect(el.style.left).toBe("200px");
    expect(el.style.top).toBe("158px");
  });

  it("clamps into the viewport instead of opening off-screen", () => {
    const el = host();
    // jsdom windows are 1024x768 by default; an anchor past the right and
    // bottom edges must clamp back inside with the 12px margin.
    showCitationTooltip(el, payload(), { x: 5000, y: 5000 });
    const left = parseFloat(el.style.left);
    const top = parseFloat(el.style.top);
    expect(left).toBeLessThanOrEqual(window.innerWidth - 12);
    expect(top).toBeLessThanOrEqual(window.innerHeight - 12);
  });

  it("clamps a near-origin anchor to the margin floor", () => {
    const el = host();
    showCitationTooltip(el, payload(), { x: -40, y: -40 });
    expect(parseFloat(el.style.left)).toBeGreaterThanOrEqual(12);
    expect(parseFloat(el.style.top)).toBeGreaterThanOrEqual(12);
  });

  it("no anchor: never invents a position", () => {
    const el = host();
    showCitationTooltip(el, payload());
    expect(el.hidden).toBe(false);
    expect(el.style.left).toBe("");
    expect(el.style.top).toBe("");
  });

  it("not-found payload renders the empty line", () => {
    const el = host();
    showCitationTooltip(el, payload({ found: false }), { x: 100, y: 100 });
    expect(el.textContent).toContain("No evidence found");
  });

  it("hideCitationTooltip clears content and hides", () => {
    const el = host();
    showCitationTooltip(el, payload(), { x: 100, y: 100 });
    hideCitationTooltip(el);
    expect(el.hidden).toBe(true);
    expect(el.textContent).toBe("");
  });
});

describe("dispatch sites carry the anchor", () => {
  it("drill citation chip click rides anchor coords on the event", async () => {
    const { mountDrillsPanel } = await import("../components/drills-panel.js");
    const container = document.createElement("div");
    document.body.append(container);
    mountDrillsPanel(container, [
      {
        situation: "Bar 24",
        behavior: "b",
        impact: "i",
        action_recommended: "a",
        citation: "evt:12:44",
      },
    ]);
    let seen: { citation: string; anchorX: number; anchorY: number } | null = null;
    container.addEventListener("citation-click", (e: Event) => {
      seen = (e as CustomEvent).detail;
    });
    const chip = container.querySelector<HTMLButtonElement>(".vmx-drill-citation")!;
    chip.dispatchEvent(
      new MouseEvent("click", { bubbles: true, clientX: 320, clientY: 240, detail: 1 }),
    );
    expect(seen).not.toBeNull();
    expect(seen!.citation).toBe("evt:12:44");
    expect(seen!.anchorX).toBe(320);
    expect(seen!.anchorY).toBe(240);
  });

  it("keyboard activation (detail 0) falls back to the chip's rect", async () => {
    const { mountDrillsPanel } = await import("../components/drills-panel.js");
    const container = document.createElement("div");
    document.body.append(container);
    mountDrillsPanel(container, [
      {
        situation: "Bar 24",
        behavior: "b",
        impact: "i",
        action_recommended: "a",
        citation: "evt:12:44",
      },
    ]);
    let seen: { anchorX: number; anchorY: number } | null = null;
    container.addEventListener("citation-click", (e: Event) => {
      seen = (e as CustomEvent).detail;
    });
    const chip = container.querySelector<HTMLButtonElement>(".vmx-drill-citation")!;
    chip.dispatchEvent(new MouseEvent("click", { bubbles: true, detail: 0 }));
    // jsdom rects are zero — the contract is "numbers from the rect", not
    // the stale 0,0 a coordinate-less MouseEvent would have carried anyway;
    // in a real layout these are the chip's left/bottom.
    expect(typeof seen!.anchorX).toBe("number");
    expect(typeof seen!.anchorY).toBe("number");
  });
});
