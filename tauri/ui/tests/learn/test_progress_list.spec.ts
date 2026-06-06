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
    lesson_id: "L1.01",
    title: "opening dialog",
    course_id: "course_1_anatomy",
    course_label: "Course 1 · Anatomy",
    status: "empty",
    ...overrides,
  };
}

const SAMPLE_LESSONS: ReadonlyArray<ProgressListEntry> = [
  mkLesson({
    lesson_id: "L1.01",
    title: "opening dialog",
    status: "completed",
  }),
  mkLesson({
    lesson_id: "L1.02",
    title: "meet your controller",
    status: "completed",
  }),
  mkLesson({
    lesson_id: "L1.03",
    title: "channel strip",
    status: "in-progress",
  }),
  mkLesson({
    lesson_id: "L1.04",
    title: "crossfader",
    status: "empty",
  }),
  // Course 2 group
  mkLesson({
    lesson_id: "L2.01",
    title: "beatmatching by ear",
    course_id: "course_2_transitions",
    course_label: "Course 2 · Transitions",
    status: "empty",
  }),
  mkLesson({
    lesson_id: "L2.02",
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

  it("opens only the relevant course by default", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);

    const groups = Array.from(
      root.querySelectorAll<HTMLElement>(".vmx-progress-list__group"),
    );

    expect(groups.map((group) => group.dataset.expanded)).toEqual([
      "true",
      "false",
    ]);
    expect(
      groups[0]?.querySelector<HTMLElement>(".vmx-progress-list__group-body")
        ?.hidden,
    ).toBe(false);
    expect(
      groups[1]?.querySelector<HTMLElement>(".vmx-progress-list__group-body")
        ?.hidden,
    ).toBe(true);
  });

  it("expands collapsed courses without replacing the lesson map", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    const course2 = root.querySelector<HTMLElement>(
      "[data-course='course_2_transitions']",
    );
    const toggle = course2?.querySelector<HTMLButtonElement>(
      ".vmx-progress-list__group-toggle",
    );

    expect(toggle?.getAttribute("aria-expanded")).toBe("false");
    toggle!.click();

    expect(course2?.dataset.expanded).toBe("true");
    expect(toggle?.getAttribute("aria-expanded")).toBe("true");
    expect(
      course2?.querySelector<HTMLElement>(".vmx-progress-list__group-body")
        ?.hidden,
    ).toBe(false);
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

  it("completed buttons announce replay in aria/title text", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    const first = root.querySelector<HTMLButtonElement>(
      ".vmx-progress-list__lesson",
    );
    expect(first?.getAttribute("aria-label")).toBe(
      "opening dialog, completed, press to replay",
    );
    expect(first?.getAttribute("title")).toBe("press to replay this lesson.");
  });

  it("in-progress buttons announce retry without adding visible chrome", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    const retry = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L1.03']",
    );
    expect(retry?.getAttribute("aria-label")).toBe(
      "channel strip, in-progress, retry",
    );
    expect(retry?.getAttribute("title")).toBe("retry this lesson.");
    expect(retry?.querySelector(".vmx-progress-list__tag")).toBeNull();
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
      "[data-lesson-id='L1.04']",
    );
    btn!.click();
    expect(onPick).toHaveBeenCalledTimes(1);
    expect(onPick).toHaveBeenCalledWith("L1.04", "fresh");
  });

  it("clicking a completed lesson fires onPickLesson with level='replay'", () => {
    const onPick = vi.fn();
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: onPick,
    });
    document.body.append(root);
    const btn = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L1.01']",
    );
    btn!.click();
    expect(onPick).toHaveBeenCalledTimes(1);
    expect(onPick).toHaveBeenCalledWith("L1.01", "replay");
  });

  it("clicking an in-progress lesson fires onPickLesson with level='fresh'", () => {
    const onPick = vi.fn();
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: onPick,
    });
    document.body.append(root);
    const btn = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L1.03']",
    );
    btn!.click();
    expect(onPick).toHaveBeenCalledWith("L1.03", "fresh");
  });

  it("does not fire onPickLesson for a locked lesson", () => {
    const onPick = vi.fn();
    const onLocked = vi.fn();
    const lockedLesson = mkLesson({
      lesson_id: "L2.01",
      title: "beatmatching by ear",
      course_id: "course_2_transitions",
      course_label: "Course 2 · Transitions",
      locked: true,
      lock_reason: "pass course 1 first",
    });
    const root = renderProgressList({
      lessons: [lockedLesson],
      onPickLesson: onPick,
      onLockedLesson: onLocked,
    });
    document.body.append(root);
    const btn = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L2.01']",
    );
    expect(btn?.dataset.locked).toBe("true");
    expect(btn?.getAttribute("aria-disabled")).toBe("true");
    expect(btn?.querySelector(".vmx-progress-list__tag")?.textContent).toBe(
      "locked",
    );
    expect(btn?.getAttribute("aria-label")).toBe(
      "beatmatching by ear, empty, locked, pass course 1 first",
    );
    expect(btn?.getAttribute("title")).toBe("pass course 1 first");
    btn!.click();
    expect(onPick).not.toHaveBeenCalled();
    expect(onLocked).toHaveBeenCalledTimes(1);
    expect(onLocked).toHaveBeenCalledWith(lockedLesson);
  });

  it("marks the recommended lesson with a small next tag", () => {
    const root = renderProgressList({
      lessons: [
        mkLesson({
          lesson_id: "L1.03",
          title: "channel strip",
          is_recommended: true,
        }),
      ],
      onPickLesson: () => {},
    });
    document.body.append(root);
    const btn = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L1.03']",
    );
    expect(btn?.dataset.recommended).toBe("true");
    expect(btn?.getAttribute("aria-label")).toBe(
      "channel strip, empty, next",
    );
    expect(btn?.querySelector(".vmx-progress-list__tag")?.textContent).toBe(
      "next",
    );
  });

  it("marks banked practice rows without stealing the whole map", () => {
    const root = renderProgressList({
      lessons: [
        mkLesson({
          lesson_id: "L1.03",
          title: "channel strip",
          status: "in-progress",
          practice_bank_count: 2,
        }),
      ],
      onPickLesson: () => {},
    });
    document.body.append(root);

    const btn = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L1.03']",
    );
    const tag = btn?.querySelector<HTMLElement>(".vmx-progress-list__tag");

    expect(btn?.dataset.practiceBanked).toBe("true");
    expect(btn?.dataset.practiceBank).toBe("2");
    expect(tag?.textContent).toBe("banked");
    expect(tag?.dataset.kind).toBe("banked");
    expect(btn?.getAttribute("aria-label")).toBe(
      "channel strip, in-progress, practice bank 2 of 3, retry",
    );
    expect(btn?.getAttribute("title")).toBe(
      "practice bank 2 of 3. press to finish this lesson.",
    );
  });

  it("keeps next as the visible tag when a banked row is recommended", () => {
    const root = renderProgressList({
      lessons: [
        mkLesson({
          lesson_id: "L1.03",
          title: "channel strip",
          status: "in-progress",
          is_recommended: true,
          practice_bank_count: 3,
        }),
      ],
      onPickLesson: () => {},
    });
    document.body.append(root);

    const btn = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L1.03']",
    );
    const tag = btn?.querySelector<HTMLElement>(".vmx-progress-list__tag");

    expect(btn?.dataset.practiceBanked).toBe("true");
    expect(tag?.textContent).toBe("next");
    expect(tag?.dataset.kind).toBe("next");
    expect(btn?.getAttribute("aria-label")).toBe(
      "channel strip, in-progress, next, practice bank 3 of 3, retry",
    );
  });
});

describe("progress-list — empty state", () => {
  it("shows screen-deck readiness when showNoControllerHint=true", () => {
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
    expect(hint!.textContent).toBe("screen deck is ready");
    expect(NO_CONTROLLER_HINT).toBe("screen deck is ready");
  });

  it("does NOT render the hint banner when showNoControllerHint is falsey", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    expect(root.querySelector(".vmx-progress-list__no-controller")).toBeNull();
  });

  it("the open course stays focus-traversable when the hint is visible", () => {
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
    const openButtons = buttons.filter(
      (btn) =>
        btn.closest<HTMLElement>(".vmx-progress-list__group")?.dataset
          .expanded === "true",
    );
    expect(openButtons.map((btn) => btn.dataset.lessonId)).toEqual([
      "L1.01",
      "L1.02",
      "L1.03",
      "L1.04",
    ]);
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

  it("ArrowDown at the bottom of the open course clamps (no wrap)", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    const buttons = Array.from(
      root.querySelectorAll<HTMLButtonElement>(".vmx-progress-list__lesson"),
    );
    const last = buttons.find((btn) => btn.dataset.lessonId === "L1.04")!;
    last.focus();
    last.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }),
    );
    expect(document.activeElement).toBe(last);
  });

  it("ArrowDown can move into another course after that course is expanded", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    root.querySelector<HTMLButtonElement>(
      "[data-course='course_2_transitions'] .vmx-progress-list__group-toggle",
    )!.click();
    const l104 = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L1.04']",
    )!;
    const l201 = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L2.01']",
    )!;

    l104.focus();
    l104.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }),
    );

    expect(document.activeElement).toBe(l201);
  });
});

describe("progress-list — setStatus", () => {
  it("setStatus(lesson_id, 'completed') flips the dot + button data-status", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);
    const result = root.setStatus("L1.04", "completed");
    expect(result).toBe(true);
    const btn = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L1.04']",
    );
    expect(btn?.dataset.status).toBe("completed");
    expect(btn?.getAttribute("aria-label")).toBe(
      "crossfader, completed, press to replay",
    );
    expect(btn?.getAttribute("title")).toBe("press to replay this lesson.");
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
    root.setStatus("L1.04", "completed");
    const btn = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L1.04']",
    );
    btn!.click();
    expect(onPick).toHaveBeenCalledWith("L1.04", "replay");
  });

  it("setStatus refreshes the course summary", () => {
    const root = renderProgressList({
      lessons: SAMPLE_LESSONS,
      onPickLesson: () => {},
    });
    document.body.append(root);

    expect(
      root.querySelector<HTMLElement>(
        "[data-course='course_1_anatomy'] .vmx-progress-list__group-summary",
      )?.textContent,
    ).toBe("2/4 done, in progress");

    root.setStatus("L1.03", "completed");

    expect(
      root.querySelector<HTMLElement>(
        "[data-course='course_1_anatomy'] .vmx-progress-list__group-summary",
      )?.textContent,
    ).toBe("3/4 done");
  });

  it("setStatus clears the banked row treatment after completion", () => {
    const root = renderProgressList({
      lessons: [
        mkLesson({
          lesson_id: "L1.03",
          title: "channel strip",
          status: "in-progress",
          practice_bank_count: 2,
        }),
      ],
      onPickLesson: () => {},
    });
    document.body.append(root);

    root.setStatus("L1.03", "completed");

    const btn = root.querySelector<HTMLButtonElement>(
      "[data-lesson-id='L1.03']",
    );
    expect(btn?.dataset.practiceBanked).toBe("false");
    expect(btn?.querySelector(".vmx-progress-list__tag")).toBeNull();
    expect(btn?.getAttribute("aria-label")).toBe(
      "channel strip, completed, press to replay",
    );
  });

  it("course summaries call out a banked unfinished lesson", () => {
    const root = renderProgressList({
      lessons: [
        mkLesson({
          lesson_id: "L1.01",
          title: "opening dialog",
          status: "completed",
        }),
        mkLesson({
          lesson_id: "L1.03",
          title: "channel strip",
          status: "in-progress",
          practice_bank_count: 1,
        }),
      ],
      onPickLesson: () => {},
    });
    document.body.append(root);

    expect(
      root.querySelector<HTMLElement>(
        "[data-course='course_1_anatomy'] .vmx-progress-list__group-summary",
      )?.textContent,
    ).toBe("1/2 done, banked");
  });
});
