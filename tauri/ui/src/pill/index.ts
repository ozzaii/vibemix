/* Phase 62 Plan 04 — Pill webview entrypoint.
 *
 * Boots the floating pill: subscribes to the EXISTING ws:8765 bus (direct-WS,
 * like the mascot), derives the four states (idle / listening / speaking /
 * expand-on-event) from real wire data, drives the speaking-state waveform
 * from the REAL voice.rms signal (Levels.update_voice), and renders the
 * verbatim reaction text + citation strip in the expand panel. Drags from the
 * top 28px strip.
 *
 * Cloned from the shipped mascot index entry (drag handler + bus wiring +
 * reader/writer handleMessage discipline) MINUS the Three.js renderer. The
 * ws-client is COPIED into src/pill so the pill is decoupled from the mascot
 * source tree and the mascot-audit fence stays green.
 *
 * READER vs WRITER (62-PATTERNS "Frame fan-out"):
 *   - snapshot / flat live frames are READERS — they update cohostStatus +
 *     voiceRms (read defensively flat-or-nested, LIVE-05a) without forcing a
 *     transition.
 *   - cohost-reaction is the only WRITER — it drives expand-on-event with the
 *     verbatim text + chips.
 *
 * Frame content is rendered via textContent / contract-tested renderCitationStrip
 * — NEVER eval'd or innerHTML'd from wire data (T-62-11/T-62-12). The pill
 * registers NO message-send path — consume-only for v1 (T-62-14).
 */

import { renderCitationStrip, type CitationChip } from "../session/components/citation-strip.js";
import {
  applyFrame,
  initialPillState,
  tickCollapse,
  type CohostStatus,
  type PillFrame,
  type PillState,
} from "./state-machine.js";
import { connectMascotBus, type MascotBusClient } from "./ws-client.js";

const TAG = "[pill]";

// ── Pure frame reader (unit-testable, no DOM / no globals) ─────────────────

/**
 * Normalise a raw wire message into a PillFrame, reading `voice` defensively
 * flat-or-nested (LIVE-05a): `voice` is FLAT on the direct live frame,
 * nested under `meters.voice.rms` on the bridged snapshot. Returns `null` for
 * a frame the pill ignores (e.g. a malformed object with nothing the pill
 * cares about) so the caller can cheaply skip.
 *
 * Exported for index.test.ts — keeps the frame→state map deterministic and
 * DOM-free.
 */
export function toPillFrame(msg: unknown): PillFrame | null {
  if (msg == null || typeof msg !== "object") return null;
  const m = msg as Record<string, unknown>;
  const type = typeof m.type === "string" ? m.type : undefined;

  // WRITER — cohost-reaction (either the bare or the ipc-prefixed type).
  if (type === "cohost-reaction" || type === "ipc.session.cohost-reaction") {
    const text = typeof m.text === "string" ? m.text : "";
    const chips = Array.isArray(m.citation_strip)
      ? (m.citation_strip as CitationChip[])
      : [];
    return { type, text, chips };
  }

  // READER — snapshot / flat live frame. Read voice defensively (LIVE-05a):
  // flat `voice` on the live frame OR nested `meters.voice.rms` on the bridged
  // snapshot. Leave undefined (→ prior value) when neither is present.
  const meters = (m.meters as Record<string, unknown> | undefined) ?? undefined;
  const metersVoice = meters?.voice as Record<string, unknown> | undefined;
  const flatVoice = typeof m.voice === "number" ? m.voice : undefined;
  const nestedVoice =
    typeof metersVoice?.rms === "number" ? (metersVoice.rms as number) : undefined;
  const voiceRms = flatVoice ?? nestedVoice;

  const flatPeak = typeof m.peak === "number" ? m.peak : undefined;
  const nestedPeak =
    typeof metersVoice?.peak === "number" ? (metersVoice.peak as number) : undefined;
  const voicePeak = flatPeak ?? nestedPeak;

  const cohostStatus = isCohostStatus(m.cohost_status) ? m.cohost_status : undefined;

  // A frame with no status AND no voice signal carries nothing the pill reads.
  if (cohostStatus === undefined && voiceRms === undefined && voicePeak === undefined) {
    return null;
  }

  return {
    cohostStatus: cohostStatus ?? null,
    voiceRms: voiceRms ?? null,
    voicePeak: voicePeak ?? null,
  };
}

function isCohostStatus(v: unknown): v is CohostStatus {
  return v === "IDLE" || v === "LISTENING" || v === "TALKING";
}

/**
 * Pure reduce: apply one raw wire message to the pill state. Exported for
 * tests so the frame→state map is asserted without the bus or DOM.
 */
export function reduceFrame(state: PillState, msg: unknown, now: number): PillState {
  const frame = toPillFrame(msg);
  if (frame === null) return state;
  return applyFrame(state, frame, now);
}

// ── DOM view (impure — only runs in the webview) ──────────────────────────

interface PillView {
  root: HTMLElement;
  label: HTMLElement;
  reaction: HTMLElement;
  expand: HTMLElement;
  waveMount: HTMLElement;
}

const STATE_LABEL: Record<PillState["mode"], string> = {
  idle: "IDLE",
  listening: "LISTENING",
  speaking: "SPEAKING",
  // While expanded the collapsed label keeps the base state's caption; the
  // expand panel carries the reaction text. We re-derive the base label in
  // render() so "expand" never paints a literal "EXPAND" string.
  expand: "",
};

/** Repaint the DOM from the pill state. Idempotent; called from the rAF loop. */
function render(view: PillView, state: PillState, baseLabel: string): void {
  // data-state drives the dot pulse cadence + the expand panel visibility (CSS).
  view.root.dataset.state = state.mode;
  view.label.textContent = baseLabel;

  if (state.mode === "expand") {
    // Reaction text rendered VERBATIM as a text node (T-62-11 — never innerHTML).
    view.reaction.textContent = state.reactionText;
    // Citation strip rendered VERBATIM via the shipped component (T-62-12).
    syncCitationStrip(view.expand, state.chips);
  }
}

let lastChipsKey = "";
function syncCitationStrip(expandEl: HTMLElement, chips: CitationChip[]): void {
  // Only rebuild the strip when the chip set changes (cheap key) — the rAF
  // loop calls render() every frame.
  const key = chips.map((c) => `${c.event_id}@${c.timestamp_s}`).join("|");
  if (key === lastChipsKey) return;
  lastChipsKey = key;
  expandEl.querySelector(".vmx-citation-strip")?.remove();
  const strip = renderCitationStrip({
    chips,
    // v1: no-op. A future plan deep-links to the debrief at the cited moment.
    onChipClick: () => {},
  });
  if (strip) {
    // Tag the strip so a chip click does not start a window drag.
    strip.setAttribute("data-no-drag", "");
    // Insert before the deck-chips mount (62-05 populates that).
    const decks = expandEl.querySelector("#pill-decks");
    expandEl.insertBefore(strip, decks);
  }
}

// ── Boot ──────────────────────────────────────────────────────────────────

function boot(): void {
  const root = document.getElementById("pill");
  const label = document.getElementById("pill-label");
  const reaction = document.getElementById("pill-reaction");
  const expand = document.getElementById("pill-expand");
  const waveMount = document.getElementById("pill-wave");
  const dragStrip = document.getElementById("pill-drag");
  if (!root || !label || !reaction || !expand || !waveMount || !dragStrip) {
    console.error(`${TAG} pill DOM skeleton missing — cannot mount`);
    return;
  }

  // The waveform mount is populated in Task 3 (meter.ts reuse).
  const view: PillView = { root, label, reaction, expand, waveMount };

  let state = initialPillState(performance.now());

  // ── Drag-to-move — clone the mascot's explicit JS startDragging(), scoped
  // to the top 28px drag strip (62-UI-SPEC §Drag handle). data-tauri-drag-region
  // is unreliable alone on non-activating windows. ──────────────────────────
  void (async () => {
    try {
      const mod = await import("@tauri-apps/api/window");
      const tauriWin = mod.getCurrentWindow();
      dragStrip.addEventListener("mousedown", (ev) => {
        const me = ev as MouseEvent;
        if (me.button !== 0) return; // left-click only
        const target = me.target as HTMLElement | null;
        if (target?.closest("[data-no-drag]")) return; // chips/controls exempt
        tauriWin
          .startDragging()
          .catch((e: unknown) => console.warn(`${TAG} startDragging() rejected:`, e));
      });
    } catch (err) {
      console.warn(`${TAG} drag handler unavailable (likely test/browser):`, err);
    }
  })();

  // ── Bus subscription — REUSE the copied connectMascotBus ──────────────────
  let bus: MascotBusClient | null = null;
  try {
    bus = connectMascotBus("ws://127.0.0.1:8765");
    bus.addMessageListener((msg) => {
      state = reduceFrame(state, msg, performance.now());
    });
    // 62-UI-SPEC §Copywriting: NO error UI on the pill — silence is the honest
    // empty state; bus-health surfaces in the main session window, not here.
    bus.addStatusListener(() => {});
  } catch (err) {
    console.warn(`${TAG} bus unavailable (likely test/browser):`, err);
  }

  // ── rAF loop — fire the data-driven collapse + repaint the waveform ──────
  function frame(): void {
    const now = performance.now();
    state = tickCollapse(state, now);

    // Base label tracks the underlying status even while expanded.
    const baseLabel =
      state.mode === "expand"
        ? labelForStatus(state.cohostStatus)
        : (STATE_LABEL[state.mode] ?? "IDLE");
    render(view, state, baseLabel);

    // Task 3 wires the real voice.rms waveform here.

    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

function labelForStatus(s: CohostStatus): string {
  if (s === "TALKING") return "SPEAKING";
  if (s === "LISTENING") return "LISTENING";
  return "IDLE";
}

// Only boot inside a real document (the webview) — tests import the pure
// helpers without triggering the bus/DOM boot.
if (typeof document !== "undefined" && document.getElementById("pill")) {
  boot();
}
