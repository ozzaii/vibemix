// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 — DrillsPanel vitest spec.

import { afterEach, describe, expect, it, vi } from "vitest";

import { mountDrillsPanel } from "../components/drills-panel.js";

const drill = {
  situation: "S",
  behavior: "B [ev:M@1]",
  impact: "I [ev:P@2]",
  action_recommended: "A [track:t1]",
  citation: "[ev:M@1]",
};

afterEach(() => {
  document.body.replaceChildren();
});

describe("drills-panel", () => {
  it("renders 3 articles with 4 <dt>/<dd> rows each", () => {
    const div = document.createElement("div");
    document.body.append(div);
    mountDrillsPanel(div, [drill, drill, drill]);

    const articles = Array.from(
      div.querySelectorAll("article.vmx-drill"),
    );
    expect(articles.length).toBe(3);
    for (const a of articles) {
      const dts = a.querySelectorAll("dt");
      const dds = a.querySelectorAll("dd");
      expect(dts.length).toBe(4);
      expect(dds.length).toBe(4);
    }
  });

  it("citation chip shows the [ev:*] tag verbatim", () => {
    const div = document.createElement("div");
    document.body.append(div);
    mountDrillsPanel(div, [drill, drill, drill]);
    const chips = div.querySelectorAll("button.vmx-drill-citation");
    expect(chips.length).toBe(3);
    expect((chips[0] as HTMLElement).textContent).toBe("[ev:M@1]");
  });

  it("citation chip click emits citation-click event with detail", () => {
    const div = document.createElement("div");
    document.body.append(div);
    const onClick = vi.fn();
    div.addEventListener("citation-click", (e: Event) => {
      onClick((e as CustomEvent).detail);
    });
    mountDrillsPanel(div, [drill, drill, drill]);
    (div.querySelector("button.vmx-drill-citation") as HTMLButtonElement).click();
    expect(onClick).toHaveBeenCalledWith({ citation: "[ev:M@1]" });
  });

  it("drill text is rendered via textContent (no XSS surface)", () => {
    const div = document.createElement("div");
    document.body.append(div);
    const malicious = {
      situation: "<script>alert(1)</script>",
      behavior: "B [ev:M@1]",
      impact: "I [ev:P@2]",
      action_recommended: "A [track:t1]",
      citation: "[ev:M@1]",
    };
    mountDrillsPanel(div, [malicious, malicious, malicious]);
    expect(div.querySelector("script")).toBeNull();
    // The text appears as text, not parsed as HTML.
    expect(div.innerHTML).toContain("&lt;script&gt;");
  });
});
