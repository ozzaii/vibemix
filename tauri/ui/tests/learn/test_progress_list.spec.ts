// SPDX-License-Identifier: Apache-2.0
//
// Phase 97 / ONBOARD-05 + ONBOARD-06 — Lesson progress-list contract.
//
// Pins: dot states, group rendering, click-to-pick, replay vs fresh
// level, keyboard nav, empty-state copy verbatim, in-place setStatus.

import { describe, it, expect, afterEach, vi } from "vitest";
import {
  renderProgressList,
  NO_CONTROLLER_HINT,
  type ProgressListEntry,
} from "../../src/learn/lesson/progress-list.js";

afterEach(() => {
  document.body.replaceChildren();
});

function mkLesson(
  overrides: Partial<ProgressListEntry> = {},
): ProgressListEntry {
  return {
    lesson_id: "L1.01-opening-dialog",
    title: "opening dialog",
    course_id: "course_1_anatomy",
    course_label: "Course 1 · Anatomy",
    status: "empty",
    ...overrides,
  };
}

const SAMPLE_LESSONS: ReadonlyArray<ProgressListEntry> = [
  mkLesson({
    lesson_id: "L1.01-opening-dialog",
    title: "opening dialog",
    status: "completed",
  }),
  mkLesson({
    lesson_id: "L1.02-meet-controller",
    title: "meet your controller",
    status: "completed",
  }),
  mkLesson({
    lesson_id: "L1.03-channel-strip",
    title: "channel strip",
    status: "in-progress",
  }),
  mkLesson({
    lesson_id: "L1.04-crossfader",
    title: "crossfader",
    status: "empty",
  }),
  // Course 2 group
  mkLesson({
    lesson_id: "L2.01-beatmatch-by-ear",
    title: "beatmatching by ear",
    course_id: "course_2_transitions",
    course_label: "Course 2 · Transitions",
    status: "empty",
  }),
  mkLesson({
    lesson_id: "L2.02-beatmatch-sync",
    title: "beatmatching with sync",
    course_id: "course_2_transitions",
    course_label: "Course 2 · Transitions",
    status: "empty",
  }),
];

describe("progress-list — rendering", () => {
  it("renders one button per lesson + one group per course", () => {
    const onPick = vi.fn();
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: onPick,
    });
    document.body.append(root);
    const buttons = root.querySelectorAll<HTMLButtonElement>(
      ".vmx-progress-list__lesson",
    );
    expect(buttons).toHaveLength(6);
    const groups = root.querySelectorAll(".vmx-progress-list__group");
    expect(groups).toHaveLength(2); // Course 1 + Course 2
  });

  it("uses the course_label verbatim for the group heading", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    const labels = Array.from(
      root.querySelectorAll<HTMLElement>(".vmx-progress-list__group-label"),
    ).map((el) => el.textContent);
    expect(labels).toEqual(["Course 1 · Anatomy", "Course 2 · Transitions"]);
  });

  it("dot status mirrors entry status (data-status attribute)", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    const dots = Array.from(
      root.querySelectorAll<HTMLElement>(".vmx-progress-list__dot"),
    );
    expect(dots.map((d) => d.dataset.status)).toEqual([
      "completed",
      "completed",
      "in-progress",
      "empty",
      "empty",
      "empty",
    ]);
  });

  it("button carries aria-label = '<title> — <status>'", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    const first = root.querySelector<HTMLButtonElement>(
      ".vmx-progress-list__lesson",
    );
    expect(first?.getAttribute("aria-label")).toBe(
      "opening dialog — completed",
    );
  });

  it("the lesson_id-head is rendered as the right-aligned mono label", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    const idLabels = Array.from(
      root.querySelectorAll<HTMLElement>(".vmx-progress-list__lesson-id"),
    ).map((el) => el.textContent);
    expect(idLabels).toEqual([
      "L1.01",
      "L1.02",
      "L1.03",
      "L1.04",
      "L2.01",
      "L2.02",
    ]);
  });
});

describe("progress-list — pick + level", () => {
  it("clicking an empty lesson fires onPickLesson with level='fresh'", () => {
    const onPick = vi.fn();
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: onPick,
    });
    document.body.append(root);
    // L1.04 is empty.
    const btn = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L1.04-crossfader']",
    );
    btn!.click();
    expect(onPick).toHaveBeenCalledTimes(1);
    expect(onPick).toHaveBeenCalledWith("L1.04-crossfader", "fresh");
  });

  it("clicking a completed lesson fires onPickLesson with level='replay'", () => {
    const onPick = vi.fn();
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: onPick,
    });
    document.body.append(root);
    const btn = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L1.01-opening-dialog']",
    );
    btn!.click();
    expect(onPick).toHaveBeenCalledTimes(1);
    expect(onPick).toHaveBeenCalledWith("L1.01-opening-dialog", "replay");
  });

  it("clicking an in-progress lesson fires onPickLesson with level='fresh'", () => {
    const onPick = vi.fn();
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: onPick,
    });
    document.body.append(root);
    const btn = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L1.03-channel-strip']",
    );
    btn!.click();
    expect(onPick).toHaveBeenCalledWith("L1.03-channel-strip", "fresh");
  });
});

describe("progress-list — empty state", () => {
  it("shows 'no controller? plug one in' verbatim when showNoControllerHint=true", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      showNoControllerHint: true,
      onPickLesson: () => {},
    });
    document.body.append(root);
    const hint = root.querySelector<HTMLElement>(
      ".vmx-progress-list__no-controller",
    );
    expect(hint).not.toBeNull();
    expect(hint!.textContent).toBe("no controller? plug one in");
    expect(NO_CONTROLLER_HINT).toBe("no controller? plug one in");
  });

  it("does NOT render the hint banner when showNoControllerHint is falsey", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    expect(root.querySelector(".vmx-progress-list__no-controller")).toBeNull();
  });

  it("the lesson list stays focus-traversable even when hint is visible", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      showNoControllerHint: true,
      onPickLesson: () => {},
    });
    document.body.append(root);
    const buttons = Array.from(
      root.querySelectorAll<HTMLButtonElement>(
        ".vmx-progress-list__lesson",
      ),
    );
    expect(buttons).toHaveLength(6);
    // All buttons are still type=button + tabbable (default focusable).
    for (const btn of buttons) {
      expect(btn.type).toBe("button");
    }
  });
});

describe("progress-list — keyboard navigation", () => {
  it("ArrowDown moves focus to the next lesson button", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    const buttons = Array.from(
      root.querySelectorAll<HTMLButtonElement>(".vmx-progress-list__lesson"),
    );
    buttons[0]!.focus();
    expect(document.activeElement).toBe(buttons[0]);
    buttons[0]!.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }),
    );
    expect(document.activeElement).toBe(buttons[1]);
  });

  it("ArrowUp moves focus to the previous lesson button", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    const buttons = Array.from(
      root.querySelectorAll<HTMLButtonElement>(".vmx-progress-list__lesson"),
    );
    buttons[2]!.focus();
    buttons[2]!.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }),
    );
    expect(document.activeElement).toBe(buttons[1]);
  });

  it("ArrowDown at the bottom of the list clamps (no wrap)", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    const buttons = Array.from(
      root.querySelectorAll<HTMLButtonElement>(".vmx-progress-list__lesson"),
    );
    const last = buttons[buttons.length - 1]!;
    last.focus();
    last.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }),
    );
    expect(document.activeElement).toBe(last);
  });
});

describe("progress-list — setStatus", () => {
  it("setStatus(lesson_id, 'completed') flips the dot + button data-status", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    const result = root.setStatus("L1.04-crossfader", "completed");
    expect(result).toBe(true);
    const btn = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L1.04-crossfader']",
    );
    expect(btn?.dataset.status).toBe("completed");
    const dot = btn?.querySelector<HTMLElement>(".vmx-progress-list__dot");
    expect(dot?.dataset.status).toBe("completed");
  });

  it("setStatus on an unknown lesson_id returns false (no throw)", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    const result = root.setStatus("L9.99-unknown", "completed");
    expect(result).toBe(false);
  });

  it("after setStatus → click fires with the new level", () => {
    const onPick = vi.fn();
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: onPick,
    });
    document.body.append(root);
    // L1.04 starts empty → fresh.
    root.setStatus("L1.04-crossfader", "completed");
    const btn = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L1.04-crossfader']",
    );
    btn!.click();
    expect(onPick).toHaveBeenCalledWith("L1.04-crossfader", "replay");
  });
});
