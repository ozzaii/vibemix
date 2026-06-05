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

const referral = {
  lesson_id: "L2.01",
  course_id: "course_2_transitions",
  course_label: "Course 2: Transitions",
  skill_id: "beatmatching",
  skill_label: "beatmatching",
  title: "beatmatching by ear",
  reason: "Debrief found tempo drift.",
  cta: "Practice beatmatching by ear",
};

afterEach(() => {
  document.body.replaceChildren();
});

describe("drills-panel", () => {
  it("titles each card with the situation and renders 3 SBI rows (no 'Drill N' filler)", () => {
    const div = document.createElement("div");
    document.body.append(div);
    mountDrillsPanel(div, [drill, drill, drill]);

    const articles = Array.from(
      div.querySelectorAll("article.vmx-drill"),
    );
    expect(articles.length).toBe(3);
    for (const a of articles) {
      // The real situation line is the title, not "Drill 1/2/3".
      expect(a.querySelector(".vmx-drill-title")?.textContent).toBe("S");
      const dts = a.querySelectorAll("dt");
      const dds = a.querySelectorAll("dd");
      expect(dts.length).toBe(3);
      expect(dds.length).toBe(3);
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

  it("learn referral renders a practice CTA with lesson metadata", () => {
    const div = document.createElement("div");
    document.body.append(div);
    mountDrillsPanel(div, [
      { ...drill, learn_referral: referral },
      drill,
      drill,
    ]);

    const button = div.querySelector<HTMLButtonElement>(".vmx-drill-learn");
    expect(button?.textContent).toBe("Practice beatmatching by ear");
    expect(button?.dataset.lessonId).toBe("L2.01");
    expect(div.querySelector(".vmx-drill-learn-meta")?.textContent).toContain(
      "L2.01",
    );
  });

  it("learn referral CTA emits learn-referral-click event with detail", () => {
    const div = document.createElement("div");
    document.body.append(div);
    const onClick = vi.fn();
    div.addEventListener("learn-referral-click", (e: Event) => {
      onClick((e as CustomEvent).detail);
    });
    mountDrillsPanel(div, [
      { ...drill, learn_referral: referral },
      drill,
      drill,
    ]);

    div.querySelector<HTMLButtonElement>(".vmx-drill-learn")?.click();

    expect(onClick).toHaveBeenCalledWith({ referral });
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
