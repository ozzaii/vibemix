// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 05 — Learn webview entrypoint (the REAL renderer).
//
// REPLACES Plan 01's placeholder. Subscribes to ws://127.0.0.1:8765 (the
// SAME socket the live deck uses — one-socket invariant #4), consumes
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
// RENDER-07: NO new ws port — `ws-client.ts` opens
// `new WebSocket("ws://127.0.0.1:8765")`.
//
// Architecture diagram:
//
//   LearnWsClient (ws:8765)
//      onmessage → CustomEvent on window
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
import { LessonHud, type LessonHudHandle } from "./lesson/hud.js";
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
  type ProgressListHandle,
} from "./lesson/progress-list.js";
import {
  buildProgressEntries,
  CURRICULUM_META,
} from "./lesson/curriculum-meta.js";
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

interface IpcEnvelopeMeta {
  ts?: string;
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
    }>;
  };
}

const LEARN_ROOT_ID = "learn-root";

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
} {
  root.innerHTML = `
    <div id="learn-titlebar"></div>
    <div id="learn-stage" class="learn-stage"></div>
    <aside id="learn-progress-list-host" class="learn-progress-list-host" data-visible="true"></aside>
    <div id="learn-status-bar"></div>
    <div id="learn-sr-announcement" class="learn-sr-announcement" aria-live="polite" aria-atomic="true"></div>
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

  // First paint: empty state until ipc.learn.controller_detected lands.
  mountEmptyState(stageEl);
  status.setMirrorStatus("waiting");

  // Phase 97 / ONBOARD-05 — Lesson progress list.
  // Mounts as a sibling section under the stage; hides itself once a
  // lesson is loaded (HUD takes over the surface). Clicks emit
  // ipc.learn.start_lesson with the canonical slug-suffixed lesson_id
  // matching the schema regex ^L[0-9]+\.[0-9]+-.+$. The component carries
  // a `setStatus(lesson_id, status)` updater the progress_state handler
  // calls to keep dot states current.
  const progressListHost = root.querySelector(
    "#learn-progress-list-host",
  ) as HTMLElement;
  let controllerDetected = false; // flipped by controller_detected handler
  const progressList: ProgressListHandle = renderProgressList({
    lessons: buildProgressEntries(null), // initial = all empty
    showNoControllerHint: !controllerDetected,
    onPickLesson: (lesson_id, level) => {
      // Fire-and-forget ipc.learn.start_lesson. The runtime FSM picks
      // up the lesson and emits lesson_loaded → highlight → tutor_speak
      // back to the renderer; lesson-mode class flips on, and the
      // progress-list host hides itself.
      void emitIpc("ipc.learn.start_lesson", {
        lesson_id,
        level,
      }).catch((err: unknown) => {
        // eslint-disable-next-line no-console
        console.warn("[learn] start_lesson emit failed:", err);
      });
    },
  });
  progressListHost.appendChild(progressList);

  // Phase 97 / ONBOARD-07 + RENDER-08 — disclaimer footer.
  // The verbatim copy lives in a module-level constant so the
  // tests/learn/test_disclaimer_present.py source-scanner finds it
  // deterministically (the test asserts the fragment appears in some
  // .ts file under tauri/ui/src/learn/).
  const footer = root.querySelector("#learn-footer") as HTMLElement;
  footer.textContent = TRADEMARK_DISCLAIMER;

  // Phase 97 / ONBOARD-02 — first-launch tutor announce-by-name. On the
  // FIRST controller-connect event of this app run, the aria-live region
  // speaks the verbatim greeting "I see your <controller name> — let's
  // go." This is the SECOND permitted "let's go." exception in the
  // v9.0 slop blocklist (the first was L1.01's iconic closer; the
  // blocklist uses multi-word tokens like 'now let's' so the bare
  // 'let's go.' here does NOT trip). Subsequent re-connects fall back
  // to the standard "<name> connected." text — the greeting is
  // first-launch only so a user who unplugs and re-plugs mid-session
  // doesn't hear "let's go" on every cycle.
  let hasAnnouncedFirstController = false;

  // ipc.learn.controller_detected handler — mounts/clears the SVG.
  window.addEventListener("ipc.learn.controller_detected", (ev: Event) => {
    const detail = (ev as CustomEvent<ControllerDetectedPayload>).detail;
    if (!detail) return;
    if (detail.connected) {
      titlebar.setControllerName(detail.display_name);
      status.setMirrorStatus("live", detail.display_name);
      // First-launch greeting (verbatim) — second permitted "let's go."
      // exception in v9.0. The em-dash matches the iconic dialog precedent.
      if (!hasAnnouncedFirstController) {
        sr.textContent = `I see your ${detail.display_name} — let's go.`;
        hasAnnouncedFirstController = true;
      } else {
        sr.textContent = `${detail.display_name} connected.`;
      }
      // Async dynamic-import; the empty-state stays visible until the
      // SVG body lands. `render` is idempotent (no-op when controller_id
      // unchanged — T-91-05-03).
      void (async () => {
        await stage.render(detail.controller_id);
      })();
    } else {
      titlebar.setControllerName(null);
      status.setMirrorStatus("unplugged");
      sr.textContent = "controller disconnected.";
      stage.clear();
      mountEmptyState(stageEl);
      showUnpluggedToast(detail.display_name);
      pendingPositions = null;
      pendingControllerId = null;
    }
  });

  // ipc.learn.midi_position handler — record latest frame for rAF drain.
  window.addEventListener("ipc.learn.midi_position", (ev: Event) => {
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

  /* ===================================================================
   * Phase 92 Plan 05 — lesson-mode envelope handlers.
   *
   * 9 sidecar→shell envelopes consumed here (lesson_loaded / highlight /
   * tutor_speak / advance / complete_lesson / progress_state /
   * exemplar_play / exemplar_stop) + a SECOND midi_position listener that
   * emits `ipc.learn.ack` whenever a controlled position changes while a
   * lesson is active. shell→sidecar envelopes (start_course /
   * start_lesson) are not subscribed to here — only emitted by the mode
   * picker (P97) and devtools-invoke during demos.
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
  let currentLessonId: string | null = null;
  // Per-controlled-position last-known values (for delta detection in
  // the ack-emit listener). Cleared on lesson_loaded so a fresh lesson
  // doesn't inherit stale deltas.
  let lastPositions: Record<string, number> = {};

  // ipc.learn.lesson_loaded → mount HUD + prep dock + skip-button lockout.
  window.addEventListener("ipc.learn.lesson_loaded", (ev: Event) => {
    const payload = (ev as CustomEvent<LessonLoadedPayload>).detail;
    if (!payload) return;
    currentLessonId = payload.lesson_id;
    lastPositions = {};

    // Flip the lesson-mode class so the grid extends to host the HUD + dock.
    root.classList.add("lesson-mode");

    // Phase 97 / ONBOARD-05 — hide the progress list once a lesson is
    // active; the HUD takes over the surface. Visibility flag is a
    // data-attribute so CSS controls display (avoids a layout shift on
    // re-show after complete_lesson).
    progressListHost.dataset.visible = "false";

    // Mount or refresh the HUD between titlebar + stage.
    if (lessonHud) {
      lessonHud.update(payload);
    } else {
      lessonHud = LessonHud(payload);
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
          void emitIpc("ipc.learn.complete_lesson", {
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
  window.addEventListener("ipc.learn.highlight", (ev: Event) => {
    const payload = (ev as CustomEvent<HighlightPayload>).detail;
    if (!payload) return;
    if (stage.currentControllerId === null) return;
    applyHighlight(stageEl, payload);
  });

  // ipc.learn.tutor_speak → dock.show + (hint state → pulse-ring intensify).
  window.addEventListener("ipc.learn.tutor_speak", (ev: Event) => {
    const payload = (ev as CustomEvent<TutorSpeakWirePayload>).detail;
    if (!payload) return;
    if (tutorDock) tutorDock.show(payload);
    // Secondary a11y channel — when the dock enters hint state, the
    // currently-lit highlight intensifies (UI-SPEC §Motion line 306).
    setHighlightHintIntensity(stageEl, payload.data_state === "hint");
  });

  // ipc.learn.advance → cycle dock + clear highlight.
  window.addEventListener("ipc.learn.advance", (ev: Event) => {
    const payload = (ev as CustomEvent<AdvancePayload>).detail;
    if (!payload) return;
    if (tutorDock) tutorDock.advance();
    clearHighlight(stageEl);
  });

  // ipc.learn.complete_lesson → no paint here; the runtime will follow up
  // with progress_state(snapshot) to refresh dot state. We track the
  // lesson-end so the ack-emit listener stops firing. Phase 97 also
  // re-shows the progress list so the user can pick another lesson.
  window.addEventListener("ipc.learn.complete_lesson", (ev: Event) => {
    const payload = (ev as CustomEvent<CompleteLessonPayload>).detail;
    if (!payload) return;
    // For P92 hello-world (1-lesson course), this marks the end. For
    // future multi-lesson courses, the next lesson_loaded re-populates
    // currentLessonId. The skip button stays locked until a fresh
    // lesson_loaded fires resetLockout.
    currentLessonId = null;
    if (tutorDock) tutorDock.hide();
    clearHighlight(stageEl);
    lastPositions = {};
    // Phase 97 / ONBOARD-05 — surface the progress list again.
    progressListHost.dataset.visible = "true";
    // If we have a completed lesson_id, flip its dot to "completed"
    // locally; the next progress_state(snapshot) re-confirms.
    if (payload.lesson_id && payload.reason === "completed") {
      progressList.setStatus(payload.lesson_id, "completed");
    }
  });

  // ipc.learn.progress_state → refresh HUD dots; surface recovery / reset
  // toasts on the corresponding action.
  window.addEventListener("ipc.learn.progress_state", (ev: Event) => {
    const payload = (ev as CustomEvent<ProgressStatePayload>).detail;
    if (!payload) return;
    if (payload.action === "reset_ack") {
      showLearnToast("learn progress reset.");
    } else if (payload.was_recovered) {
      showLearnToast("learn progress restored.");
    }
    // Phase 97 / ONBOARD-05 — snapshot path now drives the progress-list
    // dot states. For each entry in CURRICULUM_META, look up the new
    // status from payload.progress.lessons and update the dot in place
    // via the component's setStatus helper.
    if (payload.action === "snapshot" && payload.progress) {
      const entries = buildProgressEntries(payload.progress);
      for (const entry of entries) {
        progressList.setStatus(entry.lesson_id, entry.status);
      }
    }
  });

  // ipc.learn.exemplar_play / exemplar_stop → log-only in P92 (P93 lands
  // the UI consumer; the envelope shapes exist so the wire contract is
  // stable, but no paint surface mounts yet).
  window.addEventListener("ipc.learn.exemplar_play", (ev: Event) => {
    // eslint-disable-next-line no-console
    console.log("[learn] exemplar_play:", (ev as CustomEvent).detail);
  });
  window.addEventListener("ipc.learn.exemplar_stop", (ev: Event) => {
    // eslint-disable-next-line no-console
    console.log("[learn] exemplar_stop:", (ev as CustomEvent).detail);
  });

  // Second midi_position listener — emits ipc.learn.ack whenever a
  // controlled position changes while a lesson is active. The P91 listener
  // above stays intact (records pendingPositions for rAF drain); this one
  // ADDITIVELY emits acks. The LessonRuntime's action_matches filter on
  // the sidecar end discards acks that don't match the lesson's expected
  // action — so a blast of unrelated control changes during the lesson
  // doesn't false-advance.
  window.addEventListener("ipc.learn.midi_position", (ev: Event) => {
    if (!currentLessonId) return;
    const detail = (ev as CustomEvent<MidiPositionPayload>).detail;
    if (!detail) return;
    for (const [controlId, value] of Object.entries(detail.positions ?? {})) {
      if (typeof value !== "number") continue;
      const prev = lastPositions[controlId];
      if (prev === undefined) {
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
      void emitIpc("ipc.learn.ack", {
        control_id: controlId,
        source: "midi",
        value,
        direction,
      });
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
  const ws = new LearnWsClient();
  ws.connect();

  // WR-03: tear down on beforeunload so a future HMR reload / test
  // remount doesn't stack timers + rAF loops. Production impact today
  // is zero (the page tears down naturally on close) but the cleanup
  // is cheap and makes the lifecycle explicit. Wired only when running
  // in a real window environment; jsdom tests skip the listener.
  if (typeof window !== "undefined" && typeof window.addEventListener === "function") {
    const teardown = () => {
      drainerStopped = true;
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
        ws.close();
      } catch {
        /* swallow */
      }
    };
    window.addEventListener("beforeunload", teardown, { once: true });
  }

  return { ws, titlebar, stage, status };
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
