// SPDX-License-Identifier: Apache-2.0
//
// Phase 92 Plan 05 — LessonSkipButton component (UI-SPEC §Component Inventory).
//
// The "i got it" escape hatch. ALWAYS visible inside the tutor-speak
// dock's bottom row. Pedagogy contract:
//
//   - LESSON-04 anti-speedrun: 45 s minimum dwell. Before the floor,
//     `aria-disabled="true"` + `data-min-dwell-locked="true"` keep the
//     button non-interactive. Click is short-circuited inside the
//     handler (so SR clients reading the disabled state are not lied
//     to). Hover/focus reveals the verbatim tooltip:
//         "at least 45 seconds per lesson — that's the floor."
//   - On unlock at t=45s: aria-disabled and data-min-dwell-locked are
//     removed; no animation; no SR announcement (silent unlock per
//     UI-SPEC §Accessibility line 333).
//   - After unlock: click → `opts.onSkip()`. The wiring side
//     (learn-window.ts) emits `ipc.learn.complete_lesson { reason:
//     "user_skip" }`. Sidecar replies with progress_state snapshot.
//
// Motor-impaired-safe contract: NO time-pressure on lesson advancement.
// The 45 s floor is a PEDAGOGICAL floor, not a hostile timer — the
// button never grays out after the floor and never expires.
//
// Visual contract: silk-only. NEVER amber (UI-SPEC §Color point 7 —
// amber on skip would teach the user that skip is the primary CTA;
// silk keeps it as a sibling-of-last-resort).
// Key-hint glyph `SPACE ↵` lives in `.key-hint` next to the label.

export interface LessonSkipOpts {
  /** Fired after click + unlock; the wiring side emits the envelope. */
  onSkip: () => void;
  /** Override the 45 s minimum dwell (used by tests). */
  minDwellMs?: number;
}

export interface LessonSkipHandle extends HTMLButtonElement {
  /** Flip aria-disabled / data-min-dwell-locked OFF; clicks are live. */
  unlock(): void;
  /** Restart the dwell timer (called on new lesson_loaded). */
  resetLockout(): void;
  /** Cancel any pending unlock timer (called on dispose / hide). */
  dispose(): void;
}

const DEFAULT_MIN_DWELL_MS = 45_000;
const LOCK_TOOLTIP =
  "at least 45 seconds per lesson — that's the floor.";

/**
 * Build the "i got it" skip button. Returns a `<button>` with
 * `.unlock() / .resetLockout() / .dispose()` methods.
 *
 * Lockout starts immediately on construction; `resetLockout()` is the
 * way to restart the 45 s timer for a fresh lesson without throwing
 * away the existing DOM node.
 */
export function LessonSkipButton(opts: LessonSkipOpts): LessonSkipHandle {
  const btn = document.createElement("button") as LessonSkipHandle;
  btn.type = "button";
  btn.className = "learn-skip";
  btn.dataset.action = "skip-lesson";
  // innerHTML is intentional — the markup is static (no payload-derived
  // text) so XSS surface is nil. textContent equivalent would require
  // 3 separate element appends; the markup is plainer this way.
  btn.innerHTML =
    '<span class="label">i got it</span>' +
    '<span class="key-hint" aria-hidden="true">SPACE ↵</span>';

  // Lockout state — kept in a closure so `unlock()` and the click
  // handler share one source of truth.
  let unlocked = false;
  let timerId: ReturnType<typeof setTimeout> | null = null;
  let suppressNextKeyboardClick = false;

  const minDwellMs =
    opts.minDwellMs !== undefined ? opts.minDwellMs : DEFAULT_MIN_DWELL_MS;

  const applyLockedAttrs = () => {
    btn.setAttribute("aria-disabled", "true");
    btn.setAttribute("data-min-dwell-locked", "true");
    btn.title = LOCK_TOOLTIP;
  };

  const clearLockedAttrs = () => {
    btn.removeAttribute("aria-disabled");
    btn.removeAttribute("data-min-dwell-locked");
    btn.removeAttribute("title");
  };

  // Click handler — short-circuits during lockout, fires onSkip otherwise.
  // Space + Enter on a focused button trigger this same handler natively
  // (the browser maps key activations through click), so no extra
  // keydown listener is needed.
  const onClick = (ev: Event) => {
    if (suppressNextKeyboardClick) {
      suppressNextKeyboardClick = false;
      return;
    }
    if (!unlocked) {
      ev.preventDefault();
      ev.stopPropagation();
      return;
    }
    opts.onSkip();
  };
  const onKeyDown = (ev: KeyboardEvent) => {
    if (ev.key !== " " && ev.key !== "Enter") return;
    ev.preventDefault();
    if (!unlocked) {
      ev.stopPropagation();
      return;
    }
    suppressNextKeyboardClick = true;
    opts.onSkip();
  };
  btn.addEventListener("click", onClick);
  btn.addEventListener("keydown", onKeyDown);

  btn.unlock = () => {
    unlocked = true;
    clearLockedAttrs();
    if (timerId !== null) {
      clearTimeout(timerId);
      timerId = null;
    }
  };

  btn.resetLockout = () => {
    unlocked = false;
    applyLockedAttrs();
    if (timerId !== null) {
      clearTimeout(timerId);
      timerId = null;
    }
    // Schedule the unlock only when a runnable timer exists (jsdom +
    // browser both expose setTimeout; the guard preserves test mounts
    // that override the global).
    if (typeof setTimeout === "function") {
      timerId = setTimeout(() => btn.unlock(), minDwellMs);
    }
  };

  btn.dispose = () => {
    if (timerId !== null) {
      clearTimeout(timerId);
      timerId = null;
    }
    btn.removeEventListener("click", onClick);
    btn.removeEventListener("keydown", onKeyDown);
  };

  // Start lockout immediately on creation.
  btn.resetLockout();

  return btn;
}
