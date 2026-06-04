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
 * Mount once via `mountSessionLayout(root, state, { onOpenSettings })`, then
 * `renderSessionFrame(mounted, next)` diffs + pokes textContent / CSS vars /
 * data-attrs only — no rebuild on the rAF hot path. Aliveness lives in the live
 * meter (real RMS, smoothed) + the type/receipt gesture; there is deliberately
 * NO heartbeat dot and NO green LEDs (status is silk-dim when fine, red only on
 * a dropped input).
 *
 * The SessionState prop shape is the render-loop projection contract and is
 * UNCHANGED by this rebuild except optional action callbacks. Components are
 * presentation-only — NO IPC, NO timers, NO state.
 */

import { registerStyle } from "./components/_style-registry.js";
import { renderModePicker, setModePickerActive, type ModePickerMode } from "./components/mode-picker.js";
import { renderTitlebar, setTitlebarClock, setTitlebarPill, type PillLevel } from "./components/titlebar.js";
import { GROUNDING_FAILURE_MS, type CohostStatus, type ReactionsByTs, type TranscriptLine } from "./components/cohost.js";
import { renderDropChip } from "./components/drop-chip.js";
import type { CitationChip } from "./components/citation-strip.js";
import { type PhaseChunk } from "./components/phase-tape.js";
import { type MidiEvent } from "./components/event-ribbon.js";
import type { BadgeState } from "./components/status-bar.js";

type StatusRecheckComponent = "livekit" | "gemini" | "midi" | "screen";

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
  actions: {
    /** Open the Library/Viber chat + set-building window. */
    onOpenVibeEngine?: () => void;
  };
  status: {
    livekit: BadgeState;
    gemini: "ok" | "down" | null;
    midi: number | null;
    screen: "ok" | "denied" | "unavailable" | null;
    voice?: "ok" | "muted" | null;
    captureDevice?: string | null;
    midiActivity?:
      | "disconnected"
      | "connected_no_midi_traffic"
      | "midi_traffic_unmapped"
      | "midi_events_no_moves"
      | "active"
      | "unknown"
      | null;
    midiDevice?: string | null;
    muted: boolean;
    hotkey: string;
    /** Recheck a down status input via ipc.status.recheck. */
    onRecheck?: (component: StatusRecheckComponent) => void;
    errors?: Partial<Record<"livekit" | "gemini" | "midi" | "screen", string>>;
  };
  claimPolicy?: {
    level: "green" | "yellow" | "red";
    label: string;
    policy: string;
    reason: string | null;
  } | null;
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
  /** Phase 97 / ONBOARD-01 — top-level mode (cohost/learn/build/debrief).
   *  Optional on the layout-side type so existing tests / mocks that omit
   *  it still type-check. mountSessionLayout defaults to "cohost". */
  mode?: ModePickerMode;
  /** Phase 97 / ONBOARD-01 — click handler fired by the mode picker.
   *  Render-loop wires it to modeChangeHandler (setSessionState +
   *  ipc.session.set_mode). Omitted (dev mock) → click is a no-op. */
  onModeChange?: (mode: ModePickerMode) => void;
}

export interface Mounted {
  root: HTMLElement;
  titlebar: HTMLElement;
  /** Phase 97 / ONBOARD-01 — 4-mode picker row between titlebar and stage. */
  modePicker: HTMLElement;
  /** Rail persona button (tap-to-cycle mood). */
  persona: HTMLElement;
  personaValue: HTMLElement;
  vibeEngineButton: HTMLElement;
  muteButton: HTMLElement;
  /** Cross-fade liveness labels (always mounted; opacity toggled by mode). */
  liveFault: HTMLElement;
  ghosts: [HTMLElement, HTMLElement];
  idleProof: HTMLElement;
  idleProofCells: {
    audio: HTMLElement;
    sven: HTMLElement;
    controller: HTMLElement;
    screen: HTMLElement;
  };
  idleProofNext: HTMLElement;
  now: HTMLElement;
  receipt: HTMLElement;
  dropSlot: HTMLElement;
  cite: HTMLElement;
  bpm: HTMLElement;
  key: HTMLElement;
  meterFill: HTMLElement;
  meterPeak: HTMLElement;
  statusInputs: {
    audio: HTMLButtonElement;
    ai: HTMLButtonElement;
    voice: HTMLButtonElement;
    voiceSep: HTMLElement;
    screen: HTMLButtonElement;
    midi: HTMLButtonElement;
  };
  statusRight: HTMLElement;
  claimPolicy: HTMLElement;
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

export interface MountSessionLayoutOptions {
  /** Router/mock entry point owns the settings drawer module. The layout only
   *  receives the action so it stays a presentational surface. */
  onOpenSettings?: () => void;
}

// Calm idle hero shown before the co-host's first reaction. It is an operating
// state, not a fabricated reaction: why the deck is quiet and what arms proof.
const IDLE_HERO_LINE = "Ready for the first move.";

const METER_ATTACK = 0.16;
const METER_PEAK_DECAY = 0.04;
const METER_CEIL = 86;
const METER_DB_FLOOR = -36;
const METER_DB_CEIL = -6;

const LAYOUT_CSS = `
  .vmx-session {
    display: grid;
    grid-template-rows: var(--titlebar-h) auto 1fr var(--statusbar-h);
    height: 100vh;
    position: relative;
    overflow: hidden;
    background:
      linear-gradient(112deg, rgba(255, 165, 223, 0.040), transparent 34%),
      linear-gradient(180deg, rgba(255, 251, 244, 0.016), transparent 24%),
      var(--void-5);
  }
  /* Phase 97 / ONBOARD-01 — mode picker bar between titlebar and stage.
   * Sized by content (height: 34px from the picker itself + 12px padding
   * either side). Sits flush against the titlebar with a faint --silk-22
   * hairline below to separate the navigation layer from the deck stage. */
  .vmx-modebar {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--sp-2) clamp(22px, 5vw, 76px);
    border-bottom: 1px solid var(--silk-22);
    background-color: var(--void);
    position: relative;
    z-index: 1;
  }
  .vmx-modebar .vmx-mode-picker { max-width: 480px; }
  .vmx-drop-slot:empty { display: none; }

  /* === THE DECK — no card. Open void. Hero anchored low (mixer LCD). ==== */
  .vmx-stage { display: grid; place-items: stretch; min-height: 0; position: relative; z-index: 1; }
  .vmx-stage::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background:
      radial-gradient(92% 76% at 50% 44%, rgba(255, 222, 242, 0.038), transparent 62%),
      linear-gradient(180deg, transparent 0%, rgba(255, 165, 223, 0.030) 100%);
    opacity: 0.9;
  }
  .vmx-deck {
    position: relative;
    display: grid;
    grid-template-rows: auto 1fr auto;
    min-height: 0;
    padding: clamp(18px, 2.4vw, 32px) clamp(22px, 5vw, 76px);
  }
  .vmx-deck > * { position: relative; z-index: 1; }

  /* --- top rail: persona (tap-to-cycle) · controls · liveness label --- */
  .vmx-deck__rail {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-4);
    margin: 0 clamp(0px, 1.2vw, 18px);
    /* Borderless control strip, NOT a bordered card. Only the voice slab is a
     * lit surface (the 20/80 the docstring describes) — the rail holds chrome
     * controls, so it reads as a thin strip above the hero, not a third slab. */
    padding: 2px 2px 0;
    min-width: 0;
  }
  .vmx-persona {
    appearance: none; -webkit-appearance: none;
    position: relative; overflow: hidden;
    display: flex; align-items: center; gap: var(--sp-3);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    background:
      linear-gradient(180deg, rgba(255, 251, 244, 0.020), rgba(0, 0, 0, 0.18)),
      rgba(0, 0, 0, 0.18);
    margin: 0;
    padding: 8px 10px;
    min-width: 128px;
    cursor: pointer;
    box-shadow:
      inset 0 1px 0 rgba(255, 251, 244, 0.028),
      inset 0 -2px 0 rgba(0, 0, 0, 0.64);
    transition: border-color 180ms cubic-bezier(0.16, 1, 0.3, 1), box-shadow 180ms cubic-bezier(0.16, 1, 0.3, 1);
  }
  /* DELIGHT (impeccable, 2026-06-03): the persona is the co-host's character
   * dial — the control a DJ taps mid-set to swing hype → coach → teach. When you
   * reach for it, a rose key-light pools up from the lower-left (mirroring the
   * voice slab's own pool) and the mood word brightens: the co-host leaning
   * toward your hand. One-Rose (a hover state, not a second ambient breath),
   * eased, rose-only, frozen by the rail's reduced-motion handling. */
  .vmx-persona::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: radial-gradient(120% 120% at 16% 118%, var(--amber-22), transparent 58%);
    opacity: 0;
    transition: opacity 180ms cubic-bezier(0.16, 1, 0.3, 1);
  }
  .vmx-persona:hover::before,
  .vmx-persona:focus-visible::before { opacity: 1; }
  .vmx-persona:hover {
    border-color: var(--amber-40);
  }
  .vmx-persona:hover .vmx-persona__v,
  .vmx-persona:focus-visible .vmx-persona__v {
    color: var(--amber);
    text-shadow: 0 0 9px var(--amber-40);
  }
  .vmx-persona:active {
    transform: translateY(1px);
    box-shadow:
      inset 0 2px 5px rgba(0, 0, 0, 0.62),
      inset 0 1px 0 rgba(255, 251, 244, 0.016);
  }
  .vmx-persona:focus-visible { outline: 2px solid var(--amber); outline-offset: 3px; border-radius: var(--rad-sm); }
  /* The "PERSONA" key micro-label was redundant chrome — the lit mood word plus
   * the button's full aria-label ("co-host mood: hype. tap to cycle…") already
   * name the control. Cut so the rose mood word reads in one beat, no key/value
   * spec-sheet tic (impeccable layout pass, 2026-06-03). */
  .vmx-persona__v {
    font-family: var(--type-display);
    font-variation-settings: 'wdth' 85, 'wght' 700;
    font-size: 14px; letter-spacing: 0.12em; text-transform: uppercase;
    color: var(--silk-65);
    transition: color var(--motion-transition) ease-out, text-shadow var(--motion-transition) ease-out;
  }
  .vmx-persona[data-mood="HYPE"] .vmx-persona__v,
  .vmx-persona[data-mood="TEACH"] .vmx-persona__v,
  .vmx-persona[data-mood="COACH"] .vmx-persona__v {
    color: var(--amber-pale);
    text-shadow: 0 0 7px var(--amber-22);
  }
  /* persistent low-ink at rest (reachable mid-set), full on hover/focus.
   * Real mute also bound to the push-to-mute hotkey (session-shortcuts.ts). */
  .vmx-deck__controls { display: flex; gap: var(--sp-2); opacity: 0.58; transition: opacity 180ms ease-out; }
  .vmx-deck:hover .vmx-deck__controls, .vmx-deck:focus-within .vmx-deck__controls { opacity: 1; }
  .vmx-deck__controls button {
    font-family: var(--type-display);
    font-variation-settings: 'wdth' 85, 'wght' 600;
    font-size: 9px; letter-spacing: 0.2em; text-transform: uppercase;
    color: var(--silk-40);
    border: 1px solid var(--glass-edge); border-radius: var(--rad-sm);
    padding: 6px 13px;
    background:
      linear-gradient(180deg, rgba(255, 251, 244, 0.024), rgba(0, 0, 0, 0.20)),
      rgba(2, 3, 6, 0.58);
    box-shadow:
      inset 0 1px 0 rgba(255, 251, 244, 0.040),
      inset 0 -2px 0 rgba(0, 0, 0, 0.68),
      0 1px 0 rgba(0, 0, 0, 0.68);
    white-space: nowrap; cursor: pointer;
    transition: color var(--motion-step) ease-out, border-color var(--motion-step) ease-out, box-shadow var(--motion-step) ease-out, background var(--motion-step) ease-out;
  }
  .vmx-deck__controls button:active {
    transform: translateY(1px);
    box-shadow:
      inset 0 2px 5px rgba(0, 0, 0, 0.62),
      inset 0 1px 0 rgba(255, 251, 244, 0.016);
  }
  .vmx-deck__controls button:hover {
    color: var(--silk);
    border-color: var(--glass-edge-up);
    box-shadow:
      inset 0 1px 0 rgba(255, 251, 244, 0.038),
      inset 0 -1px 0 rgba(0, 0, 0, 0.70);
  }
  .vmx-deck__controls button[data-on="true"] {
    color: var(--amber-pale);
    border-color: var(--amber-40);
    background:
      linear-gradient(180deg, rgba(255, 165, 223, 0.11), rgba(255, 165, 223, 0.025) 58%, rgba(0, 0, 0, 0.22)),
      rgba(2, 3, 6, 0.66);
    box-shadow:
      inset 0 1px 0 rgba(255, 251, 244, 0.040),
      inset 0 -1px 0 var(--amber-22),
      inset 0 0 14px rgba(255, 165, 223, 0.10);
  }
  .vmx-deck__controls button[data-primary="true"] {
    color: var(--amber-pale);
    border-color: var(--amber-22);
    background:
      linear-gradient(180deg, rgba(255, 165, 223, 0.075), rgba(255, 165, 223, 0.018) 58%, rgba(0, 0, 0, 0.22)),
      rgba(2, 3, 6, 0.62);
    box-shadow:
      inset 0 1px 0 rgba(255, 251, 244, 0.034),
      inset 0 -1px 0 rgba(255, 165, 223, 0.16),
      inset 0 0 12px rgba(255, 165, 223, 0.060);
  }
  .vmx-deck__controls button[data-primary="true"]:hover {
    color: var(--amber);
    border-color: var(--amber-40);
  }
  .vmx-live { position: relative; min-width: 168px; height: 1.2em; text-align: right; }
  .vmx-live__s {
    position: absolute; right: 0; top: 0; white-space: nowrap; opacity: 0;
    transition: opacity 700ms ease-out;
    font-family: var(--type-mono); font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase;
    /* The three labels stack absolutely; opacity-0 elements still capture
     * clicks, so suppress pointer events on all of them and re-enable only
     * the fault label in fault mode (it's the only clickable one — restart). */
    pointer-events: none;
  }
  .vmx-live__s--live { color: var(--silk-40); }
  .vmx-live__s--silent { color: var(--silk-22); }
  .vmx-live__s--fault { color: var(--amber-pale); }
  .vmx-session:not([data-mode]) .vmx-live__s--live,
  .vmx-session[data-mode=""] .vmx-live__s--live { opacity: 1; }
  .vmx-session[data-mode="silent"] .vmx-live__s--silent { opacity: 1; }
  .vmx-session[data-mode="fault"] .vmx-live__s--fault { opacity: 1; }
  /* Fault recovery — the cause line doubles as the fix. Only armed (and
   * cursor-pointer) once the deck is actually in fault mode. */
  button.vmx-live__s { background: none; border: none; padding: 0; text-align: right; font: inherit; letter-spacing: inherit; text-transform: inherit; color: inherit; }
  .vmx-session[data-mode="fault"] .vmx-live__s--fault { pointer-events: auto; cursor: pointer; }
  .vmx-session[data-mode="fault"] .vmx-live__s--fault:hover { color: var(--amber); text-shadow: var(--glow-soft); }

  /* --- THE HERO: the co-host speaks, anchored low on void --- */
  .vmx-deck__speak {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr);
    align-items: stretch;
    min-height: 0;
    padding: clamp(16px, 3vh, 26px) clamp(0px, 1.2vw, 18px);
  }
  .vmx-voice {
    position: relative;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    gap: var(--sp-3);
    min-width: 0;
    width: auto;
    min-height: 0;
    /* The hero gets the generous air; the rail + foot are thin chrome strips, so
     * the vertical rhythm steps >1.25 from strip to slab (impeccable layout). */
    padding: clamp(28px, 4.5vw, 52px);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-md);
    /* The deck display — a lit machined slab, not an empty dark box (2026-05-30
     * level-up). One soft rose key-light pools where the spoken line sits
     * (bottom-left), a top sheen catches the lip, the floor falls into shadow.
     * The co-host's voice now reads as glowing up out of the obsidian. */
    background:
      radial-gradient(88% 86% at 14% 102%, rgba(255, 165, 223, 0.145), transparent 58%),
      radial-gradient(64% 52% at 92% 0%, rgba(255, 255, 255, 0.034), transparent 62%),
      linear-gradient(180deg, rgba(255, 251, 244, 0.034), transparent 28%, rgba(0, 0, 0, 0.20)),
      rgba(255, 251, 244, 0.026);
    box-shadow:
      inset 0 1px 0 rgba(255, 210, 240, 0.07),
      inset 0 -2px 0 rgba(0, 0, 0, 0.62),
      inset 0 0 50px rgba(0, 0, 0, 0.18),
      0 2px 0 rgba(0, 0, 0, 0.44),
      0 22px 56px -14px rgba(0, 0, 0, 0.44),
      0 0 90px -34px rgba(255, 165, 223, 0.18);
    overflow: hidden;
  }
  /* The engraved inner faceplate (2026-05-30 level-up): an inset machined frame
   * + a milled vertical grid + a top sheen, lifted from near-invisible (0.010-
   * 0.035 alpha) to read as a real precision deck face — so the slab's open area
   * is hardware character, not dead empty box. The frame catches a 0.5px lip. */
  .vmx-voice::before {
    content: "";
    position: absolute;
    inset: 12px;
    border: 1px solid var(--border-subtle);
    border-radius: var(--rad-sm);
    background:
      repeating-linear-gradient(90deg, transparent 0 46px, rgba(255, 222, 242, 0.034) 46px 47px),
      linear-gradient(180deg, rgba(255, 251, 244, 0.026) 0%, transparent 16%, transparent 100%);
    box-shadow: inset 0 0.5px 0 rgba(255, 210, 240, 0.07);
    pointer-events: none;
  }
  /* (One-Rose) The hero slab carries a single decorative texture — the ::before
   * faceplate. The old ::after dot-matrix grille was a SECOND non-load-bearing
   * texture competing for the slab's one-rose budget; cut so the spoken line and
   * its receipt own the surface (impeccable layout pass, 2026-06-03). */
  .vmx-voice > * {
    position: relative;
    z-index: 1;
  }
  /* The co-host's PRIOR lines, receding up the slab toward the void — a quiet
   * receipt of what it just said, so the display reads as a living stream, not
   * a single line floating in an empty box (2026-05-30 level-up). In the hero
   * serif (the same voice) but small + dim, two graded steps back. */
  .vmx-ghost {
    font-family: var(--type-serif);
    font-weight: 400;
    font-size: clamp(18px, 1.7vw, 22px); line-height: 1.32; letter-spacing: 0;
    transition: color 700ms ease-out;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: min(58ch, 100%);
  }
  .vmx-ghost--g2 { color: var(--text-disabled); opacity: 0.7; }
  .vmx-ghost--g1 { color: var(--text-muted); }
  .vmx-claim { display: flex; flex-direction: column; align-items: flex-start; gap: var(--sp-3); margin-top: var(--sp-2); }
  .vmx-idle-proof {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1px;
    width: min(760px, 100%);
    margin: 0 auto var(--sp-2);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    background:
      linear-gradient(180deg, rgba(255, 251, 244, 0.024), rgba(0, 0, 0, 0.18)),
      rgba(0, 0, 0, 0.16);
    box-shadow:
      inset 0 1px 0 rgba(255, 251, 244, 0.028),
      inset 0 -1px 0 rgba(0, 0, 0, 0.58);
    overflow: hidden;
  }
  .vmx-idle-proof[hidden] { display: none; }
  .vmx-idle-proof__cell {
    display: flex;
    flex-direction: column;
    gap: 5px;
    min-width: 0;
    padding: 10px 12px;
    background: rgba(255, 251, 244, 0.018);
  }
  .vmx-idle-proof__k {
    font-family: var(--type-display);
    font-variation-settings: 'wdth' 85, 'wght' 650;
    font-size: 9px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk-22);
  }
  .vmx-idle-proof__v {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: var(--type-mono);
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--silk-65);
  }
  .vmx-idle-proof__cell[data-state="ok"] .vmx-idle-proof__v {
    color: var(--amber-pale);
    text-shadow: 0 0 7px var(--amber-22);
  }
  .vmx-idle-proof__cell[data-state="warn"] .vmx-idle-proof__v {
    color: var(--silk-40);
  }
  .vmx-idle-proof__cell[data-state="fault"] .vmx-idle-proof__v {
    color: var(--led-fault);
    text-shadow: 0 0 6px rgba(212, 65, 58, 0.42);
  }
  .vmx-idle-proof__next {
    grid-column: 1 / -1;
    padding: 8px 12px 9px;
    border-top: 1px solid var(--border-subtle);
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: var(--silk-40);
    background: rgba(0, 0, 0, 0.16);
  }
  /* The co-host SPEAKING — set in the one warm human face of the system
   * (Instrument Serif, the documented hero voice per DESIGN.md §3). The impl
   * had been rendering this in condensed Saira display, which read industrial /
   * label-like and was the single biggest reason the hero felt cheap rather
   * than like a friend talking (2026-05-30 level-up). Larger, with a real
   * machined-edge text-shadow so the letters sit ON the lit slab. */
  .vmx-now {
    font-family: var(--type-serif);
    font-weight: 400;
    font-size: clamp(44px, 5.6vw, 78px); line-height: 1.02; letter-spacing: 0;
    color: var(--text-primary); text-wrap: balance; max-width: 18ch;
    text-shadow:
      0 1px 0 rgba(176, 112, 160, 0.20),
      0 2px 1px rgba(20, 16, 18, 0.5),
      0 18px 46px rgba(0, 0, 0, 0.55);
    transition: color 700ms ease-out;
    /* The hero is the one unbounded text object: a long live line ran off the
       slab and clipped mid-word. Hold it to three lines, then ellipsis. */
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
    overflow: hidden;
  }
  /* Emphasis ignites rose — the co-host leaning on the word that matters. The
   * one charisma beat in the hero line (mirrors the mock's cohost-line em). */
  .vmx-now em {
    font-style: italic;
    font-weight: 400;
    color: var(--brand);
    text-shadow:
      0 1px 0 rgba(176, 112, 160, 0.35),
      0 0 24px var(--brand-22),
      0 0 48px var(--brand-12);
  }
  /* Inline numerics / timecodes in the spoken line read as a lit mono cite
   * lifted off the prose, not prose themselves (the "02:14" beat in the mock). */
  .vmx-now .num {
    font-family: var(--type-mono);
    font-weight: 600;
    font-size: 0.58em;
    letter-spacing: 0.02em;
    color: var(--text-secondary);
    vertical-align: 0.16em;
    font-style: normal;
  }
  .vmx-now[data-arrived="true"] { animation: vmx-rise 400ms cubic-bezier(0.16, 1, 0.3, 1); }
  @keyframes vmx-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

  /* THE RECEIPT — rule draws L→R, cite ignites at its terminus [signature] */
  .vmx-receipt {
    display: flex; align-items: center; gap: var(--sp-3);
    width: min(44ch, 100%); max-width: 680px;
    transition: opacity 700ms ease-out;
  }
  .vmx-receipt[hidden] { display: none; }
  .vmx-receipt__rule {
    flex: 1; height: 1px;
    background: linear-gradient(90deg, var(--amber-40), var(--amber));
    box-shadow: 0 0 10px var(--amber-22);
    transform: scaleX(0); transform-origin: left;
  }
  .vmx-receipt[data-arrived="true"] .vmx-receipt__rule { animation: vmx-draw 520ms cubic-bezier(0.22, 1, 0.36, 1) 360ms forwards; }
  .vmx-cite {
    flex: none; display: inline-flex; align-items: center; gap: 6px;
    font-family: var(--type-mono); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--amber-pale); border: 1px solid var(--amber-22); border-radius: var(--rad-sm);
    padding: 5px 10px;
    background:
      linear-gradient(180deg, rgba(255, 251, 244, 0.026), transparent 44%, rgba(0, 0, 0, 0.22)),
      rgba(255, 165, 223, 0.045);
    cursor: pointer;
    text-shadow: 0 0 5px var(--amber-22);
    box-shadow:
      inset 0 1px 0 rgba(255, 251, 244, 0.034),
      inset 0 -1px 0 var(--amber-22),
      inset 0 0 12px rgba(255, 165, 223, 0.075);
  }
  .vmx-receipt[data-arrived="true"] .vmx-cite { animation: vmx-ignite 380ms cubic-bezier(0.16, 1, 0.3, 1) 900ms both; }
  .vmx-cite:hover { border-color: var(--amber-40); background: rgba(255, 165, 223, 0.09); }
  .vmx-cite:focus-visible { outline: 2px solid var(--amber); outline-offset: 2px; }
  @keyframes vmx-draw { to { transform: scaleX(1); } }
  @keyframes vmx-ignite {
    0% { opacity: 0; color: var(--silk-40); border-color: var(--glass-edge); background: transparent; text-shadow: none; box-shadow: none; }
    55% { opacity: 1; color: var(--amber); border-color: var(--amber-65); background: rgba(255, 165, 223, 0.10); text-shadow: 0 0 8px var(--amber-65); box-shadow: var(--glow-soft); }
    100% { opacity: 1; color: var(--amber-pale); border-color: var(--amber-22); background: rgba(255, 165, 223, 0.04); text-shadow: 0 0 6px var(--amber-22); box-shadow: none; }
  }

  /* --- FOOT: one steady master readout (BPM · key · live level) --- */
  .vmx-deck__foot {
    display: grid; grid-template-columns: auto auto 1fr; align-items: center;
    gap: clamp(20px, 3vw, 48px);
    margin: 0 clamp(0px, 1.2vw, 18px);
    /* One steady master readout engraved into the void behind a SINGLE hairline,
     * the docstring's "single master strip" — not a third bordered+shadowed slab.
     * De-carded so only the voice slab is a lit surface (impeccable layout). */
    padding: 12px 2px 2px;
    border-top: 1px solid var(--glass-edge);
  }
  .vmx-read { display: flex; align-items: baseline; gap: var(--sp-2); }
  .vmx-read__lab {
    font-family: var(--type-display); font-variation-settings: 'wdth' 85, 'wght' 600;
    font-size: 9px; letter-spacing: 0.22em; text-transform: uppercase; color: var(--silk-22);
  }
  /* BPM and key read at ONE mono scale (was 22 vs 18, near-equal-weight mush);
   * the numerics carry the read, the 9px labels stay dim. Key keeps amber — the
   * one quarantined heat hue — so it still reads as the second value, by HUE not
   * size (impeccable layout pass, hierarchy fix). */
  .vmx-read__num {
    font-family: var(--type-mono); font-weight: 500; font-size: 20px; letter-spacing: 0.02em;
    color: var(--silk); transition: color 700ms ease-out;
  }
  .vmx-read__key {
    font-family: var(--type-mono); font-weight: 500; font-size: 20px; letter-spacing: 0.04em;
    color: var(--amber-pale); transition: color 700ms ease-out;
  }
  .vmx-fmeter {
    position: relative; height: 14px; border-radius: var(--rad-sm);
    background: var(--void-1); border: 1px solid var(--glass-edge);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.035),
      inset 0 -1px 0 rgba(0, 0, 0, 0.72),
      inset 0 0 8px rgba(0, 0, 0, 0.78);
    overflow: hidden;
    isolation: isolate;
  }
  .vmx-fmeter::after {
    content: "";
    position: absolute;
    inset: 1px;
    background:
      repeating-linear-gradient(90deg, transparent 0 11px, rgba(0, 0, 0, 0.56) 11px 13px),
      linear-gradient(180deg, rgba(255, 255, 255, 0.060), transparent 45%, rgba(0, 0, 0, 0.20));
    pointer-events: none;
    z-index: 3;
  }
  .vmx-fmeter__fill {
    position: absolute; inset: 1px; width: 0%; border-radius: 1px;
    background: linear-gradient(90deg, var(--amber-40), var(--amber-78) 80%, var(--amber));
    transition: background 700ms ease-out;
    box-shadow: 0 0 14px var(--amber-22);
    z-index: 1;
  }
  .vmx-fmeter__peak {
    position: absolute; top: 1px; bottom: 1px; left: 0; width: 2px;
    background: var(--amber-pale); transition: opacity 700ms ease-out;
    box-shadow: 0 0 8px var(--amber-65);
    z-index: 4;
  }

  /* === status row — silk-dim when fine; lights red on a dropped input === */
  .vmx-statusrow {
    display: flex; align-items: center; justify-content: space-between; padding: 0 var(--sp-5);
    background:
      linear-gradient(90deg, rgba(255, 165, 223, 0.026), transparent 38%, transparent 62%, rgba(255, 251, 244, 0.012)),
      rgba(0, 0, 0, 0.42);
    backdrop-filter: var(--blur-glass-light);
    -webkit-backdrop-filter: var(--blur-glass-light); border-top: 1px solid var(--glass-edge);
  }
  .vmx-statusrow__inputs {
    display: flex; align-items: center;
    font-family: var(--type-mono); font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--silk-22);
  }
  .vmx-statusrow__i {
    appearance: none; -webkit-appearance: none;
    border: 0; background: transparent; margin: 0; padding: 0;
    font: inherit; letter-spacing: inherit; text-transform: inherit;
    color: inherit; opacity: 1;
    cursor: default;
    transition: color 700ms ease-out, text-shadow 700ms ease-out;
  }
  .vmx-statusrow__i[data-actionable="true"] { cursor: pointer; }
  .vmx-statusrow__i[data-actionable="true"]:hover {
    color: var(--amber-pale);
    text-shadow: 0 0 6px var(--amber-22);
  }
  .vmx-statusrow__i:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 3px;
    border-radius: var(--rad-sm);
  }
  .vmx-statusrow__i[data-down="true"] { color: var(--led-fault); text-shadow: 0 0 6px rgba(212, 65, 58, 0.5); }
  .vmx-statusrow__sep { color: var(--silk-12); margin: 0 8px; }
  .vmx-statusrow__meta {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    min-width: 0;
  }
  .vmx-statusrow__right { font-family: var(--type-mono); font-size: 11px; color: var(--silk-40); letter-spacing: 0.08em; }
  .vmx-claim-policy {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    margin-left: 14px;
    padding: 3px 8px;
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--silk-40);
    background: rgba(0, 0, 0, 0.18);
    white-space: nowrap;
  }
  .vmx-claim-policy::before {
    content: "";
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--led-warn);
    box-shadow: 0 0 7px rgba(244, 197, 66, 0.35);
  }
  .vmx-claim-policy[data-level="green"]::before {
    background: var(--led-ok);
    box-shadow: 0 0 7px rgba(109, 212, 74, 0.32);
  }
  .vmx-claim-policy[data-level="red"] {
    color: var(--silk-65);
    border-color: rgba(212, 65, 58, 0.34);
  }
  .vmx-claim-policy[data-level="red"]::before {
    background: var(--led-fault);
    box-shadow: 0 0 7px rgba(212, 65, 58, 0.42);
  }

  /* === SILENT + FAULT — the surface settles into listening / holds on a drop = */
  .vmx-session[data-mode="silent"] .vmx-now { color: var(--text-muted); }
  .vmx-session[data-mode="fault"] .vmx-now { color: var(--silk-40); }
  /* Idle/fault hold a single grounded line (no live receipt), so center it in
   * the faceplate instead of pinning to the live receipt-floor — kills the vast
   * empty box above one line at rest (2026-05-30 level-up). Live keeps flex-end
   * so the receipt still prints up from the floor. */
  .vmx-session[data-mode="silent"] .vmx-voice,
  .vmx-session[data-mode="fault"] .vmx-voice { justify-content: center; }
  .vmx-session[data-mode="silent"] .vmx-now {
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.62), 0 0 20px rgba(255, 251, 244, 0.055);
  }
  .vmx-session[data-mode="silent"] .vmx-ghost {
    font-family: var(--type-mono);
    font-size: clamp(11px, 1vw, 13px);
    line-height: 1.45;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    text-align: center;
    max-width: min(72ch, 100%);
    white-space: normal;
    text-overflow: clip;
  }
  .vmx-session[data-mode="silent"] .vmx-ghost--g2 {
    color: var(--text-disabled);
    opacity: 1;
  }
  .vmx-session[data-mode="silent"] .vmx-ghost--g1 {
    color: var(--text-muted);
  }
  .vmx-session[data-mode="silent"] .vmx-claim {
    align-items: center;
    margin-top: var(--sp-2);
  }
  .vmx-session[data-mode="silent"] .vmx-now {
    max-width: min(20ch, 100%);
    text-align: center;
  }
  .vmx-session[data-mode="fault"] .vmx-now {
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.75), 0 0 18px rgba(212, 65, 58, 0.14);
  }
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
  @media (max-width: 780px) {
    .vmx-titlebar__traffic { display: none; }
    .vmx-titlebar { padding: 0 var(--sp-4); gap: var(--sp-3); }
    .vmx-titlebar__pills { margin-left: var(--sp-3); }
    .vmx-titlebar__clock { font-size: 16px; }
    .vmx-deck {
      padding: 0 var(--sp-4);
    }
    .vmx-deck::before,
    .vmx-deck::after {
      left: var(--sp-4);
      right: var(--sp-4);
    }
    .vmx-deck__rail {
      gap: var(--sp-3);
      margin: var(--sp-4) 0 0;
      padding: 9px;
      align-items: flex-start;
    }
    .vmx-persona {
      min-width: 0;
      padding: 7px 8px;
      gap: var(--sp-2);
    }
    .vmx-live {
      display: none;
    }
    .vmx-deck__controls {
      margin-left: auto;
      opacity: 0.9;
    }
    .vmx-deck__controls button {
      padding: 6px 10px;
      letter-spacing: 0.14em;
    }
    .vmx-voice {
      width: 100%;
      padding: var(--sp-5) var(--sp-4);
      min-height: 260px;
    }
    .vmx-ghost {
      display: none;
      font-size: 14px;
      max-width: 100%;
    }
    .vmx-idle-proof {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      width: 100%;
    }
    .vmx-idle-proof__cell {
      padding: 9px 10px;
    }
    .vmx-idle-proof__v {
      font-size: 10px;
      letter-spacing: 0.06em;
    }
    .vmx-now {
      font-size: clamp(28px, 9vw, 42px);
      max-width: 12ch;
      -webkit-line-clamp: 2; /* the narrow voice slab holds two lines, not three */
    }
    .vmx-receipt {
      width: min(30ch, 100%);
    }
    .vmx-deck__foot {
      grid-template-columns: auto auto;
      gap: var(--sp-4);
      margin: 0 0 var(--sp-4);
      padding: 10px 12px;
    }
    .vmx-fmeter {
      grid-column: 1 / -1;
      width: 100%;
    }
    .vmx-statusrow {
      padding: 0 var(--sp-4);
      gap: var(--sp-3);
      overflow: hidden;
    }
    .vmx-statusrow__inputs {
      flex: none;
    }
  .vmx-statusrow__meta {
    min-width: 0;
    overflow: hidden;
  }
  .vmx-statusrow__right {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .vmx-claim-policy {
    display: none;
  }
  }
`;

registerStyle("vmx-session", LAYOUT_CSS);

/** Build and mount the full live-session DOM tree. Returns a handle the
 *  renderer uses for hot updates. */
export function mountSessionLayout(
  rootEl: HTMLElement,
  initial?: SessionState,
  options: MountSessionLayoutOptions = {},
): Mounted {
  const state = initial ?? defaultState();
  let mountedHandle: Mounted | null = null;

  const root = document.createElement("div");
  root.className = "vmx-session";
  root.dataset.mode = "";
  root.dataset.wire = "session.runtime";

  // Titlebar (reused) — gear opens the settings drawer.
  const titlebar = renderTitlebar({
    live: state.titlebar.live,
    rec: state.titlebar.rec,
    sys: state.titlebar.sys,
    clock: state.titlebar.clock,
    onSettingsClick: options.onOpenSettings,
  });
  titlebar.dataset.wire = "session.titlebar";
  root.append(titlebar);

  // Phase 97 / ONBOARD-01 — mode picker bar between titlebar and stage.
  // Sits in its own grid row (auto-sized) so the deck stage still gets
  // the 1fr flex remainder. Click handler reads the live mounted handle
  // so the picker survives state diffs without re-mounting.
  const modebar = document.createElement("div");
  modebar.className = "vmx-modebar";
  modebar.dataset.wire = "session.mode-picker";
  const modePicker = renderModePicker({
    active: state.mode ?? "cohost",
    onChange: (m) => mountedHandle?.current.onModeChange?.(m),
    ariaLabel: "vibemix mode",
  });
  modebar.append(modePicker);
  root.append(modebar);

  // Stage → the single deck.
  const stage = document.createElement("main");
  stage.className = "vmx-stage";
  stage.dataset.wire = "session.stage";
  const deck = document.createElement("section");
  deck.className = "vmx-deck";
  deck.dataset.wire = "session.primary";
  deck.tabIndex = 0;
  deck.setAttribute("aria-label", "co-host");

  // --- rail
  const rail = document.createElement("div");
  rail.className = "vmx-deck__rail";

  const persona = document.createElement("button");
  persona.type = "button";
  persona.className = "vmx-persona";
  // Mood value only — the "persona" key label was redundant with the aria-label
  // ("co-host mood: …. tap to cycle …") set on every mood change below.
  const personaValue = document.createElement("span");
  personaValue.className = "vmx-persona__v";
  persona.append(personaValue);
  persona.addEventListener("click", () => mountedHandle?.current.persona.onCycleMood?.());

  const controls = document.createElement("div");
  controls.className = "vmx-deck__controls";
  const vibeEngineBtn = document.createElement("button");
  vibeEngineBtn.type = "button";
  vibeEngineBtn.dataset.action = "vibe-engine";
  vibeEngineBtn.dataset.wire = "session.vibe-engine";
  vibeEngineBtn.dataset.primary = "true";
  vibeEngineBtn.textContent = "crate";
  vibeEngineBtn.setAttribute("aria-label", "open Viber crate");
  vibeEngineBtn.setAttribute("title", "open Viber library and set builder");
  vibeEngineBtn.addEventListener("click", () => mountedHandle?.current.actions.onOpenVibeEngine?.());
  const muteBtn = document.createElement("button");
  muteBtn.type = "button";
  muteBtn.dataset.action = "mute";
  muteBtn.textContent = "mute";
  muteBtn.addEventListener("click", () => mountedHandle?.current.cohost.onMute?.());
  controls.append(vibeEngineBtn, muteBtn);

  const live = document.createElement("div");
  live.className = "vmx-live";
  const liveLive = makeLiveLabel("live", "reading the room");
  const liveSilent = makeLiveLabel("silent", "listening");
  // Fault label is a <button> so it can recover the session — clicking the
  // cause line restarts the co-host (wires cohost.onRetry → restart_sidecar).
  // CSS gates pointer-events so it's only clickable in fault mode.
  const liveFault = makeLiveLabel("fault", "", /* clickable */ true);
  liveFault.setAttribute("title", "restart co-host");
  liveFault.addEventListener("click", () => mountedHandle?.current.cohost.onRetry?.());
  live.append(liveLive, liveSilent, liveFault);

  rail.append(persona, controls, live);
  deck.append(rail);

  // --- speak (ghosts + claim[now + receipt])
  const speak = document.createElement("div");
  speak.className = "vmx-deck__speak";
  const voice = document.createElement("div");
  voice.className = "vmx-voice";
  const ghost2 = document.createElement("p");
  ghost2.className = "vmx-ghost vmx-ghost--g2";
  const ghost1 = document.createElement("p");
  ghost1.className = "vmx-ghost vmx-ghost--g1";
  const idleProof = document.createElement("div");
  idleProof.className = "vmx-idle-proof";
  idleProof.dataset.wire = "session.idle-proof";
  idleProof.hidden = true;
  const idleAudio = makeIdleProofCell("audio");
  const idleSven = makeIdleProofCell("sven");
  const idleController = makeIdleProofCell("controller");
  const idleScreen = makeIdleProofCell("proof");
  const idleProofNext = document.createElement("div");
  idleProofNext.className = "vmx-idle-proof__next";
  idleProofNext.dataset.wire = "session.idle-proof.next";
  idleProof.append(idleAudio.cell, idleSven.cell, idleController.cell, idleScreen.cell, idleProofNext);
  const claim = document.createElement("div");
  claim.className = "vmx-claim";
  const now = document.createElement("p");
  now.className = "vmx-now";
  now.dataset.wire = "session.now-line";
  const receipt = document.createElement("div");
  receipt.className = "vmx-receipt";
  receipt.hidden = true;
  const rule = document.createElement("span");
  rule.className = "vmx-receipt__rule";
  rule.setAttribute("aria-hidden", "true");
  const cite = document.createElement("button");
  cite.type = "button";
  cite.className = "vmx-cite";
  cite.dataset.wire = "session.citation";
  receipt.append(rule, cite);
  const dropSlot = document.createElement("div");
  dropSlot.className = "vmx-drop-slot";
  dropSlot.dataset.wire = "session.drop";
  claim.append(now, receipt, dropSlot);
  voice.append(ghost2, ghost1, idleProof, claim);

  speak.append(voice);
  deck.append(speak);

  // --- foot (bpm · key · live meter)
  const foot = document.createElement("div");
  foot.className = "vmx-deck__foot";
  const { wrap: bpmWrap, value: bpm } = makeReadout("bpm");
  const { wrap: keyWrap, value: key } = makeReadout("key", true);
  const fmeter = document.createElement("div");
  fmeter.className = "vmx-fmeter";
  fmeter.dataset.wire = "session.meter";
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
  statusRow.dataset.wire = "session.status";
  const inputsEl = document.createElement("div");
  inputsEl.className = "vmx-statusrow__inputs";
  const inAudio = makeInput("audio", "livekit", () => mountedHandle);
  const inAi = makeInput("ai", "gemini", () => mountedHandle);
  const inVoice = makeInput("voice", "gemini", () => mountedHandle);
  const voiceSep = sep();
  const inScreen = makeInput("screen", "screen", () => mountedHandle);
  const inMidi = makeInput("midi", "midi", () => mountedHandle);
  inputsEl.append(inAudio, sep(), inAi, voiceSep, inVoice, sep(), inScreen, sep(), inMidi);
  const statusRight = document.createElement("div");
  statusRight.className = "vmx-statusrow__right";
  const claimPolicy = document.createElement("span");
  claimPolicy.className = "vmx-claim-policy";
  claimPolicy.dataset.wire = "session.claim-policy";
  claimPolicy.hidden = true;
  const statusMeta = document.createElement("div");
  statusMeta.className = "vmx-statusrow__meta";
  statusMeta.append(statusRight, claimPolicy);
  statusRow.append(inputsEl, statusMeta);
  root.append(statusRow);

  rootEl.replaceChildren(root);

  const mounted: Mounted = {
    root,
    titlebar,
    modePicker,
    persona,
    personaValue,
    vibeEngineButton: vibeEngineBtn,
    muteButton: muteBtn,
    liveFault,
    ghosts: [ghost1, ghost2],
    idleProof,
    idleProofCells: {
      audio: idleAudio.value,
      sven: idleSven.value,
      controller: idleController.value,
      screen: idleScreen.value,
    },
    idleProofNext,
    now,
    receipt,
    dropSlot,
    cite,
    bpm,
    key,
    meterFill,
    meterPeak,
    statusInputs: {
      audio: inAudio,
      ai: inAi,
      voice: inVoice,
      voiceSep,
      screen: inScreen,
      midi: inMidi,
    },
    statusRight,
    claimPolicy,
    current: state,
    groundedFalseSinceMs: state.cohost.grounded ? null : Date.now(),
    meterCur: 0,
    meterPk: 0,
    lastNowTs: null,
    citeChip: null,
  };
  mountedHandle = mounted;

  // Seed the visible content from the initial state (mount = first paint).
  applyState(mounted, state, /* isMount */ true);
  return mounted;
}

function makeLiveLabel(
  kind: "live" | "silent" | "fault",
  text: string,
  clickable = false,
): HTMLElement {
  const el = document.createElement(clickable ? "button" : "span");
  if (clickable) (el as HTMLButtonElement).type = "button";
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

function makeIdleProofCell(label: string): { cell: HTMLElement; value: HTMLElement } {
  const cell = document.createElement("div");
  cell.className = "vmx-idle-proof__cell";
  cell.dataset.axis = label;
  const lab = document.createElement("span");
  lab.className = "vmx-idle-proof__k";
  lab.textContent = label;
  const value = document.createElement("span");
  value.className = "vmx-idle-proof__v";
  value.dataset.value = label;
  cell.append(lab, value);
  return { cell, value };
}

function makeInput(
  name: string,
  component: StatusRecheckComponent,
  getMounted: () => Mounted | null,
): HTMLButtonElement {
  const el = document.createElement("button");
  el.type = "button";
  el.className = "vmx-statusrow__i";
  el.dataset.input = name;
  el.textContent = name;
  el.disabled = true;
  el.addEventListener("click", () => {
    getMounted()?.current.status.onRecheck?.(component);
  });
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

  // --- mode picker (Phase 97 / ONBOARD-01) ---
  // External sync path: cold-boot ipc.settings.state may carry a persisted
  // mode. setModePickerActive flips data-active in place so the lit segment
  // matches the singleton without rebuilding the picker.
  const nextMode = next.mode ?? "cohost";
  const prevMode = prev.mode ?? "cohost";
  if (isMount || prevMode !== nextMode) {
    setModePickerActive(mounted.modePicker, nextMode);
  }

  // --- persona (tap-to-cycle mood headline) ---
  if (isMount || prev.persona.mood !== next.persona.mood) {
    mounted.personaValue.textContent = next.persona.mood.toLowerCase();
    mounted.persona.dataset.mood = next.persona.mood;
    mounted.persona.setAttribute(
      "aria-label",
      `co-host mood: ${next.persona.mood.toLowerCase()}. tap to cycle hype, coach, teach.`,
    );
  }

  // --- grounding-failure timer ---
  // Only runs while the co-host is ACTIVE. At IDLE there's no music to ground
  // to, so grounded=false is EXPECTED — not a failure. Counting it at idle is
  // what made a quiet session falsely flip to "AI service unreachable" after 5s
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
          : "◂ ai service unreachable";
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
  if (!nowLine && mode === "silent") {
    const idle = idleReadinessLines(next);
    setGhostText(mounted.ghosts[0], idle.action);
    setGhostText(mounted.ghosts[1], idle.inputs);
    setIdleProof(mounted, next);
  } else {
    setGhost(mounted.ghosts[0], g1Line);
    setGhost(mounted.ghosts[1], g2Line);
    mounted.idleProof.hidden = true;
  }

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

  // --- drop countdown chip ---
  if (
    isMount
    || prev.drop.bars !== next.drop.bars
    || prev.drop.bpmPeriodMs !== next.drop.bpmPeriodMs
  ) {
    const dropChip = renderDropChip(next.drop);
    if (dropChip) mounted.dropSlot.replaceChildren(dropChip);
    else mounted.dropSlot.replaceChildren();
  }

  // --- foot readouts ---
  const bpmText = next.timecode.bpm != null ? next.timecode.bpm.toFixed(1) : "—";
  if (mounted.bpm.textContent !== bpmText) mounted.bpm.textContent = bpmText;
  // A null BPM is usually read as "the counter is broken" when the deck is
  // visually alive. Name the honest cause on the readout itself: no grounded
  // audio has reached the detector yet, so the BPM must stay blank.
  if (next.timecode.bpm == null) {
    const bpmTitle = bpmWaitingTitle(next.status.captureDevice, next.meters.music);
    if (mounted.bpm.getAttribute("aria-label") !== bpmTitle) {
      mounted.bpm.setAttribute("title", bpmTitle);
      mounted.bpm.setAttribute("aria-label", bpmTitle);
    }
  } else if (mounted.bpm.hasAttribute("aria-label")) {
    mounted.bpm.removeAttribute("title");
    mounted.bpm.removeAttribute("aria-label");
  }
  const keyText = next.timecode.key ?? "—";
  if (mounted.key.textContent !== keyText) mounted.key.textContent = keyText;
  // A null key shows the dash glyph; name it so the dim slot reads as
  // "not detected yet", not "broken". The value itself stays dark until
  // the backend reports a key (not a frontend bug to fabricate around).
  if (next.timecode.key == null) {
    if (mounted.key.getAttribute("aria-label") !== "Key not detected yet.") {
      mounted.key.setAttribute("title", "Key not detected yet.");
      mounted.key.setAttribute("aria-label", "Key not detected yet.");
    }
  } else if (mounted.key.hasAttribute("aria-label")) {
    mounted.key.removeAttribute("title");
    mounted.key.removeAttribute("aria-label");
  }

  // --- master meter (smoothed; live only — held/recolored by CSS in silent/fault) ---
  if (mode === "") {
    const target = meterLevelPct(next.meters.music.rms);
    mounted.meterCur += (target - mounted.meterCur) * METER_ATTACK;
    const peakTarget = meterLevelPct(next.meters.music.peak ?? next.meters.music.rms);
    const lead = Math.max(mounted.meterCur + 4, peakTarget);
    if (lead > mounted.meterPk) mounted.meterPk = lead;
    else mounted.meterPk += (lead - mounted.meterPk) * METER_PEAK_DECAY;
    const w = Math.min(mounted.meterCur, 100);
    mounted.meterFill.style.width = `${w.toFixed(1)}%`;
    mounted.meterPeak.style.left = `${Math.min(mounted.meterPk, METER_CEIL).toFixed(1)}%`;
  }

  // --- mute control reflects state ---
  if (isMount || prev.status.muted !== next.status.muted) {
    const muteBtn = mounted.muteButton;
    if (muteBtn) {
      muteBtn.dataset.on = next.status.muted ? "true" : "false";
      muteBtn.textContent = next.status.muted ? "muted" : "mute";
    }
  }

  // --- status row inputs (silk-dim; red on a dropped input) ---
  setInputDown(mounted.statusInputs.audio, next.status.livekit === "down");
  setInputDown(
    mounted.statusInputs.ai,
    next.status.gemini === "down" || downInput === "gemini",
  );
  setPassiveInputDown(mounted.statusInputs.voice, next.status.voice === "muted");
  mounted.statusInputs.voice.hidden = next.status.voice !== "muted";
  mounted.statusInputs.voiceSep.hidden = next.status.voice !== "muted";
  setInputDown(mounted.statusInputs.screen, next.status.screen === "denied");
  setInputDown(mounted.statusInputs.midi, next.status.midi === 0);
  // Just the live output route — the one fact here that can change mid-set and
  // matters at a glance (where the co-host's voice lands). Voice name + genre are
  // set-once Settings config, not live status; printing them in always-on chrome
  // was extra text a DJ never reads mid-set (impeccable: status-row text cut).
  const rightText = outputLabel(next.output);
  if (mounted.statusRight.textContent !== rightText) mounted.statusRight.textContent = rightText;
  const claim = next.claimPolicy ?? null;
  mounted.claimPolicy.hidden = !claim;
  if (claim) {
    if (mounted.claimPolicy.textContent !== claim.label) mounted.claimPolicy.textContent = claim.label;
    mounted.claimPolicy.dataset.level = claim.level;
    const title = claim.reason
      ? `${claim.policy}: ${claim.reason}`
      : claim.policy;
    mounted.claimPolicy.setAttribute("title", title);
    mounted.claimPolicy.setAttribute("aria-label", `live claim status: ${claim.label}`);
  }
}

function setGhost(el: HTMLElement, line: TranscriptLine | null): void {
  const text = line ? line.text : "";
  setGhostText(el, text);
}

function setGhostText(el: HTMLElement, text: string): void {
  if (el.textContent !== text) el.textContent = text;
  el.style.display = text ? "" : "none";
}

function idleReadinessLines(state: SessionState): { inputs: string; action: string } {
  const audioActive = musicSignalActive(state.meters.music);
  const audioWaiting = state.status.livekit === "ok" && !audioActive;
  const controllerWaiting = state.status.midi === 0;
  const audio = state.status.livekit === "ok"
    ? audioActive
      ? "audio hearing"
      : "audio waiting"
    : state.status.livekit === "connecting"
      ? "audio connecting"
      : "audio checking";
  const ai = state.status.voice === "muted"
    ? "Sven voice muted"
    : state.status.gemini === "ok"
      ? "Sven ready"
      : state.status.gemini === "down"
        ? "Sven down"
        : "Sven checking";
  const controller = state.status.midi != null && state.status.midi > 0
    ? "controller seen"
    : state.status.midi === 0 && state.status.midiActivity === "connected_no_midi_traffic"
      ? `${midiDeviceLabel(state.status.midiDevice)} waiting`
    : state.status.midi === 0 && state.status.midiActivity === "midi_traffic_unmapped"
      ? `${midiDeviceLabel(state.status.midiDevice)} unmapped`
    : state.status.midi === 0
      ? "controller not proven"
      : "controller checking";
  const screen = state.status.screen === "ok"
    ? "screen proof ready"
    : state.status.screen === "denied"
      ? "screen proof denied"
      : state.status.screen === "unavailable"
        ? "screen proof unavailable"
        : "screen proof checking";
  const action = audioWaiting
    ? `${captureDeviceLabel(state.status.captureDevice)} silent · ${captureRouteInstruction(state.status.captureDevice)}`
    : controllerWaiting
      ? `${screen} · ${midiProofAction(state.status.midiActivity, state.status.midiDevice)}`
      : `${screen} · Start playback, I will not guess.`;
  return {
    inputs: `${audio} · ${ai} · ${controller}`,
    action,
  };
}

type IdleProofState = "ok" | "warn" | "fault";

function setIdleProof(mounted: Mounted, state: SessionState): void {
  mounted.idleProof.hidden = false;
  const audio = audioProof(state.status.livekit, state.meters.music);
  const sven = svenProof(state.status.gemini, state.status.voice);
  const controller = controllerProof(state.status.midi);
  const screen = screenProof(state.status.screen);
  setIdleCell(mounted.idleProofCells.audio, audio);
  setIdleCell(mounted.idleProofCells.sven, sven);
  setIdleCell(mounted.idleProofCells.controller, controller);
  setIdleCell(mounted.idleProofCells.screen, screen);
  const next = idleProofNext(
    audio,
    controller,
    screen,
    state.status.captureDevice,
    state.status.midiActivity,
    state.status.midiDevice,
  );
  if (mounted.idleProofNext.textContent !== next) mounted.idleProofNext.textContent = next;
}

function setIdleCell(
  value: HTMLElement,
  proof: { label: string; state: IdleProofState },
): void {
  if (value.textContent !== proof.label) value.textContent = proof.label;
  const cell = value.parentElement;
  if (cell && cell.dataset.state !== proof.state) cell.dataset.state = proof.state;
}

function idleProofNext(
  audio: { label: string; state: IdleProofState },
  controller: { label: string; state: IdleProofState },
  screen: { label: string; state: IdleProofState },
  captureDevice?: string | null,
  midiActivity?: SessionState["status"]["midiActivity"],
  midiDevice?: string | null,
): string {
  if (audio.label === "waiting") {
    const device = captureDeviceLabel(captureDevice);
    return `${device} is silent. ${captureRouteInstruction(captureDevice)}`;
  }
  if (controller.label === "no motion") {
    return midiProofNext(midiActivity, midiDevice);
  }
  return screen.state === "ok"
    ? "Start playback. Sven will cite what lands."
    : "Start playback. Sven waits for proof.";
}

function musicSignalActive(music: SessionState["meters"]["music"]): boolean {
  return Math.max(music.rms || 0, music.peak || 0) > 0.015;
}

function captureDeviceLabel(captureDevice?: string | null): string {
  const text = (captureDevice ?? "").trim().replace(/\s+/g, " ");
  return text || "capture";
}

function captureRouteInstruction(captureDevice?: string | null): string {
  const device = captureDeviceLabel(captureDevice).toLowerCase();
  if (isControllerCaptureDevice(device)) {
    return "Use BlackHole/eqMac capture, speaker audio is not proof.";
  }
  if (device === "eqmac export") {
    return "Send DJ app to Multi-Output (eqMac), not speaker only.";
  }
  if (isBlackHoleCaptureDevice(device)) {
    return "Send DJ app to a Multi-Output/Aggregate that includes BlackHole; speaker output alone is not proof.";
  }
  return "Route DJ output into capture.";
}

function isBlackHoleCaptureDevice(device: string): boolean {
  return device.includes("blackhole");
}

function isControllerCaptureDevice(device: string): boolean {
  return (
    device.includes("ddj")
    || device.includes("flx")
    || device.includes("pioneer")
    || device.includes("rekordbox aggregate")
  );
}

function bpmWaitingTitle(
  captureDevice: SessionState["status"]["captureDevice"],
  music: SessionState["meters"]["music"],
): string {
  const device = captureDeviceLabel(captureDevice);
  if (musicSignalActive(music)) return "BPM is not locked yet.";
  if (isControllerCaptureDevice(device.toLowerCase())) {
    return `BPM waits for master capture. ${device} is not hearing the master.`;
  }
  if (isBlackHoleCaptureDevice(device.toLowerCase())) {
    return `BPM waits for audio from ${device}; speaker output alone is not capture proof.`;
  }
  return `BPM waits for audio from ${device}.`;
}

function midiDeviceLabel(midiDevice?: string | null): string {
  const text = (midiDevice ?? "").trim().replace(/\s+/g, " ");
  return text || "controller";
}

function midiProofAction(
  midiActivity?: SessionState["status"]["midiActivity"],
  midiDevice?: string | null,
): string {
  const device = midiDeviceLabel(midiDevice);
  if (midiActivity === "connected_no_midi_traffic") {
    return `${device} waiting · Move mixer/deck control.`;
  }
  if (midiActivity === "midi_traffic_unmapped") {
    return `${device} unmapped · Run controller mapping.`;
  }
  if (midiActivity === "midi_events_no_moves") {
    return `${device} seen · Move a deck control.`;
  }
  return "Move a control once, I will not guess.";
}

function midiProofNext(
  midiActivity?: SessionState["status"]["midiActivity"],
  midiDevice?: string | null,
): string {
  const device = midiDeviceLabel(midiDevice);
  if (midiActivity === "connected_no_midi_traffic") {
    return `${device} is connected. Move mixer/deck control for proof.`;
  }
  if (midiActivity === "midi_traffic_unmapped") {
    return `${device} sends MIDI, but the profile is not mapping it.`;
  }
  if (midiActivity === "midi_events_no_moves") {
    return `${device} is visible. Move a deck control for proof.`;
  }
  return "Move the controller once. Sven waits for proof.";
}

function audioProof(
  status: SessionState["status"]["livekit"],
  music: SessionState["meters"]["music"],
): {
  label: string;
  state: IdleProofState;
} {
  if (status === "ok") {
    return musicSignalActive(music)
      ? { label: "hearing", state: "ok" }
      : { label: "waiting", state: "warn" };
  }
  if (status === "down") return { label: "dropped", state: "fault" };
  if (status === "connecting") return { label: "connecting", state: "warn" };
  return { label: "checking", state: "warn" };
}

function svenProof(
  status: SessionState["status"]["gemini"],
  voice: SessionState["status"]["voice"],
): {
  label: string;
  state: IdleProofState;
} {
  if (voice === "muted") return { label: "voice muted", state: "warn" };
  if (status === "ok") return { label: "ready", state: "ok" };
  if (status === "down") return { label: "offline", state: "fault" };
  return { label: "checking", state: "warn" };
}

function controllerProof(status: SessionState["status"]["midi"]): {
  label: string;
  state: IdleProofState;
} {
  if (status != null && status > 0) return { label: "seen", state: "ok" };
  if (status === 0) return { label: "no motion", state: "warn" };
  return { label: "checking", state: "warn" };
}

function screenProof(status: SessionState["status"]["screen"]): {
  label: string;
  state: IdleProofState;
} {
  if (status === "ok") return { label: "screen ready", state: "ok" };
  if (status === "denied") return { label: "denied", state: "fault" };
  if (status === "unavailable") return { label: "unavailable", state: "warn" };
  return { label: "checking", state: "warn" };
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
 *  audio/gemini path being down. Priority: audio (livekit) > gemini grounding.
 *  Returns null when everything is fine.
 *
 *  2026-05-26: screen=denied is NO LONGER a deck fault. Audio-only is a valid
 *  mode (vibemix's first promise is "listens to your master output"; screen is
 *  an enhancement that watches the DJ software). A denied screen surfaces as a
 *  red SCREEN badge in the status row — never a blank deck. This keeps the new
 *  ~1Hz ipc.status.tick (ws_bus.py) zero-new-fault: it emits a live screen
 *  probe for the badge without ever flipping the hero to fault. */
function faultInput(
  status: SessionState["status"],
  failureElapsedMs: number | null,
): "audio" | "screen" | "gemini" | null {
  if (status.livekit === "down") return "audio";
  if (status.gemini === "down") return "gemini";
  if (failureElapsedMs != null && failureElapsedMs >= GROUNDING_FAILURE_MS) return "gemini";
  return null;
}

function setInputDown(el: HTMLButtonElement, down: boolean): void {
  const v = down ? "true" : "false";
  if (el.dataset.down !== v) el.dataset.down = v;
  el.disabled = !down;
  el.dataset.actionable = down ? "true" : "false";
  const label = el.dataset.input ?? "input";
  el.setAttribute(
    "aria-label",
    down ? `recheck ${label} status` : `${label} status ok`,
  );
}

function setPassiveInputDown(el: HTMLButtonElement, down: boolean): void {
  const v = down ? "true" : "false";
  if (el.dataset.down !== v) el.dataset.down = v;
  el.disabled = true;
  el.dataset.actionable = "false";
  el.setAttribute("aria-label", down ? "voice status muted" : "voice status ok");
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

function outputLabel(output: SessionState["output"]): string {
  return `${output.profile} ${deviceLabel(output.device)}`;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function clamp01(n: number): number {
  if (!Number.isFinite(n)) return 0;
  if (n < 0) return 0;
  if (n > 1) return 1;
  return n;
}

export function meterLevelPct(level: number): number {
  const value = clamp01(level);
  if (value <= 0) return 0;
  const db = 20 * Math.log10(value);
  return clamp01((db - METER_DB_FLOOR) / (METER_DB_CEIL - METER_DB_FLOOR)) * 100;
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
    actions: {},
    status: {
      livekit: null,
      gemini: null,
      midi: null,
      screen: null,
      voice: null,
      captureDevice: null,
      midiActivity: null,
      midiDevice: null,
      muted: false,
      hotkey: "⌘⇧M",
      errors: {},
    },
    claimPolicy: null,
    persona: { skill: "INT", interaction: "HYPE", mood: "HYPE", voice: "Adam", genre: "techno" },
    output: { device: "MacBook Pro Speakers", profile: "HP" },
    mode: "cohost",
  };
}
