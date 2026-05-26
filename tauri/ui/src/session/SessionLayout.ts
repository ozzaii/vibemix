/* SessionLayout.ts — composer for the live session window.
 *
 * "THE DECK SPEAKS" (2026-05-26 full rebuild). The whole window is one
 * CDJ-3000 master section at rest: pure void, no glass cards, no panel grid.
 * The co-host's latest line is the hero (large lit type floating on void);
 * prior lines recede upward as ghost type (memory, not a chat log). A single
 * master strip (BPM / key / live level) sits at the foot behind one hairline.
 *
 * THE SIGNATURE GESTURE: when a new reaction arrives the `.vmx-now` line
 * rises in silk; a 1px amber rule draws left-to-right beneath it, terminating
 * at the grounding cite, which ignites (spark then settle). "The sentence
 * underlines its own claim with its own evidence." The one piece of amber
 * choreography — the anti-slop thesis made visible. It re-fires per reaction
 * (keyed off the now-line `ts`, retriggered via forced reflow).
 *
 * Three states (data-mode on the root): "" live (deck speaks, meter twitches),
 * "silent" (calm listening — line held dim, receipt gone, meter idle-breathes),
 * "fault" (a dropped input — the offending status word lights red, the line
 * holds, the meter goes dead-flat).
 *
 * Mount once via `mountSessionLayout(root)`, then `renderSessionFrame(mounted,
 * next)` diffs + pokes textContent / CSS vars / data-attrs only — no rebuild on
 * the rAF hot path. Aliveness lives in the live meter (real RMS, smoothed) +
 * the type/receipt gesture; there is deliberately NO heartbeat dot and NO green
 * LEDs (status is silk-dim when fine, red only on a dropped input).
 *
 * The SessionState prop shape is the render-loop projection contract and is
 * UNCHANGED by this rebuild (one optional addition: cohost.onMute). Components
 * are presentation-only — NO IPC, NO timers, NO state.
 */

import { registerStyle } from "./components/_style-registry.js";
import { renderTitlebar, setTitlebarClock, setTitlebarPill, type PillLevel } from "./components/titlebar.js";
import { GROUNDING_FAILURE_MS, type CohostStatus, type ReactionsByTs, type TranscriptLine } from "./components/cohost.js";
import type { CitationChip } from "./components/citation-strip.js";
import type { PhaseChunk } from "./components/phase-tape.js";
import type { MidiEvent } from "./components/event-ribbon.js";
import type { BadgeState } from "./components/status-bar.js";

export interface SessionState {
  titlebar: {
    live: PillLevel;
    rec: PillLevel;
    sys: PillLevel;
    clock: string;
  };
  meters: {
    music: { rms: number; peak: number | null };
    voice: { rms: number; peak: number | null };
    mic: { rms: number; peak: number | null };
  };
  timecode: {
    clock: string;
    bpm: number | null;
    key: string | null;
    deck: string | null;
    track: { title: string; artist?: string | null } | null;
    genre: string | null;
  };
  phase: {
    chunks: PhaseChunk[];
    nowPct: number;
  };
  drop: {
    bars: number | null;
    bpmPeriodMs?: number;
  };
  events: MidiEvent[];
  cohost: {
    status: CohostStatus;
    transcript: TranscriptLine[];
    latencyMs: number | null;
    grounded: boolean;
    /** H9 retry — wired to restart_sidecar by the render-loop. */
    onRetry?: () => void;
    /** Citation chip strips keyed by transcript line `ts`. */
    reactions?: ReactionsByTs;
    /** Chip click → debrief deep-link (render-loop builds the invoke). */
    onChipClick?: (chip: CitationChip) => void;
    /** "see all reactions" → debrief window (render-loop wires it). */
    onOpenAllReactions?: () => void;
    /** Deck mute control → ipc.session.mute (render-loop wires it).
     *  Omitted (dev mock) → the mute control renders but is a no-op. */
    onMute?: () => void;
  };
  status: {
    livekit: BadgeState;
    gemini: "ok" | "down" | null;
    midi: number | null;
    screen: "ok" | "denied" | null;
    muted: boolean;
    hotkey: string;
    errors?: Partial<Record<"livekit" | "gemini" | "midi" | "screen", string>>;
  };
  persona: {
    skill: "BEG" | "INT" | "PRO";
    /** Legacy 2-state — retained for back-compat with existing tests / wires. */
    interaction: "HYPE" | "COACH";
    mood: "HYPE" | "TEACH" | "COACH";
    voice: string;
    genre: string;
    /** Tap-to-cycle mood (HYPE → TEACH → COACH) — render-loop wires it to
     *  ipc.settings.set mood. Omitted (dev mock) → tap is a no-op. */
    onCycleMood?: () => void;
  };
  output: {
    device: string;
    profile: "HP" | "SPK";
  };
}

export interface Mounted {
  root: HTMLElement;
  titlebar: HTMLElement;
  /** Rail persona button (tap-to-cycle mood). */
  persona: HTMLElement;
  personaValue: HTMLElement;
  /** Cross-fade liveness labels (always mounted; opacity toggled by mode). */
  liveFault: HTMLElement;
  ghosts: [HTMLElement, HTMLElement];
  now: HTMLElement;
  receipt: HTMLElement;
  cite: HTMLElement;
  bpm: HTMLElement;
  key: HTMLElement;
  meterFill: HTMLElement;
  meterPeak: HTMLElement;
  statusInputs: { audio: HTMLElement; screen: HTMLElement; midi: HTMLElement };
  statusRight: HTMLElement;
  current: SessionState;
  /** Timestamp (Date.now()) of the most-recent grounded true→false transition.
   *  Null when grounded is currently true. Drives the >5s grounding-failure
   *  flip to the fault state. */
  groundedFalseSinceMs: number | null;
  /** Smoothing state for the live master meter (0.16 attack / 0.04 peak decay
   *  / 86% ceiling — carried from the north-star mock so real RMS reads as
   *  "breathing", not twitchy). Percentages 0..100. */
  meterCur: number;
  meterPk: number;
  /** Last now-line `ts` — when it changes the receipt gesture re-fires. */
  lastNowTs: string | null;
  /** Chip click handler currently bound on the cite (re-bound on change). */
  citeChip: CitationChip | null;
}

// Calm idle hero line shown in silent mode before the co-host's first reaction
// (honest placeholder, dimmed by the silent CSS — never a fabricated reaction).
const IDLE_HERO_LINE = "listening for the mix…";

const METER_ATTACK = 0.16;
const METER_PEAK_DECAY = 0.04;
const METER_CEIL = 86;

const LAYOUT_CSS = `
  .vmx-session {
    display: grid;
    grid-template-rows: var(--titlebar-h) 1fr var(--statusbar-h);
    height: 100vh;
    position: relative;
    overflow: hidden;
  }

  /* === THE DECK — no card. Open void. Hero anchored low (mixer LCD). ==== */
  .vmx-stage { display: grid; place-items: stretch; min-height: 0; position: relative; }
  .vmx-deck {
    position: relative;
    display: grid;
    grid-template-rows: auto 1fr auto;
    min-height: 0;
    padding: 0 clamp(24px, 6vw, 96px);
  }

  /* --- top rail: persona (tap-to-cycle) · controls · liveness label --- */
  .vmx-deck__rail {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-4);
    padding: var(--sp-5) 0 var(--sp-4);
    border-bottom: 1px solid var(--glass-edge);
  }
  .vmx-persona {
    appearance: none; -webkit-appearance: none;
    display: flex; align-items: baseline; gap: var(--sp-3);
    border: 0; background: none; margin: 0; padding: 2px 0;
    cursor: pointer;
    transition: opacity 150ms ease-out;
  }
  .vmx-persona:hover { opacity: 0.82; }
  .vmx-persona:focus-visible { outline: 2px solid var(--amber); outline-offset: 3px; border-radius: var(--rad-sm); }
  .vmx-persona__k {
    font-family: var(--type-display);
    font-variation-settings: 'wdth' 85, 'wght' 600;
    font-size: 10px; letter-spacing: 0.22em; text-transform: uppercase;
    color: var(--silk-22);
  }
  .vmx-persona__v {
    font-family: var(--type-display);
    font-variation-settings: 'wdth' 85, 'wght' 700;
    font-size: 14px; letter-spacing: 0.12em; text-transform: uppercase;
    color: var(--silk-65);
  }
  /* persistent low-ink at rest (reachable mid-set), full on hover/focus.
   * Real mute also bound to the push-to-mute hotkey (session-shortcuts.ts). */
  .vmx-deck__controls { display: flex; gap: var(--sp-2); opacity: 0.32; transition: opacity 180ms ease-out; }
  .vmx-deck:hover .vmx-deck__controls, .vmx-deck:focus-within .vmx-deck__controls { opacity: 1; }
  .vmx-deck__controls button {
    font-family: var(--type-display);
    font-variation-settings: 'wdth' 85, 'wght' 600;
    font-size: 9px; letter-spacing: 0.2em; text-transform: uppercase;
    color: var(--silk-40);
    border: 1px solid var(--glass-edge); border-radius: var(--rad-sm);
    padding: 5px 12px; background: rgba(2, 3, 6, 0.4);
    transition: color var(--motion-step) ease-out, border-color var(--motion-step) ease-out;
  }
  .vmx-deck__controls button:hover { color: var(--silk); border-color: var(--glass-edge-up); }
  .vmx-deck__controls button[data-on="true"] { color: var(--amber); border-color: var(--amber-40); }
  .vmx-live { position: relative; min-width: 168px; height: 1.2em; text-align: right; }
  .vmx-live__s {
    position: absolute; right: 0; top: 0; white-space: nowrap; opacity: 0;
    transition: opacity 700ms ease-out;
    font-family: var(--type-mono); font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase;
  }
  .vmx-live__s--live { color: var(--silk-40); }
  .vmx-live__s--silent { color: var(--silk-22); }
  .vmx-live__s--fault { color: var(--amber-pale); }
  .vmx-session:not([data-mode]) .vmx-live__s--live,
  .vmx-session[data-mode=""] .vmx-live__s--live { opacity: 1; }
  .vmx-session[data-mode="silent"] .vmx-live__s--silent { opacity: 1; }
  .vmx-session[data-mode="fault"] .vmx-live__s--fault { opacity: 1; }

  /* --- THE HERO: the co-host speaks, anchored low on void --- */
  .vmx-deck__speak {
    display: flex; flex-direction: column; justify-content: flex-end;
    gap: var(--sp-3); min-height: 0; padding: var(--sp-7) 0 var(--sp-6);
  }
  .vmx-ghost {
    font-family: var(--type-body);
    font-variation-settings: 'wdth' 100, 'wght' 400;
    font-size: 15px; line-height: 1.4;
    transition: color 700ms ease-out;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 40ch;
  }
  .vmx-ghost--g2 { color: var(--silk-12); }
  .vmx-ghost--g1 { color: var(--silk-22); }
  .vmx-claim { display: flex; flex-direction: column; align-items: flex-start; gap: var(--sp-3); margin-top: var(--sp-2); }
  .vmx-now {
    font-family: var(--type-display);
    font-variation-settings: 'wdth' 92, 'wght' 600;
    font-size: clamp(30px, 3.6vw, 48px); line-height: 1.04; letter-spacing: 0.003em;
    color: var(--silk); text-wrap: balance; max-width: 22ch;
    transition: color 700ms ease-out;
  }
  .vmx-now[data-arrived="true"] { animation: vmx-rise 400ms cubic-bezier(0.16, 1, 0.3, 1); }
  @keyframes vmx-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

  /* THE RECEIPT — rule draws L→R, cite ignites at its terminus [signature] */
  .vmx-receipt {
    display: flex; align-items: center; gap: var(--sp-3);
    width: min(22ch, 100%); max-width: 520px;
    transition: opacity 700ms ease-out;
  }
  .vmx-receipt[hidden] { display: none; }
  .vmx-receipt__rule {
    flex: 1; height: 1px;
    background: linear-gradient(90deg, var(--amber-40), var(--amber));
    transform: scaleX(0); transform-origin: left;
  }
  .vmx-receipt[data-arrived="true"] .vmx-receipt__rule { animation: vmx-draw 520ms cubic-bezier(0.22, 1, 0.36, 1) 360ms forwards; }
  .vmx-cite {
    flex: none; display: inline-flex; align-items: center; gap: 6px;
    font-family: var(--type-mono); font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--amber-pale); border: 1px solid var(--amber-22); border-radius: var(--rad-sm);
    padding: 3px 8px; background: rgba(255, 138, 61, 0.04); cursor: pointer;
    text-shadow: 0 0 6px var(--amber-22);
  }
  .vmx-receipt[data-arrived="true"] .vmx-cite { animation: vmx-ignite 380ms cubic-bezier(0.16, 1, 0.3, 1) 900ms both; }
  .vmx-cite:hover { border-color: var(--amber-40); background: rgba(255, 138, 61, 0.09); }
  .vmx-cite:focus-visible { outline: 2px solid var(--amber); outline-offset: 2px; }
  @keyframes vmx-draw { to { transform: scaleX(1); } }
  @keyframes vmx-ignite {
    0% { opacity: 0; color: var(--silk-40); border-color: var(--glass-edge); background: transparent; text-shadow: none; box-shadow: none; }
    55% { opacity: 1; color: var(--amber); border-color: var(--amber-65); background: rgba(255, 138, 61, 0.10); text-shadow: 0 0 8px var(--amber-65); box-shadow: var(--glow-soft); }
    100% { opacity: 1; color: var(--amber-pale); border-color: var(--amber-22); background: rgba(255, 138, 61, 0.04); text-shadow: 0 0 6px var(--amber-22); box-shadow: none; }
  }

  /* --- FOOT: one steady master readout (BPM · key · live level) --- */
  .vmx-deck__foot {
    display: grid; grid-template-columns: auto auto 1fr; align-items: center;
    gap: clamp(24px, 4vw, 64px); padding: var(--sp-4) 0 var(--sp-5);
    border-top: 1px solid var(--glass-edge);
  }
  .vmx-read { display: flex; align-items: baseline; gap: var(--sp-2); }
  .vmx-read__lab {
    font-family: var(--type-display); font-variation-settings: 'wdth' 85, 'wght' 600;
    font-size: 9px; letter-spacing: 0.22em; text-transform: uppercase; color: var(--silk-22);
  }
  .vmx-read__num {
    font-family: var(--type-mono); font-weight: 500; font-size: 22px; letter-spacing: 0.02em;
    color: var(--silk); transition: color 700ms ease-out;
  }
  .vmx-read__key {
    font-family: var(--type-mono); font-weight: 500; font-size: 18px; letter-spacing: 0.04em;
    color: var(--amber-pale); transition: color 700ms ease-out;
  }
  .vmx-fmeter {
    position: relative; height: 12px; border-radius: var(--rad-sm);
    background: var(--void-1); border: 1px solid var(--glass-edge);
    box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.7); overflow: hidden;
  }
  .vmx-fmeter__fill {
    position: absolute; inset: 1px; width: 0%; border-radius: 1px;
    background: linear-gradient(90deg, var(--amber-40), var(--amber-78) 80%, var(--amber));
    transition: background 700ms ease-out;
  }
  .vmx-fmeter__peak {
    position: absolute; top: 1px; bottom: 1px; left: 0; width: 2px;
    background: var(--amber-pale); transition: opacity 700ms ease-out;
  }

  /* === status row — silk-dim when fine; lights red on a dropped input === */
  .vmx-statusrow {
    display: flex; align-items: center; justify-content: space-between; padding: 0 var(--sp-5);
    background: rgba(0, 0, 0, 0.55); backdrop-filter: var(--blur-glass-light);
    -webkit-backdrop-filter: var(--blur-glass-light); border-top: 1px solid var(--glass-edge);
  }
  .vmx-statusrow__inputs {
    display: flex; align-items: center;
    font-family: var(--type-mono); font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--silk-22);
  }
  .vmx-statusrow__i { transition: color 700ms ease-out, text-shadow 700ms ease-out; }
  .vmx-statusrow__i[data-down="true"] { color: var(--led-fault); text-shadow: 0 0 6px rgba(212, 65, 58, 0.5); }
  .vmx-statusrow__sep { color: var(--silk-12); margin: 0 8px; }
  .vmx-statusrow__right { font-family: var(--type-mono); font-size: 11px; color: var(--silk-40); letter-spacing: 0.08em; }

  /* === SILENT + FAULT — the surface settles into listening / holds on a drop = */
  .vmx-session[data-mode="silent"] .vmx-now,
  .vmx-session[data-mode="fault"] .vmx-now { color: var(--silk-40); }
  .vmx-session[data-mode="silent"] .vmx-receipt,
  .vmx-session[data-mode="fault"] .vmx-receipt { opacity: 0; pointer-events: none; }
  .vmx-session[data-mode="silent"] .vmx-read__num,
  .vmx-session[data-mode="silent"] .vmx-read__key,
  .vmx-session[data-mode="fault"] .vmx-read__num,
  .vmx-session[data-mode="fault"] .vmx-read__key { color: var(--silk-40); }
  .vmx-session[data-mode="silent"] .vmx-fmeter__fill {
    background: var(--silk-22); animation: vmx-idlebreath 3200ms ease-in-out infinite;
  }
  .vmx-session[data-mode="fault"] .vmx-fmeter__fill { background: var(--silk-12); animation: none; }
  .vmx-session[data-mode="silent"] .vmx-fmeter__peak,
  .vmx-session[data-mode="fault"] .vmx-fmeter__peak { opacity: 0; }
  @keyframes vmx-idlebreath { 0%, 100% { opacity: 0.4; } 50% { opacity: 0.85; } }

  @media (prefers-reduced-motion: reduce) {
    .vmx-now[data-arrived="true"] { animation: none; }
    .vmx-receipt[data-arrived="true"] .vmx-receipt__rule { animation: none; transform: scaleX(1); }
    .vmx-receipt[data-arrived="true"] .vmx-cite { animation: none; }
    .vmx-session[data-mode="silent"] .vmx-fmeter__fill { animation: none; }
  }
`;

registerStyle("vmx-session", LAYOUT_CSS);

/** Build and mount the full live-session DOM tree. Returns a handle the
 *  renderer uses for hot updates. */
export function mountSessionLayout(rootEl: HTMLElement, initial?: SessionState): Mounted {
  const state = initial ?? defaultState();

  const root = document.createElement("div");
  root.className = "vmx-session";
  root.dataset.mode = "";

  // Titlebar (reused) — gear opens the settings drawer.
  const titlebar = renderTitlebar({
    live: state.titlebar.live,
    rec: state.titlebar.rec,
    sys: state.titlebar.sys,
    clock: state.titlebar.clock,
    onSettingsClick: () => {
      void import("../settings/SettingsDrawer.js").then((m) => m.openSettings());
    },
  });
  root.append(titlebar);

  // Stage → the single deck.
  const stage = document.createElement("main");
  stage.className = "vmx-stage";
  const deck = document.createElement("section");
  deck.className = "vmx-deck";
  deck.tabIndex = 0;
  deck.setAttribute("aria-label", "co-host");

  // --- rail
  const rail = document.createElement("div");
  rail.className = "vmx-deck__rail";

  const persona = document.createElement("button");
  persona.type = "button";
  persona.className = "vmx-persona";
  const personaK = document.createElement("span");
  personaK.className = "vmx-persona__k";
  personaK.textContent = "persona";
  const personaValue = document.createElement("span");
  personaValue.className = "vmx-persona__v";
  persona.append(personaK, personaValue);
  persona.addEventListener("click", () => state.persona.onCycleMood?.());

  const controls = document.createElement("div");
  controls.className = "vmx-deck__controls";
  const muteBtn = document.createElement("button");
  muteBtn.type = "button";
  muteBtn.dataset.action = "mute";
  muteBtn.textContent = "mute";
  muteBtn.addEventListener("click", () => state.cohost.onMute?.());
  controls.append(muteBtn);

  const live = document.createElement("div");
  live.className = "vmx-live";
  const liveLive = makeLiveLabel("live", "reading the room");
  const liveSilent = makeLiveLabel("silent", "listening");
  const liveFault = makeLiveLabel("fault", "");
  live.append(liveLive, liveSilent, liveFault);

  rail.append(persona, controls, live);
  deck.append(rail);

  // --- speak (ghosts + claim[now + receipt])
  const speak = document.createElement("div");
  speak.className = "vmx-deck__speak";
  const ghost2 = document.createElement("p");
  ghost2.className = "vmx-ghost vmx-ghost--g2";
  const ghost1 = document.createElement("p");
  ghost1.className = "vmx-ghost vmx-ghost--g1";
  const claim = document.createElement("div");
  claim.className = "vmx-claim";
  const now = document.createElement("p");
  now.className = "vmx-now";
  const receipt = document.createElement("div");
  receipt.className = "vmx-receipt";
  receipt.hidden = true;
  const rule = document.createElement("span");
  rule.className = "vmx-receipt__rule";
  rule.setAttribute("aria-hidden", "true");
  const cite = document.createElement("button");
  cite.type = "button";
  cite.className = "vmx-cite";
  receipt.append(rule, cite);
  claim.append(now, receipt);
  speak.append(ghost2, ghost1, claim);
  deck.append(speak);

  // --- foot (bpm · key · live meter)
  const foot = document.createElement("div");
  foot.className = "vmx-deck__foot";
  const { wrap: bpmWrap, value: bpm } = makeReadout("bpm");
  const { wrap: keyWrap, value: key } = makeReadout("key", true);
  const fmeter = document.createElement("div");
  fmeter.className = "vmx-fmeter";
  fmeter.setAttribute("aria-label", "master level");
  const meterFill = document.createElement("div");
  meterFill.className = "vmx-fmeter__fill";
  const meterPeak = document.createElement("div");
  meterPeak.className = "vmx-fmeter__peak";
  fmeter.append(meterFill, meterPeak);
  foot.append(bpmWrap, keyWrap, fmeter);
  deck.append(foot);

  stage.append(deck);
  root.append(stage);

  // --- status row
  const statusRow = document.createElement("footer");
  statusRow.className = "vmx-statusrow";
  const inputsEl = document.createElement("div");
  inputsEl.className = "vmx-statusrow__inputs";
  const inAudio = makeInput("audio");
  const inScreen = makeInput("screen");
  const inMidi = makeInput("midi");
  inputsEl.append(inAudio, sep(), inScreen, sep(), inMidi);
  const statusRight = document.createElement("div");
  statusRight.className = "vmx-statusrow__right";
  statusRow.append(inputsEl, statusRight);
  root.append(statusRow);

  rootEl.replaceChildren(root);

  const mounted: Mounted = {
    root,
    titlebar,
    persona,
    personaValue,
    liveFault,
    ghosts: [ghost1, ghost2],
    now,
    receipt,
    cite,
    bpm,
    key,
    meterFill,
    meterPeak,
    statusInputs: { audio: inAudio, screen: inScreen, midi: inMidi },
    statusRight,
    current: state,
    groundedFalseSinceMs: state.cohost.grounded ? null : Date.now(),
    meterCur: 0,
    meterPk: 0,
    lastNowTs: null,
    citeChip: null,
  };

  // Seed the visible content from the initial state (mount = first paint).
  applyState(mounted, state, /* isMount */ true);
  return mounted;
}

function makeLiveLabel(kind: "live" | "silent" | "fault", text: string): HTMLElement {
  const el = document.createElement("span");
  el.className = `vmx-live__s vmx-live__s--${kind}`;
  el.textContent = text;
  return el;
}

function makeReadout(label: string, isKey = false): { wrap: HTMLElement; value: HTMLElement } {
  const wrap = document.createElement("div");
  wrap.className = "vmx-read";
  const lab = document.createElement("span");
  lab.className = "vmx-read__lab";
  lab.textContent = label;
  const value = document.createElement("span");
  value.className = isKey ? "vmx-read__key" : "vmx-read__num";
  wrap.append(lab, value);
  return { wrap, value };
}

function makeInput(name: string): HTMLElement {
  const el = document.createElement("span");
  el.className = "vmx-statusrow__i";
  el.dataset.input = name;
  el.textContent = name;
  return el;
}

function sep(): HTMLElement {
  const s = document.createElement("span");
  s.className = "vmx-statusrow__sep";
  s.textContent = "·";
  s.setAttribute("aria-hidden", "true");
  return s;
}

/** Idempotent hot-update. Diffs `mounted.current` against `next` and pokes
 *  textContent / data-attrs / CSS only. Called on mount (full apply) and on
 *  every rAF tick (cheap diffs). */
export function renderSessionFrame(mounted: Mounted, next: SessionState): void {
  applyState(mounted, next, /* isMount */ false);
  mounted.current = next;
}

function applyState(mounted: Mounted, next: SessionState, isMount: boolean): void {
  const prev = mounted.current;

  // --- titlebar (clock + pills) ---
  if (isMount || prev.titlebar.clock !== next.titlebar.clock) setTitlebarClock(mounted.titlebar, next.titlebar.clock);
  if (isMount || prev.titlebar.live !== next.titlebar.live) setTitlebarPill(mounted.titlebar, "live", next.titlebar.live);
  if (isMount || prev.titlebar.rec !== next.titlebar.rec) setTitlebarPill(mounted.titlebar, "rec", next.titlebar.rec);
  if (isMount || prev.titlebar.sys !== next.titlebar.sys) setTitlebarPill(mounted.titlebar, "sys", next.titlebar.sys);

  // --- persona (tap-to-cycle mood headline) ---
  if (isMount || prev.persona.mood !== next.persona.mood) {
    mounted.personaValue.textContent = next.persona.mood.toLowerCase();
    mounted.persona.setAttribute(
      "aria-label",
      `co-host mood: ${next.persona.mood.toLowerCase()}. tap to cycle hype, teach, coach.`,
    );
  }

  // --- grounding-failure timer ---
  // Only runs while the co-host is ACTIVE. At IDLE there's no music to ground
  // to, so grounded=false is EXPECTED — not a failure. Counting it at idle is
  // what made a quiet session falsely flip to "gemini unreachable" after 5s
  // (fault mode → blank hero, the recurring "empty screen / always broken").
  // The clock starts once when the co-host is active+ungrounded and clears the
  // instant it grounds a reaction or returns to idle.
  if (next.cohost.status === "IDLE" || next.cohost.grounded) {
    mounted.groundedFalseSinceMs = null;
  } else if (mounted.groundedFalseSinceMs == null) {
    mounted.groundedFalseSinceMs = Date.now();
  }
  const failureElapsedMs =
    mounted.groundedFalseSinceMs != null ? Date.now() - mounted.groundedFalseSinceMs : null;

  // --- resolve the three-state mode ---
  const downInput = faultInput(next.status, failureElapsedMs);
  const mode: "" | "silent" | "fault" = downInput
    ? "fault"
    : next.cohost.status === "IDLE"
      ? "silent"
      : "";
  if (mounted.root.dataset.mode !== mode) mounted.root.dataset.mode = mode;

  // Fault label states the cause; refresh whenever the cause changes.
  if (downInput) {
    const causeText =
      downInput === "audio"
        ? "◂ audio input dropped"
        : downInput === "screen"
          ? "◂ screen capture lost"
          : "◂ gemini unreachable";
    if (mounted.liveFault.textContent !== causeText) mounted.liveFault.textContent = causeText;
  }

  // --- the spoken line + ghosts (newest = now, prior two recede) ---
  const lines = next.cohost.transcript;
  const nowLine = lines.length ? lines[lines.length - 1]! : null;
  const g1Line = lines.length >= 2 ? lines[lines.length - 2]! : null;
  const g2Line = lines.length >= 3 ? lines[lines.length - 3]! : null;
  // Idle affordance: before the co-host's first line (empty transcript) the
  // hero — the centerpiece of "The Deck Speaks" — would otherwise be blank,
  // reading as a dead/empty screen. In silent mode show a calm, dimmed prompt
  // (the silent CSS already greys .vmx-now to silk-40, so it reads as a
  // placeholder, NOT a fabricated reaction). Real lines replace it the instant
  // the co-host speaks. Live mode keeps "" (a live deck always has a line).
  const nowText = nowLine ? nowLine.text : mode === "silent" ? IDLE_HERO_LINE : "";
  if (mounted.now.textContent !== nowText) mounted.now.textContent = nowText;
  setGhost(mounted.ghosts[0], g1Line);
  setGhost(mounted.ghosts[1], g2Line);

  // --- the receipt (cite for the now-line) ---
  const chips = nowLine && next.cohost.reactions ? next.cohost.reactions.get(nowLine.ts) : undefined;
  const chip = chips && chips.length ? chips[0]! : null;
  if (chip) {
    mounted.receipt.hidden = false;
    const citeText = `◂ ${chip.verb} @ ${formatTs(chip.timestamp_s)}`;
    if (mounted.cite.textContent !== citeText) mounted.cite.textContent = citeText;
    // Re-bind the click only when the chip identity changes.
    if (mounted.citeChip?.event_id !== chip.event_id) {
      mounted.citeChip = chip;
      mounted.cite.onclick = next.cohost.onChipClick ? () => next.cohost.onChipClick!(chip) : null;
    }
  } else {
    mounted.receipt.hidden = true;
    mounted.citeChip = null;
    mounted.cite.onclick = null;
  }

  // --- THE SIGNATURE GESTURE — re-fire on a genuinely new now-line ---
  const nowTs = nowLine ? nowLine.ts : null;
  if (nowTs && nowTs !== mounted.lastNowTs && mode === "" && !isMount) {
    fireReceipt(mounted);
  }
  mounted.lastNowTs = nowTs;

  // --- foot readouts ---
  const bpmText = next.timecode.bpm != null ? next.timecode.bpm.toFixed(1) : "—";
  if (mounted.bpm.textContent !== bpmText) mounted.bpm.textContent = bpmText;
  const keyText = next.timecode.key ?? "—";
  if (mounted.key.textContent !== keyText) mounted.key.textContent = keyText;

  // --- master meter (smoothed; live only — held/recolored by CSS in silent/fault) ---
  if (mode === "") {
    const target = clamp01(next.meters.music.rms) * 100;
    mounted.meterCur += (target - mounted.meterCur) * METER_ATTACK;
    const lead = mounted.meterCur + 4;
    if (lead > mounted.meterPk) mounted.meterPk = lead;
    else mounted.meterPk += (lead - mounted.meterPk) * METER_PEAK_DECAY;
    const w = Math.min(mounted.meterCur, 100);
    mounted.meterFill.style.width = `${w.toFixed(1)}%`;
    mounted.meterPeak.style.left = `${Math.min(mounted.meterPk, METER_CEIL).toFixed(1)}%`;
  }

  // --- mute control reflects state ---
  if (isMount || prev.status.muted !== next.status.muted) {
    const muteBtn = mounted.persona.parentElement?.querySelector<HTMLElement>('[data-action="mute"]');
    if (muteBtn) {
      muteBtn.dataset.on = next.status.muted ? "true" : "false";
      muteBtn.textContent = next.status.muted ? "muted" : "mute";
    }
  }

  // --- status row inputs (silk-dim; red on a dropped input) ---
  setInputDown(mounted.statusInputs.audio, next.status.livekit === "down");
  setInputDown(mounted.statusInputs.screen, next.status.screen === "denied");
  setInputDown(mounted.statusInputs.midi, next.status.midi === 0);
  const rightText = `${deviceLabel(next.output.device)} · 48.0k`;
  if (mounted.statusRight.textContent !== rightText) mounted.statusRight.textContent = rightText;
}

function setGhost(el: HTMLElement, line: TranscriptLine | null): void {
  const text = line ? line.text : "";
  if (el.textContent !== text) el.textContent = text;
  el.style.display = text ? "" : "none";
}

/** Re-trigger the rise + draw + ignite CSS animations on a new reaction.
 *  CSS won't replay an animation on a class already present, so we clear
 *  data-arrived, force a reflow, then set it — the canonical retrigger. */
function fireReceipt(mounted: Mounted): void {
  mounted.now.dataset.arrived = "";
  mounted.receipt.dataset.arrived = "";
  // Force reflow so the cleared animation is committed before re-adding.
  void mounted.now.offsetWidth;
  mounted.now.dataset.arrived = "true";
  mounted.receipt.dataset.arrived = "true";
}

/** Which input (if any) is in a fault state — the offending one lights red
 *  and names the cause. Grounding-failure (>5s ungrounded) reads as the
 *  audio/gemini path being down. Priority: audio (livekit) > screen > gemini
 *  grounding. Returns null when everything is fine. */
function faultInput(
  status: SessionState["status"],
  failureElapsedMs: number | null,
): "audio" | "screen" | "gemini" | null {
  if (status.livekit === "down") return "audio";
  if (status.screen === "denied") return "screen";
  if (status.gemini === "down") return "gemini";
  if (failureElapsedMs != null && failureElapsedMs >= GROUNDING_FAILURE_MS) return "gemini";
  return null;
}

function setInputDown(el: HTMLElement, down: boolean): void {
  const v = down ? "true" : "false";
  if (el.dataset.down !== v) el.dataset.down = v;
}

/** Format a citation timestamp (seconds) as mm:ss (or h:mm:ss past an hour). */
function formatTs(s: number): string {
  const total = Math.max(0, Math.floor(s));
  const hh = Math.floor(total / 3600);
  const mm = Math.floor((total % 3600) / 60);
  const ss = total % 60;
  const p = (n: number): string => n.toString().padStart(2, "0");
  return hh > 0 ? `${hh}:${p(mm)}:${p(ss)}` : `${mm}:${p(ss)}`;
}

/** Trim a device id/name to a short status-row label. */
function deviceLabel(device: string): string {
  if (!device || device === "AUTO") return "default out";
  return device.length > 22 ? device.slice(0, 21) + "…" : device;
}

function clamp01(n: number): number {
  if (!Number.isFinite(n)) return 0;
  if (n < 0) return 0;
  if (n > 1) return 1;
  return n;
}

/** Mock-friendly default state for `?dev=session-mock` and tests. */
export function defaultState(): SessionState {
  return {
    titlebar: { live: "ok", rec: "ok", sys: "ok", clock: "00:00:00" },
    meters: {
      music: { rms: 0, peak: 0 },
      voice: { rms: 0, peak: 0 },
      mic: { rms: 0, peak: 0 },
    },
    timecode: { clock: "00:00:00", bpm: null, key: null, deck: null, track: null, genre: null },
    phase: { chunks: [], nowPct: 0 },
    drop: { bars: null },
    events: [],
    cohost: {
      status: "IDLE",
      transcript: [],
      latencyMs: null,
      grounded: false,
    },
    status: {
      livekit: null,
      gemini: null,
      midi: null,
      screen: null,
      muted: false,
      hotkey: "⌘⇧M",
      errors: {},
    },
    persona: { skill: "INT", interaction: "HYPE", mood: "HYPE", voice: "kore", genre: "techno" },
    output: { device: "MacBook Pro Speakers", profile: "HP" },
  };
}
