// SPDX-License-Identifier: Apache-2.0

import { describe, expect, it } from "vitest";
import {
  buildProgressEntries,
  COURSE_REGISTRY,
  firstRecommendedLessonId,
} from "../../src/learn/lesson/curriculum-meta.js";

describe("curriculum meta projection", () => {
  it("keeps course 1 open and locks later courses by default", () => {
    const entries = buildProgressEntries(null);

    expect(entries.find((entry) => entry.lesson_id === "L1.01")?.locked).toBe(
      false,
    );
    expect(entries.find((entry) => entry.lesson_id === "L2.01")?.locked).toBe(
      true,
    );
    expect(entries.find((entry) => entry.lesson_id === "L3.01")?.locked).toBe(
      true,
    );
    expect(firstRecommendedLessonId(null)).toBe("L1.01");
  });

  it("uses unlock flags to release courses 2 and 3", () => {
    const entries = buildProgressEntries({
      course_2_unlocked: true,
      course_3_unlocked: true,
      lessons: {},
    });

    expect(entries.find((entry) => entry.lesson_id === "L2.01")?.locked).toBe(
      false,
    );
    expect(entries.find((entry) => entry.lesson_id === "L3.01")?.locked).toBe(
      false,
    );
  });

  it("carries the course capability contract without rendering it as a wall", () => {
    expect(COURSE_REGISTRY.course_1_anatomy.frontstage_mode).toBe(
      "practice_booth",
    );
    expect(COURSE_REGISTRY.course_1_anatomy.capabilities).toContain(
      "library_exemplars",
    );
    expect(COURSE_REGISTRY.course_3_play_mode.frontstage_mode).toBe(
      "live_play_mode",
    );
    expect(COURSE_REGISTRY.course_3_play_mode.capabilities).toContain(
      "live_audio",
    );
  });

  it("recommends the first unlocked unfinished lesson", () => {
    const progress = {
      lessons: {
        "L1.01": { completed: true },
        "L1.02": { completed: true },
      },
    };
    const entries = buildProgressEntries(progress);

    expect(firstRecommendedLessonId(progress)).toBe("L1.03");
    expect(entries.find((entry) => entry.lesson_id === "L1.03")?.is_recommended)
      .toBe(true);
  });

  it("marks started but unfinished rows as in-progress", () => {
    const progress = {
      lessons: {
        "L1.03": {
          completed: false,
          completed_at: null,
          strikes_used: 0,
        },
      },
    };

    const entries = buildProgressEntries(progress);

    expect(entries.find((entry) => entry.lesson_id === "L1.03")?.status).toBe(
      "in-progress",
    );
    expect(firstRecommendedLessonId(progress)).toBe("L1.03");
  });

  it("carries strike memory for adaptive retry cues", () => {
    const progress = {
      lessons: {
        "L1.03": {
          completed: false,
          completed_at: null,
          strikes_used: 2,
        },
      },
    };

    const retry = buildProgressEntries(progress).find(
      (entry) => entry.lesson_id === "L1.03",
    );

    expect(retry?.status).toBe("in-progress");
    expect(retry?.strikes_used).toBe(2);
    expect(retry?.is_recommended).toBe(true);
  });

  it("preserves completed locked-course rows for replay orientation", () => {
    const entries = buildProgressEntries({
      course_2_unlocked: false,
      lessons: {
        "L2.01": { completed: true },
      },
    });

    const completedCourse2 = entries.find((entry) => entry.lesson_id === "L2.01");
    expect(completedCourse2?.status).toBe("completed");
    expect(completedCourse2?.locked).toBe(false);
  });
});
