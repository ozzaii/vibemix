// SPDX-License-Identifier: Apache-2.0
//
// Phase 97 / ONBOARD-05 + ONBOARD-06 — Lesson progress list.
//
// Renders the optional lesson chooser as a calm course accordion: the
// current/recommended course opens, other courses summarize quietly, and
// every lesson remains reachable when its course is expanded. Each lesson is
// a tabbable <button> carrying a status dot:
//
//   - empty       (--silk-22 outline)  : not yet started
//   - in-progress (--silk-40 solid)    : completed_at == null AND
//                                        strikes_used > 0 (started, not done)
//   - completed   (--amber solid)       : completed: true
//
// Click → emit ipc.learn.start_lesson { lesson_id, level: "fresh" | "replay" }
// where level = "replay" when the lesson was already completed, "fresh"
// otherwise. The lesson_id is the Python curriculum key ("L1.01" etc.).
//
// Empty-state: when no physical controller is detected, the list confirms
// that the on-screen practice deck is live. Hardware remains optional.
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
  /** Canonical lesson_id, e.g. "L1.01". The progress-list component does
   *  NOT validate — callers pass the Python curriculum keys verbatim. */
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
  /** Persisted hint count from the last unfinished or completed attempt. */
  strikes_used?: number;
  /** Locked lessons are visible for orientation but cannot be started. */
  locked?: boolean;
  /** The single lesson the booth should offer as the recommended next step. */
  is_recommended?: boolean;
  /** Capped free-practice reps banked for this lesson before starting it. */
  practice_bank_count?: number;
  /** Monotonic receipt order for the latest free-practice gesture on this lesson. */
  last_practice_seq?: number;
  /** Measured miss that should send the learner into a repair rep. */
  practice_feedback?: {
    kind: "beatmatch" | "cue_placement" | "control";
    label: string;
    message: string;
    detail?: string;
  };
  /** Monotonic receipt order for the latest measured-miss recovery target. */
  last_feedback_seq?: number;
  /** Optional short reason for the locked state. */
  lock_reason?: string;
}

export interface ProgressListProps {
  /** Ordered list of lessons. Groups are derived from `course_id`
   *  contiguity — callers SHOULD pass lessons in canonical course
   *  order (Course 1 then Course 2 then Course 3). */
  lessons: ReadonlyArray<ProgressListEntry>;
  /** If true, renders the screen-deck readiness banner
   *  INSTEAD of the lesson list. The list itself stays in the DOM
   *  (focus-traversable for users browsing curriculum without
   *  hardware) but the empty-state banner is the foreground message.
   *  Default false (a controller is detected). */
  showNoControllerHint?: boolean;
  /** Callback fired when the user picks a lesson. The component decides
   *  level based on `status` — already-completed → "replay", else "fresh".
   *  Parent wires this to ipc.learn.start_lesson. */
  onPickLesson: (lesson_id: string, level: "fresh" | "replay") => void;
  /** Optional calm feedback hook when a locked visible lesson is activated. */
  onLockedLesson?: (lesson: ProgressListEntry) => void;
}

export interface ProgressListHandle extends HTMLDivElement {
  /** Update a single lesson's status in place (e.g. on
   *  ipc.learn.complete_lesson). Returns true if the lesson was found. */
  setStatus(lesson_id: string, status: LessonStatus): boolean;
}

interface LessonGroup {
  course_id: string;
  course_label: string;
  lessons: ProgressListEntry[];
}

/** No-controller empty-state copy. Lowercase, tone-disciplined. */
export const NO_CONTROLLER_HINT = "screen deck is ready";

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

  const groups = groupLessons(props.lessons);
  const defaultOpenCourseId = defaultExpandedCourseId(groups);
  const lessonButtons: HTMLButtonElement[] = [];
  const lessonEntries = new Map<string, ProgressListEntry>();
  const groupSummaries = new Map<string, HTMLElement>();

  const visibleLessonButtons = (): HTMLButtonElement[] =>
    lessonButtons.filter(
      (btn) =>
        btn.closest<HTMLElement>(".vmx-progress-list__group")?.dataset
          .expanded === "true",
    );

  groups.forEach((group, groupIdx) => {
    const groupEl = document.createElement("div");
    groupEl.className = "vmx-progress-list__group";
    groupEl.dataset.course = group.course_id;
    const expanded = group.course_id === defaultOpenCourseId;
    groupEl.dataset.expanded = expanded ? "true" : "false";

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "vmx-progress-list__group-toggle";
    const bodyId = `learn-course-group-${groupIdx}`;
    toggle.setAttribute("aria-controls", bodyId);
    toggle.setAttribute("aria-expanded", String(expanded));

    const label = document.createElement("span");
    label.className = "vmx-progress-list__group-label";
    label.textContent = group.course_label;

    const summary = document.createElement("span");
    summary.className = "vmx-progress-list__group-summary";
    summary.textContent = groupSummary(group.lessons);
    groupSummaries.set(group.course_id, summary);

    toggle.append(label, summary);
    groupEl.append(toggle);

    const body = document.createElement("div");
    body.id = bodyId;
    body.className = "vmx-progress-list__group-body";
    body.hidden = !expanded;

    toggle.addEventListener("click", () => {
      const nextExpanded = groupEl.dataset.expanded !== "true";
      groupEl.dataset.expanded = nextExpanded ? "true" : "false";
      body.hidden = !nextExpanded;
      toggle.setAttribute("aria-expanded", String(nextExpanded));
    });

    root.append(groupEl);

    for (const lesson of group.lessons) {
      lessonEntries.set(lesson.lesson_id, lesson);

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "vmx-progress-list__lesson";
      btn.dataset.lessonId = lesson.lesson_id;
      if (lesson.locked) {
        btn.setAttribute("aria-disabled", "true");
        if (lesson.lock_reason) btn.title = lesson.lock_reason;
      }
      btn.setAttribute("role", "listitem");

      const dot = document.createElement("span");
      dot.className = "vmx-progress-list__dot";
      dot.setAttribute("aria-hidden", "true");

      const title = document.createElement("span");
      title.className = "vmx-progress-list__title";
      title.textContent = lesson.title;

      btn.append(dot, title);
      syncLessonButton(btn, lesson);

      btn.addEventListener("click", () => {
        if (btn.dataset.locked === "true") {
          props.onLockedLesson?.(lesson);
          return;
        }
        const level: "fresh" | "replay" =
          btn.dataset.status === "completed" ? "replay" : "fresh";
        props.onPickLesson(lesson.lesson_id, level);
      });

      // Keyboard nav — ArrowUp / ArrowDown move focus across visible rows.
      btn.addEventListener("keydown", (ev) => {
        if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
          ev.preventDefault();
          const visibleButtons = visibleLessonButtons();
          const idx = visibleButtons.indexOf(btn);
          if (idx < 0) return;
          const nextIdx =
            ev.key === "ArrowDown"
              ? Math.min(idx + 1, visibleButtons.length - 1)
              : Math.max(idx - 1, 0);
          visibleButtons[nextIdx]?.focus();
        }
      });

      body.append(btn);
      lessonButtons.push(btn);
    }
    groupEl.append(body);
  });

  root.setStatus = (lesson_id: string, status: LessonStatus): boolean => {
    const btn = root.querySelector<HTMLButtonElement>(
      `[data-lesson-id="${cssEscape(lesson_id)}"]`,
    );
    if (!btn) return false;
    const entry = lessonEntries.get(lesson_id);
    if (entry) {
      entry.status = status;
      const summary = groupSummaries.get(entry.course_id);
      if (summary) {
        const group = groups.find((row) => row.course_id === entry.course_id);
        if (group) summary.textContent = groupSummary(group.lessons);
      }
    }
    if (entry) {
      syncLessonButton(btn, entry);
    } else {
      btn.dataset.status = status;
      const dot = btn.querySelector<HTMLElement>(".vmx-progress-list__dot");
      if (dot) dot.dataset.status = status;
    }
    return true;
  };

  return root;
}

function groupLessons(lessons: ReadonlyArray<ProgressListEntry>): LessonGroup[] {
  const groups: LessonGroup[] = [];
  let current: LessonGroup | null = null;
  for (const lesson of lessons) {
    if (!current || current.course_id !== lesson.course_id) {
      current = {
        course_id: lesson.course_id,
        course_label: lesson.course_label,
        lessons: [],
      };
      groups.push(current);
    }
    current.lessons.push({ ...lesson });
  }
  return groups;
}

function defaultExpandedCourseId(groups: ReadonlyArray<LessonGroup>): string | null {
  return (
    groups.find((group) =>
      group.lessons.some((lesson) => lesson.is_recommended && !lesson.locked),
    ) ??
    groups.find((group) =>
      group.lessons.some((lesson) => lesson.status === "in-progress" && !lesson.locked),
    ) ??
    groups.find((group) => group.lessons.some((lesson) => !lesson.locked)) ??
    groups[0] ??
    null
  )?.course_id ?? null;
}

function groupSummary(lessons: ReadonlyArray<ProgressListEntry>): string {
  const total = lessons.length;
  const completed = lessons.filter((lesson) => lesson.status === "completed").length;
  const hasFix = lessons.some((lesson) => effectivePracticeFeedback(lesson));
  const hasBanked = lessons.some((lesson) => effectivePracticeBankCount(lesson) > 0);
  const inProgress = lessons.some((lesson) => lesson.status === "in-progress");
  const allLocked = lessons.every((lesson) => lesson.locked && lesson.status !== "completed");
  if (allLocked) return `${total} locked`;
  if (completed === total) return `${total}/${total} complete`;
  if (hasFix) return `${completed}/${total} done, fix queued`;
  if (hasBanked) return `${completed}/${total} done, banked`;
  if (inProgress) return `${completed}/${total} done, in progress`;
  return `${completed}/${total} done`;
}

function syncLessonButton(
  btn: HTMLButtonElement,
  lesson: ProgressListEntry,
): void {
  btn.dataset.status = lesson.status;
  btn.dataset.locked = lesson.locked ? "true" : "false";
  btn.dataset.recommended = lesson.is_recommended ? "true" : "false";
  const bankCount = effectivePracticeBankCount(lesson);
  const feedback = effectivePracticeFeedback(lesson);
  btn.dataset.practiceBanked = bankCount > 0 ? "true" : "false";
  btn.dataset.practiceBank = String(bankCount);
  btn.dataset.practiceFeedback = feedback ? "true" : "false";
  if (feedback) {
    btn.dataset.practiceFeedbackKind = feedback.kind;
  } else {
    delete btn.dataset.practiceFeedbackKind;
  }
  const dot = btn.querySelector<HTMLElement>(".vmx-progress-list__dot");
  if (dot) dot.dataset.status = lesson.status;
  syncLessonTag(btn, lesson, bankCount, feedback);
  setButtonAriaLabel(btn, lesson);
}

function syncLessonTag(
  btn: HTMLButtonElement,
  lesson: ProgressListEntry,
  bankCount: number,
  feedback: ProgressListEntry["practice_feedback"] | null,
): void {
  const tagText = lessonTagText(lesson, bankCount, feedback);
  const existing = btn.querySelector<HTMLElement>(".vmx-progress-list__tag");
  if (!tagText) {
    existing?.remove();
    return;
  }
  const tag = existing ?? document.createElement("span");
  tag.className = "vmx-progress-list__tag";
  tag.dataset.kind = lesson.locked
    ? "locked"
    : feedback
      ? "fix"
      : lesson.is_recommended
      ? "next"
      : "banked";
  tag.textContent = tagText;
  if (!existing) btn.append(tag);
}

function lessonTagText(
  lesson: ProgressListEntry,
  bankCount: number,
  feedback: ProgressListEntry["practice_feedback"] | null,
): string | null {
  if (lesson.locked) return "locked";
  if (feedback) return "fix";
  if (lesson.is_recommended) return "next";
  if (bankCount > 0) return "banked";
  return null;
}

function setButtonAriaLabel(btn: HTMLButtonElement, lesson: ProgressListEntry): void {
  const stateLabel = lessonStateLabel(lesson);
  btn.setAttribute("aria-label", `${lesson.title}, ${stateLabel}`);
  const title = lessonTitle(lesson);
  if (title) {
    btn.title = title;
  } else {
    btn.removeAttribute("title");
  }
}

function lessonStateLabel(lesson: ProgressListEntry): string {
  if (lesson.locked) {
    return lesson.lock_reason
      ? `${lesson.status}, locked, ${lesson.lock_reason}`
      : `${lesson.status}, locked`;
  }
  const parts: string[] = [lesson.status];
  const feedback = effectivePracticeFeedback(lesson);
  if (feedback) parts.push(`fix ${feedback.label}`);
  if (lesson.is_recommended) parts.push("next");
  const bankCount = effectivePracticeBankCount(lesson);
  if (bankCount > 0) parts.push(`practice bank ${bankCount} of 3`);
  if (lesson.status === "completed") parts.push("press to replay");
  if (lesson.status === "in-progress") parts.push("retry");
  return parts.join(", ");
}

function lessonTitle(lesson: ProgressListEntry): string | null {
  if (lesson.locked) return lesson.lock_reason ?? "locked";
  const feedback = effectivePracticeFeedback(lesson);
  if (feedback) return `fix ${feedback.message}. start the recovery drill.`;
  const bankCount = effectivePracticeBankCount(lesson);
  if (bankCount > 0) return `practice bank ${bankCount} of 3. press to finish this lesson.`;
  if (lesson.status === "completed") return "press to replay this lesson.";
  if (lesson.status === "in-progress") return "retry this lesson.";
  return null;
}

function effectivePracticeBankCount(lesson: ProgressListEntry): number {
  if (lesson.status === "completed") return 0;
  return Math.min(3, Math.max(0, Math.trunc(lesson.practice_bank_count ?? 0)));
}

function effectivePracticeFeedback(
  lesson: ProgressListEntry,
): ProgressListEntry["practice_feedback"] | null {
  if (lesson.locked || lesson.status === "completed") return null;
  const feedback = lesson.practice_feedback;
  if (!feedback) return null;
  const label = feedback.label.trim();
  const message = feedback.message.trim();
  if (!label || !message) return null;
  return {
    ...feedback,
    label,
    message,
  };
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
