// SPDX-License-Identifier: Apache-2.0
//
// Phase 97 / ONBOARD-05 — frontend curriculum mirror.
//
// The authoritative curriculum lives in src/vibemix/learn/curriculum.py
// (Python module). For v1, the progress-list renders a static frontend
// mirror — 36 lessons across 3 courses (Anatomy 16 + Transitions 14 +
// Play-Mode 6). The mirror is a TS constant kept in lock-step with the
// Python source via a future drift gate (TODO P98 — add a CI test that
// reads curriculum.py and asserts the same ordered list of lesson_ids
// + titles + course_ids matches this file).
//
// Lesson IDs use the v9.0 short form "L1.NN" / "L2.NN" / "L3.NN" without
// the slug suffix that the schema regex ^L[0-9]+\.[0-9]+-.+$ requires for
// ipc.learn.start_lesson envelopes. The progress-list component appends
// a stable slug derived from the title at emit time — see
// `lessonIdWithSlug()` in this module.
//
// This is intentionally a SMALL surface — the v9.0 curriculum is locked,
// adding a 37th lesson is a milestone-scope decision, not a hot-iteration
// path. When v9.1 lands a new lesson, both this file and curriculum.py
// update in the same commit (gated by the future drift test).

import type { ProgressListEntry, LessonStatus } from "./progress-list.js";

/** Course label registry — drives the group headings in the progress-list. */
export const COURSE_LABELS: Readonly<Record<string, string>> = {
  course_1_anatomy: "Course 1 · Anatomy",
  course_2_transitions: "Course 2 · Transitions",
  course_3_play_mode: "Course 3 · Play Mode",
};

interface CurriculumMetaRow {
  short_id: string; // "L1.01" — what curriculum.py keys CURRICULUM with
  course_id: keyof typeof COURSE_LABELS;
  title: string;
  /** Slug-tail appended to the short_id to form the canonical lesson_id
   *  matching the schema regex ^L[0-9]+\.[0-9]+-.+$ (e.g.
   *  "L1.01-opening-dialog"). MUST match the curriculum.py
   *  ``transcript_path`` slug — drift is caught by the future P98 CI gate. */
  slug: string;
}

/** Canonical lesson order — Course 1 (16) → Course 2 (14) → Course 3 (6).
 *  Mirrors src/vibemix/learn/curriculum.py:CURRICULUM. */
export const CURRICULUM_META: ReadonlyArray<CurriculumMetaRow> = [
  // Course 1 — Anatomy of a Deck (16)
  { short_id: "L1.01", course_id: "course_1_anatomy", title: "opening dialog", slug: "opening-dialog" },
  { short_id: "L1.02", course_id: "course_1_anatomy", title: "meet your controller", slug: "meet-controller" },
  { short_id: "L1.03", course_id: "course_1_anatomy", title: "channel strip", slug: "channel-strip" },
  { short_id: "L1.04", course_id: "course_1_anatomy", title: "crossfader", slug: "crossfader" },
  { short_id: "L1.05", course_id: "course_1_anatomy", title: "pitch fader", slug: "pitch-fader" },
  { short_id: "L1.06", course_id: "course_1_anatomy", title: "transport buttons", slug: "transport-buttons" },
  { short_id: "L1.07", course_id: "course_1_anatomy", title: "jog wheel", slug: "jog-wheel" },
  { short_id: "L1.08", course_id: "course_1_anatomy", title: "loop section", slug: "loop-section" },
  { short_id: "L1.09", course_id: "course_1_anatomy", title: "master booth headphones", slug: "master-booth-headphones" },
  { short_id: "L1.10", course_id: "course_1_anatomy", title: "filter knob", slug: "filter-knob" },
  { short_id: "L1.11", course_id: "course_1_anatomy", title: "fx pads", slug: "fx-pads" },
  { short_id: "L1.12", course_id: "course_1_anatomy", title: "spot a breakdown by ear", slug: "spot-breakdown-by-ear" },
  { short_id: "L1.13", course_id: "course_1_anatomy", title: "browse the library", slug: "browse-library" },
  { short_id: "L1.14", course_id: "course_1_anatomy", title: "eq as tutor", slug: "eq-as-tutor" },
  { short_id: "L1.15", course_id: "course_1_anatomy", title: "load two tracks", slug: "load-two-tracks" },
  { short_id: "L1.16", course_id: "course_1_anatomy", title: "course 1 recital", slug: "course-1-recital" },
  // Course 2 — Transitions (14)
  { short_id: "L2.01", course_id: "course_2_transitions", title: "beatmatching by ear", slug: "beatmatch-by-ear" },
  { short_id: "L2.02", course_id: "course_2_transitions", title: "beatmatching with sync", slug: "beatmatch-sync" },
  { short_id: "L2.03", course_id: "course_2_transitions", title: "long blend", slug: "long-blend" },
  { short_id: "L2.04", course_id: "course_2_transitions", title: "eq swap", slug: "eq-swap" },
  { short_id: "L2.05", course_id: "course_2_transitions", title: "bassline swap", slug: "bassline-swap" },
  { short_id: "L2.06", course_id: "course_2_transitions", title: "filter fade", slug: "filter-fade" },
  { short_id: "L2.07", course_id: "course_2_transitions", title: "echo-out", slug: "echo-out" },
  { short_id: "L2.08", course_id: "course_2_transitions", title: "drop swap", slug: "drop-swap" },
  { short_id: "L2.09", course_id: "course_2_transitions", title: "loop transition", slug: "loop-transition" },
  { short_id: "L2.10", course_id: "course_2_transitions", title: "hot cues and memory cues", slug: "hot-cues" },
  { short_id: "L2.11", course_id: "course_2_transitions", title: "camelot wheel", slug: "camelot-wheel" },
  { short_id: "L2.12", course_id: "course_2_transitions", title: "phrase matching", slug: "phrase-matching" },
  { short_id: "L2.13", course_id: "course_2_transitions", title: "diagnosing a train wreck", slug: "train-wreck" },
  { short_id: "L2.14", course_id: "course_2_transitions", title: "course 2 recital", slug: "course-2-recital" },
  // Course 3 — Play Mode (6)
  { short_id: "L3.01", course_id: "course_3_play_mode", title: "playing live versus the booth", slug: "live-vs-booth" },
  { short_id: "L3.02", course_id: "course_3_play_mode", title: "reading the floor", slug: "reading-floor" },
  { short_id: "L3.03", course_id: "course_3_play_mode", title: "set programming", slug: "set-programming" },
  { short_id: "L3.04", course_id: "course_3_play_mode", title: "energy curve", slug: "energy-curve" },
  { short_id: "L3.05", course_id: "course_3_play_mode", title: "recovery moves", slug: "recovery-moves" },
  { short_id: "L3.06", course_id: "course_3_play_mode", title: "course 3 recital", slug: "course-3-recital" },
];

/** Build a fully-qualified lesson_id (matching the schema regex
 *  ^L[0-9]+\.[0-9]+-.+$) from a short_id + slug. Exported so the
 *  click handler in learn-window can format the wire envelope. */
export function lessonIdWithSlug(meta: CurriculumMetaRow): string {
  return `${meta.short_id}-${meta.slug}`;
}

/** Project the static curriculum mirror onto the progress-list's
 *  ProgressListEntry shape, applying the per-lesson status from the
 *  `progress` payload that `ipc.learn.progress_state` carries.
 *
 *  Unknown lesson_ids in the payload (or short_ids not present in the
 *  payload) default to "empty". The progress payload uses the FULL
 *  lesson_id (with slug) as its key — we match by short_id prefix +
 *  slug since lessons may carry either form historically. */
export function buildProgressEntries(
  progress: {
    lessons?: Record<
      string,
      { completed?: boolean; strikes_used?: number } | undefined
    >;
  } | null,
): ProgressListEntry[] {
  const lessonsMap = progress?.lessons ?? {};
  return CURRICULUM_META.map((meta) => {
    const fullId = lessonIdWithSlug(meta);
    // Look up by full slug-id first, then by short_id for forward-compat
    // with payloads that still use the bare form.
    const entry = lessonsMap[fullId] ?? lessonsMap[meta.short_id];
    let status: LessonStatus = "empty";
    if (entry?.completed) {
      status = "completed";
    } else if (entry?.strikes_used && entry.strikes_used > 0) {
      status = "in-progress";
    }
    return {
      lesson_id: fullId,
      title: meta.title,
      course_id: meta.course_id,
      course_label: COURSE_LABELS[meta.course_id]!,
      status,
    };
  });
}
