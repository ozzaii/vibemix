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
import { renderTitlebar, setTitlebarClock, setTitlebarPill, type PillLevel } from "./components/titlebar.js";
import { GROUNDING_FAILURE_MS, type CohostStatus, type ReactionsByTs, type TranscriptLine } from "./cohost-model.js";
import { renderDropChip } from "./components/drop-chip.js";
import type { CitationChip } from "./components/citation-strip.js";
import { type PhaseChunk } from "./components/phase-tape.js";
import { type MidiEvent } from "./components/event-ribbon.js";
import type { BadgeState } from "./components/status-bar.js";

type StatusRecheckComponent = "livekit" | "gemini" | "midi" | "screen";

/** Top-level vibemix mode persisted in the projected state. The in-deck mode
 *  picker chrome was cut (DJs do not switch modes mid-set; the surrounding
 *  shell owns nav), but the render-loop still projects the mode + change
 *  handler so the field stays part of the layout prop contract. */
type SessionTopMode = "cohost" | "learn" | "build" | "debrief";

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
    /** Persona display value. Kept as `mood` for layout compatibility. */
    mood: "HYPE" | "TEACH" | "COACH";
    voice: string;
    genre: string;
    /** Direct persona select (the strip's three chips). Render-loop wires it
     *  to ipc.settings.set lens. Omitted (dev mock) means taps are no-ops. */
    onSelectMood?: (mood: "HYPE" | "TEACH" | "COACH") => void;
  };
  output: {
    device: string;
    profile: "HP" | "SPK";
  };
  /** Top-level mode (cohost/learn/build/debrief). The in-deck mode picker was
   *  removed, but the render-loop still projects this field; it persists the
   *  last-picked mode and feeds the surrounding shell nav. */
  mode?: SessionTopMode;
  /** Click handler the render-loop wires to modeChangeHandler (setSessionState
   *  + ipc.session.set_mode). Retained on the prop contract even though the
   *  deck no longer renders the picker that called it. */
  onModeChange?: (mode: SessionTopMode) => void;
  /** SHIP-WIRE START-gate — live-session run-state. "armed" (the real-boot
   *  default) shows the idle Start gate with no reactions; "running" shows the
   *  live deck. defaultState() leaves it "running" so existing fixtures keep
   *  the live deck; the render-loop projection drives the armed boot. */
  runState?: "armed" | "running";
  /** Deck-visible failure notice — THE single ipc.error surface (see
   *  ws-bridge.DECK_NOTICE_ERROR_TYPES). Null hides the line. */
  notice?: { text: string; tone: "error" | "info" } | null;
  /** Start gate handlers — the render-loop wires onStart/onStop to
   *  ipc.session.start / ipc.session.stop + optimistic setSessionState. The
   *  deck also flips data-runstate locally on click (repaint convention).
   *  Omitted (dev mock without a render-loop) → the buttons still flip the
   *  deck locally, they're just a no-op on the wire. */
  onStart?: () => void;
  onStop?: () => void;
}

export interface Mounted {
  root: HTMLElement;
  titlebar: HTMLElement;
  /** Rail persona strip (direct-select mood chips). */
  persona: HTMLElement;
  personaChips: Record<"HYPE" | "COACH" | "TEACH", HTMLButtonElement>;
  muteButton: HTMLElement;
  /** Cross-fade liveness labels (always mounted; opacity toggled by mode). */
  liveFault: HTMLElement;
  armedContext: {
    capture: HTMLElement;
    midi: HTMLElement;
    output: HTMLElement;
    persona: HTMLElement;
  };
  ghosts: [HTMLElement, HTMLElement];
  now: HTMLElement;
  receipt: HTMLElement;
  dropSlot: HTMLElement;
  /** Deck notice line (THE ipc.error surface). */
  notice: HTMLElement;
  cite: HTMLElement;
  citeTime: HTMLElement;
  citeBand: HTMLElement;
  bpm: HTMLElement;
  key: HTMLElement;
  track: HTMLElement;
  meterFill: HTMLElement;
  meterPeak: HTMLElement;
  meterChunks: HTMLElement;
  statusInputs: {
    audio: HTMLButtonElement;
    ai: HTMLButtonElement;
    voice: HTMLButtonElement;
    voiceSep: HTMLElement;
    screen: HTMLButtonElement;
    midi: HTMLButtonElement;
  };
  statusRow: HTMLElement;
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
    grid-template-rows: var(--titlebar-h) 1fr 0;
    height: 100vh;
    position: relative;
    overflow: hidden;
    /* THE ROOM (fable pass 2026-06-09): the deck sits inside the lit obsidian
     * scene tokens.css already stages — one rose key-light top-left, a faint
     * gold counter-warmth, a top sheen, a floor vignette. The previous flat
     * void-5 + 4% rose wash read as grey mauve (the "washed-out soup" Kaan
     * called pre-fable slop); --scene-lit is the cinematic room the design
     * system promised and the deck never used. */
    background: var(--scene-lit);
  }
  .vmx-session[data-statusrow="alert"] {
    grid-template-rows: var(--titlebar-h) 1fr var(--statusbar-h);
  }
  .vmx-drop-slot:empty { display: none; }

  /* === THE DECK — no card. Open void. Hero anchored low (mixer LCD). ==== */
  .vmx-stage { display: grid; place-items: stretch; min-height: 0; position: relative; z-index: 1; }
  .vmx-stage::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    /* One soft lift where the voice lives — the scene's vignette does the rest.
     * The old double wash (center glow + floor rose) fought --scene-lit and
     * flattened the room back toward grey. */
    background:
      radial-gradient(72% 56% at 38% 56%, rgba(255, 222, 242, 0.020), transparent 64%);
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
  /* The mock's .persona-strip — a recessed hardware well holding all three
   * moods, the active one physically pressed in. The old single rose "HYPE"
   * label hid coach/teach behind a blind tap-to-cycle; here the choices are
   * visible and direct-select. Optimistic repaint per the settings-control
   * rule: the chip flips data-active locally, the echoed ipc.settings.state
   * stays authoritative. */
  .vmx-persona {
    display: inline-flex;
    align-items: stretch;
    gap: 2px;
    margin: 0;
    padding: 3px;
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    background: linear-gradient(180deg, var(--void-5) 0%, var(--void-8) 100%);
    box-shadow:
      inset 0 2px 4px rgba(0, 0, 0, 0.45),
      inset 0 -1px 0 rgba(255, 255, 255, 0.03),
      0 1px 0 rgba(255, 255, 255, 0.03);
  }
  .vmx-persona__chip {
    appearance: none; -webkit-appearance: none;
    display: grid;
    place-items: center;
    margin: 0;
    padding: 7px 10px;
    border: 0;
    border-radius: var(--r-xs);
    background: transparent;
    font-family: var(--type-mono);
    font-weight: 600;
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    line-height: 1;
    color: var(--text-muted);
    cursor: pointer;
    transition: color 200ms var(--ease-brand), background 200ms var(--ease-brand),
                box-shadow 250ms var(--ease-brand);
  }
  .vmx-persona__chip:hover {
    color: var(--text-primary);
    background: var(--brand-04);
  }
  .vmx-persona__chip:active { transform: scale(0.96); }
  .vmx-persona__chip[data-active="true"] {
    color: var(--brand);
    background: radial-gradient(ellipse at top, var(--void-0) 0%, var(--void-12) 100%);
    text-shadow: var(--text-emboss);
    box-shadow:
      inset 0 2px 5px rgba(0, 0, 0, 0.55),
      inset 0 -1px 0 rgba(255, 255, 255, 0.04),
      inset 0 0 0 1px var(--brand-22),
      inset 0 0 14px var(--brand-04);
  }
  /* persistent low-ink at rest (reachable mid-set), full on hover/focus.
   * Real mute also bound to the push-to-mute hotkey (session-shortcuts.ts). */
  /* MUTE/STOP are live-set SAFETY controls — they rest powered (ink on a
   * machined rim), never behind a 0.58 row dimmer that read as disabled. */
  .vmx-deck__controls { display: flex; gap: var(--sp-2); margin-left: auto; }
  .vmx-deck__controls button {
    font-family: var(--type-display);
    font-variation-settings: 'wdth' 85, 'wght' 600;
    font-size: 9px; letter-spacing: 0.2em; text-transform: uppercase;
    color: var(--text-muted);
    border: 1px solid var(--border-default); border-radius: var(--rad-sm);
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
  .vmx-live__s--live { color: var(--text-muted); }
  .vmx-live__s--silent { color: var(--text-disabled); }
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

  /* --- deck notice — THE user-visible ipc.error surface (lanes B+D). A
   * failed GO LIVE names its cause ON the deck instead of dying in the
   * operator log. Amber = the established fault vocabulary; hidden when
   * null so the deck stays clean at rest. */
  .vmx-deck__notice {
    justify-self: center;
    align-self: end;
    max-width: 72ch;
    margin: 0 auto;
    padding: 6px 16px;
    font-family: var(--type-mono);
    font-size: 11px;
    letter-spacing: 0.04em;
    color: var(--amber-pale);
    border: 1px solid var(--amber-40);
    border-radius: 999px;
    background: rgba(0, 0, 0, 0.35);
  }
  .vmx-deck__notice[hidden] { display: none; }

  /* --- SHIP-WIRE START-gate ------------------------------------------------
     The deck is armed (idle, no reactions) until the user presses Start, then
     running. Orthogonal to data-mode. Stop is a running-only control; mute is
     meaningless before Start; the armed gate replaces the reaction zone. */
  .vmx-deck__controls button[data-action="stop"] { display: none; }
  .vmx-session[data-runstate="running"] .vmx-deck__controls button[data-action="stop"] { display: inline-flex; }
  .vmx-session[data-runstate="armed"] .vmx-deck__controls button[data-action="mute"] { display: none; }
  .vmx-armed { display: none; }
  .vmx-session[data-runstate="armed"] .vmx-voice { display: none; }
  .vmx-session[data-runstate="armed"] .vmx-live { visibility: hidden; }
  .vmx-session[data-runstate="armed"] .vmx-deck__rail {
    align-self: start;
    justify-content: flex-end;
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
  }
  .vmx-session[data-runstate="armed"] .vmx-persona {
    border-color: transparent;
    background: transparent;
    box-shadow: none;
  }
  .vmx-session[data-runstate="armed"] .vmx-armed {
    position: relative;
    isolation: isolate;
    display: grid;
    grid-template-columns: minmax(0, min(640px, 100%));
    justify-content: center;
    justify-items: center;
    align-content: center;
    gap: clamp(28px, 5vw, 72px);
    min-height: 0;
    width: 100%;
    max-width: 1120px;
    margin: 0 auto;
    padding: clamp(28px, 6vh, 72px) clamp(4px, 1.8vw, 22px) clamp(34px, 7vh, 86px);
    text-align: center;
    animation: vmxArmedIn 520ms var(--ease-brand);
  }
  /* The idle stage is a powered deck warming up, not dead black. A low rose
   * dawn rises from beneath the stage (toward the Start action) and breathes
   * slowly — at armed-idle the voice + tail cursor are hidden, so this ambient
   * is the screen's single sign-of-life (One-Rose holds). Subliminal: a wash,
   * never nameable as "pink". This is the difference between premium-restraint
   * and cheap-empty. */
  .vmx-armed__field {
    position: absolute;
    inset: -10% -8% -16%;
    z-index: -1;
    pointer-events: none;
    background:
      radial-gradient(135% 92% at 50% 116%, var(--brand-16), var(--brand-04) 38%, transparent 66%),
      linear-gradient(112deg, transparent 0%, var(--brand-04) 30%, transparent 56%),
      radial-gradient(80% 60% at 82% 8%, rgba(255, 222, 242, 0.03), transparent 58%);
    filter: blur(0.2px);
    opacity: 0.86;
    transform: translate3d(0, 0, 0);
    animation: vmxArmedField 8600ms var(--ease-brand) infinite alternate;
  }
  .vmx-armed__copy {
    display: grid;
    gap: var(--sp-4);
    justify-items: center;
    min-width: 0;
  }
  .vmx-armed__eyebrow,
  .vmx-armed__kicker,
  .vmx-armed__context-label {
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
  }
  .vmx-armed__eyebrow {
    color: var(--brand);
    text-shadow: 0 0 18px var(--brand-22);
  }
  .vmx-armed__title {
    margin: 0;
    margin-inline: auto;
    max-width: 11ch;
    font-family: var(--type-serif);
    font-weight: 400;
    font-size: clamp(64px, 7vw, 96px);
    line-height: 0.96;
    letter-spacing: 0;
    color: var(--text-primary);
    text-wrap: balance;
    text-shadow:
      0 1px 0 rgba(176, 112, 160, 0.20),
      0 22px 58px rgba(0, 0, 0, 0.58);
  }
  .vmx-armed__title em {
    font-style: italic;
    font-weight: 400;
    color: var(--brand);
    text-shadow:
      0 1px 0 rgba(176, 112, 160, 0.35),
      0 0 24px var(--brand-22),
      0 0 48px var(--brand-12);
  }
  .vmx-armed__lead {
    max-width: 48ch;
    margin: 0;
    margin-inline: auto;
    font-family: var(--type-body);
    font-size: 17px;
    line-height: 1.55;
    color: var(--text-muted);
  }
  /* The four at-rest states are TELEMETRY, not four dashboard cards. Boxed
   * identical cells read as a SaaS stat-grid (the exact AI-slop tell); a
   * Pioneer faceplate spells its status flush on the metal. So: no per-cell
   * boxes — a single machined seam seats the readout like a spec line, the
   * values flow at their natural width, one figure on one ground. */
  .vmx-armed__context {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: clamp(20px, 3vw, 44px);
    margin-top: var(--sp-4);
    padding-top: var(--sp-4);
    box-shadow: inset 0 1px 0 rgba(255, 222, 242, 0.07);
  }
  .vmx-armed__context-item {
    min-width: 0;
    display: grid;
    gap: 6px;
  }
  .vmx-armed__context-label {
    color: var(--text-disabled);
  }
  .vmx-armed__context-value {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 90, "wght" 600;
    font-size: 14px;
    letter-spacing: 0;
    color: var(--text-secondary);
  }
  /* F9 polish: the Start CTA reads WITH the copy column, not as a separate
   * raised dashboard tile. Keep the element (start-gate.spec.ts:92) and its
   * kicker/button/note stack; drop the pad-box, radius, fill, and bevel. */
  .vmx-armed__module {
    position: relative;
    display: grid;
    gap: var(--sp-4);
    align-self: center;
    justify-self: center;
  }
  /* Text floor: nothing the DJ is meant to READ sits below the contract's
   * dimmest legal step (= --text-disabled). The old silk-40/22 values were
   * decoration-grade on load-bearing words. */
  .vmx-armed__kicker {
    color: var(--text-muted);
  }
  .vmx-armed__note {
    font-family: var(--type-mono);
    font-size: 11px;
    letter-spacing: 0.04em;
    color: var(--text-disabled);
  }
  /* Start: the one rose-lit physical control on the idle deck — the mock's
   * cohost-pill material: brand gradient slab, machined specular top line,
   * pressed-metal shadow stack. Ink text (not rose-on-rose) so it reads as a
   * lit key, not a tinted outline. */
  .vmx-armed__start {
    position: relative;
    isolation: isolate;
    overflow: hidden;
    font-family: var(--type-mono);
    font-weight: 600;
    font-size: 13px; letter-spacing: 0.3em; text-transform: uppercase;
    color: var(--text-primary);
    text-shadow: var(--text-emboss);
    min-height: 60px;
    padding: 18px 44px;
    border: 1px solid var(--brand-35); border-radius: var(--rad-md);
    background:
      linear-gradient(180deg, var(--brand-22) 0%, var(--brand-10) 50%, var(--brand-06) 100%),
      linear-gradient(180deg, var(--void-12), var(--void-8));
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.18),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45),
      inset 0 0 24px var(--brand-06),
      0 1px 0 rgba(255, 255, 255, 0.04),
      0 6px 18px rgba(176, 112, 160, 0.18),
      0 16px 38px rgba(0, 0, 0, 0.42);
    cursor: pointer;
    transition: color var(--motion-step) var(--ease-brand), border-color var(--motion-step) var(--ease-brand), box-shadow var(--motion-step) var(--ease-brand), filter var(--motion-step) var(--ease-brand), transform var(--motion-step) var(--ease-brand);
  }
  .vmx-armed__start::after {
    content: "";
    position: absolute;
    top: 0; left: 10%; right: 10%;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
  }
  .vmx-armed__start::before {
    content: "";
    position: absolute;
    inset: -28%;
    z-index: -1;
    background: radial-gradient(70% 70% at 50% 100%, var(--brand-22), transparent 62%);
    opacity: 0;
    transform: scale(0.72);
    transition: opacity var(--motion-step) var(--ease-brand), transform var(--motion-step) var(--ease-brand);
  }
  .vmx-armed__start:hover {
    filter: brightness(1.12);
    border-color: var(--brand-50);
  }
  .vmx-armed__start:hover::before,
  .vmx-armed__start:focus-visible::before {
    opacity: 1;
    transform: scale(1);
  }
  .vmx-armed__start:active {
    transform: translateY(2px) scale(0.992);
    box-shadow:
      inset 0 3px 8px rgba(0, 0, 0, 0.58),
      inset 0 1px 0 rgba(255, 251, 244, 0.03),
      0 10px 28px rgba(0, 0, 0, 0.52);
  }
  .vmx-armed__start:focus-visible { outline: 2px solid var(--amber); outline-offset: 3px; }
  @keyframes vmxArmedIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes vmxArmedField {
    from { opacity: 0.46; transform: translate3d(-8px, 5px, 0) scale(0.992); }
    to { opacity: 0.76; transform: translate3d(8px, -5px, 0) scale(1.006); }
  }
  /* THE SIGN OF LIFE (direction-final contract): a hairline frame seats the
   * idle deck like the front panel of a powered instrument, and ONE slow brand
   * light travels its perimeter — the gentle pulse of a CDJ sitting idle.
   * Armed-only: when the deck goes live the voice + meter are the life. */
  .vmx-armed__frame {
    position: absolute;
    inset: clamp(10px, 2.4vh, 26px) clamp(2px, 1.2vw, 16px);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-md);
    pointer-events: none;
    z-index: -1;
    overflow: hidden;
  }
  /* The traveling light is the conic's FROM angle animating via @property —
   * never transform:rotate on the masked element (rotating the element rotates
   * its ring mask too, which streaks the light diagonally across the panel). */
  @property --vmx-sweep {
    syntax: "<angle>";
    initial-value: 0deg;
    inherits: false;
  }
  .vmx-armed__frame::before {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    padding: 1px;
    background: conic-gradient(
      from var(--vmx-sweep) at 50% 50%,
      transparent 0%,
      transparent 38%,
      var(--brand-22) 47%,
      var(--brand-50) 50%,
      var(--brand-22) 53%,
      transparent 62%,
      transparent 100%
    );
    -webkit-mask:
      linear-gradient(rgba(0, 0, 0, 1) 0 0) content-box,
      linear-gradient(rgba(0, 0, 0, 1) 0 0);
    -webkit-mask-composite: xor;
            mask:
      linear-gradient(rgba(0, 0, 0, 1) 0 0) content-box,
      linear-gradient(rgba(0, 0, 0, 1) 0 0);
            mask-composite: exclude;
    /* Stilled (one-breath law): vmxArmedField is the gate's ONE ambient —
     * the perimeter holds as a static lit seam instead of a second motion. */
    opacity: 0.5;
  }
  /* The idle deck has no live signal — the master meter is runtime telemetry.
   * Showing its empty groove at armed read as a stray progress bar. */
  .vmx-session[data-runstate="armed"] .vmx-deck__foot { opacity: 0; visibility: hidden; }
  @media (prefers-reduced-motion: reduce) {
    .vmx-session[data-runstate="armed"] .vmx-armed { animation: none; }
    .vmx-armed__field { animation: none; }
  }

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
    /* With the slab gone the voice commands the vertical centre of the open void
     * instead of hugging the floor (which left a bare dead zone above it). The
     * rose key-light below follows it up so the glow haloes the line. */
    justify-content: center;
    gap: var(--sp-3);
    min-width: 0;
    width: auto;
    min-height: 0;
    /* The hero gets the generous air; the rail + foot are thin chrome strips, so
     * the vertical rhythm steps >1.25 from strip to slab (impeccable layout). */
    padding: clamp(28px, 4.5vw, 52px);
    border: 0;
    border-radius: var(--rad-md);
    /* BOLD REDESIGN (2026-06-08, Kaan "go bold"): the glass slab is GONE. The
     * co-host's voice now lives full-bleed on the raw obsidian void — the
     * bravoh-grade-pink contract's actual signature, far more cinematic than a
     * voice boxed in a tile. All that remains is a soft rose key-light pooling up
     * from the floor where the line sits, bleeding edgelessly into the void. No
     * bevel, no box, no frame: the void IS the stage, the voice glows out of it. */
    background:
      radial-gradient(70% 78% at 24% 50%, rgba(255, 165, 223, 0.115), transparent 64%);
    overflow: visible;
  }
  /* The engraved inner faceplate is retired with the slab (bold redesign):
   * a machined frame only makes sense around a box, and the box is gone. The
   * voice sits on the open void now. */
  .vmx-voice::before { display: none; }
  /* Cursor-lit (mock contract): a 320px rose halo follows the pointer across
   * the voice — the co-host noticing your hand. Hover-only, 4% alpha. */
  .vmx-voice::after {
    content: "";
    position: absolute;
    inset: -16px -24px;
    background: radial-gradient(320px circle at var(--mx, 50%) var(--my, 50%), var(--brand-04), transparent 60%);
    border-radius: 18px;
    opacity: 0;
    transition: opacity 0.6s var(--ease-brand);
    pointer-events: none;
    z-index: 0;
  }
  .vmx-voice:hover::after { opacity: 1; }
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
    margin: 0;
    transition: color 700ms ease-out;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: min(58ch, 100%);
  }
  .vmx-ghost--g2 { color: var(--text-disabled); opacity: 0.7; }
  .vmx-ghost--g1 { color: var(--text-muted); }
  /* The nearest ghost wears the mock's ghost-mark — a mono "earlier" anchor
   * so prior speech reads as a labeled receipt, not an unexplained echo.
   * g2 stays bare so the stack still recedes. */
  .vmx-ghost--g1:not(:empty)::before {
    content: "earlier";
    font-family: var(--type-mono);
    font-size: 9px;
    font-weight: 500;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--text-disabled);
    margin-right: 10px;
  }
  .vmx-claim { display: flex; flex-direction: column; align-items: flex-start; gap: var(--sp-3); margin-top: var(--sp-2); }
  /* BOLD REDESIGN: the instrument readout crowning the voice — BPM · KEY laid
   * horizontally just above the spoken line (the bravoh-grade-pink mock's
   * framing). A quiet mono context strip; the serif voice below stays the hero.
   * The min-width:0 drops the foot-grid sizing so the values hug their content. */
  /* THE SCENE LINE (fable pass): the mock's single mono telemetry row crowning
   * the voice — a 32px brand hairline leads in, dot separators between reads.
   * Small, tracked-out, deliberate: the serif voice below is the hero; this is
   * the instrument quietly stating what it hears. */
  .vmx-voice__readout {
    display: flex;
    align-items: center;
    gap: 18px;
    margin-bottom: clamp(24px, 4.5vh, 52px);
  }
  .vmx-voice__readout::before {
    content: "";
    width: 32px;
    height: 1px;
    background: var(--brand-22);
  }
  .vmx-voice__readout .vmx-read { min-width: 0; }
  .vmx-voice__readout .vmx-read + .vmx-read::before {
    content: "";
    width: 3px;
    height: 3px;
    border-radius: 50%;
    background: var(--border-strong);
    align-self: center;
    margin-right: 14px;
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
    /* Editorial scale per the mock's cohost-line: 44-72px at 1.1 leading, NOT
     * the 96px billboard that forced 17ch wrapping. A friend leaning in, not a
     * headline shouting. */
    font-size: clamp(44px, 5.6vw, 72px); line-height: 1.1; letter-spacing: -0.018em;
    margin: 0;
    color: var(--text-primary); text-wrap: balance; max-width: min(920px, 100%);
    text-shadow: var(--text-3d);
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
  .vmx-now[data-arrived="true"] { animation: vmx-rise 400ms var(--ease-brand); }
  @keyframes vmx-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

  /* THE RECEIPT — rule draws L→R, cite ignites at its terminus [signature] */
  .vmx-receipt {
    display: flex; align-items: center; gap: var(--sp-3);
    width: min(52ch, 100%); max-width: 720px;
    margin-top: var(--sp-4);
    transition: opacity 700ms ease-out;
  }
  /* The evidence chip: ONE machined glass slab holding the waveform emblem and
   * the stacked time/band proof — the mock's receipt, with its left brand-bar.
   * The rule terminates here; the chip is the claim's physical proof object,
   * and hovering it lights the claim's own numerics (cite-linked) so proof and
   * claim visibly connect. */
  .vmx-receipt__chip {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 16px;
    padding: 14px 18px 14px 20px;
    border: 1px solid var(--border-default);
    border-radius: var(--r-sm);
    background:
      linear-gradient(180deg, var(--brand-08) 0%, var(--brand-04) 40%, transparent 100%),
      linear-gradient(180deg, var(--void-8) 0%, var(--void-5) 100%);
    backdrop-filter: var(--blur-glass-light);
    -webkit-backdrop-filter: var(--blur-glass-light);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 rgba(0, 0, 0, 0.4),
      0 1px 0 rgba(255, 255, 255, 0.02),
      0 4px 14px rgba(0, 0, 0, 0.35),
      0 12px 32px rgba(0, 0, 0, 0.18);
    transition: border-color 300ms var(--ease-brand),
                box-shadow 300ms var(--ease-brand),
                transform 200ms var(--ease-brand);
  }
  .vmx-receipt__chip:hover {
    border-color: var(--brand-35);
    transform: translateY(-1px);
  }
  .vmx-receipt__chip::before {
    content: "";
    position: absolute;
    left: 0; top: 12px; bottom: 12px;
    width: 2px;
    background: var(--brand);
    box-shadow: 0 0 6px var(--brand-50);
    border-radius: 0 1px 1px 0;
  }
  /* Corner bracket — the hover affordance that says "this is an object you
   * can pick up" (mock receipt::after). */
  .vmx-receipt__chip::after {
    content: "";
    position: absolute;
    width: 7px; height: 7px;
    bottom: -1px; right: -1px;
    border-bottom: 1px solid var(--brand);
    border-right: 1px solid var(--brand);
    opacity: 0;
    transition: opacity 300ms var(--ease-brand);
  }
  .vmx-receipt__chip:hover::after { opacity: 0.85; }
  .vmx-receipt[hidden] { display: none; }
  .vmx-receipt__rule {
    flex: 1; height: 1px;
    background: linear-gradient(90deg, var(--amber-40), var(--amber));
    box-shadow: 0 0 10px var(--amber-22);
    transform: scaleX(0); transform-origin: left;
  }
  .vmx-receipt[data-arrived="true"] .vmx-receipt__rule { animation: vmx-draw 520ms var(--ease-draw) 360ms forwards; }
  /* The cited moment's waveform — the mock's receipt signature. Not data: a
   * material emblem that this cite IS an audio moment, breathing at phrase
   * tempo beside the timestamp. */
  .vmx-receipt__wave {
    display: flex; align-items: center; gap: 2px; height: 28px; flex: none;
  }
  .vmx-receipt__wave span {
    width: 2.5px; border-radius: 1.25px;
    background: var(--brand); opacity: 0.55;
    animation: vmx-wave 1.8s ease-in-out infinite;
  }
  .vmx-receipt__wave span:nth-child(3) {
    /* silk alias (= the brightest warm off-white): the v5 legacy-token gate
     * greedily matches the bare v6 text-ladder names, so session CSS reads
     * the alias. */
    background: var(--silk); opacity: 0.95;
    box-shadow: 0 0 6px var(--brand-50);
  }
  @keyframes vmx-wave {
    0%, 100% { transform: scaleY(0.4); }
    50%      { transform: scaleY(1); }
  }
  @media (prefers-reduced-motion: reduce) {
    .vmx-receipt__wave span { animation: none; transform: scaleY(0.7); }
  }
  /* The cite lives INSIDE the chip slab as a two-line proof object (mock
   * receipt-meta): bold tabular time stacked over the muted band line. Ignite
   * plays on the time line; the slab stays steady. */
  .vmx-cite {
    flex: none; display: flex; flex-direction: column; gap: 2px; align-items: flex-start;
    font-family: var(--type-mono); text-transform: uppercase;
    line-height: 1;
    border: 0; border-radius: var(--rad-sm);
    padding: 0;
    background: transparent;
    cursor: pointer;
  }
  .vmx-cite__time {
    color: var(--text-primary);
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.18em;
    font-variant-numeric: tabular-nums;
    text-shadow: var(--text-emboss);
  }
  .vmx-cite__band {
    color: var(--text-muted);
    font-size: 10px;
    letter-spacing: 0.15em;
  }
  .vmx-receipt[data-arrived="true"] .vmx-cite__time { animation: vmx-ignite 380ms var(--ease-brand) 900ms both; }
  .vmx-cite:hover .vmx-cite__time { color: var(--brand-glow); text-shadow: 0 0 8px var(--brand-22); }
  .vmx-cite:focus-visible { outline: 2px solid var(--amber); outline-offset: 2px; }
  /* Claim↔proof link: hovering the receipt lights the spoken line's own
   * numerics — the grounding gesture made visible. */
  .vmx-now.cite-linked .num {
    color: var(--brand);
    text-shadow: 0 0 10px var(--brand-40);
    text-decoration: underline;
    text-underline-offset: 3px;
    text-decoration-color: var(--brand-40);
  }
  @keyframes vmx-draw { to { transform: scaleX(1); } }
  @keyframes vmx-ignite {
    0% { opacity: 0; color: var(--silk-40); text-shadow: none; }
    55% { opacity: 1; color: var(--amber); text-shadow: 0 0 8px var(--amber-65); }
    100% { opacity: 1; color: var(--text-primary); text-shadow: var(--text-emboss); }
  }

  /* --- FOOT: one steady master readout (BPM · key · live level) --- */
  .vmx-deck__foot {
    display: grid;
    /* The mock's phrase strip: groove takes the width, the drop phrase-label
     * rides its right end on the same row. */
    grid-template-columns: 1fr auto;
    align-items: center;
    gap: clamp(14px, 2.4vw, 40px);
    margin: 0 clamp(0px, 1.2vw, 18px);
    /* One steady master readout engraved into the void behind a SINGLE hairline,
     * the docstring's "single master strip" — not a third bordered+shadowed slab.
     * De-carded so only the voice slab is a lit surface (impeccable layout). */
    padding: 12px 2px 2px;
    border-top: 0;
    box-shadow: inset 0 1px 0 rgba(255, 222, 242, 0.052);
  }
  .vmx-read { display: flex; align-items: baseline; gap: var(--sp-2); min-width: 0; overflow: visible; white-space: nowrap; }
  .vmx-read[hidden] { display: none; }
  .vmx-read[data-readout="bpm"] { min-width: 9ch; }
  .vmx-read[data-readout="key"] { min-width: 6ch; }
  /* The now-playing read: a real track name is prose, not telemetry — body
   * face, sentence case, ellipsized; the dim mono "now" key stays the label. */
  .vmx-read[data-readout="track"] { min-width: 0; }
  .vmx-read[data-readout="track"] .vmx-read__num {
    font-family: var(--type-body);
    font-weight: 500;
    font-size: 13px;
    letter-spacing: 0;
    text-transform: none;
    color: var(--text-secondary);
    min-width: 0;
    max-width: 34ch;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .vmx-read__lab {
    font-family: var(--type-mono);
    font-size: 10px; font-weight: 500; letter-spacing: 0.32em; text-transform: uppercase;
    color: var(--text-disabled);
  }
  /* Scene-line values: one mono scale, tracked like the mock's "130 bpm · 8A".
   * BPM reads in quiet ink; KEY ignites in brand — the harmonic fact is the
   * one the co-host acts on, so it carries the single accent (by hue, small). */
  .vmx-read__num {
    font-family: var(--type-mono); font-weight: 700; font-size: 13px; letter-spacing: 0.06em;
    font-variant-numeric: tabular-nums;
    color: var(--text-tertiary); transition: color 700ms ease-out;
    display: inline-block; min-width: 5ch; overflow: visible;
    text-shadow: var(--text-emboss);
  }
  .vmx-read__key {
    font-family: var(--type-mono); font-weight: 700; font-size: 13px; letter-spacing: 0.06em;
    color: var(--brand); transition: color 700ms ease-out;
    display: inline-block; min-width: 4ch; overflow: visible;
    text-shadow: var(--text-emboss);
  }
  /* THE MASTER GROOVE (fable pass): the 14px segmented bar read as a cheap
   * dotted progress strip — the loudest slop tell on the deck. Rebuilt as the
   * mock's phrase hairline: a 4px machined groove recessed into the obsidian,
   * the live level as a soft rose wash inside it, the peak as a lit playhead
   * orb riding above. Same wires (.vmx-fmeter__fill width / __peak left). */
  .vmx-fmeter {
    position: relative; height: 4px; border-radius: 2px;
    background: linear-gradient(180deg, var(--void-0) 0%, var(--void-8) 100%);
    box-shadow:
      inset 0 1px 2px rgba(0, 0, 0, 0.55),
      inset 0 -1px 0 rgba(255, 255, 255, 0.04),
      0 1px 0 rgba(255, 255, 255, 0.03);
    overflow: visible;
    margin: 5px 0 7px;
  }
  /* The phrase tape inside the groove: phase chunks render as stepped
   * brand-alpha bands (silent stays void, groove a low wash, build brighter,
   * drop-ghost an outlined promise) so the strip plots SONG STRUCTURE and the
   * playhead rides the real now position. Live RMS demotes to the fill's
   * breathing opacity — the needle stops lying about what it measures. */
  .vmx-fmeter__chunks {
    position: absolute; inset: 0; display: flex; border-radius: 2px;
    overflow: hidden; z-index: 0;
  }
  .vmx-fmeter__chunks span { height: 100%; flex-basis: 0; }
  .vmx-fmeter__chunks span + span { border-left: 1px solid rgba(0, 0, 0, 0.4); }
  .vmx-fmeter__chunks span[data-kind="silent"] { background: transparent; }
  .vmx-fmeter__chunks span[data-kind="groove"] { background: var(--brand-08); }
  .vmx-fmeter__chunks span[data-kind="build"] { background: var(--brand-22); }
  .vmx-fmeter__chunks span[data-kind="drop-ghost"] {
    background: transparent;
    box-shadow: inset 0 0 0 1px var(--brand-35);
  }
  .vmx-fmeter__fill {
    position: absolute; inset: 0; width: 0%; border-radius: 2px;
    background: linear-gradient(90deg, var(--brand-10), var(--brand-22) 70%, var(--brand-35));
    transition: background 700ms ease-out;
    box-shadow: 0 0 12px var(--brand-08);
    z-index: 1;
  }
  .vmx-fmeter__peak {
    position: absolute; top: -5px; bottom: -5px; left: 0; width: 1.5px;
    background: var(--brand);
    /* The playhead glides one beat at a time — the mock's BPM-locked motion
     * thesis. Falls back to the house beat (461ms ≈ 130bpm) until live tempo
     * writes --bpm-period-ms on the groove. */
    transition: opacity 700ms ease-out, left calc(var(--bpm-period-ms, 461ms)) linear;
    box-shadow: 0 0 6px var(--brand-50);
    z-index: 4;
  }
  @media (prefers-reduced-motion: reduce) {
    .vmx-fmeter__peak { transition: opacity 700ms ease-out; }
  }
  .vmx-fmeter__peak::before {
    content: "";
    position: absolute;
    top: -4px; left: 50%;
    width: 7px; height: 7px;
    transform: translateX(-50%);
    border-radius: 50%;
    background: radial-gradient(circle at 35% 30%, var(--brand-glow), var(--brand) 60%, var(--brand-press) 100%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.4),
      inset 0 -1px 0 rgba(0, 0, 0, 0.3),
      0 0 8px var(--brand),
      0 0 14px var(--brand-50);
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
  .vmx-statusrow[hidden] { display: none; }
  .vmx-statusrow__inputs {
    display: flex; align-items: center;
    font-family: var(--type-mono); font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--text-disabled);
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
  .vmx-statusrow__right { font-family: var(--type-mono); font-size: 11px; color: var(--text-muted); letter-spacing: 0.08em; }

  /* === SILENT + FAULT — the surface settles into listening / holds on a drop = */
  .vmx-session[data-mode="silent"] .vmx-now { color: var(--text-muted); }
  .vmx-session[data-mode="fault"] .vmx-now { color: var(--text-disabled); }
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
  .vmx-session[data-mode="fault"] .vmx-read__key { color: var(--text-disabled); }
  .vmx-session[data-mode="silent"] .vmx-fmeter__fill {
    background: var(--silk-22); animation: vmx-idlebreath 3200ms ease-in-out infinite;
  }
  .vmx-session[data-mode="fault"] .vmx-fmeter__fill { background: var(--silk-12); animation: none; }
  /* The armed gate hides the foot — its meter breath and drop pips must not
   * keep burning compositor time behind visibility:hidden. */
  .vmx-session[data-runstate="armed"] .vmx-fmeter__fill,
  .vmx-session[data-runstate="armed"] .vmx-drop-chip__pip { animation: none; }
  .vmx-session[data-mode="silent"] .vmx-fmeter__peak,
  .vmx-session[data-mode="fault"] .vmx-fmeter__peak { opacity: 0; }
  @keyframes vmx-idlebreath { 0%, 100% { opacity: 0.4; } 50% { opacity: 0.85; } }

  @media (prefers-reduced-motion: reduce) {
    .vmx-now[data-arrived="true"] { animation: none; }
    .vmx-receipt[data-arrived="true"] .vmx-receipt__rule { animation: none; transform: scaleX(1); }
    /* Without the ignite animation the time line would stay at its keyframe
       start (opacity 0) and vanish for reduced-motion users; pin it visible. */
    .vmx-receipt[data-arrived="true"] .vmx-cite__time { animation: none; opacity: 1; }
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
    }
    .vmx-deck__controls button {
      padding: 6px 10px;
      letter-spacing: 0.14em;
    }
    .vmx-session[data-runstate="armed"] .vmx-armed {
      grid-template-columns: 1fr;
      gap: var(--sp-5);
      padding: var(--sp-5) 0 var(--sp-6);
    }
    .vmx-armed__title {
      font-size: 44px;
      max-width: 10ch;
    }
    .vmx-armed__module {
      width: 100%;
      box-sizing: border-box;
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
    .vmx-now {
      font-size: clamp(28px, 9vw, 42px);
      max-width: 12ch;
      -webkit-line-clamp: 2; /* the narrow voice slab holds two lines, not three */
    }
    .vmx-receipt {
      width: min(30ch, 100%);
    }
    .vmx-deck__foot {
      grid-template-columns: max-content max-content;
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
  root.dataset.statusrow = "quiet";
  // SHIP-WIRE START-gate — seed run-state at creation so the armed gate paints
  // on first frame (no flash before applyState's mount pass corrects it).
  root.dataset.runstate = state.runState ?? "running";
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

  const persona = document.createElement("div");
  persona.className = "vmx-persona";
  persona.setAttribute("role", "radiogroup");
  persona.setAttribute("aria-label", "co-host persona");
  const personaChips: Record<"HYPE" | "COACH" | "TEACH", HTMLButtonElement> = {
    HYPE: document.createElement("button"),
    COACH: document.createElement("button"),
    TEACH: document.createElement("button"),
  };
  for (const mood of ["HYPE", "COACH", "TEACH"] as const) {
    const chip = personaChips[mood];
    chip.type = "button";
    chip.className = "vmx-persona__chip";
    chip.dataset.mood = mood;
    chip.setAttribute("role", "radio");
    chip.setAttribute("aria-checked", "false");
    chip.textContent = mood.toLowerCase();
    chip.addEventListener("click", () => {
      // Optimistic repaint — flip the pressed chip NOW; the echoed
      // ipc.settings.state re-syncs on the next frame and self-corrects.
      for (const m of ["HYPE", "COACH", "TEACH"] as const) {
        personaChips[m].dataset.active = String(m === mood);
        personaChips[m].setAttribute("aria-checked", String(m === mood));
      }
      mountedHandle?.current.persona.onSelectMood?.(mood);
    });
    persona.append(chip);
  }

  const controls = document.createElement("div");
  controls.className = "vmx-deck__controls";
  const muteBtn = document.createElement("button");
  muteBtn.type = "button";
  muteBtn.dataset.action = "mute";
  muteBtn.textContent = "mute";
  // a11y: a bare "mute" label gave screen-reader users no read on the toggle
  // state. Name it + expose aria-pressed; applyState keeps both in sync.
  muteBtn.setAttribute("aria-label", "mute co-host");
  muteBtn.setAttribute("aria-pressed", "false");
  muteBtn.addEventListener("click", () => mountedHandle?.current.cohost.onMute?.());
  // SHIP-WIRE START-gate — Stop returns the live co-host to idle. Shown only
  // while running (CSS gates on data-runstate); hidden in the armed gate where
  // Start is the only action. Optimistic repaint: flip the deck to armed
  // locally on click, then onStop fires ipc.session.stop + setSessionState.
  const stopBtn = document.createElement("button");
  stopBtn.type = "button";
  stopBtn.dataset.action = "stop";
  stopBtn.textContent = "stop";
  stopBtn.setAttribute("aria-label", "stop co-host");
  stopBtn.addEventListener("click", () => {
    root.dataset.runstate = "armed";
    mountedHandle?.current.onStop?.();
  });
  controls.append(muteBtn, stopBtn);

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
  // Cursor-lit voice (mock contract): track the pointer into --mx/--my so the
  // ::after halo follows the hand. Pointer-event only — never on the rAF path.
  voice.addEventListener("mousemove", (e: MouseEvent) => {
    const rect = voice.getBoundingClientRect();
    voice.style.setProperty("--mx", `${(((e.clientX - rect.left) / rect.width) * 100).toFixed(1)}%`);
    voice.style.setProperty("--my", `${(((e.clientY - rect.top) / rect.height) * 100).toFixed(1)}%`);
  });
  const ghost2 = document.createElement("p");
  ghost2.className = "vmx-ghost vmx-ghost--g2";
  const ghost1 = document.createElement("p");
  ghost1.className = "vmx-ghost vmx-ghost--g1";
  const claim = document.createElement("div");
  claim.className = "vmx-claim";
  const now = document.createElement("p");
  now.className = "vmx-now";
  now.dataset.wire = "session.now-line";
  // The co-host's spoken line. It updated silently before, so screen-reader
  // users never heard the co-host; announce each new line politely.
  now.setAttribute("aria-live", "polite");
  now.setAttribute("aria-atomic", "true");
  const receipt = document.createElement("div");
  receipt.className = "vmx-receipt";
  receipt.hidden = true;
  const rule = document.createElement("span");
  rule.className = "vmx-receipt__rule";
  rule.setAttribute("aria-hidden", "true");
  // The cited moment's waveform emblem (fable pass): five bars breathing at
  // phrase tempo beside the cite. Decorative material, never data — heights
  // and delays are fixed so it can't pretend to plot the real signal.
  const wave = document.createElement("span");
  wave.className = "vmx-receipt__wave";
  wave.setAttribute("aria-hidden", "true");
  for (const [h, delay] of [
    [7, 0],
    [11, 0.12],
    [17, 0.24],
    [9, 0.36],
    [12, 0.48],
  ] as const) {
    const bar = document.createElement("span");
    bar.style.height = `${h}px`;
    bar.style.animationDelay = `${delay}s`;
    wave.append(bar);
  }
  const cite = document.createElement("button");
  cite.type = "button";
  cite.className = "vmx-cite";
  cite.dataset.wire = "session.citation";
  // Two-line proof object (mock receipt-meta): bold tabular time over the
  // muted band line.
  const citeTime = document.createElement("span");
  citeTime.className = "vmx-cite__time";
  const citeBand = document.createElement("span");
  citeBand.className = "vmx-cite__band";
  cite.append(citeTime, citeBand);
  // One glass slab holds the wave emblem + cite — the proof object the
  // signature rule terminates at.
  const receiptChip = document.createElement("span");
  receiptChip.className = "vmx-receipt__chip";
  receiptChip.append(wave, cite);
  // Claim↔proof link: hovering the proof object lights the claim's numerics.
  receiptChip.addEventListener("mouseenter", () => now.classList.add("cite-linked"));
  receiptChip.addEventListener("mouseleave", () => now.classList.remove("cite-linked"));
  receipt.append(rule, receiptChip);
  const dropSlot = document.createElement("div");
  dropSlot.className = "vmx-drop-slot";
  dropSlot.dataset.wire = "session.drop";
  claim.append(now, receipt);
  voice.append(ghost2, ghost1, claim);

  // --- armed gate (SHIP-WIRE START-gate) ---
  // Shown only when data-runstate="armed": the co-host is loaded but idle, no
  // reactions. A single Start affordance flips the deck live. CSS hides
  // .vmx-voice while armed so the reaction zone reads as a calm, deliberate
  // "ready" — never a fault (Invariant #5: idle is calm, not broken).
  const armed = document.createElement("div");
  armed.className = "vmx-armed";
  const armedField = document.createElement("div");
  armedField.className = "vmx-armed__field";
  armedField.setAttribute("aria-hidden", "true");
  // The sign of life (direction-final): a hairline frame seating the idle deck
  // + ONE slow brand light traveling its perimeter (tokens.css .border-anim,
  // 22s). The session deck's single allowed sweep, armed-only.
  const armedFrame = document.createElement("div");
  armedFrame.className = "vmx-armed__frame";
  armedFrame.setAttribute("aria-hidden", "true");
  const armedCopy = document.createElement("div");
  armedCopy.className = "vmx-armed__copy";
  const armedEyebrow = document.createElement("span");
  armedEyebrow.className = "vmx-armed__eyebrow";
  armedEyebrow.textContent = "armed and waiting";
  const armedTitle = document.createElement("h1");
  armedTitle.className = "vmx-armed__title";
  // The one charisma beat at idle: the moment the co-host is waiting for
  // ignites in rose italic (mirrors the live hero's em treatment). Static
  // copy, built node-wise — no innerHTML.
  armedTitle.append(document.createTextNode("I'm awake before the "));
  const armedEm = document.createElement("em");
  armedEm.textContent = "first bar";
  armedTitle.append(armedEm, document.createTextNode("."));
  const armedLead = document.createElement("p");
  armedLead.className = "vmx-armed__lead";
  armedLead.textContent =
    "Start when the mix is moving. I will only speak from audio, controller, and screen proof.";
  const armedContext = document.createElement("div");
  armedContext.className = "vmx-armed__context";
  const captureContext = makeArmedContextItem("capture");
  const midiContext = makeArmedContextItem("controller");
  const outputContext = makeArmedContextItem("output");
  const personaContext = makeArmedContextItem("persona");
  armedContext.append(
    captureContext.wrap,
    midiContext.wrap,
    outputContext.wrap,
    personaContext.wrap,
  );
  armedCopy.append(armedEyebrow, armedTitle, armedLead, armedContext);
  const armedModule = document.createElement("div");
  armedModule.className = "vmx-armed__module";
  const armedKicker = document.createElement("span");
  armedKicker.className = "vmx-armed__kicker";
  armedKicker.textContent = "ready to listen";
  const startBtn = document.createElement("button");
  startBtn.type = "button";
  startBtn.dataset.action = "start";
  startBtn.className = "vmx-armed__start";
  startBtn.textContent = "Go live";
  startBtn.setAttribute("aria-label", "go live, start the co-host");
  // Optimistic repaint (CLAUDE.md rule): flip the deck to running locally so
  // the live surface appears instantly; onStart fires ipc.session.start +
  // setSessionState, and the next render frame confirms the run-state.
  startBtn.addEventListener("click", () => {
    root.dataset.runstate = "running";
    mountedHandle?.current.onStart?.();
  });
  const armedNote = document.createElement("span");
  armedNote.className = "vmx-armed__note";
  armedNote.textContent = "Stands by until you go live.";
  armedModule.append(armedKicker, startBtn, armedNote);
  armed.append(armedFrame, armedField, armedCopy, armedModule);

  speak.append(voice, armed);
  deck.append(speak);

  // --- deck notice — THE user-visible ipc.error surface (lanes B+D).
  // ws-bridge.applyIpcError writes SessionState.deckNotice; the render-loop
  // projects it here. Hidden whenever null. role=status so screen readers
  // announce the failure without stealing focus.
  const notice = document.createElement("p");
  notice.className = "vmx-deck__notice";
  notice.dataset.wire = "session.notice";
  notice.setAttribute("role", "status");
  notice.hidden = true;
  deck.append(notice);

  // --- foot (bpm · key · live meter)
  const foot = document.createElement("div");
  foot.className = "vmx-deck__foot";
  const { wrap: bpmWrap, value: bpm } = makeReadout("bpm");
  const { wrap: keyWrap, value: key } = makeReadout("key", true);
  // BOLD REDESIGN (2026-06-08): the instrument readout (BPM · KEY) now CROWNS the
  // voice from above — the bravoh-grade-pink mock's structure — instead of sitting
  // stranded at the foot. The render-loop writes `bpm`/`key` by ref (see the
  // update fn), so relocating the wrappers keeps them live with ZERO wiring
  // change. The foot keeps the level meter, now full-width like the mock's strip.
  const readoutFrame = document.createElement("div");
  readoutFrame.className = "vmx-voice__readout";
  // The third scene-line read: what's actually playing (timecode.track from
  // the real now-playing wire). Hidden until a real title lands — never a
  // fabricated value (Invariant #3).
  const { wrap: trackWrap, value: track } = makeReadout("now");
  trackWrap.dataset.readout = "track";
  trackWrap.hidden = true;
  readoutFrame.append(bpmWrap, keyWrap, trackWrap);
  claim.prepend(readoutFrame);
  const fmeter = document.createElement("div");
  fmeter.className = "vmx-fmeter";
  fmeter.dataset.wire = "session.meter";
  fmeter.setAttribute("aria-label", "master level");
  const meterChunks = document.createElement("div");
  meterChunks.className = "vmx-fmeter__chunks";
  meterChunks.setAttribute("aria-hidden", "true");
  const meterFill = document.createElement("div");
  meterFill.className = "vmx-fmeter__fill";
  const meterPeak = document.createElement("div");
  meterPeak.className = "vmx-fmeter__peak";
  fmeter.append(meterChunks, meterFill, meterPeak);
  // The drop countdown rides the groove as its phrase label (the mock's
  // "drop in ~N bars" position) — empty slot collapses via :empty.
  foot.append(fmeter, dropSlot);
  deck.append(foot);

  stage.append(deck);
  root.append(stage);

  // --- status row
  const statusRow = document.createElement("footer");
  statusRow.className = "vmx-statusrow";
  statusRow.dataset.wire = "session.status";
  statusRow.hidden = true;
  statusRow.setAttribute("aria-hidden", "true");
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
  const statusMeta = document.createElement("div");
  statusMeta.className = "vmx-statusrow__meta";
  statusMeta.append(statusRight);
  statusRow.append(inputsEl, statusMeta);
  root.append(statusRow);

  rootEl.replaceChildren(root);

  const mounted: Mounted = {
    root,
    titlebar,
    persona,
    personaChips,
    muteButton: muteBtn,
    liveFault,
    armedContext: {
      capture: captureContext.value,
      midi: midiContext.value,
      output: outputContext.value,
      persona: personaContext.value,
    },
    ghosts: [ghost1, ghost2],
    now,
    receipt,
    dropSlot,
    notice,
    cite,
    citeTime,
    citeBand,
    bpm,
    key,
    track,
    meterFill,
    meterPeak,
    meterChunks,
    statusInputs: {
      audio: inAudio,
      ai: inAi,
      voice: inVoice,
      voiceSep,
      screen: inScreen,
      midi: inMidi,
    },
    statusRow,
    statusRight,
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

/** Render the co-host's spoken line with its charisma intact: inline timecodes
 *  (M:SS / MM:SS, e.g. "02:14") lift into a lit mono cite (`.num`) the way the
 *  bravoh-grade-pink contract sets them, the rest stays plain serif prose. This
 *  is the difference between a flat sentence and a co-host pointing at a moment.
 *
 *  Grounding-safe (it only reformats a timecode already in the real reaction
 *  text, never fabricates one) and XSS-safe: built node-by-node with text nodes,
 *  never innerHTML, so AI-authored reaction text can never inject markup — the
 *  only element we create is the known `.num` span. `el.textContent` still
 *  concatenates back to the raw line, so the caller's skip-if-unchanged guard
 *  and the aria-live announcement both keep working. */
export function setVoiceLine(el: HTMLElement, text: string): void {
  el.replaceChildren();
  if (!text) return;
  const re = /\b\d{1,2}:\d{2}\b/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      el.appendChild(document.createTextNode(text.slice(last, m.index)));
    }
    const num = document.createElement("span");
    num.className = "num";
    num.textContent = m[0];
    el.appendChild(num);
    last = m.index + m[0].length;
  }
  if (last < text.length) {
    el.appendChild(document.createTextNode(text.slice(last)));
  }
}

function makeReadout(label: string, isKey = false): { wrap: HTMLElement; value: HTMLElement } {
  const wrap = document.createElement("div");
  wrap.className = "vmx-read";
  wrap.dataset.readout = isKey ? "key" : "bpm";
  const lab = document.createElement("span");
  lab.className = "vmx-read__lab";
  lab.textContent = label;
  const value = document.createElement("span");
  value.className = isKey ? "vmx-read__key" : "vmx-read__num";
  wrap.append(lab, value);
  return { wrap, value };
}

function makeArmedContextItem(label: string): { wrap: HTMLElement; value: HTMLElement } {
  const wrap = document.createElement("div");
  wrap.className = "vmx-armed__context-item";
  const labelEl = document.createElement("span");
  labelEl.className = "vmx-armed__context-label";
  labelEl.textContent = label;
  const value = document.createElement("span");
  value.className = "vmx-armed__context-value";
  wrap.append(labelEl, value);
  return { wrap, value };
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

  // --- persona (direct-select mood strip) ---
  if (isMount || prev.persona.mood !== next.persona.mood) {
    mounted.persona.dataset.mood = next.persona.mood;
    for (const m of ["HYPE", "COACH", "TEACH"] as const) {
      mounted.personaChips[m].dataset.active = String(m === next.persona.mood);
      mounted.personaChips[m].setAttribute("aria-checked", String(m === next.persona.mood));
    }
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

  // --- SHIP-WIRE START-gate run-state ---
  // Orthogonal to data-mode: armed = the idle Start gate (no reactions);
  // running = the live deck. Authoritative from the projected state; the
  // click handlers flip it optimistically for instant feedback and this
  // confirms it on the next frame.
  const runState: "armed" | "running" = next.runState ?? "running";
  if (mounted.root.dataset.runstate !== runState) {
    mounted.root.dataset.runstate = runState;
  }
  syncArmedContext(mounted, next);

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
  // textContent of the built line concatenates to nowText, so this guard still
  // holds (skip the DOM rebuild when the line is unchanged).
  if (mounted.now.textContent !== nowText) setVoiceLine(mounted.now, nowText);
  if (!nowLine && mode === "silent") {
    const idle = idleReadinessLines(next);
    setGhostText(mounted.ghosts[0], idle.action);
    setGhostText(mounted.ghosts[1], idle.inputs);
  } else {
    setGhost(mounted.ghosts[0], g1Line);
    setGhost(mounted.ghosts[1], g2Line);
  }

  // --- the receipt (cite for the now-line) ---
  const chips = nowLine && next.cohost.reactions ? next.cohost.reactions.get(nowLine.ts) : undefined;
  const chip = chips && chips.length ? chips[0]! : null;
  if (chip) {
    mounted.receipt.hidden = false;
    const timeText = formatTs(chip.timestamp_s);
    const bandText = chip.verb.toLowerCase();
    if (mounted.citeTime.textContent !== timeText) mounted.citeTime.textContent = timeText;
    if (mounted.citeBand.textContent !== bandText) mounted.citeBand.textContent = bandText;
    // Re-bind the click only when the chip identity changes.
    if (mounted.citeChip?.event_id !== chip.event_id) {
      mounted.citeChip = chip;
      mounted.cite.setAttribute("aria-label", `evidence: ${bandText} at ${timeText}`);
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
  const bpmValue = next.timecode.bpm;
  const bpmMissing = bpmValue == null;
  const bpmText = bpmMissing ? "" : bpmValue.toFixed(1);
  if (mounted.bpm.textContent !== bpmText) mounted.bpm.textContent = bpmText;
  mounted.bpm.dataset.empty = bpmMissing ? "true" : "false";
  // A null BPM is usually read as "the counter is broken" when the deck is
  // visually alive. Name the honest cause on the readout itself, but keep the
  // visible value blank: no grounded audio has reached the detector yet.
  if (bpmMissing) {
    const bpmTitle = bpmWaitingTitle(next.status.captureDevice, next.meters.music);
    if (mounted.bpm.getAttribute("aria-label") !== bpmTitle) {
      mounted.bpm.setAttribute("title", bpmTitle);
      mounted.bpm.setAttribute("aria-label", bpmTitle);
    }
  } else if (mounted.bpm.hasAttribute("aria-label")) {
    mounted.bpm.removeAttribute("title");
    mounted.bpm.removeAttribute("aria-label");
  }
  // Track read — title (+ artist when known) from the real now-playing wire.
  // The whole read hides when nothing is detected; it never invents a title.
  const trackInfo = next.timecode.track;
  const trackText = trackInfo
    ? trackInfo.artist
      ? `${trackInfo.title} — ${trackInfo.artist}`
      : trackInfo.title
    : "";
  if (mounted.track.textContent !== trackText) mounted.track.textContent = trackText;
  const trackWrapEl = mounted.track.closest<HTMLElement>(".vmx-read");
  if (trackWrapEl && trackWrapEl.hidden !== !trackText) trackWrapEl.hidden = !trackText;

  const keyValue = next.timecode.key;
  const keyMissing = keyValue == null;
  const keyText = keyMissing ? "" : keyValue;
  if (mounted.key.textContent !== keyText) mounted.key.textContent = keyText;
  mounted.key.dataset.empty = keyMissing ? "true" : "false";
  // A null key stays visually blank; name it so the reserved slot reads as
  // "not detected yet", not "broken". The value appears only when grounded.
  if (keyMissing) {
    if (mounted.key.getAttribute("aria-label") !== "Key not detected yet.") {
      mounted.key.setAttribute("title", "Key not detected yet.");
      mounted.key.setAttribute("aria-label", "Key not detected yet.");
    }
  } else if (mounted.key.hasAttribute("aria-label")) {
    mounted.key.removeAttribute("title");
    mounted.key.removeAttribute("aria-label");
  }

  // --- master groove (live only — held/recolored by CSS in silent/fault) ---
  // The phrase tape renders when the structure read exists: chunks band the
  // groove, fill + playhead ride the real now position, and live RMS breathes
  // the wash's opacity instead of impersonating progress. With no chunks yet
  // the groove falls back to the smoothed RMS level — fill and needle clamped
  // to the SAME ceiling so the orb never trails the fill's end.
  if (isMount || prev.phase.chunks !== next.phase.chunks) {
    mounted.meterChunks.replaceChildren(
      ...next.phase.chunks.map((chunk) => {
        const seg = document.createElement("span");
        seg.dataset.kind = chunk.kind;
        seg.style.flexGrow = String(Math.max(chunk.weight, 0.0001));
        return seg;
      }),
    );
  }
  if (mode === "") {
    // Live tempo drives the playhead's beat-length glide (CSS transition on
    // --bpm-period-ms); the drop chip sets the same var on its own root.
    const groove = mounted.meterChunks.parentElement;
    if (groove && next.drop.bpmPeriodMs && next.drop.bpmPeriodMs > 0) {
      groove.style.setProperty("--bpm-period-ms", `${next.drop.bpmPeriodMs}ms`);
    }
    if (next.phase.chunks.length > 0) {
      const pct = Math.min(Math.max(next.phase.nowPct, 0), 100);
      const lvl = Math.min(meterLevelPct(next.meters.music.rms), 100);
      mounted.meterFill.style.width = `${pct.toFixed(1)}%`;
      mounted.meterFill.style.opacity = (0.45 + (0.55 * lvl) / 100).toFixed(2);
      mounted.meterPeak.style.left = `${pct.toFixed(1)}%`;
    } else {
      mounted.meterFill.style.opacity = "";
      const target = meterLevelPct(next.meters.music.rms);
      mounted.meterCur += (target - mounted.meterCur) * METER_ATTACK;
      const peakTarget = meterLevelPct(next.meters.music.peak ?? next.meters.music.rms);
      const lead = Math.max(mounted.meterCur + 4, peakTarget);
      if (lead > mounted.meterPk) mounted.meterPk = lead;
      else mounted.meterPk += (lead - mounted.meterPk) * METER_PEAK_DECAY;
      const w = Math.min(mounted.meterCur, METER_CEIL);
      mounted.meterFill.style.width = `${w.toFixed(1)}%`;
      mounted.meterPeak.style.left = `${Math.min(mounted.meterPk, METER_CEIL).toFixed(1)}%`;
    }
  }

  // --- mute control reflects state ---
  if (isMount || prev.status.muted !== next.status.muted) {
    const muteBtn = mounted.muteButton;
    if (muteBtn) {
      muteBtn.dataset.on = next.status.muted ? "true" : "false";
      muteBtn.textContent = next.status.muted ? "muted" : "mute";
      muteBtn.setAttribute("aria-pressed", next.status.muted ? "true" : "false");
      muteBtn.setAttribute("aria-label", next.status.muted ? "unmute co-host" : "mute co-host");
    }
  }

  // --- deck notice (THE ipc.error surface — null hides the line) ---
  const nextNotice = next.notice ?? null;
  const prevNotice = prev.notice ?? null;
  if (isMount || prevNotice !== nextNotice) {
    mounted.notice.textContent = nextNotice ? nextNotice.text : "";
    if (nextNotice) mounted.notice.dataset.tone = nextNotice.tone;
    else delete mounted.notice.dataset.tone;
    mounted.notice.hidden = nextNotice === null;
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
  const statusRowAlert =
    next.status.livekit === "down" ||
    next.status.gemini === "down" ||
    downInput === "gemini" ||
    next.status.voice === "muted" ||
    next.status.screen === "denied";
  const statusRowMode = statusRowAlert ? "alert" : "quiet";
  if (mounted.root.dataset.statusrow !== statusRowMode) {
    mounted.root.dataset.statusrow = statusRowMode;
  }
  if (mounted.statusRow.hidden === statusRowAlert) {
    mounted.statusRow.hidden = !statusRowAlert;
    mounted.statusRow.setAttribute("aria-hidden", statusRowAlert ? "false" : "true");
  }
  // Just the live output route — the one fact here that can change mid-set and
  // matters at a glance (where the co-host's voice lands). Voice name + genre are
  // set-once Settings config, not live status; printing them in always-on chrome
  // was extra text a DJ never reads mid-set (impeccable: status-row text cut).
  const rightText = outputLabel(next.output);
  if (mounted.statusRight.textContent !== rightText) mounted.statusRight.textContent = rightText;
}

function setGhost(el: HTMLElement, line: TranscriptLine | null): void {
  const text = line ? line.text : "";
  setGhostText(el, text);
}

function setGhostText(el: HTMLElement, text: string): void {
  if (el.textContent !== text) el.textContent = text;
  el.style.display = text ? "" : "none";
}

function syncArmedContext(mounted: Mounted, state: SessionState): void {
  setText(mounted.armedContext.capture, armedCaptureText(state));
  setText(mounted.armedContext.midi, armedMidiText(state));
  setText(mounted.armedContext.output, outputLabel(state.output));
  setText(
    mounted.armedContext.persona,
    `${state.persona.mood.toLowerCase()} / ${state.persona.voice}`,
  );
}

function setText(el: HTMLElement, text: string): void {
  if (el.textContent !== text) el.textContent = text;
}

function armedCaptureText(state: SessionState): string {
  if (state.status.livekit === "ok" && musicSignalActive(state.meters.music)) {
    return "master in";
  }
  if (state.status.livekit === "ok") return "armed";
  if (state.status.livekit === "connecting") return "connecting";
  if (state.status.livekit === "down") return "dropped";
  return "checking";
}

function armedMidiText(state: SessionState): string {
  const device = midiDeviceLabel(state.status.midiDevice);
  if (state.status.midi != null && state.status.midi > 0) return `${device} seen`;
  if (state.status.midiActivity === "connected_no_midi_traffic") return `${device} connected`;
  if (state.status.midiActivity === "midi_traffic_unmapped") return `${device} unmapped`;
  if (state.status.midiActivity === "midi_events_no_moves") return `${device} needs move`;
  if (state.status.midiActivity === "disconnected") return "controller offline";
  return "motion pending";
}

function idleReadinessLines(state: SessionState): { inputs: string; action: string } {
  const audioActive = musicSignalActive(state.meters.music);
  const audioWaiting = state.status.livekit === "ok" && !audioActive;
  const controllerWaiting = state.status.midi === 0;
  const notes: string[] = [];
  if (state.status.livekit === "connecting") notes.push("Audio connecting.");
  else if (state.status.livekit !== "ok") notes.push("Audio checking.");
  if (state.status.voice === "muted") notes.push("Voice muted.");
  else if (state.status.gemini === "down") notes.push("Co-host offline.");
  else if (state.status.gemini !== "ok") notes.push("Co-host checking.");
  if (state.status.screen === "denied") notes.push("Screen proof denied.");
  const action = audioWaiting
    ? captureRouteAction(state.status.captureDevice)
    : controllerWaiting
      ? midiProofAction(state.status.midiActivity, state.status.midiDevice)
      : "";
  return {
    inputs: notes.join(" "),
    action,
  };
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

function captureRouteAction(captureDevice?: string | null): string {
  const label = captureDeviceLabel(captureDevice);
  const instruction = captureRouteInstruction(captureDevice);
  return label === "capture" ? instruction : `${label}: ${instruction}`;
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
    return `${device}: Move mixer/deck control.`;
  }
  if (midiActivity === "midi_traffic_unmapped") {
    return `${device}: Run controller mapping.`;
  }
  if (midiActivity === "midi_events_no_moves") {
    return `${device}: Move a deck control.`;
  }
  if (midiActivity === "disconnected") {
    return "Connect the controller, then recheck MIDI.";
  }
  return "Move a control once, I will not guess.";
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
    // SHIP-WIRE START-gate — this fixture default is "running" (the live deck)
    // so existing SessionLayout specs that construct defaultState() keep their
    // behaviour. The real boot drives the armed gate through the render-loop
    // projection of the bridge state's runState.
    runState: "running",
  };
}
