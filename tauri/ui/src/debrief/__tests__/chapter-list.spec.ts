// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 — chapter-list vitest spec.

import { afterEach, describe, expect, it, vi } from "vitest";

import { mountChapterList } from "../components/chapter-list.js";

afterEach(() => {
  document.body.replaceChildren();
});

describe("chapter-list", () => {
  it("renders one button per chapter with data-chapter-id", () => {
    const ul = document.createElement("ol");
    document.body.append(ul);
    mountChapterList(ul, [
      {
        id: "track-01",
        start: 0,
        end: 300,
        label: "Track 1: A",
        kind: "track",
        citation_event_id: "ev:TRACK_CHANGE@0.000",
      },
      {
        id: "track-02",
        start: 300,
        end: 600,
        label: "Track 2: B",
        kind: "track",
        citation_event_id: "ev:TRACK_CHANGE@300.000",
      },
    ]);
    const buttons = ul.querySelectorAll<HTMLButtonElement>(
      "button.vmx-debrief-chapter-btn",
    );
    expect(buttons.length).toBe(2);
    const b0 = buttons[0];
    const b1 = buttons[1];
    expect(b0).toBeDefined();
    expect(b1).toBeDefined();
    expect(b0!.dataset.chapterId).toBe("track-01");
    expect(b1!.dataset.kind).toBe("track");
  });

  it("emits chapter-selected with citation_event_id on click", () => {
    const ul = document.createElement("ol");
    document.body.append(ul);
    const onSelect = vi.fn();
    ul.addEventListener("chapter-selected", (e: Event) => {
      onSelect((e as CustomEvent).detail);
    });
    mountChapterList(ul, [
      {
        id: "track-01",
        start: 0,
        end: 300,
        label: "Track 1",
        kind: "track",
        citation_event_id: "ev:T@0",
      },
    ]);
    ul.querySelector<HTMLButtonElement>("button")?.click();
    expect(onSelect).toHaveBeenCalledWith({
      id: "track-01",
      start: 0,
      citation_event_id: "ev:T@0",
    });
  });

  it("re-mount clears previous children", () => {
    const ul = document.createElement("ol");
    document.body.append(ul);
    mountChapterList(ul, [
      { id: "a", start: 0, end: 1, label: "A", kind: "track", citation_event_id: "ev:A@0" },
    ]);
    mountChapterList(ul, [
      { id: "b", start: 0, end: 1, label: "B", kind: "phase", citation_event_id: "ev:B@0" },
      { id: "c", start: 1, end: 2, label: "C", kind: "phase", citation_event_id: "ev:C@1" },
    ]);
    expect(ul.querySelectorAll("button").length).toBe(2);
  });
});
