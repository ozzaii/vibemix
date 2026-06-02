// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 05 — Learn webview entrypoint (the REAL renderer).
//
// REPLACES Plan 01's placeholder. Subscribes through the established
// Tauri IPC event bridge in production (with a ws://127.0.0.1:8765
// browser harness fallback), consumes
// `ipc.learn.controller_detected` (single-fire per plug) and
// `ipc.learn.midi_position` (30 Hz delta-suppressed), and drives the
// LearnTitlebar / ControllerStage / StatusBar components.
//
// RENDER-01: on `controller_detected { connected: true }`, dynamic-import
// the matching SVG and mount within 2s (jsdom synthetic; production
// Tauri webview measurement is the §LEARN-LATENCY-CONTINGENCY gate).
// RENDER-02: on `midi_position`, apply transform-only DOM mutations
// inside a `requestAnimationFrame` drainer (RESEARCH §Pitfall 6 —
// frame-flood handling: only the LATEST frame between repaint slots
// is consumed).
// RENDER-03: aria-live="polite" announces controller connect/disconnect
// once per state-change (UI-SPEC §Accessibility Contract).
// RENDER-05: dual-cue slots already scaffolded inside the SVGs (P92
// lights them).
// RENDER-07: NO new ws port. Production Tauri reuses the Rust event
// bridge; browser/dev fallback opens `new WebSocket("ws://127.0.0.1:8765")`.
//
// Architecture diagram:
//
//   LearnWsClient (Tauri event bridge or ws:8765 fallback)
//      envelope → CustomEvent on window
//
//   window.addEventListener("ipc.learn.controller_detected", ...)
//      → titlebar.setControllerName / stage.render / status.setMirrorStatus
//      → unplugged-toast on disconnect
//      → aria-live announcement
//
//   window.addEventListener("ipc.learn.midi_position", ...)
//      → pendingPositions = e.detail.positions (LWW under flood)
//      → rAF drainer: stage.applyPositionFrame + status.pushLatency

import "./styles/learn.css";
import { LearnWsClient } from "./ws-client.js";
import {
  ControllerStage,
  applyHighlight,
  clearHighlight,
  setHighlightHintIntensity,
} from "./components/controller-stage.js";
import { LearnTitlebar } from "./components/titlebar.js";
import { StatusBar } from "./components/status-bar.js";
import { mountEmptyState } from "./components/empty-state.js";
import { showUnpluggedToast } from "./components/unplugged-toast.js";
import {
  LessonHud,
  PENDING_DOT_TOOLTIP,
  type LessonHudHandle,
} from "./lesson/hud.js";
import {
  TutorSpeakDock,
  type TutorSpeakHandle,
} from "./lesson/tutor-dock.js";
import {
  LessonSkipButton,
  type LessonSkipHandle,
} from "./lesson/skip-button.js";
import {
  renderProgressList,
  type LessonStatus,
  type ProgressListEntry,
  type ProgressListHandle,
} from "./lesson/progress-list.js";
import {
  buildProgressEntries,
  CURRICULUM_META,
  firstRecommendedLessonId,
  type LearnProgressProjection,
} from "./lesson/curriculum-meta.js";
import {
  normalizeOperatorAction,
  type LearnOperatorAction,
} from "./lesson/operator-action.js";
import { emitIpc } from "../ipc/client.js";

interface ControllerDetectedPayload {
  connected: boolean;
  controller_id: string;
  display_name: string;
  port_name: string;
}

/**
 * Phase 97 / ONBOARD-07 + RENDER-08 — Trademark disclaimer copy (verbatim).
 *
 * Required to be present in two surfaces: the app's Learn-window footer
 * (this constant) AND the repo README's Trademarks section. The
 * `tests/learn/test_disclaimer_present.py` source-scan asserts both.
 * Do not paraphrase — the wording is the legal posture for nominative
 * fair use of the controller names + Pioneer / Hercules / Numark
 * trademarks the rendered SVGs reference.
 */
export const TRADEMARK_DISCLAIMER =
  "Visual representation for instructional use. DDJ-FLX4, XDJ-RX3, etc. are trademarks of AlphaTheta / Pioneer DJ. Inpulse is a trademark of Hercules. Numark is a trademark of inMusic Brands. vibemix is not affiliated with or endorsed by these manufacturers.";

interface MidiPositionPayload {
  controller_id: string;
  positions: Record<string, number>;
  // Optional emit_ts attached by the ws-client for latency measurement
  // (the canonical envelope ts is ISO-8601; we parse it on receive).
}

interface StatusTickPayload {
  midi?: number;
  payload?: {
    midi?: number;
  };
}

interface IpcEnvelopeMeta {
  ts?: string;
}

interface Course3LensPayload {
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
}

function statusTickMidiCount(detail: StatusTickPayload | undefined): number {
  return Number(detail?.midi ?? detail?.payload?.midi ?? 0);
}

/* ===================================================================
 * Phase 92 Plan 05 — lesson-mode envelope payload interfaces.
 *
 * Mirrors the shapes in `tauri/ui/src/ipc/messages.ts` (LearnHighlight /
 * LearnTutorSpeak / LearnLessonLoaded / LearnAdvance / LearnCompleteLesson /
 * LearnProgressState / LearnExemplarPlay / LearnExemplarStop). The ws-client
 * already runs each envelope through the pre-compiled ajv validator before
 * dispatching the CustomEvent (with the payload as `detail`), so the
 * handlers here treat the payload as already-validated.
 * =================================================================== */

interface LessonLoadedPayload {
  course_id: string;
  lesson_id: string;
  title: string;
  controller_id: string;
  progress_dots: ReadonlyArray<{
    lesson_id: string;
    status: "pending" | "current" | "completed";
  }>;
}

interface HighlightPayload {
  control_id: string;
  deck: "" | "A" | "B" | "C" | "D";
  cue_color: "amber" | "warning";
  cue_shape: "pulse-ring" | "static-glow";
  annotation: string;
  expected_action: {
    type: "cc" | "button";
    control: string;
    deck?: "" | "A" | "B" | "C" | "D";
    direction?: "" | "up" | "down";
    min_delta?: number;
  };
}

interface TutorSpeakWirePayload {
  text: string;
  tts_marker: string;
  citations: ReadonlyArray<string>;
  data_state: "active" | "hint";
}

interface AdvancePayload {
  lesson_id: string;
  reason: "action_matched" | "user_skip";
}

interface CompleteLessonPayload {
  lesson_id: string;
  reason: "completed" | "user_skip";
}

interface ProgressStatePayload {
  action: "snapshot" | "reset" | "reset_ack";
  was_recovered?: boolean;
  progress?: {
    schema_version: number;
    courses: Record<string, { completed?: boolean; completed_at?: string | null }>;
    lessons: Record<string, {
      completed?: boolean;
      completed_at?: string | null;
      strikes_used?: number;
      practice_sources?: { hardware?: number; screen?: number };
      last_practice_source?: "hardware" | "screen" | null;
    }>;
    course_2_unlocked?: boolean;
    course_3_unlocked?: boolean;
  };
}

interface ExemplarPlayPayload {
  track_id: string;
  duration_s: number;
  gain_db: number;
}

interface ExemplarStopPayload {
  track_id: string;
  reason: "completed" | "interrupted";
}

interface ExpectedActionPayload {
  type: "cc" | "button";
  control: string;
  deck?: "" | "A" | "B" | "C" | "D";
  direction?: "" | "up" | "down";
  min_delta?: number;
}

const LEARN_ROOT_ID = "learn-root";
const DEFAULT_PRACTICE_CONTROLLER_ID = "pioneer_ddj_flx4";
const SCREEN_ONLY_LEARN_CONTROLS = new Set([
  "headphone_cue",
  "lesson_continue",
  "master_vol",
]);
type LearnStartCourseWireId = "course_1" | "course_2" | "course_3";
interface LearnStartCoursePayload extends Record<string, unknown> {
  course_id: LearnStartCourseWireId;
  controller_id: string;
}
const COURSE_START_WIRE_IDS: Readonly<Record<string, LearnStartCourseWireId>> = {
  course_1: "course_1",
  course_1_anatomy: "course_1",
  course_2: "course_2",
  course_2_transitions: "course_2",
  course_3: "course_3",
  course_3_play_mode: "course_3",
};
const ACTION_FEEDBACK_LABELS = [
  "clean touch",
  "right move",
  "pocket held",
  "locked in",
] as const;
const CONTROL_FEEDBACK_LABELS: Readonly<Record<string, string>> = {
  cue: "cue hit",
  eq_hi: "eq turn",
  eq_low: "eq turn",
  eq_mid: "eq turn",
  filter: "filter turn",
  filter_fx: "fx hit",
  fx_echo: "echo hit",
  headphone_cue: "cue check",
  hotcue: "hot cue",
  jog: "jog nudge",
  jog_touch: "jog nudge",
  jog_touched: "jog nudge",
  lesson_continue: "next beat",
  loop_in: "loop in",
  loop_out: "loop out",
  master_vol: "master lift",
  play: "play hit",
  sync: "sync hit",
  tap_tempo: "tap set",
  tempo: "tempo touch",
  vol: "fader lift",
  xfader: "blend move",
};

/**
 * Module-level latest-frame holder (RESEARCH §Pitfall 6). Set on every
 * midi_position event; drained by the rAF callback. When the user
 * focuses a sibling window and 200 frames flood the receive buffer on
 * refocus, only the LAST sets `pendingPositions` — the rAF drainer
 * paints exactly one frame per repaint slot.
 */
let pendingPositions: Record<string, number> | null = null;
let pendingEmitTs: number | null = null;

/**
 * Frame-tracking guard (T-91-05-03 + §Pitfall 6): we also remember the
 * controller id of the most recent midi_position so the stage doesn't
 * try to apply a frame to the wrong SVG on a same-tick swap.
 */
let pendingControllerId: string | null = null;
let activeLearnWindowDisposer: (() => void) | null = null;

/**
 * Initialise the Learn window: build the DOM scaffold, mount the
 * components, open the ws client, install the rAF drainer + ws event
 * subscribers.
 */
function mountLearnWindow(root: HTMLElement): {
  ws: LearnWsClient;
  titlebar: LearnTitlebar;
  stage: ControllerStage;
  status: StatusBar;
  dispose: () => void;
} {
  activeLearnWindowDisposer?.();

  root.innerHTML = `
    <div id="learn-titlebar"></div>
    <div id="learn-stage" class="learn-stage"></div>
    <section id="learn-booth-panel" class="learn-booth-panel" data-visible="true">
      <div class="learn-booth-kicker">ready to practice</div>
      <div id="learn-booth-pulse" class="learn-booth-pulse" data-state="ready" aria-live="polite">practice deck ready</div>
      <button id="learn-start-recommended" class="learn-booth-primary" type="button">start practice</button>
      <button id="learn-open-map" class="learn-booth-secondary" type="button">choose lesson</button>
    </section>
    <button id="learn-screen-action" class="learn-screen-action" type="button" hidden>continue</button>
    <div id="learn-exemplar-chip" class="learn-exemplar-chip" data-active="false" hidden aria-live="polite">
      <span class="learn-exemplar-chip__led" aria-hidden="true"></span>
      <span id="learn-exemplar-label" class="learn-exemplar-chip__label">example</span>
      <strong id="learn-exemplar-track" class="learn-exemplar-chip__track"></strong>
      <span id="learn-exemplar-meta" class="learn-exemplar-chip__meta"></span>
    </div>
    <aside id="learn-progress-list-host" class="learn-progress-list-host" data-visible="false" aria-hidden="true">
      <div class="learn-progress-list-shell">
        <div class="learn-progress-list-head">
          <span>practice map</span>
          <button id="learn-close-map" type="button" aria-label="close lesson chooser">close</button>
        </div>
        <div id="learn-progress-list-body"></div>
      </div>
    </aside>
    <div id="learn-status-bar"></div>
    <div id="learn-sr-announcement" class="learn-sr-announcement" data-sr-region="tutor" aria-live="polite" aria-atomic="true"></div>
    <footer id="learn-footer" class="learn-footer"></footer>
  `;

  const titlebar = new LearnTitlebar(
    root.querySelector("#learn-titlebar") as HTMLElement,
  );
  const stageEl = root.querySelector("#learn-stage") as HTMLElement;
  const stage = new ControllerStage(stageEl);
  const status = new StatusBar(
    root.querySelector("#learn-status-bar") as HTMLElement,
  );
  const sr = root.querySelector("#learn-sr-announcement") as HTMLElement;
  const windowListeners: Array<[string, EventListener]> = [];
  const addWindowListener = (type: string, handler: EventListener): void => {
    window.addEventListener(type, handler);
    windowListeners.push([type, handler]);
  };

  const renderPracticeDeck = async (): Promise<void> => {
    try {
      await stage.render(DEFAULT_PRACTICE_CONTROLLER_ID);
    } catch (err: unknown) {
      // eslint-disable-next-line no-console
      console.warn("[learn] default practice deck render failed:", err);
      mountEmptyState(stageEl);
    }
  };

  // First paint: a usable on-screen practice deck. A physical controller
  // swaps this surface the moment ipc.learn.controller_detected lands.
  status.setMirrorStatus("screen");

  // Phase 97 / ONBOARD-05 — Lesson progress list.
  // Mounts as a sibling section under the stage; hides itself once a
  // lesson is loaded (HUD takes over the surface). Clicks emit
  // ipc.learn.start_lesson with the canonical Python lesson id
  // ("L1.01", etc.). The component carries
  // a `setStatus(lesson_id, status)` updater the progress_state handler
  // calls to keep dot states current.
  const progressListHost = root.querySelector(
    "#learn-progress-list-host",
  ) as HTMLElement;
  const progressListBody = root.querySelector(
    "#learn-progress-list-body",
  ) as HTMLElement;
  const boothPanel = root.querySelector("#learn-booth-panel") as HTMLElement;
  const boothPulse = root.querySelector("#learn-booth-pulse") as HTMLElement;
  const screenAction = root.querySelector("#learn-screen-action") as HTMLButtonElement;
  const openMapButton = root.querySelector("#learn-open-map") as HTMLButtonElement;
  const closeMapButton = root.querySelector("#learn-close-map") as HTMLButtonElement;
  const startRecommendedButton = root.querySelector(
    "#learn-start-recommended",
  ) as HTMLButtonElement;
  openMapButton.setAttribute("aria-controls", "learn-progress-list-host");
  openMapButton.setAttribute("aria-expanded", "false");
  const exemplarChip = root.querySelector("#learn-exemplar-chip") as HTMLElement;
  const exemplarLabel = root.querySelector("#learn-exemplar-label") as HTMLElement;
  const exemplarTrack = root.querySelector("#learn-exemplar-track") as HTMLElement;
  const exemplarMeta = root.querySelector("#learn-exemplar-meta") as HTMLElement;
  let latestProgress: LearnProgressProjection | null = null;
  let recommendedLessonId = firstRecommendedLessonId(latestProgress);
  let recommendedLessonLevel: "fresh" | "replay" = "fresh";
  let exemplarHideTimer: ReturnType<typeof setTimeout> | null = null;
  let controllerDetected = false; // flipped by controller_detected handler
  let midiSeenOnStatusTick = false;
  let controllerDisplayName: string | null = null;
  let currentLessonId: string | null = null;
  let currentExpectedAction: ExpectedActionPayload | null = null;
  let lastHighlightPayload: HighlightPayload | null = null;
  let lastPositions: Record<string, number> = {};
  let lastActionSource: "click" | "midi" | null = null;
  let lessonActionCount = 0;
  let lessonMatchedSourceCounts = freshLessonSourceCounts();
  let lessonUsedHint = false;
  const setBoothPulse = (
    state: "idle" | "ready" | "listening" | "success",
    text: string,
    options: { ariaLabel?: string; title?: string } = {},
  ): void => {
    boothPulse.dataset.state = state;
    boothPulse.textContent = text;
    boothPulse.setAttribute("aria-label", options.ariaLabel ?? text);
    if (options.title) {
      boothPulse.title = options.title;
    } else {
      boothPulse.removeAttribute("title");
    }
    boothPulse.classList.remove("is-fresh");
    // eslint-disable-next-line @typescript-eslint/no-unused-expressions
    void boothPulse.offsetWidth;
    boothPulse.classList.add("is-fresh");
  };
  const clearExemplarTimer = (): void => {
    if (exemplarHideTimer !== null) {
      clearTimeout(exemplarHideTimer);
      exemplarHideTimer = null;
    }
  };
  const hideExemplarChip = (): void => {
    clearExemplarTimer();
    exemplarChip.hidden = true;
    exemplarChip.dataset.active = "false";
    exemplarChip.removeAttribute("aria-label");
    exemplarLabel.textContent = "example";
    exemplarTrack.textContent = "";
    exemplarMeta.textContent = "";
  };
  const showExemplarPlay = (payload: ExemplarPlayPayload): void => {
    clearExemplarTimer();
    const track = shortTrackId(payload.track_id);
    const duration = Math.max(0, Math.round(payload.duration_s));
    const gain = Number.isFinite(payload.gain_db)
      ? payload.gain_db.toFixed(1)
      : "0.0";
    exemplarChip.hidden = false;
    exemplarChip.dataset.active = "true";
    exemplarChip.removeAttribute("data-reason");
    exemplarLabel.textContent = "example playing";
    exemplarTrack.textContent = track;
    exemplarMeta.textContent = `${duration}s at ${gain} dB`;
    exemplarChip.setAttribute(
      "aria-label",
      `example playing, ${track}, ${duration}s at ${gain} dB`,
    );
  };
  const showExemplarStop = (payload: ExemplarStopPayload): void => {
    clearExemplarTimer();
    if (exemplarChip.hidden) return;
    exemplarChip.dataset.active = "false";
    exemplarChip.dataset.reason = payload.reason;
    exemplarLabel.textContent = payload.reason === "completed"
      ? "example complete"
      : "example stopped";
    exemplarMeta.textContent = payload.reason;
    exemplarChip.setAttribute(
      "aria-label",
      `${exemplarLabel.textContent}, ${shortTrackId(payload.track_id)}`,
    );
    exemplarHideTimer = setTimeout(() => {
      hideExemplarChip();
    }, 1400);
  };
  let ws: LearnWsClient | null = null;
  const emitLearnIpc = async (
    type: string,
    payload: Record<string, unknown>,
  ): Promise<void> => {
    try {
      await emitIpc(type, payload);
      return;
    } catch (err) {
      if (ws !== null) {
        ws.sendIpc(type, payload);
        return;
      }
      throw err;
    }
  };
  const focusRecommendedLesson = (): void => {
    const target =
      progressListHost.querySelector<HTMLButtonElement>(
        ".vmx-progress-list__lesson[data-recommended='true'][data-locked='false']",
      ) ??
      progressListHost.querySelector<HTMLButtonElement>(
        ".vmx-progress-list__lesson[data-locked='false']",
      ) ??
      closeMapButton;
    target.focus();
  };
  const openLessonMap = (): void => {
    progressListHost.dataset.visible = "true";
    progressListHost.setAttribute("aria-hidden", "false");
    openMapButton.setAttribute("aria-expanded", "true");
    focusRecommendedLesson();
  };
  const closeLessonMap = (restoreFocus = true): void => {
    progressListHost.dataset.visible = "false";
    progressListHost.setAttribute("aria-hidden", "true");
    openMapButton.setAttribute("aria-expanded", "false");
    if (restoreFocus) openMapButton.focus();
  };
  const pickLesson = (lesson_id: string, level: "fresh" | "replay") => {
    closeLessonMap(false);
    boothPanel.dataset.visible = "false";
    setBoothPulse("listening", "hands on deck");
    void emitLearnIpc("ipc.learn.start_lesson", {
      lesson_id,
      level,
    }).catch((err: unknown) => {
      // eslint-disable-next-line no-console
      console.warn("[learn] start_lesson emit failed:", err);
    });
  };
  const handleHudDotActivation = (target: EventTarget | null): void => {
    if (!lessonHud || !(target instanceof Element)) return;
    const dot = target.closest<HTMLElement>(".dot");
    if (!dot || !lessonHud.contains(dot)) return;
    const status = dot.dataset.status;
    if (status === "completed") {
      const lessonId = dot.dataset.lessonId;
      if (lessonId) pickLesson(lessonId, "replay");
      return;
    }
    if (status === "pending") {
      dot.dataset.tooltipVisible = "true";
      dot.setAttribute("title", PENDING_DOT_TOOLTIP);
    }
  };
  let progressList: ProgressListHandle;
  const renderLessonChooser = (): void => {
    const lessons = buildProgressEntries(latestProgress);
    const recommended = lessons.find((lesson) => lesson.is_recommended);
    recommendedLessonId =
      recommended?.lesson_id ?? firstRecommendedLessonId(latestProgress);
    recommendedLessonLevel = recommended?.status === "completed" ? "replay" : "fresh";
    const recommendedVerb = recommendedActionVerb(recommended?.status);
    startRecommendedButton.textContent = recommended
      ? `${recommendedVerb} ${recommended.title}`
      : "start practice";
    progressList = renderProgressList({
      lessons,
      showNoControllerHint: !controllerDetected,
      onPickLesson: pickLesson,
      onLockedLesson: (lesson) => {
        setBoothPulse("idle", lesson.lock_reason ?? "locked");
      },
    });
    progressListBody.replaceChildren(progressList);
    updateBoothPulseForRecommendation(recommended);
  };
  const updateBoothPulseForRecommendation = (
    recommended: ProgressListEntry | undefined,
  ): void => {
    if (boothPanel.dataset.visible !== "true") return;
    const readiness = controllerDetected
      ? "hardware"
      : midiSeenOnStatusTick
        ? "midi"
        : "screen";
    boothPanel.dataset.readiness = readiness;
    const cue = recommendationBoothCue(
      recommended,
      readiness,
      controllerDisplayName,
    );
    setBoothPulse(cue.state, cue.text, {
      ariaLabel: cue.ariaLabel,
      title: cue.title,
    });
  };
  renderLessonChooser();

  const updateScreenActionForHighlight = (payload: HighlightPayload): void => {
    const expectedControlId = controlIdFromExpectedAction(payload.expected_action);
    const hasScreenTarget = hasVisualControl(expectedControlId);
    const hidden =
      payload.expected_action.control !== "lesson_continue" && hasScreenTarget;
    screenAction.hidden = hidden;
    screenAction.textContent = screenActionLabel(payload.expected_action);
    if (hidden) {
      screenAction.removeAttribute("aria-label");
      screenAction.removeAttribute("title");
      return;
    }
    const accessibleLabel = screenActionAccessibleLabel(
      payload.expected_action,
      hasScreenTarget,
    );
    screenAction.setAttribute("aria-label", accessibleLabel);
    screenAction.title = accessibleLabel;
  };

  const paintHighlightPayload = (payload: HighlightPayload): void => {
    updateScreenActionForHighlight(payload);
    if (isScreenOnlyAction(payload.expected_action)) {
      clearHighlight(stageEl);
      return;
    }
    if (stage.currentControllerId === null) return;
    applyHighlight(stageEl, payload);
  };

  const repaintCurrentLessonHighlight = (): void => {
    if (!currentLessonId || !lastHighlightPayload) return;
    paintHighlightPayload(lastHighlightPayload);
  };

  // First paint: a usable on-screen practice deck. A physical controller
  // swaps this surface the moment ipc.learn.controller_detected lands. If a
  // lesson highlight arrives while the SVG chunk is still loading, replay it.
  void renderPracticeDeck().then(() => {
    repaintCurrentLessonHighlight();
  });

  openMapButton.addEventListener("click", () => {
    openLessonMap();
  });
  closeMapButton.addEventListener("click", () => {
    closeLessonMap();
  });
  progressListHost.addEventListener("keydown", (event: KeyboardEvent) => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    closeLessonMap();
  });
  startRecommendedButton.addEventListener("click", () => {
    pickLesson(recommendedLessonId, recommendedLessonLevel);
  });
  addWindowListener("learn.start_course", (ev: Event) => {
    const payload = normalizeStartCourseDetail(
      (ev as CustomEvent<unknown>).detail,
    );
    if (payload === null) {
      // eslint-disable-next-line no-console
      console.warn("[learn] start_course event ignored: invalid payload");
      return;
    }
    closeLessonMap(false);
    boothPanel.dataset.visible = "false";
    setBoothPulse("listening", "hands on deck");
    void emitLearnIpc("ipc.learn.start_course", payload).catch(
      (err: unknown) => {
        // eslint-disable-next-line no-console
        console.warn("[learn] start_course emit failed:", err);
      },
    );
  });

  // Phase 97 / ONBOARD-07 + RENDER-08 — disclaimer footer.
  // The verbatim copy lives in a module-level constant so the
  // tests/learn/test_disclaimer_present.py source-scanner finds it
  // deterministically (the test asserts the fragment appears in some
  // .ts file under tauri/ui/src/learn/).
  const footer = root.querySelector("#learn-footer") as HTMLElement;
  footer.textContent = TRADEMARK_DISCLAIMER;

  // Phase 97 / ONBOARD-02 — first-launch tutor announce-by-name. On the
  // FIRST controller-connect event of this app run, the aria-live region
  // speaks the verbatim greeting "I see your <controller name>. Let's
  // go." This is the SECOND permitted "let's go." exception in the
  // v9.0 slop blocklist (the first was L1.01's iconic closer; the
  // blocklist uses multi-word tokens like 'now let's' so the bare
  // 'let's go.' here does NOT trip). Subsequent re-connects fall back
  // to the standard "<name> connected." text — the greeting is
  // first-launch only so a user who unplugs and re-plugs mid-session
  // doesn't hear "let's go" on every cycle.
  let hasAnnouncedFirstController = false;

  // ipc.learn.controller_detected handler — mounts/clears the SVG.
  addWindowListener("ipc.learn.controller_detected", (ev: Event) => {
    const detail = (ev as CustomEvent<ControllerDetectedPayload>).detail;
    if (!detail) return;
    if (detail.connected) {
      controllerDetected = true;
      midiSeenOnStatusTick = true;
      controllerDisplayName = detail.display_name;
      titlebar.setControllerName(detail.display_name);
      status.setMirrorStatus("live", detail.display_name);
      renderLessonChooser();
      // First-launch greeting (verbatim) — second permitted "let's go."
      // exception in v9.0. Plain sentence punctuation keeps product copy tight.
      sr.setAttribute("aria-live", "polite");
      if (!hasAnnouncedFirstController) {
        sr.textContent = `I see your ${detail.display_name}. Let's go.`;
        hasAnnouncedFirstController = true;
      } else {
        sr.textContent = `${detail.display_name} connected.`;
      }
      // Async dynamic-import; the empty-state stays visible until the
      // SVG body lands. `render` is idempotent (no-op when controller_id
      // unchanged — T-91-05-03).
      void (async () => {
        await stage.render(detail.controller_id);
        repaintCurrentLessonHighlight();
      })();
    } else {
      controllerDetected = false;
      controllerDisplayName = null;
      titlebar.setControllerName(null);
      status.setMirrorStatus("screen");
      renderLessonChooser();
      sr.setAttribute("aria-live", "polite");
      sr.textContent = "controller disconnected.";
      stage.clear();
      repaintCurrentLessonHighlight();
      void (async () => {
        await renderPracticeDeck();
        repaintCurrentLessonHighlight();
      })();
      showUnpluggedToast(detail.display_name);
      pendingPositions = null;
      pendingControllerId = null;
    }
  });

  // ipc.learn.midi_position handler — record latest frame for rAF drain.
  addWindowListener("ipc.learn.midi_position", (ev: Event) => {
    const detail = (ev as CustomEvent<MidiPositionPayload>).detail;
    if (!detail) return;
    pendingPositions = detail.positions;
    pendingControllerId = detail.controller_id;
    // Parse envelope ts → emit timestamp (ms since epoch). The envelope
    // ts is on the custom-event's parent envelope, not the payload, so
    // we conservatively use the now() time when the event fires.
    pendingEmitTs = performance.now();
    // ts on the envelope wrapper itself — we'd need to thread it through
    // the ws-client; for P91 we use the event-arrival timestamp which
    // overstates real latency by the ws → DOM hop (a few ms). Good
    // enough for the dev-visible status pip; the canonical synthetic
    // measurement lives in `tests/learn/highlight-latency.test.ts`.
    const envelopeMeta = (ev as CustomEvent<MidiPositionPayload> & { detail: { __envelope__?: IpcEnvelopeMeta } });
    void envelopeMeta;
  });

  // The main runtime can see a MIDI port before the Learn-specific controller
  // map handshake emits `ipc.learn.controller_detected`. Do not show "screen
  // deck ready" while the app already knows hardware is present.
  addWindowListener("ipc.status.tick", (ev: Event) => {
    const detail = (ev as CustomEvent<StatusTickPayload>).detail;
    const nextMidiSeen = statusTickMidiCount(detail) > 0;
    if (midiSeenOnStatusTick === nextMidiSeen) return;
    midiSeenOnStatusTick = nextMidiSeen;
    if (!controllerDetected) {
      status.setMirrorStatus(nextMidiSeen ? "midi" : "screen");
    }
    renderLessonChooser();
  });

  // learn.course3_lens: quiet Course 3 live-evidence indicator. This is
  // intentionally not an ipc.learn.* envelope: it is a local webview event
  // distilled from the shared 30 Hz socket frame.
  addWindowListener("learn.course3_lens", (ev: Event) => {
    const detail = (ev as CustomEvent<Course3LensPayload>).detail;
    if (!detail) return;
    status.setCourse3Lens(detail);
  });

  // learn.operator_action: generic one-action Learn seam for backstage
  // readiness checks or future courses. The frontstage stays a single
  // compact prompt; full steps ride in aria/title for review.
  addWindowListener("learn.operator_action", (ev: Event) => {
    const action = normalizeOperatorAction((ev as CustomEvent<unknown>).detail);
    status.setOperatorAction(action);
  });

  /* ===================================================================
   * Phase 92 Plan 05 — lesson-mode envelope handlers.
   *
   * 9 sidecar→shell envelopes consumed here (lesson_loaded / highlight /
   * tutor_speak / advance / complete_lesson / progress_state /
   * exemplar_play / exemplar_stop) + a SECOND midi_position listener that
   * emits `ipc.learn.ack` whenever a controlled position changes while a
   * lesson is active. shell→sidecar envelopes (start_course /
   * start_lesson) are emitted here, not subscribed: start_course via the
   * local `learn.start_course` automation hook, and start_lesson via the
   * mode picker (P97) / devtools-invoke demos.
   *
   * The 3 lesson components (LessonHud / TutorSpeakDock /
   * LessonSkipButton) mount lazily on the first `ipc.learn.lesson_loaded`
   * envelope. Without an active lesson, the P91 Learn-window layout
   * stays untouched. UI-SPEC §Wiring contract lines 354-371 is the
   * locked map for what each handler paints.
   * =================================================================== */

  // Lazy-mount handles for the 3 lesson components. Tracked at function
  // scope so subsequent handlers can reach the same instances without
  // re-mounting. `currentLessonId` is the source of truth for "is a
  // lesson currently active" — gates the ack-emit listener below.
  let lessonHud: LessonHudHandle | null = null;
  let tutorDock: TutorSpeakHandle | null = null;
  let skipButton: LessonSkipHandle | null = null;
  // Per-controlled-position last-known values (for delta detection in
  // the ack-emit listener). Cleared on lesson_loaded so a fresh lesson
  // doesn't inherit stale deltas.

  function hasVisualControl(controlId: string): boolean {
    return visualControlCandidates(controlId).some((candidate) =>
      stageEl.querySelector(`[data-control-id="${candidate}"]`) !== null,
    );
  }

  function visualControlIdFor(controlId: string): string {
    return (
      visualControlCandidates(controlId).find((candidate) =>
        stageEl.querySelector(`[data-control-id="${candidate}"]`) !== null,
      ) ?? controlId
    );
  }

  // ipc.learn.lesson_loaded → mount HUD + prep dock + skip-button lockout.
  addWindowListener("ipc.learn.lesson_loaded", (ev: Event) => {
    const payload = (ev as CustomEvent<LessonLoadedPayload>).detail;
    if (!payload) return;
    currentLessonId = payload.lesson_id;
    status.setCourse3LessonActive(
      payload.course_id === "course_3_play_mode" || payload.lesson_id.startsWith("L3."),
    );
    currentExpectedAction = null;
    lastHighlightPayload = null;
    screenAction.hidden = true;
    lastPositions = {};
    lastActionSource = null;
    lessonActionCount = 0;
    lessonMatchedSourceCounts = freshLessonSourceCounts();
    lessonUsedHint = false;

    // Flip the lesson-mode class so the grid extends to host the HUD + dock.
    root.classList.add("lesson-mode");

    // Phase 97 / ONBOARD-05 — hide the progress list once a lesson is
    // active; the HUD takes over the surface. Visibility flag is a
    // data-attribute so CSS controls display (avoids a layout shift on
    // re-show after complete_lesson).
    closeLessonMap(false);
    boothPanel.dataset.visible = "false";

    // Mount or refresh the HUD between titlebar + stage.
    if (lessonHud) {
      lessonHud.update(payload);
    } else {
      lessonHud = LessonHud(payload);
      lessonHud.addEventListener("click", (event) => {
        handleHudDotActivation(event.target);
      });
      lessonHud.addEventListener("keydown", (event) => {
        if (!(event instanceof KeyboardEvent)) return;
        if (event.key !== "Enter" && event.key !== " ") return;
        handleHudDotActivation(event.target);
      });
      // Insert HUD before the stage element so the grid order matches
      // titlebar / hud / stage / dock / statusbar.
      stageEl.parentElement?.insertBefore(lessonHud, stageEl);
    }

    // Mount the dock after the stage if not already present. Starts
    // collapsed (data-state="idle") until the first tutor_speak.
    if (!tutorDock) {
      tutorDock = TutorSpeakDock();
      stageEl.parentElement?.insertBefore(tutorDock, stageEl.nextSibling);
    } else {
      tutorDock.hide();
    }

    // Mount the skip button inside the dock's receipt-row skip-slot.
    if (!skipButton) {
      skipButton = LessonSkipButton({
        onSkip: () => {
          if (!currentLessonId) return;
          void emitLearnIpc("ipc.learn.complete_lesson", {
            lesson_id: currentLessonId,
            reason: "user_skip",
          });
        },
      });
      const skipSlot = tutorDock.querySelector(".skip-slot");
      if (skipSlot) skipSlot.appendChild(skipButton);
    }
    // New lesson → restart the 45 s anti-speedrun lockout fresh.
    skipButton.resetLockout();
  });

  // ipc.learn.highlight → paint highlight on the matched <g data-control-id>.
  // WR-07 fix (P92 REVIEW): gate the apply on a mounted controller SVG.
  // When the controller disconnects mid-lesson, `stage.clear()` resets
  // `mountedControllerId` to null and wipes the stage's innerHTML; if a
  // highlight envelope arrives in the gap before the next
  // `controller_detected{connected:true}`, walking an empty stage emits
  // a spurious console.warn and the highlight is silently lost.
  // Short-circuit when no SVG is mounted — the runtime keeps emitting
  // (its FSM doesn't see the unplug); we just don't paint until the
  // SVG is back. The next highlight envelope after re-bind paints
  // correctly because the runtime's on_enter_awaiting_action re-emits
  // on every transition that lands in awaiting_action.
  addWindowListener("ipc.learn.highlight", (ev: Event) => {
    const payload = (ev as CustomEvent<HighlightPayload>).detail;
    if (!payload) return;
    currentExpectedAction = payload.expected_action;
    lastHighlightPayload = payload;
    paintHighlightPayload(payload);
  });

  // ipc.learn.tutor_speak → dock.show + (hint state → pulse-ring intensify).
  addWindowListener("ipc.learn.tutor_speak", (ev: Event) => {
    const payload = (ev as CustomEvent<TutorSpeakWirePayload>).detail;
    if (!payload) return;
    if (payload.data_state === "hint") lessonUsedHint = true;
    if (tutorDock) tutorDock.show(payload);
    // Secondary a11y channel — when the dock enters hint state, the
    // currently-lit highlight intensifies (UI-SPEC §Motion line 306).
    setHighlightHintIntensity(stageEl, payload.data_state === "hint");
  });

  // ipc.learn.advance → cycle dock + clear highlight.
  addWindowListener("ipc.learn.advance", (ev: Event) => {
    const payload = (ev as CustomEvent<AdvancePayload>).detail;
    if (!payload) return;
    const feedback = payload.reason === "action_matched"
      ? {
          label: actionFeedbackLabel(lessonActionCount + 1, currentExpectedAction),
          sourceLabel: actionSourceFeedbackLabel(lastActionSource),
          count: lessonActionCount + 1,
        }
      : undefined;
    if (feedback) {
      lessonActionCount = feedback.count;
      recordMatchedActionSource(lessonMatchedSourceCounts, lastActionSource);
    }
    if (tutorDock) tutorDock.advance(feedback);
    clearHighlight(stageEl);
    currentExpectedAction = null;
    lastHighlightPayload = null;
    lastActionSource = null;
    screenAction.hidden = true;
  });

  // ipc.learn.complete_lesson → no paint here; the runtime will follow up
  // with progress_state(snapshot) to refresh dot state. We track the
  // lesson-end so the ack-emit listener stops firing. Phase 97 also
  // re-shows the progress list so the user can pick another lesson.
  addWindowListener("ipc.learn.complete_lesson", (ev: Event) => {
    const payload = (ev as CustomEvent<CompleteLessonPayload>).detail;
    if (!payload) return;
    // For P92 hello-world (1-lesson course), this marks the end. For
    // future multi-lesson courses, the next lesson_loaded re-populates
    // currentLessonId. The skip button stays locked until a fresh
    // lesson_loaded fires resetLockout.
    currentLessonId = null;
    status.setCourse3LessonActive(false);
    currentExpectedAction = null;
    lastHighlightPayload = null;
    screenAction.hidden = true;
    if (tutorDock) tutorDock.hide();
    hideExemplarChip();
    clearHighlight(stageEl);
    lastPositions = {};
    lastActionSource = null;
    // If we have a completed lesson_id, flip its dot to "completed"
    // locally and refresh the booth recommendation. The next
    // progress_state(snapshot) re-confirms from disk, but the frontstage
    // should not offer the just-finished lesson while waiting for it.
    if (payload.lesson_id && payload.reason === "completed") {
      progressList.setStatus(payload.lesson_id, "completed");
      latestProgress = {
        ...(latestProgress ?? {}),
        lessons: {
          ...(latestProgress?.lessons ?? {}),
          [payload.lesson_id]: {
            ...(latestProgress?.lessons?.[payload.lesson_id] ?? {}),
            completed: true,
          },
        },
      };
      renderLessonChooser();
    }
    // Return to the simple booth surface; the full map stays opt-in.
    boothPanel.dataset.visible = "true";
    const completionText = completionPulseLabel(
      payload.reason,
      lessonActionCount,
      lessonMatchedSourceCounts,
      lessonUsedHint,
    );
    setBoothPulse(
      payload.reason === "completed" ? "success" : "idle",
      completionText,
      completionPulseA11y(
        payload.reason,
        completionText,
        startRecommendedButton.textContent,
      ),
    );
    lessonActionCount = 0;
    lessonMatchedSourceCounts = freshLessonSourceCounts();
    lessonUsedHint = false;
    closeLessonMap(false);
  });

  // ipc.learn.progress_state → refresh HUD dots; surface recovery / reset
  // toasts on the corresponding action.
  addWindowListener("ipc.learn.progress_state", (ev: Event) => {
    const payload = (ev as CustomEvent<ProgressStatePayload>).detail;
    if (!payload) return;
    if (payload.action === "reset_ack") {
      showLearnToast("learn progress reset.");
    } else if (payload.was_recovered) {
      showLearnToast("learn progress restored.");
    }
    // Snapshot and reset-ack paths refresh status, course locks, and the
    // recommended next lesson together so the chooser never advertises a stale
    // jump after a settings reset.
    if (
      (payload.action === "snapshot" || payload.action === "reset_ack") &&
      payload.progress
    ) {
      latestProgress = payload.progress;
      renderLessonChooser();
    }
  });

  addWindowListener("ipc.learn.exemplar_play", (ev: Event) => {
    const payload = (ev as CustomEvent<ExemplarPlayPayload>).detail;
    if (!payload) return;
    showExemplarPlay(payload);
  });
  addWindowListener("ipc.learn.exemplar_stop", (ev: Event) => {
    const payload = (ev as CustomEvent<ExemplarStopPayload>).detail;
    if (!payload) return;
    showExemplarStop(payload);
  });

  const emitLearnAction = (
    controlId: string,
    source: "midi" | "click",
    value: number,
    prevValue: number,
    direction: "" | "up" | "down",
  ): void => {
    lastActionSource = source;
    void emitLearnIpc("ipc.learn.ack", {
      control_id: controlId,
      source,
      value,
      prev_value: prevValue,
      direction,
    });
  };

  const triggerScreenControl = (controlId: string): void => {
    if (!currentLessonId) return;
    const ackControlId = ackControlIdFor(controlId, currentExpectedAction);
    const visualControlId = visualControlIdFor(controlId);
    const isButton = isButtonControl(ackControlId);
    let prev = isButton ? 0 : (lastPositions[ackControlId] ?? 0);
    const next = isButton ? 127 : (prev <= 63 ? 127 : 0);
    if (!isButton && currentExpectedAction?.type === "cc") {
      const minDelta = Math.max(1, Number(currentExpectedAction.min_delta ?? 38));
      if (Math.abs(next - prev) < minDelta) {
        prev = next >= 64 ? 0 : 127;
      }
    }
    const direction: "" | "up" | "down" =
      isButton ? "down" : (next > prev ? "down" : "up");
    lastPositions[ackControlId] = next;
    stage.applyPositionFrame({ [visualControlId]: next });
    emitLearnAction(ackControlId, "click", next, prev, direction);
  };

  screenAction.addEventListener("click", () => {
    if (!currentExpectedAction) return;
    triggerScreenControl(controlIdFromExpectedAction(currentExpectedAction));
  });

  const handleStageControlActivation = (ev: Event): void => {
    const group = controlGroupFromStageEvent(ev, stageEl);
    const controlId = group?.getAttribute("data-control-id");
    if (!controlId) return;
    ev.preventDefault();
    triggerScreenControl(controlId);
  };

  stageEl.addEventListener("pointerdown", handleStageControlActivation);
  stageEl.addEventListener("keydown", (ev: KeyboardEvent) => {
    if (ev.key !== "Enter" && ev.key !== " ") return;
    handleStageControlActivation(ev);
  });

  // Second midi_position listener — emits ipc.learn.ack whenever a
  // controlled position changes while a lesson is active. The P91 listener
  // above stays intact (records pendingPositions for rAF drain); this one
  // ADDITIVELY emits acks. The LessonRuntime's action_matches filter on
  // the sidecar end discards acks that don't match the lesson's expected
  // action — so a blast of unrelated control changes during the lesson
  // doesn't false-advance.
  addWindowListener("ipc.learn.midi_position", (ev: Event) => {
    if (!currentLessonId) return;
    const detail = (ev as CustomEvent<MidiPositionPayload>).detail;
    if (!detail) return;
    for (const [controlId, value] of Object.entries(detail.positions ?? {})) {
      if (typeof value !== "number") continue;
      const prev = lastPositions[controlId];
      if (prev === undefined) {
        if (isOneShotPulseControl(controlId) && value > 0) {
          lastPositions[controlId] = value;
          const ackControlId = ackControlIdFor(controlId, currentExpectedAction);
          emitLearnAction(ackControlId, "midi", value, 0, "down");
          continue;
        }
        // First sighting — record baseline; do NOT emit ack (no delta yet).
        lastPositions[controlId] = value;
        continue;
      }
      if (value === prev) continue;
      const direction: "up" | "down" = value > prev ? "down" : "up";
      // ipc.learn.ack { control_id, source, value, direction } — wire
      // shape matches `LearnAck` in tauri/ui/src/ipc/messages.ts. The
      // sidecar LessonRuntime evaluates the ack via action_matches and
      // replies with advance(reason="action_matched") when it fits.
      emitLearnAction(controlId, "midi", value, prev, direction);
      lastPositions[controlId] = value;
    }
  });

  // rAF drainer — paint at most one frame per repaint slot
  // (RESEARCH §Pitfall 6). On tab-resume floods, only the latest
  // pendingPositions reaches the SVG.
  //
  // WR-01 fix: actually consult `pendingControllerId` here so a same-tick
  // controller swap (controller_detected{A} → midi_position{B} →
  // controller_detected{B} arriving before the next rAF) can't paint A's
  // positions onto B's SVG. Most `<g data-control-id>` keys overlap
  // across SKUs (vol:A, eq_hi:A etc.) so the silent miscolor would go
  // unnoticed in production but is wrong; the guard the comment promised
  // is now actually wired.
  //
  // WR-03 fix: a `stopped` flag the drainer checks before re-scheduling
  // so the unbounded rAF loop can be torn down on beforeunload. Without
  // it, an HMR reload or a future test fixture that re-mounts on the
  // same page would stack drainers indefinitely.
  let drainerStopped = false;
  function drainFrame(): void {
    if (drainerStopped) return;
    if (
      pendingPositions !== null &&
      pendingControllerId !== null &&
      stage.currentControllerId === pendingControllerId
    ) {
      const positions = pendingPositions;
      const emitTs = pendingEmitTs;
      stage.applyPositionFrame(positions);
      if (emitTs !== null) {
        status.pushLatency(performance.now() - emitTs);
      }
    }
    // Always clear after a drain attempt — stale pending frames don't
    // accumulate; the next midi_position event repopulates.
    pendingPositions = null;
    pendingEmitTs = null;
    requestAnimationFrame(drainFrame);
  }
  requestAnimationFrame(drainFrame);

  // Open ws + start streaming.
  ws = new LearnWsClient();
  ws.connect();
  void emitLearnIpc("ipc.learn.progress_state", { action: "snapshot" }).catch(
    (err: unknown) => {
      // eslint-disable-next-line no-console
      console.warn("[learn] progress snapshot emit failed:", err);
    },
  );

  // WR-03: tear down on beforeunload so a future HMR reload / test
  // remount doesn't stack timers + rAF loops. Production impact today
  // is zero (the page tears down naturally on close) but the cleanup
  // is cheap and makes the lifecycle explicit. Wired only when running
  // in a real window environment; jsdom tests skip the listener.
  let disposed = false;
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    drainerStopped = true;
    for (const [type, handler] of windowListeners.splice(0)) {
      window.removeEventListener(type, handler);
    }
    try {
      titlebar.dispose();
    } catch {
      /* swallow — best-effort cleanup */
    }
    try {
      status.dispose();
    } catch {
      /* swallow */
    }
    try {
      ws?.close();
    } catch {
      /* swallow */
    }
    hideExemplarChip();
    if (activeLearnWindowDisposer === dispose) {
      activeLearnWindowDisposer = null;
    }
  };
  activeLearnWindowDisposer = dispose;

  if (typeof window !== "undefined" && typeof window.addEventListener === "function") {
    addWindowListener("beforeunload", dispose as EventListener);
  }

  return { ws, titlebar, stage, status, dispose };
}

function isButtonControl(controlId: string): boolean {
  const head = controlId.split(":")[0] ?? controlId;
  return (
    head === "play" ||
    head === "cue" ||
    head === "sync" ||
    head === "loop_in" ||
    head === "loop_out" ||
    head === "hotcue" ||
    head === "jog" ||
    head === "jog_touch" ||
    head === "jog_touched" ||
    head === "filter_fx" ||
    head === "fx_echo" ||
    head === "tap_tempo" ||
    head === "headphone_cue" ||
    head === "lesson_continue"
  );
}

function isOneShotPulseControl(controlId: string): boolean {
  const head = controlId.split(":")[0] ?? controlId;
  return (
    head === "sync" ||
    head === "loop_in" ||
    head === "loop_out" ||
    head === "hotcue" ||
    head === "jog" ||
    head === "fx_echo" ||
    head === "filter_fx" ||
    head === "tap_tempo"
  );
}

function controlIdFromExpectedAction(action: ExpectedActionPayload): string {
  const deck = action.deck ?? "";
  return deck ? `${action.control}:${deck}` : action.control;
}

function screenActionLabel(action: ExpectedActionPayload): string {
  if (action.control === "lesson_continue") return "continue";
  const verb = action.type === "button" ? "press" : "move";
  const deck = action.deck ? `deck ${action.deck} ` : "";
  return `${verb} ${deck}${controlLabel(action.control)}`;
}

function screenActionAccessibleLabel(
  action: ExpectedActionPayload,
  hasScreenTarget: boolean,
): string {
  if (action.control === "lesson_continue") return "continue lesson";
  const label = screenActionLabel(action);
  return hasScreenTarget ? label : `screen fallback: ${label}`;
}

function isScreenOnlyAction(action: ExpectedActionPayload): boolean {
  return SCREEN_ONLY_LEARN_CONTROLS.has(action.control);
}

function controlLabel(control: string): string {
  const labels: Record<string, string> = {
    eq_hi: "high EQ",
    eq_mid: "mid EQ",
    eq_low: "low EQ",
    filter: "filter",
    filter_fx: "filter FX",
    fx_echo: "echo FX",
    headphone_cue: "headphone cue",
    hotcue: "hot cue",
    jog: "jog wheel",
    jog_touch: "jog wheel",
    jog_touched: "jog wheel",
    loop_in: "loop in",
    loop_out: "loop out",
    master_vol: "master volume",
    play: "play",
    sync: "sync",
    tap_tempo: "tap tempo",
    tempo: "pitch fader",
    vol: "channel fader",
    xfader: "crossfader",
  };
  return labels[control] ?? control.replaceAll("_", " ");
}

function ackControlIdFor(
  controlId: string,
  expected: ExpectedActionPayload | null,
): string {
  if (expected?.control !== "jog") return controlId;
  const [head, deck] = controlId.split(":");
  if ((head === "jog_touch" || head === "jog_touched") && deck) {
    return `jog:${deck}`;
  }
  return controlId;
}

function visualControlCandidates(controlId: string): string[] {
  const [head, deck] = controlId.split(":");
  if (head === "jog" && deck) {
    return [controlId, `jog_touch:${deck}`, `jog_touched:${deck}`];
  }
  return [controlId];
}

function controlGroupFromStageEvent(
  ev: Event,
  stageEl: HTMLElement,
): SVGGElement | null {
  const target = ev.target as Element | null;
  const direct = target?.closest("[data-control-id]") as SVGGElement | null;
  if (direct && stageEl.contains(direct)) return direct;
  if (!(ev instanceof MouseEvent)) return null;

  const x = ev.clientX;
  const y = ev.clientY;
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;

  let best: { group: SVGGElement; area: number } | null = null;
  for (const group of Array.from(
    stageEl.querySelectorAll<SVGGElement>("[data-control-id]"),
  )) {
    const rect = group.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) continue;
    if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
      continue;
    }
    const area = rect.width * rect.height;
    if (best === null || area < best.area) {
      best = { group, area };
    }
  }
  return best?.group ?? null;
}

function actionFeedbackLabel(
  count: number,
  expected: ExpectedActionPayload | null = null,
): string {
  if (expected !== null) {
    const label = CONTROL_FEEDBACK_LABELS[expected.control];
    if (label !== undefined) return label;
  }
  const index = Math.max(0, count - 1) % ACTION_FEEDBACK_LABELS.length;
  return ACTION_FEEDBACK_LABELS[index] ?? ACTION_FEEDBACK_LABELS[0];
}

function actionSourceFeedbackLabel(source: "click" | "midi" | null): string | undefined {
  if (source === "midi") return "hardware";
  if (source === "click") return "screen";
  return undefined;
}

interface LessonSourceCounts {
  hardware: number;
  screen: number;
}

function freshLessonSourceCounts(): LessonSourceCounts {
  return { hardware: 0, screen: 0 };
}

function startCourseString(
  detail: Record<string, unknown>,
  snakeKey: string,
  camelKey: string,
): string | null {
  const snakeValue = detail[snakeKey];
  if (typeof snakeValue === "string" && snakeValue.length > 0) {
    return snakeValue;
  }
  const camelValue = detail[camelKey];
  if (typeof camelValue === "string" && camelValue.length > 0) {
    return camelValue;
  }
  return null;
}

function normalizeStartCourseDetail(raw: unknown): LearnStartCoursePayload | null {
  if (raw === null || typeof raw !== "object") return null;
  const detail = raw as Record<string, unknown>;
  const courseIdRaw = startCourseString(detail, "course_id", "courseId");
  if (courseIdRaw === null) return null;
  const courseId = COURSE_START_WIRE_IDS[courseIdRaw];
  if (courseId === undefined) return null;
  return {
    course_id: courseId,
    controller_id:
      startCourseString(detail, "controller_id", "controllerId") ??
      DEFAULT_PRACTICE_CONTROLLER_ID,
  };
}

function recordMatchedActionSource(
  counts: LessonSourceCounts,
  source: "click" | "midi" | null,
): void {
  if (source === "midi") {
    counts.hardware += 1;
  } else if (source === "click") {
    counts.screen += 1;
  }
}

function completionSourceLabel(counts: LessonSourceCounts): string | null {
  if (counts.hardware > 0 && counts.screen > 0) return "hardware + screen";
  if (counts.hardware > 0) return "hardware";
  if (counts.screen > 0) return "screen";
  return null;
}

function completionPulseLabel(
  reason: CompleteLessonPayload["reason"],
  actionCount: number,
  sourceCounts: LessonSourceCounts,
  usedHint: boolean,
): string {
  if (reason !== "completed") return "replay when ready";
  const passLabel = usedHint ? "recovered pass" : "clean pass";
  const moves = actionCount === 1 ? "1 move" : `${actionCount} moves`;
  const source = completionSourceLabel(sourceCounts);
  if (actionCount <= 0) return passLabel;
  return source !== null
    ? `${passLabel} · ${source} · ${moves}`
    : `${passLabel} · ${moves}`;
}

function completionPulseA11y(
  reason: CompleteLessonPayload["reason"],
  completionText: string,
  nextAction: string | null,
): { ariaLabel?: string; title?: string } {
  const cleanNextAction = (nextAction ?? "").trim();
  if (reason !== "completed" || !cleanNextAction) {
    return { ariaLabel: completionText };
  }
  const label = `${completionText}. next practice: ${cleanNextAction}`;
  return {
    ariaLabel: label,
    title: label,
  };
}

function recommendedActionVerb(status: LessonStatus | undefined): string {
  if (status === "completed") return "replay";
  if (status === "in-progress") return "retry";
  return "start";
}

function recommendationBoothCue(
  recommended: ProgressListEntry | undefined,
  readiness: "hardware" | "midi" | "screen",
  controllerName: string | null,
): {
  state: "ready";
  text: string;
  ariaLabel?: string;
  title?: string;
} {
  if (recommended?.status === "in-progress") {
    const strikes = lessonStrikeCount(recommended);
    if (strikes > 0) {
      const label = `retry ${recommended.title}. last attempt used ${strikes} ${pluralizeHint(
        strikes,
      )}; retry starts fresh.`;
      return {
        state: "ready",
        text: "hint ready for retry",
        ariaLabel: label,
        title: label,
      };
    }
    const label = `retry ${recommended.title}. retry starts fresh.`;
    return {
      state: "ready",
      text: "retry ready",
      ariaLabel: label,
      title: label,
    };
  }
  if (readiness === "hardware") {
    const compactName = compactControllerName(controllerName);
    const label = compactName
      ? `${compactName} is mapped for this lesson.`
      : "hardware is mapped for this lesson.";
    return {
      state: "ready",
      text: compactName ? `${compactName} ready` : "hardware ready",
      ariaLabel: label,
      title: label,
    };
  }
  if (readiness === "midi") {
    const label =
      "A controller is detected. Start a lesson; if Learn does not react, enable FLX4 MIDI output so live moves can bind.";
    return {
      state: "ready",
      text: "controller detected",
      ariaLabel: label,
      title: label,
    };
  }
  return {
    state: "ready",
    text: "practice deck ready",
    ariaLabel:
      "practice deck ready. Connect a controller or use the highlighted on-screen control.",
  };
}

function compactControllerName(raw: string | null): string | null {
  const text = raw?.trim();
  if (!text) return null;
  return text
    .replace(/\bpioneer\b/gi, "")
    .replace(/\bddj[-\s]?flx4\b/gi, "FLX4")
    .replace(/\s+/g, " ")
    .trim();
}

function lessonStrikeCount(lesson: ProgressListEntry): number {
  const raw = Number(lesson.strikes_used ?? 0);
  if (!Number.isFinite(raw)) return 0;
  return Math.max(0, Math.min(3, Math.trunc(raw)));
}

function pluralizeHint(count: number): string {
  return count === 1 ? "hint" : "hints";
}

function shortTrackId(trackId: string): string {
  if (trackId.length <= 16) return trackId;
  return `${trackId.slice(0, 8)}...${trackId.slice(-4)}`;
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      () => {
        const root = document.getElementById(LEARN_ROOT_ID);
        if (root) mountLearnWindow(root);
      },
      { once: true },
    );
  } else {
    const root = document.getElementById(LEARN_ROOT_ID);
    if (root) mountLearnWindow(root);
  }
}

/* ===================================================================
 * Phase 92 Plan 05 — toast helper for progress_state acknowledgments.
 *
 * Used by the ipc.learn.progress_state handler to surface a one-line
 * toast on `action: "reset_ack"` (after a settings-drawer reset) or
 * `was_recovered: true` (boot-time corruption recovery in Plan 92-04).
 * Mirrors the existing recordings-delete toast pattern — append a
 * transient div with class .learn-toast for 3 s.
 * =================================================================== */
function showLearnToast(message: string): void {
  if (typeof document === "undefined") return;
  const t = document.createElement("div");
  t.className = "learn-toast";
  t.textContent = message;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

// Export for vitest jsdom mounting (allows tests to call mountLearnWindow
// without DOMContentLoaded). The Plan 02 stub
// `test_controller_detected_mounts_svg.test.ts` references
// `ipc.learn.controller_detected` to detect the real renderer landed.
export { mountLearnWindow };
