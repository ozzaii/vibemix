// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 05 — StatusBar component (UI-SPEC §Component Inventory).
//
// 40px-tall bottom rail. Two segments separated by a silk-22 hairline
// `|` divider:
//
//   1. Controller display name + mirror status:
//        `<display name> · midi mirror live`  (when active)
//        `waiting for midi`                    (when no port)
//        `controller unplugged`                (when port disappeared)
//   2. Window-management hint `cmd+tab to deck`.

import {
  compactOperatorActionLabel,
  operatorActionAriaLabel,
  type LearnOperatorAction,
} from "../lesson/operator-action.js";

type MirrorStatus = "waiting" | "screen" | "midi" | "live" | "unplugged";

type Course3LensStatus = {
  session_active: boolean;
  phrase_position_confidence: number;
  next_phrase_at: number | null;
  next_phrase_cue_id: string | null;
  audio_active?: boolean;
  deck_attributed?: boolean;
  deck_track_citable?: boolean;
  cue_ready?: boolean;
  blockers?: string[];
  operator_action?: LearnOperatorAction;
};
type StatusHintState =
  | "armed"
  | "cold"
  | "external-action"
  | "listening"
  | "operator-action"
  | "waiting-audio"
  | "waiting-deck"
  | "waiting-track";

export class StatusBar {
  private el: HTMLElement;
  private controllerEl: HTMLSpanElement;
  private hintEl: HTMLSpanElement;
  private readonly defaultHint: string;
  private course3LessonActive = false;

  constructor(el: HTMLElement) {
    this.el = el;
    this.defaultHint = this.hintText();
    this.el.className = "learn-status-bar";
    this.el.innerHTML = `
      <span class="learn-status-segment learn-status-controller">waiting for midi</span>
      <span class="learn-status-divider" aria-hidden="true">|</span>
      <span class="learn-status-segment learn-status-hint">${this.defaultHint}</span>
    `;
    this.controllerEl = this.el.querySelector(
      ".learn-status-controller",
    ) as HTMLSpanElement;
    this.hintEl = this.el.querySelector(
      ".learn-status-hint",
    ) as HTMLSpanElement;
  }

  /** Set the mirror-status segment text. */
  setMirrorStatus(status: MirrorStatus, displayName?: string): void {
    let text: string;
    switch (status) {
      case "live":
        text = `${displayName ?? "controller"} · midi mirror live`;
        break;
      case "screen":
        text = "on-screen deck";
        break;
      case "midi":
        text = "controller detected";
        break;
      case "unplugged":
        text = "controller unplugged";
        break;
      default:
        text = "waiting for midi";
    }
    this.controllerEl.textContent = text;
  }

  /** Surface the Course 3 live lens as one quiet status phrase, never a data panel. */
  setCourse3Lens(lens: Course3LensStatus): void {
    const course3Active = this.course3LessonActive || lens.session_active;
    const hasCue = Boolean(lens.next_phrase_cue_id) && lens.next_phrase_at !== null;
    const hasConfidentCue = hasCue && lens.phrase_position_confidence >= 0.7;
    if (lens.cue_ready === true || hasConfidentCue) {
      this.hintEl.textContent = "phrase cue locked";
      this.hintEl.dataset.course3Lens = "armed";
      this.hintEl.setAttribute(
        "aria-label",
        "phrase cue locked, coach has citable cue evidence",
      );
      this.hintEl.dataset.operatorAction = "none";
      this.hintEl.removeAttribute("title");
      return;
    }
    const blockers = new Set(lens.blockers ?? []);
    const canSurfaceAction = course3Active || lens.audio_active === true;
    if (canSurfaceAction && blockers.size > 0) {
      const fallback = this.course3FallbackAction(lens, blockers);
      const action = lens.operator_action ?? fallback?.action ?? null;
      if (action) {
        this.renderOperatorAction(
          action,
          lens.operator_action ? "operator-action" : fallback?.state ?? "operator-action",
        );
        return;
      }
    }
    if (course3Active && lens.audio_active !== true && blockers.has("waiting_for_audio")) {
      this.hintEl.textContent = "press play on deck";
      this.hintEl.dataset.course3Lens = "waiting-audio";
      this.hintEl.setAttribute(
        "aria-label",
        "Course 3 is active, but routed master audio is not audible yet; press play on the deck",
      );
      this.hintEl.dataset.operatorAction = "none";
      this.hintEl.removeAttribute("title");
      return;
    }
    if (lens.audio_active === true && lens.deck_attributed === false) {
      this.hintEl.textContent = "open one channel";
      this.hintEl.dataset.course3Lens = "waiting-deck";
      this.hintEl.setAttribute(
        "aria-label",
        "master audio is present, but no audible deck is attributed; open one deck channel",
      );
      this.hintEl.dataset.operatorAction = "none";
      this.hintEl.removeAttribute("title");
      return;
    }
    if (
      lens.audio_active === true &&
      lens.deck_attributed === true &&
      lens.deck_track_citable === false &&
      blockers.has("waiting_for_deck_track")
    ) {
      this.hintEl.textContent = "load a track";
      this.hintEl.dataset.course3Lens = "waiting-track";
      this.hintEl.setAttribute(
        "aria-label",
        "audible deck is known, but the loaded track is not citable yet; load a track",
      );
      this.hintEl.dataset.operatorAction = "none";
      this.hintEl.removeAttribute("title");
      return;
    }
    if (!course3Active) {
      this.restoreDefaultHint();
      return;
    }
    this.hintEl.textContent = "keep playing";
    this.hintEl.dataset.course3Lens = "listening";
    this.hintEl.setAttribute(
      "aria-label",
      "listening for phrase evidence; keep playing",
    );
    this.hintEl.dataset.operatorAction = "none";
    this.hintEl.removeAttribute("title");
  }

  setOperatorAction(action: LearnOperatorAction | null): void {
    if (!action) {
      this.restoreDefaultHint();
      return;
    }
    this.renderOperatorAction(action, "external-action");
  }

  setCourse3LessonActive(active: boolean): void {
    this.course3LessonActive = active;
    if (!active) {
      this.restoreDefaultHint();
    }
  }

  dispose(): void {
    // Lifecycle hook kept for the learn-window teardown call; the status
    // bar holds no timers or listeners to release.
  }

  // ---- private ----

  private hintText(): string {
    // navigator.platform is deprecated but still the most reliable
    // jsdom-safe windows-vs-mac fork. Anything other than Mac uses Alt+Tab.
    const platform =
      typeof navigator !== "undefined"
        ? (navigator.platform ?? "").toLowerCase()
        : "";
    const isMac = platform.includes("mac");
    return isMac ? "cmd+tab to deck" : "alt+tab to deck";
  }

  private renderOperatorAction(
    action: LearnOperatorAction,
    course3Lens: StatusHintState,
  ): void {
    const ariaLabel = operatorActionAriaLabel(action);
    this.hintEl.textContent = compactOperatorActionLabel(action);
    this.hintEl.dataset.course3Lens = course3Lens;
    this.hintEl.dataset.operatorAction = "active";
    this.hintEl.setAttribute("aria-label", ariaLabel);
    this.hintEl.setAttribute("title", ariaLabel);
  }

  private course3FallbackAction(
    lens: Course3LensStatus,
    blockers: Set<string>,
  ): { action: LearnOperatorAction; state: StatusHintState } | null {
    if (lens.audio_active !== true && blockers.has("waiting_for_audio")) {
      return {
        state: "waiting-audio",
        action: {
          prompt: "Press play on deck.",
          steps: [
            "Route Rekordbox to the routed master audio path selected by readiness.",
            "Load and play a real Rekordbox library track.",
            "Raise the playing channel fader and master until the status changes.",
          ],
        },
      };
    }
    if (lens.audio_active === true && lens.deck_attributed === false) {
      return {
        state: "waiting-deck",
        action: {
          prompt: "Open one channel.",
          steps: [
            "Open one deck channel so the coach can attribute deck A or B.",
            "Keep the master up while the live lens listens.",
          ],
        },
      };
    }
    if (
      lens.audio_active === true &&
      lens.deck_attributed === true &&
      lens.deck_track_citable === false &&
      blockers.has("waiting_for_deck_track")
    ) {
      return {
        state: "waiting-track",
        action: {
          prompt: "Load a track.",
          steps: [
            "Load a Rekordbox library track on the audible deck so the coach can cite it.",
          ],
        },
      };
    }
    if (blockers.has("waiting_for_cue")) {
      return {
        state: "listening",
        action: {
          prompt: "Keep playing.",
          steps: [
            "Keep the phrase playing until cue-section lookahead locks the next phrase.",
          ],
        },
      };
    }
    return null;
  }

  private restoreDefaultHint(): void {
    this.hintEl.textContent = this.defaultHint;
    this.hintEl.dataset.course3Lens = "cold";
    this.hintEl.dataset.operatorAction = "none";
    this.hintEl.removeAttribute("aria-label");
    this.hintEl.removeAttribute("title");
  }
}
