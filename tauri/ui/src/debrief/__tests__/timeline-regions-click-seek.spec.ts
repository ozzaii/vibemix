// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 — Timeline placeholder click-to-seek + regions.

import { afterEach, describe, expect, it, vi } from "vitest";

import { mountTimelinePlaceholder } from "../components/timeline.js";

afterEach(() => {
  document.body.replaceChildren();
});

const chapters = [
  {
    id: "track-01",
    start: 0,
    end: 300,
    label: "Track 1",
    citation_event_id: "ev:TRACK_CHANGE@0",
  },
  {
    id: "track-02",
    start: 300,
    end: 900,
    label: "Track 2",
    citation_event_id: "ev:TRACK_CHANGE@300",
  },
];

describe("timeline placeholder", () => {
  it("renders one region per chapter", () => {
    const div = document.createElement("div");
    document.body.append(div);
    mountTimelinePlaceholder(div, chapters, 900);
    const regions = div.querySelectorAll(".vmx-debrief-region");
    expect(regions.length).toBe(2);
  });

  it("region widths are proportional to chapter durations", () => {
    const div = document.createElement("div");
    document.body.append(div);
    mountTimelinePlaceholder(div, chapters, 900);
    const regions = div.querySelectorAll<HTMLElement>(".vmx-debrief-region");
    const r0 = regions[0];
    const r1 = regions[1];
    expect(r0).toBeDefined();
    expect(r1).toBeDefined();
    expect(r0!.style.width.startsWith("33.")).toBe(true);
    expect(r1!.style.width.startsWith("66.")).toBe(true);
  });

  it("region click emits region-clicked with time + citation_event_id", () => {
    const div = document.createElement("div");
    document.body.append(div);
    const onClick = vi.fn();
    div.addEventListener("region-clicked", (e: Event) => {
      onClick((e as CustomEvent).detail);
    });
    mountTimelinePlaceholder(div, chapters, 900);
    (div.querySelectorAll<HTMLElement>(".vmx-debrief-region")[1] as HTMLButtonElement).click();
    expect(onClick).toHaveBeenCalledWith({
      time: 300,
      citation_event_id: "ev:TRACK_CHANGE@300",
    });
  });

  it("empty chapters renders fallback text", () => {
    const div = document.createElement("div");
    document.body.append(div);
    mountTimelinePlaceholder(div, [], 0);
    expect(div.textContent).toContain("No regions to render");
  });
});
