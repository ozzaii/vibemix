// SPDX-License-Identifier: Apache-2.0
//
// Phase 92 Plan 05 — TutorSpeakDock component (UI-SPEC §Component Inventory).
//
// Bottom region below the stage. Mounts on `ipc.learn.lesson_loaded`,
// reveals on first `ipc.learn.tutor_speak`. Inherits the "Deck Speaks"
// hero-on-void choreography from `mocks/vibemix-rebuild-session.html`
// VERBATIM — `.ghost.g2` → `.ghost.g1` → `.now` → receipt rule → cite
// chip. No chat-bubble Material chrome. No card wrapper. The void
// shows through (background: transparent + 1px glass-edge top border).
//
// Animation contract:
//   - On new tutor_speak (data_state="active"):
//       prior .now → .g1; prior .g1 → .g2; prior .g2 fades; new text
//       → .now (animation: learnTutorRise 400ms cubic-bezier).
//       receipt rule draws L→R 520ms with 360ms delay.
//       cite chip ignites at 900ms IFF payload.citations non-empty.
//   - On new tutor_speak (data_state="hint"):
//       data-state="hint" set on root → dock height 120 → 160 px.
//       hint italic line APPENDS below .now (does not replace .now).
//   - On .advance():
//       prior .now → .g1; .now cleared. Hint lines cleared.
//   - On .hide():
//       data-state="idle"; all text cleared.
//
// Citations array in the P92 hello-world lesson is `[]` — so the cite
// chip never renders in P92. The receipt rule still draws, just
// terminates blunt. P94 lights the chip once exemplar citations exist.
//
// SR announcements: writes payload.text to a shared
// `#learn-sr-announcement` aria-live region (P91 wires the region on
// the Learn root; this component also creates one on-demand if missing
// — useful in jsdom test mounts).

export interface TutorSpeakPayload {
  text: string;
  tts_marker: string;
  citations: ReadonlyArray<string>;
  data_state: "active" | "hint";
}

export interface TutorSpeakHandle extends HTMLDivElement {
  /** Apply a new tutor_speak envelope. Handles the active/hint fork. */
  show(payload: TutorSpeakPayload): void;
  /** Cycle current → g1 (called on ipc.learn.advance — no new line yet). */
  advance(): void;
  /** Collapse dock + clear all text (called on idle / complete). */
  hide(): void;
}

const SR_REGION_ID = "learn-sr-announcement";

/**
 * Build the tutor-speak dock element. Returns the root `<div>` with
 * `.show() / .advance() / .hide()` methods.
 *
 * Initial state is `data-state="idle"` (CSS collapses to display:none).
 * The first `.show()` call after mount flips to `data-state="active"`.
 */
export function TutorSpeakDock(): TutorSpeakHandle {
  const root = document.createElement("div") as TutorSpeakHandle;
  root.className = "tutor-dock";
  root.setAttribute("data-state", "idle");
  root.setAttribute("role", "region");
  root.setAttribute("aria-label", "tutor narration");

  // Build the 5 row-grid children in DOM order matching the rebuild-session
  // mock's `.speak` element so the CSS grid (auto auto auto auto auto)
  // lines them up vertically: g2 (oldest ghost) → g1 → now → hint-lines
  // → receipt.
  const g2 = document.createElement("div");
  g2.className = "ghost g2";
  const g1 = document.createElement("div");
  g1.className = "ghost g1";
  const now = document.createElement("div");
  now.className = "now";
  const hintLines = document.createElement("div");
  hintLines.className = "hint-lines";
  const receipt = document.createElement("div");
  receipt.className = "receipt";
  const rule = document.createElement("span");
  rule.className = "rule";
  receipt.appendChild(rule);
  const cite = document.createElement("span");
  cite.className = "cite";
  receipt.appendChild(cite);

  // The skip button slot — learn-window.ts injects the LessonSkipButton
  // child here after creation. Putting the slot inside the receipt row
  // matches UI-SPEC §Lesson HUD layout line 242: receipt rule on the
  // left flex-1, then cite chip, then skip button at the right edge.
  const skipSlot = document.createElement("span");
  skipSlot.className = "skip-slot";
  receipt.appendChild(skipSlot);

  [g2, g1, now, hintLines, receipt].forEach((el) => root.appendChild(el));

  const sr = ensureSrRegion();

  root.show = (payload: TutorSpeakPayload) => {
    if (payload.data_state === "hint") {
      // HINT path — APPEND italic below .now; do NOT shuffle ghosts.
      root.setAttribute("data-state", "hint");
      const line = document.createElement("div");
      line.className = "hint-line";
      line.textContent = payload.text;
      hintLines.appendChild(line);
      sr.textContent = `hint: ${payload.text}`;
      return;
    }
    // ACTIVE path — shuffle ghosts down, set new .now, draw receipt.
    root.setAttribute("data-state", "active");
    // Cascade: prior .g1 → .g2; prior .now → .g1; new text → .now.
    g2.textContent = g1.textContent;
    g1.textContent = now.textContent;
    now.textContent = payload.text;
    // Clear prior hint lines — each new active beat starts hint-free.
    hintLines.textContent = "";
    // Re-trigger the rise animation by removing+re-adding the class so
    // the keyframe restarts (CSS doesn't replay an animation on the
    // same class unless we force a reflow). Pattern lifted from the
    // rebuild-session mock.
    now.classList.remove("now");
    // eslint-disable-next-line @typescript-eslint/no-unused-expressions
    void now.offsetWidth;
    now.classList.add("now");
    // Also re-trigger the receipt rule draw.
    rule.classList.remove("rule");
    // eslint-disable-next-line @typescript-eslint/no-unused-expressions
    void rule.offsetWidth;
    rule.classList.add("rule");
    // Cite chip — light only when citations non-empty. For P92's
    // hello-world lesson, citations=[] so the chip stays hidden +
    // the receipt rule terminates blunt.
    if (payload.citations.length > 0) {
      cite.textContent = `◂ ${formatCitation(payload.citations[0]!)}`;
      cite.setAttribute("data-active", "true");
    } else {
      cite.textContent = "";
      cite.removeAttribute("data-active");
    }
    sr.textContent = payload.text;
  };

  root.advance = () => {
    // The runtime confirmed the user matched the expected action; the
    // current beat recedes into ghost memory. The next active beat
    // arrives on the following ipc.learn.tutor_speak.
    g2.textContent = g1.textContent;
    g1.textContent = now.textContent;
    now.textContent = "";
    hintLines.textContent = "";
    cite.removeAttribute("data-active");
    cite.textContent = "";
  };

  root.hide = () => {
    root.setAttribute("data-state", "idle");
    g2.textContent = "";
    g1.textContent = "";
    now.textContent = "";
    hintLines.textContent = "";
    cite.removeAttribute("data-active");
    cite.textContent = "";
  };

  return root;
}

/**
 * Translate a wire-shape citation token into the chip's display form.
 *
 * P92 hello-world citations=[] so this branch is dormant; the formatter
 * exists so when P93's exemplar engine starts emitting citations
 * (e.g. `[exemplar:track_1234]` or `[track:abc]`), the chip text reads
 * cleanly without a follow-up refactor.
 */
function formatCitation(c: string): string {
  // Drop bracket wrappers; collapse the source-prefix delimiter to space.
  const inner = c.replace(/^\[|\]$/g, "");
  return inner.replace(":", " ").toUpperCase();
}

/**
 * Ensure the polite aria-live region exists on the page. The Learn
 * window mounts `#learn-sr-announcement` at first paint (P91), but
 * test mounts and ad-hoc consumers may not — create on demand.
 */
function ensureSrRegion(): HTMLElement {
  if (typeof document === "undefined") {
    // Server-side safety; the dock is DOM-bound but the function may
    // be referenced from a module-load-time pass.
    return null as unknown as HTMLElement;
  }
  const existing = document.getElementById(SR_REGION_ID);
  if (existing) return existing;
  const created = document.createElement("div");
  created.id = SR_REGION_ID;
  created.className = "learn-sr-announcement";
  created.setAttribute("aria-live", "polite");
  created.setAttribute("aria-atomic", "true");
  if (document.body) {
    document.body.appendChild(created);
  }
  return created;
}
