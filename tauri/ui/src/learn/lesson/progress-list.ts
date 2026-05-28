// SPDX-License-Identifier: Apache-2.0
//
// Phase 97 / ONBOARD-05 + ONBOARD-06 — Lesson progress list.
//
// Renders ALL 36 v9.0 lessons grouped by course (Course 1 Anatomy = 16
// lessons, Course 2 Transitions = 14, Course 3 Play Mode = 6). Each
// lesson is a tabbable <button> carrying a status dot:
//
//   - empty       (--silk-22 outline)  : not yet started
//   - in-progress (--silk-40 solid)    : completed_at == null AND
//                                        strikes_used > 0 (started, not done)
//   - completed   (--amber solid)       : completed: true
//
// Click → emit ipc.learn.start_lesson { lesson_id, level: "fresh" | "replay" }
// where level = "replay" when the lesson was already completed, "fresh"
// otherwise. The lesson_id format matches the canonical schema regex
// ^L[0-9]+\.[0-9]+-.+$ from messages.schema.json.
//
// Empty-state: when the rendered controller is `_generic` AND no MIDI
// position has streamed (no detected hardware), the list reads
// "no controller? plug one in" — lowercase, tone-disciplined.
//
// Keyboard-nav: every lesson is a <button>, so Tab walks them in DOM
// order. Arrow Up/Down also nudges focus across siblings within a
// course block. Enter activates (default browser behaviour on buttons).

// Progress-list CSS lives in tauri/ui/src/learn/styles/learn.css under the
// `/* Phase 97 / ONBOARD-05 — progress-list */` block. The learn-side
// components avoid the session-side registerStyle registry to keep the
// learn-window bundle a single CSS surface (see learn-window.ts top-level
// `import "./styles/learn.css"`).

export type LessonStatus = "empty" | "in-progress" | "completed";

export interface ProgressListEntry {
  /** Canonical lesson_id, e.g. "L1.01-opening-dialog". MUST match the
   *  schema regex ^L[0-9]+\.[0-9]+-.+$ so ipc.learn.start_lesson accepts
   *  it. The progress-list component does NOT validate — callers pass
   *  the curriculum keys verbatim. */
  lesson_id: string;
  /** Human-readable lesson title (e.g. "opening dialog"). */
  title: string;
  /** Group label this lesson belongs under (e.g. "Course 1 · Anatomy"). */
  course_label: string;
  /** UPPER_SNAKE course id used for the data-course attribute on the
   *  group element — mirrors curriculum.py COURSE_FRAMES keys
   *  ("course_1_anatomy" etc.). */
  course_id: string;
  status: LessonStatus;
}

export interface ProgressListProps {
  /** Ordered list of lessons. Groups are derived from `course_id`
   *  contiguity — callers SHOULD pass lessons in canonical course
   *  order (Course 1 then Course 2 then Course 3). */
  lessons: ReadonlyArray<ProgressListEntry>;
  /** If true, renders the "no controller? plug one in" empty state
   *  INSTEAD of the lesson list. The list itself stays in the DOM
   *  (focus-traversable for users browsing curriculum without
   *  hardware) but the empty-state banner is the foreground message.
   *  Default false (a controller is detected). */
  showNoControllerHint?: boolean;
  /** Callback fired when the user picks a lesson. The component decides
   *  level based on `status` — already-completed → "replay", else "fresh".
   *  Parent wires this to ipc.learn.start_lesson. */
  onPickLesson: (lesson_id: string, level: "fresh" | "replay") => void;
}

export interface ProgressListHandle extends HTMLDivElement {
  /** Update a single lesson's status in place (e.g. on
   *  ipc.learn.complete_lesson). Returns true if the lesson was found. */
  setStatus(lesson_id: string, status: LessonStatus): boolean;
}

/** No-controller empty-state copy. Lowercase, tone-disciplined. */
export const NO_CONTROLLER_HINT = "no controller? plug one in";

/** Build the progress-list element. Returns the root element with an
 *  attached `.setStatus(lesson_id, status)` updater. */
export function renderProgressList(
  props: ProgressListProps,
): ProgressListHandle {
  const root = document.createElement("div") as ProgressListHandle;
  root.className = "vmx-progress-list";
  root.setAttribute("role", "list");
  root.setAttribute("aria-label", "lessons");

  // Optional no-controller hint at the top — does NOT replace the list,
  // sits as a banner so users browsing curriculum without hardware see
  // the affordance.
  if (props.showNoControllerHint) {
    const hint = document.createElement("div");
    hint.className = "vmx-progress-list__no-controller";
    hint.textContent = NO_CONTROLLER_HINT;
    root.append(hint);
  }

  // Group lessons by course_id (preserving order). Contiguity rule:
  // consecutive entries with the same course_id belong to the same
  // group. Callers SHOULD pass canonical-ordered lessons; we don't
  // re-sort because the v9.0 curriculum order is deliberate.
  let currentGroup: HTMLElement | null = null;
  let currentCourseId: string | null = null;
  const lessonButtons: HTMLButtonElement[] = [];

  for (const lesson of props.lessons) {
    if (lesson.course_id !== currentCourseId) {
      currentGroup = document.createElement("div");
      currentGroup.className = "vmx-progress-list__group";
      currentGroup.dataset.course = lesson.course_id;
      const label = document.createElement("h3");
      label.className = "vmx-progress-list__group-label";
      label.textContent = lesson.course_label;
      currentGroup.append(label);
      root.append(currentGroup);
      currentCourseId = lesson.course_id;
    }

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "vmx-progress-list__lesson";
    btn.dataset.lessonId = lesson.lesson_id;
    btn.dataset.status = lesson.status;
    btn.setAttribute("role", "listitem");
    // Accessible label carries title + status so screen readers announce both.
    btn.setAttribute(
      "aria-label",
      `${lesson.title} — ${lesson.status}`,
    );

    const dot = document.createElement("span");
    dot.className = "vmx-progress-list__dot";
    dot.dataset.status = lesson.status;
    dot.setAttribute("aria-hidden", "true");

    const title = document.createElement("span");
    title.className = "vmx-progress-list__title";
    title.textContent = lesson.title;

    const lessonId = document.createElement("span");
    lessonId.className = "vmx-progress-list__lesson-id";
    // Strip the slug-tail from the lesson_id for the display ID: "L1.02".
    const idHead = lesson.lesson_id.split("-")[0] ?? lesson.lesson_id;
    lessonId.textContent = idHead;

    btn.append(dot, title, lessonId);

    btn.addEventListener("click", () => {
      const level: "fresh" | "replay" =
        btn.dataset.status === "completed" ? "replay" : "fresh";
      props.onPickLesson(lesson.lesson_id, level);
    });

    // Keyboard nav — ArrowUp / ArrowDown move focus across siblings.
    btn.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
        ev.preventDefault();
        const idx = lessonButtons.indexOf(btn);
        if (idx < 0) return;
        const nextIdx =
          ev.key === "ArrowDown"
            ? Math.min(idx + 1, lessonButtons.length - 1)
            : Math.max(idx - 1, 0);
        lessonButtons[nextIdx]?.focus();
      }
    });

    currentGroup!.append(btn);
    lessonButtons.push(btn);
  }

  root.setStatus = (lesson_id: string, status: LessonStatus): boolean => {
    const btn = root.querySelector<HTMLButtonElement>(
      `[data-lesson-id="${cssEscape(lesson_id)}"]`,
    );
    if (!btn) return false;
    btn.dataset.status = status;
    const dot = btn.querySelector<HTMLElement>(".vmx-progress-list__dot");
    if (dot) dot.dataset.status = status;
    return true;
  };

  return root;
}

/** Minimal CSS.escape polyfill for jsdom — the test env's CSS.escape can
 *  be undefined, and lesson_ids contain `.` which would break attribute
 *  selectors otherwise. */
function cssEscape(value: string): string {
  if (
    typeof globalThis !== "undefined" &&
    typeof (globalThis as { CSS?: { escape?: (s: string) => string } }).CSS
      ?.escape === "function"
  ) {
    return (globalThis as unknown as { CSS: { escape: (s: string) => string } })
      .CSS.escape(value);
  }
  // Escape backslashes, then any non-alphanumeric ASCII character.
  return value.replace(/[^a-zA-Z0-9_-]/g, (ch) => `\\${ch}`);
}
