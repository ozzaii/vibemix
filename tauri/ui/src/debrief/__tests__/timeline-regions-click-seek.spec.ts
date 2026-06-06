// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 — Timeline placeholder click-to-seek + regions.

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  mountTimelinePlaceholder,
  setTimelineReplayWindow,
} from "../components/timeline.js";

afterEach(() => {
  document.body.replaceChildren();
  vi.clearAllTimers();
  vi.useRealTimers();
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

  it("renders real master-input peaks when supplied", () => {
    const div = document.createElement("div");
    document.body.append(div);
    mountTimelinePlaceholder(
      div,
      chapters,
      900,
      [
        [0, 0, 0],
        [255, 255, 255],
        [30, 90, 150],
      ],
    );

    const bed = div.querySelector<HTMLElement>(".vmx-debrief-signal-bed");
    const bars = bed?.querySelectorAll<HTMLElement>("span") ?? [];
    expect(bed?.dataset.source).toBe("master-input");
    expect(bed?.style.getPropertyValue("--vmx-signal-bars")).toBe("3");
    expect(bars.length).toBe(3);
    expect(bars[1]?.dataset.low).toBe("255");
    expect(bars[1]?.style.getPropertyValue("--vmx-bar-h")).toBe("92%");
  });

  it("deep-link highlights exact citation ids with percent signs", () => {
    const div = document.createElement("div");
    document.body.append(div);
    mountTimelinePlaceholder(
      div,
      [
        {
          id: "track-percent",
          start: 12,
          end: 40,
          label: "Kick handoff",
          citation_event_id: "ev:KICK@%",
        },
      ],
      60,
    );

    window.dispatchEvent(
      new CustomEvent("vmx-debrief-deeplink", {
        detail: { eventId: "ev:KICK@%", timestampS: 12 },
      }),
    );

    expect(
      div
        .querySelector(".vmx-debrief-region--highlight")
        ?.getAttribute("data-citation-event-id"),
    ).toBe("ev:KICK@%");
  });

  it("ignores deep-links with non-finite timestamps", () => {
    const div = document.createElement("div");
    document.body.append(div);
    mountTimelinePlaceholder(div, chapters, 900);

    window.dispatchEvent(
      new CustomEvent("vmx-debrief-deeplink", {
        detail: { timestampS: Number.NaN },
      }),
    );

    expect(div.querySelector(".vmx-debrief-region--highlight")).toBeNull();
  });

  it("renders and updates the near-miss replay window on the same timeline", () => {
    const div = document.createElement("div");
    document.body.append(div);
    const onReplay = vi.fn();
    div.addEventListener("replay-window-clicked", (e: Event) => {
      onReplay((e as CustomEvent).detail);
    });
    mountTimelinePlaceholder(div, chapters, 900);

    setTimelineReplayWindow(div, { start: 120, end: 150 }, 900);
    const marker = div.querySelector<HTMLButtonElement>(".vmx-debrief-replay-window");
    expect(marker?.dataset.startS).toBe("120");
    expect(marker?.style.left).toBe("13.333333333333334%");

    setTimelineReplayWindow(div, { start: 300, end: 360 }, 900);
    expect(div.querySelectorAll(".vmx-debrief-replay-window").length).toBe(1);
    marker?.click();
    expect(onReplay).toHaveBeenCalledWith({
      time: 300,
      window: [300, 360],
    });
  });
});
