// SPDX-License-Identifier: Apache-2.0
//
// Phase 92 Plan 05 — LessonHud component (UI-SPEC §Component Inventory).
//
// 56 px-tall rail between titlebar and stage. Three regions:
//   - LEFT:   course chip (e.g. `COURSE 0 · HELLO WORLD`)
//             — Saira wdth 85 wght 600 10px UPPERCASE 0.22em silk-22
//   - CENTER: lesson title (e.g. `press play`, upcased via CSS)
//             — Saira wdth 85 wght 600 14px UPPERCASE 0.12em silk-65
//             + progress dots row (6 px circles; pending=silk-22 outline,
//               current=amber+glow-faint, completed=silk-65 solid)
//   - RIGHT:  progress index (e.g. `2 OF 3`) — the lesson's position in
//             the course, not the raw curriculum key
//             — JetBrains Mono 11px UPPERCASE 0.18em silk-22
//
// Border-bottom 1px var(--glass-edge); NO panel fill — the cinematic
// void shows through. Matches the rebuild-session mock's `.rail`
// exactly (UI-SPEC §Lesson HUD layout lines 222-253).
//
// Progress dots are <button>s — Tab-reachable per UI-SPEC §Accessibility
// line 329. The Enter handler (replay completed lesson via
// `ipc.learn.start_lesson { level: "replay" }`) is wired by
// learn-window.ts; this component only renders the affordance.

import { COURSE_REGISTRY, type CourseId } from "./curriculum-meta.js";

/**
 * Legacy aliases and Course 0 labels that are outside the beginner chooser
 * projection. Beginner course labels come from generated curriculum metadata.
 */
const COURSE_DISPLAY_FALLBACKS: Readonly<Record<string, string>> = {
  course_0: "COURSE 0 · HELLO WORLD",
  course_1: "COURSE 1 · ANATOMY",
  course_2: "COURSE 2 · TRANSITIONS",
  course_3: "COURSE 3 · PLAY-MODE",
};

export interface LessonHudProgressDot {
  lesson_id: string;
  status: "pending" | "current" | "completed";
}

export interface LessonHudOpts {
  course_id: string;
  lesson_id: string;
  title: string;
  progress_dots: ReadonlyArray<LessonHudProgressDot>;
}

export interface LessonHudHandle extends HTMLDivElement {
  update(opts: Partial<LessonHudOpts>): void;
}

export const PENDING_DOT_TOOLTIP = "prerequisite lessons not yet complete.";

/**
 * Build the lesson-HUD element. Returns the root `<div class="learn-hud">`
 * with an attached `.update(opts)` method for partial-state refresh.
 *
 * The component is hand-authored DOM (no framework) — mirrors the P91
 * pattern in `tauri/ui/src/learn/components/{titlebar,status-bar,empty-state}.ts`.
 */
export function LessonHud(opts: LessonHudOpts): LessonHudHandle {
  const root = document.createElement("div") as LessonHudHandle;
  root.className = "learn-hud";

  // --- Left: course chip ---
  const courseChip = document.createElement("div");
  courseChip.className = "course-chip";
  courseChip.textContent = courseDisplayFor(opts.course_id);
  root.appendChild(courseChip);

  // --- Center: lesson title + progress dots ---
  const center = document.createElement("div");
  center.className = "lesson-center";
  const titleEl = document.createElement("div");
  titleEl.className = "lesson-title";
  titleEl.textContent = opts.title;
  const dotsRow = document.createElement("div");
  dotsRow.className = "dots";
  dotsRow.setAttribute("role", "list");
  dotsRow.setAttribute("aria-label", "lesson progress");
  renderDots(dotsRow, opts.progress_dots);
  center.appendChild(titleEl);
  center.appendChild(dotsRow);
  root.appendChild(center);

  // --- Right: progress index ---
  const indexEl = document.createElement("div");
  indexEl.className = "progress-index";
  indexEl.textContent = formatProgressIndex(opts.lesson_id, opts.progress_dots);
  root.appendChild(indexEl);

  // --- .update partial-state refresh ---
  // Keeps the latest options in a closure so partial updates can compose
  // (e.g. only `progress_dots` changing should still re-render the
  // dependent progress index correctly).
  let current: LessonHudOpts = {
    course_id: opts.course_id,
    lesson_id: opts.lesson_id,
    title: opts.title,
    progress_dots: opts.progress_dots,
  };

  root.update = (next: Partial<LessonHudOpts>) => {
    current = {
      course_id: next.course_id ?? current.course_id,
      lesson_id: next.lesson_id ?? current.lesson_id,
      title: next.title ?? current.title,
      progress_dots: next.progress_dots ?? current.progress_dots,
    };
    if (next.course_id !== undefined) {
      courseChip.textContent = courseDisplayFor(current.course_id);
    }
    if (next.title !== undefined) {
      titleEl.textContent = current.title;
    }
    if (next.progress_dots !== undefined || next.lesson_id !== undefined) {
      renderDots(dotsRow, current.progress_dots);
      indexEl.textContent = formatProgressIndex(
        current.lesson_id,
        current.progress_dots,
      );
    }
  };

  return root;
}

function courseDisplayFor(courseId: string): string {
  const registryLabel = COURSE_REGISTRY[courseId as CourseId]?.hud_label;
  if (registryLabel !== undefined) return registryLabel;
  const named = COURSE_DISPLAY_FALLBACKS[courseId];
  if (named !== undefined) return named;
  return `COURSE · ${courseId.toUpperCase()}`;
}

/**
 * Format the right-region progress index as a plain `N OF M` position so
 * the raw curriculum key (e.g. `L1.02`) never reaches user-facing copy —
 * the title + course chip already carry the semantic name.
 *
 * - The numerator is the 1-based position of the active lesson within the
 *   dots row (the dot whose lesson_id matches, else the `current` dot).
 * - The denominator is the count of dots — for the P92 hello-world
 *   1-lesson course, this is `OF 1`; for the future 16-lesson Course 1
 *   it becomes `OF 16`.
 */
function formatProgressIndex(
  lessonId: string,
  dots: ReadonlyArray<LessonHudProgressDot>,
): string {
  const head = lessonId.split("-")[0] ?? lessonId;
  let position = dots.findIndex((dot) => dot.lesson_id === head);
  if (position < 0) {
    position = dots.findIndex((dot) => dot.status === "current");
  }
  const oneBased = position >= 0 ? position + 1 : Math.max(1, dots.length);
  return `${oneBased} OF ${dots.length}`;
}

/**
 * Render the progress-dots row into the given container, replacing any
 * prior dots. Each dot is a `<button>` so it lands in the Tab cycle
 * per UI-SPEC §Accessibility line 329 — the Enter-on-completed-dot
 * replay handler is wired separately by learn-window.ts via event
 * delegation on the dots row.
 */
function renderDots(
  container: HTMLElement,
  dots: ReadonlyArray<LessonHudProgressDot>,
): void {
  container.textContent = "";
  for (const dot of dots) {
    const d = document.createElement("button");
    d.type = "button";
    d.className = "dot";
    d.setAttribute("data-status", dot.status);
    d.setAttribute("data-lesson-id", dot.lesson_id);
    d.setAttribute("role", "listitem");
    d.setAttribute("aria-label", dotAriaLabel(dot));
    if (dot.status === "current") {
      d.setAttribute("aria-current", "step");
    } else if (dot.status === "pending") {
      d.setAttribute("aria-disabled", "true");
      d.setAttribute("title", PENDING_DOT_TOOLTIP);
    } else if (dot.status === "completed") {
      d.setAttribute("title", "press to replay this lesson.");
    }
    container.appendChild(d);
  }
}

function dotAriaLabel(dot: LessonHudProgressDot): string {
  if (dot.status === "completed") {
    return `lesson ${dot.lesson_id}, completed, press to replay`;
  }
  if (dot.status === "current") {
    return `lesson ${dot.lesson_id}, current step`;
  }
  return `lesson ${dot.lesson_id}, pending, prerequisite lessons not yet complete`;
}
