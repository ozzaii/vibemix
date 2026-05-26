/* SessionLayout.ts — composer for the live session window (UI-SPEC §Layout).
 *
 * Builds the full DOM tree on `mountSessionLayout(root)`:
 *   - 4 corner screws on the shell
 *   - titlebar (with status pills + live clock + settings gear)
 *   - 3-column grid (left: persona+output+meters / center: timecode+phase+drop+events
 *     / right: cohost panel)
 *   - status bar
 *
 * Subsequent ticks call `renderSessionFrame(state)` — an idempotent
 * diffing render that pokes CSS variables + textContent ONLY. The component
 * tree is NOT rebuilt. This keeps the rAF hot path layout-thrash-free.
 *
 * Components in this file are presentation-only — NO IPC, NO setInterval,
 * NO state. Wave 3 (plan 12-04) wires the WS bridge and rAF loop.
 *
 * Grid tokens are scoped here as inline CSS variables on the wrapper —
 * UI-SPEC declared them as local-to-live-session tokens; this avoids
 * polluting tokens.css with Phase-12-only grid columns. */

import { registerStyle } from "./components/_style-registry.js";
import { renderTitlebar, setTitlebarClock, setTitlebarPill, type PillLevel } from "./components/titlebar.js";
import { renderPanel } from "./components/panel.js";
import { renderMeter, setMeterLevels } from "./components/meter.js";
import { renderTimecode, setTimecode } from "./components/timecode.js";
import { renderPhaseTape, setPhaseTape, type PhaseChunk } from "./components/phase-tape.js";
import { renderDropChip } from "./components/drop-chip.js";
import { renderEventRibbon, setEventRibbon, type MidiEvent } from "./components/event-ribbon.js";
import {
  GROUNDING_FAILURE_MS,
  renderCohostPanel,
  setCohost,
  type CohostStatus,
  type ReactionsByTs,
  type TranscriptLine,
} from "./components/cohost.js";
import type { CitationChip } from "./components/citation-strip.js";
import { renderStatusBar, type BadgeState } from "./components/status-bar.js";
import { SCREW_SVG } from "./icons/screw.svg.js";

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
    /** Optional click handler for the H9 retry button rendered after the
     *  grounding-failure threshold elapses. Layout passes this through to
     *  the cohost panel verbatim. */
    onRetry?: () => void;
    /** Phase 44-03 / LAUNCH-02 — citation chip strips keyed by
     *  transcript line `ts`. Optional; missing keys render the
     *  transcript line without a chip strip. */
    reactions?: ReactionsByTs;
    /** Phase 44-03 / LAUNCH-02 — chip click handler. Layout passes this
     *  through to the cohost panel verbatim; the render-loop projection
     *  builds the actual debrief-deep-link invoke. */
    onChipClick?: (chip: CitationChip) => void;
    /** 2026-05-19 /impeccable critique round 4 (Kaan) — "see all <N>
     *  reactions ↗" footer link routes here. The render-loop projection
     *  wires this to invoke("open_debrief_window") so the full
     *  transcript lives only in the debrief context. */
    onOpenAllReactions?: () => void;
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
  /** Persona panel state — Wave 3 (12-04) will wire onChange callbacks. */
  persona: {
    skill: "BEG" | "INT" | "PRO";
    /** Legacy 2-state — retained for back-compat with existing tests / wires. */
    interaction: "HYPE" | "COACH";
    /** 3-state mood (the v5 mood-block). Mapped from settings.mood by the
     *  render-loop projection. The persona panel renders this; settings
     *  drawer's mascot group is the authoritative write surface. */
    mood: "HYPE" | "TEACH" | "COACH";
    voice: string;
    genre: string;
    /** 2026-05-26 /impeccable critique P1 — in-deck mood cycle. Tapping the
     *  mood headline on the persona readout advances HYPE → TEACH → COACH
     *  → HYPE without opening the drawer. The render-loop wires this to
     *  emitIpc("ipc.settings.set", { field: "mood", … }) — the same real,
     *  already-wired knob the settings drawer writes. Mood IS the
     *  chattiness axis (HYPE talks over the build; COACH waits for the
     *  mix-out), so this is the lightweight "ease off / hype up" gesture
     *  H3 was missing, backed by a real setting (no broken promise).
     *  Omitted (e.g. the dev mock) → the mood headline renders but tap is
     *  a no-op. */
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
  /** Glanceable read-only persona readout on the left rail. The render
   *  loop updates its mood/skill/genre/voice text in place; clicking it
   *  opens the settings drawer (the sole persona write surface). */
  personaStatus: HTMLElement;
  meters: {
    music: HTMLElement;
    voice: HTMLElement;
    mic: HTMLElement;
  };
  timecode: HTMLElement;
  phaseTape: HTMLElement;
  dropSlot: HTMLElement;
  eventRibbon: HTMLElement;
  cohost: HTMLElement;
  statusBar: HTMLElement;
  bannerSlot: HTMLElement;
  current: SessionState;
  /** Sticky-bottom flag for the transcript. Toggled by a scroll
   *  listener wired during mount — true means new lines auto-scroll;
   *  false means the user has scrolled up and we preserve position. */
  userScrolledUp: boolean;
  /** Wave 6 (H9) — timestamp (Date.now()) of the most-recent transition
   *  from grounded=true to grounded=false. Null when grounded is currently
   *  true OR has been true since mount. The render-loop reads this on
   *  each frame to compute the failure-elapsed delta for the cohost foot;
   *  the cohost flips to "COULDN'T REACH GEMINI" once the delta crosses
   *  GROUNDING_FAILURE_MS (5s). */
  groundedFalseSinceMs: number | null;
}

/* VIS-02 (43-02): hover-glow contract is owned per-component by the
 * children mounted into this layout (titlebar / rocker / picker /
 * status-bar / cohost retry / meter). SessionLayout itself carries no
 * <button>, <a>, [role="button"] or [data-interactive] in its own CSS —
 * the screws + grid are passive ornaments. This comment is the audit-
 * trail anchor so a grep for `VIS-02` in src/session/ surfaces every
 * file in the sweep. */
const LAYOUT_CSS = `
  .vmx-session {
    --col-left: 300px;
    --col-right: 400px;
    --gap-col: var(--sp-5);
    display: grid;
    grid-template-rows: var(--titlebar-h) 1fr var(--statusbar-h);
    height: 100vh;
    position: relative;
    overflow: hidden;
  }
  /* Bolder (2026-05-20) — stage lighting. The session was a flat field of
   * equal-weight glass tiles: no light direction, so nothing read as the
   * hero. This lays a warm stage-pool behind the center deck (the glass
   * tiles' backdrop-blur turns it into a soft backlight) and a framing
   * vignette that sinks the outer rails into shadow. Static, not breathing
   * — the deck border-anim is the one breathing light. Sits at z-index 0,
   * below the children promoted to z-index 5 below, so it backlights
   * without ever painting over content. One amber; no new tokens. */
  .vmx-session::before {
    content: '';
    position: absolute;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background:
      radial-gradient(ellipse 44% 52% at 47% 40%, rgba(255, 138, 61, 0.055), transparent 64%),
      radial-gradient(ellipse 36% 30% at 47% 34%, rgba(255, 184, 138, 0.03), transparent 70%),
      radial-gradient(ellipse 120% 100% at 50% 46%, transparent 52%, rgba(0, 0, 0, 0.5) 100%);
  }
  /* The animated amber border-anim is z-index 4 (tokens.css). Promote
   * direct children above it so titlebar / grid / status-bar paint over
   * the sweep peak without being clipped by the conic mask. Excludes
   * .vmx-session__screw — those are absolutely-positioned corner
   * ornaments at z-index 100 and the :not() exclusion preserves their
   * own rule's positioning (WR-01 from 14-REVIEW.md: :not() arguments
   * bump this selector to (0,2,0), which would otherwise dominate the
   * screw rule's (0,1,0) and collapse the ornaments inline). */
  .vmx-session > *:not(.border-anim):not(.vmx-session__screw) { position: relative; z-index: 5; }
  .vmx-session__screw {
    position: absolute;
    width: 8px;
    height: 8px;
    z-index: 100;
    color: var(--silk-22);
    pointer-events: none;
  }
  .vmx-session__screw[data-corner="tl"] { top: 6px; left: 6px; }
  .vmx-session__screw[data-corner="tr"] { top: 6px; right: 6px; }
  .vmx-session__screw[data-corner="bl"] { bottom: 6px; left: 6px; }
  .vmx-session__screw[data-corner="br"] { bottom: 6px; right: 6px; }
  .vmx-session__grid {
    display: grid;
    /* Center deck is the hero: a fluid 1fr column flanked by a narrow
     * control rail and the cohost voice. minmax(0,1fr) lets the deck
     * own all reclaimed width so the frame fills edge-to-edge instead of
     * left-packing three fixed columns into a dead-space layout. */
    grid-template-columns: var(--col-left) minmax(0, 1fr) var(--col-right);
    gap: var(--gap-col);
    padding: var(--sp-5) var(--sp-6);
    overflow-y: auto;
    overflow-x: hidden;
    min-height: 0;
    overscroll-behavior: contain;
    /* Columns stretch to the full deck height — no floating panels over
     * a void floor; the instrument fills its enclosure. */
    align-items: stretch;
  }
  .vmx-session__col {
    display: flex;
    flex-direction: column;
    gap: var(--sp-4);
    min-width: 0;
    min-height: 0;
  }
  .vmx-session__col[data-col="right"] {
    height: 100%;
  }
  /* The center column reads as ONE deck unit, not a stack of widgets:
   * the now-playing display and the waveform tape are the dominant mass,
   * everything beneath settles to the deck floor. */
  .vmx-session__col[data-col="center"] {
    gap: var(--sp-5);
  }
  .vmx-session__col[data-col="center"] > .vmx-tile:first-child,
  .vmx-session__col[data-col="center"] > [data-tc] {
    flex: 0 0 auto;
  }
  .vmx-session__meter-strip {
    display: flex;
    gap: var(--sp-4);
    align-items: flex-end;
    justify-content: space-around;
    padding: var(--sp-4) 0 0;
  }
  /* Glanceable persona readout (2026-05-25 rebuild; 2026-05-26 critique P1).
   * A recessed glass tile holding two affordances: the mood headline is a
   * tap-to-cycle button (HYPE → TEACH → COACH, the real chattiness knob),
   * and the "EDIT ▸" chip opens the drawer for full persona control. The
   * tile itself is no longer clickable — the two buttons own the
   * interaction so the gesture is explicit. Mood is the silk headline; the
   * caption carries the one mood tint (set inline) so the block feels
   * alive without a second amber. */
  .vmx-persona-status {
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
    align-items: stretch;
    text-align: left;
    width: 100%;
    padding: var(--sp-4);
    background: var(--glass-2);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-md);
    box-shadow: inset 0 1px 0 var(--glass-top), inset 0 -1px 0 rgba(0, 0, 0, 0.45);
    color: var(--silk);
  }
  .vmx-persona-status__head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
  }
  .vmx-persona-status__title {
    font-family: var(--type-display);
    font-variation-settings: 'wdth' 85, 'wght' 600;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk-40);
  }
  .vmx-persona-status__edit {
    appearance: none;
    -webkit-appearance: none;
    border: 0;
    background: transparent;
    padding: 2px 0;
    margin: 0;
    cursor: pointer;
    font-family: var(--type-display);
    font-variation-settings: 'wdth' 85, 'wght' 600;
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--silk-22);
    transition: color var(--motion-step) ease-out;
  }
  .vmx-persona-status__edit:hover { color: var(--silk-40); }
  .vmx-persona-status__edit:focus-visible {
    color: var(--silk-40);
    outline: 2px solid var(--amber);
    outline-offset: 2px;
    border-radius: var(--rad-sm);
  }
  .vmx-persona-status__mood {
    appearance: none;
    -webkit-appearance: none;
    border: 0;
    background: transparent;
    padding: 0;
    margin: 0;
    text-align: left;
    cursor: pointer;
    align-self: flex-start;
    font-family: var(--type-display);
    font-variation-settings: 'wdth' 85, 'wght' 700;
    font-size: 22px;
    line-height: 1;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--silk);
    transition: text-shadow var(--motion-step) ease-out;
  }
  /* Hover/focus light the headline amber — the "tappable, this is a live
   * control" cue. Transient single-element glow, not a persistent second
   * amber, so the One-Amber Rule holds. */
  .vmx-persona-status__mood:hover { text-shadow: 0 0 8px var(--amber-22); }
  .vmx-persona-status__mood:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 3px;
    border-radius: var(--rad-sm);
  }
  .vmx-persona-status__caption {
    font-family: var(--type-body);
    font-variation-settings: 'wdth' 100, 'wght' 400;
    font-size: 11px;
    line-height: 1.35;
    letter-spacing: 0.02em;
    color: var(--silk-40);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    transition: color var(--motion-step) ease-out;
  }
  .vmx-persona-status__meta {
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.08em;
    color: var(--silk-40);
  }
  @media (max-width: 1100px) {
    .vmx-session__grid {
      grid-template-columns: 1fr;
    }
  }
`;

registerStyle("vmx-session", LAYOUT_CSS);

/** Build and mount the full live-session DOM tree. Returns a handle the
 *  renderer can use for hot updates. */
export function mountSessionLayout(rootEl: HTMLElement, initial?: SessionState): Mounted {
  const state = initial ?? defaultState();

  const root = document.createElement("div");
  root.className = "vmx-session";

  // v5 animated border — first child of the session glass panel.
  // tokens.css `.border-anim` handles the conic-gradient + mask-composite.
  // Parent already satisfies position: relative + overflow: hidden.
  const borderAnim = document.createElement("div");
  borderAnim.className = "border-anim";
  borderAnim.setAttribute("aria-hidden", "true");
  root.append(borderAnim);

  // Corner screws — pure ornament per UI-SPEC §Panel screws (recolored to --silk-22).
  for (const corner of ["tl", "tr", "bl", "br"] as const) {
    const sc = document.createElement("span");
    sc.className = "vmx-session__screw";
    sc.dataset.corner = corner;
    sc.innerHTML = SCREW_SVG;
    sc.setAttribute("aria-hidden", "true");
    root.append(sc);
  }

  // Titlebar — gear button opens the Settings drawer (mounted by the
  // session router on boot). Dynamic import keeps Phase 11 wizard mode
  // from pulling the settings bundle.
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

  // Main grid
  const grid = document.createElement("div");
  grid.className = "vmx-session__grid";

  // Left column — a slim status rail, NOT a control panel. The 2026-05-25
  // rebuild evicted the live deck's persona/output config (skill, mood,
  // voice, genre, output device, HP/SPK) into the settings drawer, which
  // already hosted duplicates of all of them. What a DJ needs mid-set is a
  // glance, not a form: who's in my ear, and is audio flowing. So the rail
  // carries one read-only persona readout (click → settings) plus the live
  // meters. This is the "one CDJ unit, mostly void — not a grid of widgets"
  // contract from DESIGN.md, finally honored on the busiest surface.
  const leftCol = document.createElement("section");
  leftCol.className = "vmx-session__col";
  leftCol.dataset.col = "left";

  const personaStatus = buildPersonaStatus(state);
  leftCol.append(personaStatus);

  // Meter strip
  const meterMusic = renderMeter({ label: "music" });
  const meterVoice = renderMeter({ label: "voice" });
  const meterMic = renderMeter({ label: "mic" });
  const meterStrip = document.createElement("div");
  meterStrip.className = "vmx-session__meter-strip";
  meterStrip.append(meterMusic, meterVoice, meterMic);
  const meterPanel = renderPanel({
    header: "AUDIO IN",
    badge: "MASTER",
    spec: "16-BIT · 48K",
    children: meterStrip,
  });
  leftCol.append(meterPanel);

  grid.append(leftCol);

  // Center column
  const centerCol = document.createElement("section");
  centerCol.className = "vmx-session__col";
  centerCol.dataset.col = "center";
  const timecode = renderTimecode(state.timecode);
  centerCol.append(timecode);
  const phaseTape = renderPhaseTape(state.phase);
  centerCol.append(phaseTape);
  const dropSlot = document.createElement("div");
  dropSlot.className = "vmx-session__drop-slot";
  const initialDrop = renderDropChip(state.drop);
  if (initialDrop) dropSlot.append(initialDrop);
  centerCol.append(dropSlot);
  const eventRibbon = renderEventRibbon({ events: state.events });
  centerCol.append(eventRibbon);
  grid.append(centerCol);

  // Right column
  const rightCol = document.createElement("section");
  rightCol.className = "vmx-session__col";
  rightCol.dataset.col = "right";
  // bannerSlot retained as an empty mount point so the layout grid stays
  // stable. The previous muted-banner mount stacked a 3rd fault-tinted
  // alarm signal alongside the cohost inline pill and the statusbar muted
  // strip; critique 2026-05-14 pass 2 collapsed mute to a single breathing
  // indicator (the cohost pill, where the eye already is). The banner
  // renderer stays in the codebase for future re-use, but mounting is
  // gated off here.
  const bannerSlot = document.createElement("div");
  bannerSlot.className = "vmx-session__banner-slot";
  rightCol.append(bannerSlot);
  // Wave 6 — pass muted + grounding-failure props through. The cohost
  // owns the visual surfaces (MUTED pill, retry button); layout owns
  // the timing source (Mounted.groundedFalseSinceMs).
  const cohost = renderCohostPanel({
    ...state.cohost,
    muted: state.status.muted,
    failureElapsedMs: null,
    onRetry: state.cohost.onRetry,
    onOpenAllReactions: state.cohost.onOpenAllReactions,
  });
  rightCol.append(cohost);
  grid.append(rightCol);

  root.append(grid);

  // Status bar
  const statusBar = renderStatusBar({
    livekit: state.status.livekit,
    gemini: state.status.gemini,
    midi: state.status.midi,
    screen: state.status.screen,
    muted: state.status.muted,
    hotkey: state.status.hotkey,
    errors: state.status.errors,
  });
  root.append(statusBar);

  rootEl.replaceChildren(root);

  // Apply initial meter levels via the same hot-path used by frame updates.
  setMeterLevels(meterMusic, state.meters.music);
  setMeterLevels(meterVoice, state.meters.voice);
  setMeterLevels(meterMic, state.meters.mic);

  const mounted: Mounted = {
    root,
    titlebar,
    personaStatus,
    meters: { music: meterMusic, voice: meterVoice, mic: meterMic },
    timecode,
    phaseTape,
    dropSlot,
    eventRibbon,
    cohost,
    statusBar,
    bannerSlot,
    current: state,
    userScrolledUp: false,
    // Initialize: if cohost boots already grounded=false, start the timer
    // immediately so the failure copy appears at t+5s rather than t+10s.
    groundedFalseSinceMs: state.cohost.grounded ? null : Date.now(),
  };

  // Wire transcript scroll listener — UI-SPEC §sticky-bottom: a user
  // who scrolls more than `SCROLL_THRESHOLD_PX` from the bottom flips
  // userScrolledUp=true and we stop auto-scrolling. Scrolling back into
  // the bottom band resets the flag. The hot-path render path reads
  // `mounted.userScrolledUp` to decide whether to call `setCohost`
  // (which respects `data-sticky`).
  const transcriptEl =
    cohost.querySelector<HTMLElement>(".vmx-cohost__transcript");
  if (transcriptEl) {
    transcriptEl.addEventListener(
      "scroll",
      () => {
        const distFromBottom =
          transcriptEl.scrollHeight -
          (transcriptEl.scrollTop + transcriptEl.clientHeight);
        const isUp = distFromBottom > SCROLL_THRESHOLD_PX;
        if (isUp !== mounted.userScrolledUp) {
          mounted.userScrolledUp = isUp;
          // Mirror the flag onto the data-sticky attr that cohost.setCohost
          // reads. true=auto-scroll on next render, false=preserve position.
          transcriptEl.dataset.sticky = isUp ? "false" : "true";
        }
      },
      { passive: true },
    );
  }

  return mounted;
}

/** Distance from the bottom (in px) below which the transcript stays
 *  "sticky" — auto-scroll on new lines. Above the threshold the user
 *  has scrolled up; preserve position. Plan §1 — 40px. */
const SCROLL_THRESHOLD_PX = 40;

/** Voice profile abstraction (2026-05-19 critique round 4).
 *  The persona panel surfaces 3 profiles (CALM / WARM / GRUFF) while
 *  the IPC payload + state.persona.voice still carries the Gemini
 *  codename. This mapping is the only place the abstraction lives;
 *  the settings drawer Power panel can override to a specific
 *  codename if a power user wants the underlying name.
 *
 *  Default codename per profile (tuned for the AI co-host voice
 *  feel, not for technical fidelity):
 *    CALM  → kore   (calm + warm character)
 *    WARM  → aoede  (smooth + melodic character)
 *    GRUFF → fenrir (rough + edged character) */
const VOICE_PROFILE_TO_CODE: Readonly<Record<string, string>> = {
  CALM: "kore",
  WARM: "aoede",
  GRUFF: "fenrir",
};
const VOICE_CODE_TO_PROFILE: Readonly<Record<string, string>> = {
  // Each codename rolls up into the closest profile so a Power-user
  // who picks "puck" in the drawer still sees the live picker land
  // on its nearest profile rather than failing to render.
  kore: "CALM", leda: "CALM", orus: "CALM", zephyr: "CALM",
  aoede: "WARM", puck: "WARM",
  fenrir: "GRUFF", charon: "GRUFF",
};
function voiceCodeToProfile(code: string): string {
  return VOICE_CODE_TO_PROFILE[code] ?? "CALM";
}
export function voiceProfileToCode(profile: string): string {
  return VOICE_PROFILE_TO_CODE[profile] ?? "kore";
}

/** Map the active mood to a 1-line DJ-vocabulary caption.
 *  Round 3 critique lift (H6): users shouldn't have to remember what
 *  HYPE / TEACH / COACH each do. The caption renders under the rocker
 *  whenever the persona-panel body is rebuilt.
 *
 *  Round 5 ("unique fun young") rewrite: verb-led, no telemetry suffix.
 *  The caption is the cohost's behavioral signature — not a menu
 *  description. "talks over the build" reads like a teammate, the
 *  prior "talking over the build · party energy" read like a config
 *  preview. */
function moodCaptionFor(mood: string): string {
  switch (mood) {
    case "HYPE":
      return "talks over the build";
    case "TEACH":
      return "spots what worked";
    case "COACH":
      return "waits for the mix-out";
    default:
      return "";
  }
}

/** Mood-tinted silk for the caption. Round 5 ("unique fun young"):
 *  silk-40 was uniform across all three moods, so the polychrome
 *  contract on the rocker had no echo below. Each mood biases the
 *  caption color toward its own hue: 70% silk + 30% mood at ~0.55
 *  alpha. Still reads as "muted descriptive text", just tinted, so
 *  the persona block feels alive without breaking the One Amber Rule. */
function moodCaptionColor(mood: string): string {
  switch (mood) {
    case "HYPE":
      // silk(214,207,199)·0.7 + magenta(255,45,143)·0.3 at 0.55
      return "rgba(226, 158, 182, 0.55)";
    case "TEACH":
      // silk·0.7 + green(109,212,74)·0.3 at 0.55
      return "rgba(182, 209, 161, 0.55)";
    case "COACH":
      // silk·0.7 + blue(72,152,255)·0.3 at 0.55
      return "rgba(171, 191, 216, 0.55)";
    default:
      return "var(--silk-40)";
  }
}

/** Build the glanceable, read-only persona readout for the left rail.
 *  The 2026-05-25 rebuild evicted the deck's PERSONA + OUTPUT control
 *  panels (skill/mood/voice/genre/device/HP-SPK) into the settings drawer,
 *  which already hosted duplicates of every one of them. Mid-set a DJ wants
 *  a glance — who's in my ear — not a form, so the deck shows the mood as a
 *  headline, its 1-line behavioral caption, and a skill·genre·voice meta
 *  line; clicking anywhere opens the drawer (the sole persona write
 *  surface). This is DESIGN.md's "one CDJ unit, mostly void" finally
 *  honored on the busiest surface. */
function buildPersonaStatus(state: SessionState): HTMLElement {
  const el = document.createElement("div");
  el.className = "vmx-persona-status";
  el.setAttribute("role", "group");
  el.setAttribute("aria-label", "persona");

  const head = document.createElement("span");
  head.className = "vmx-persona-status__head";
  const title = document.createElement("span");
  title.className = "vmx-persona-status__title";
  title.textContent = "PERSONA";
  // EDIT ▸ opens the settings drawer — the full persona/output write
  // surface. Dynamic import keeps the wizard bundle from pulling settings
  // (mirrors the titlebar gear button).
  const edit = document.createElement("button");
  edit.type = "button";
  edit.className = "vmx-persona-status__edit";
  edit.textContent = "EDIT ▸";
  edit.setAttribute("aria-label", "open settings to change persona");
  edit.addEventListener("click", () => {
    void import("../settings/SettingsDrawer.js").then((m) => m.openSettings());
  });
  head.append(title, edit);
  el.append(head);

  // Mood headline is a tap-to-cycle control (P1) — HYPE → TEACH → COACH.
  // The handler is wired by the render-loop to the real settings.set mood
  // IPC; the readout then reflects the echoed value on the next frame.
  const mood = document.createElement("button");
  mood.type = "button";
  mood.className = "vmx-persona-status__mood";
  mood.addEventListener("click", () => {
    state.persona.onCycleMood?.();
  });
  el.append(mood);

  const caption = document.createElement("span");
  caption.className = "vmx-persona-status__caption";
  el.append(caption);

  const meta = document.createElement("span");
  meta.className = "vmx-persona-status__meta";
  el.append(meta);

  setPersonaStatus(el, state);
  return el;
}

/** Idempotent update of the persona readout. Called on mount and whenever
 *  the render loop sees a persona field change. Writes textContent + the
 *  mood data-attr / caption tint only — no DOM rebuild. */
export function setPersonaStatus(el: HTMLElement, state: SessionState): void {
  const { mood, skill, genre, voice } = state.persona;
  const voiceProfile = voiceCodeToProfile(voice);

  const moodEl = el.querySelector<HTMLElement>(".vmx-persona-status__mood");
  if (moodEl) {
    if (moodEl.textContent !== mood) {
      moodEl.textContent = mood;
      // Delight (2026-05-26 /impeccable delight): the newly-chosen mood
      // settles into place, rewarding the in-deck tap control. One-shot.
      playMoodSettle(moodEl);
    }
    moodEl.dataset.mood = mood;
    // The mood headline is a tap-to-cycle control — announce the action
    // and the cycle so it isn't read as a static label.
    moodEl.setAttribute(
      "aria-label",
      `co-host mood: ${mood}. tap to cycle hype, teach, coach.`,
    );
  }

  const captionEl = el.querySelector<HTMLElement>(
    ".vmx-persona-status__caption",
  );
  if (captionEl) {
    const text = moodCaptionFor(mood);
    if (captionEl.textContent !== text) captionEl.textContent = text;
    captionEl.style.color = moodCaptionColor(mood);
  }

  const metaEl = el.querySelector<HTMLElement>(".vmx-persona-status__meta");
  const metaText = `${skill} · ${genre} · ${voiceProfile}`;
  if (metaEl && metaEl.textContent !== metaText) metaEl.textContent = metaText;

  el.setAttribute(
    "aria-label",
    `Persona: ${mood}, ${skill}, ${genre}, ${voiceProfile} voice`,
  );
}

/** Delight (2026-05-26 /impeccable delight) — a one-shot settle when the
 *  mood changes, so the in-deck tap control feels acknowledged. Uses the
 *  Web Animations API so it self-cleans and never leaves residual inline
 *  styles. No-op under prefers-reduced-motion, and silently skipped where
 *  the API is unavailable (jsdom under vitest) — delight is optional and
 *  must never be fatal to a render frame. Ease-out-expo, no overshoot. */
function playMoodSettle(el: HTMLElement): void {
  try {
    if (typeof el.animate !== "function") return;
    if (
      typeof matchMedia === "function" &&
      matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      return;
    }
    el.animate(
      [
        { opacity: 0.4, transform: "translateY(-3px)" },
        { opacity: 1, transform: "translateY(0)" },
      ],
      { duration: 240, easing: "cubic-bezier(0.16, 1, 0.3, 1)" },
    );
  } catch {
    // WAAPI unavailable or threw — the mood text is already set; skip the flourish.
  }
}

/** Idempotent hot-update. Walks the diff between mounted.current and the
 *  new state, applying minimal mutations. Hot paths poke CSS custom
 *  properties on the root element — components read them via var() so
 *  the browser composites without recomputing layout. Transcript /
 *  event-ribbon / phase-tape only rebuild when their array refs change. */
export function renderSessionFrame(mounted: Mounted, next: SessionState): void {
  // === Hot path (every frame) — CSS variable pokes on the root =============
  // These are the only writes that happen at 30Hz. var() reads in the
  // component stylesheets cascade them into the relevant nodes without
  // any innerHTML / className thrash.
  const rootStyle = mounted.root.style;
  rootStyle.setProperty(
    "--meter-music-rms",
    String(clamp01(next.meters.music.rms)),
  );
  rootStyle.setProperty(
    "--meter-voice-rms",
    String(clamp01(next.meters.voice.rms)),
  );
  rootStyle.setProperty(
    "--meter-mic-rms",
    String(clamp01(next.meters.mic.rms)),
  );
  rootStyle.setProperty(
    "--phase-now-pct",
    String(clamp01(next.phase.nowPct)),
  );
  if (next.drop.bpmPeriodMs != null) {
    rootStyle.setProperty(
      "--bpm-period-ms",
      `${Math.max(1, Math.round(next.drop.bpmPeriodMs))}ms`,
    );
  }
  rootStyle.setProperty("--clock-text", JSON.stringify(next.titlebar.clock));

  // Titlebar — clock textContent + pill data-state only.
  if (mounted.current.titlebar.clock !== next.titlebar.clock) {
    setTitlebarClock(mounted.titlebar, next.titlebar.clock);
  }
  if (mounted.current.titlebar.live !== next.titlebar.live) {
    setTitlebarPill(mounted.titlebar, "live", next.titlebar.live);
  }
  if (mounted.current.titlebar.rec !== next.titlebar.rec) {
    setTitlebarPill(mounted.titlebar, "rec", next.titlebar.rec);
  }
  if (mounted.current.titlebar.sys !== next.titlebar.sys) {
    setTitlebarPill(mounted.titlebar, "sys", next.titlebar.sys);
  }

  // Meters — the LED count + peak needle are data-attribute pokes, but
  // setMeterLevels is also responsible for clamping + diffing. Every frame.
  setMeterLevels(mounted.meters.music, next.meters.music);
  setMeterLevels(mounted.meters.voice, next.meters.voice);
  setMeterLevels(mounted.meters.mic, next.meters.mic);

  // Timecode — DSEG7 hero clock + meta cells. setTimecode internally
  // diffs textContent so unchanged digits don't repaint.
  setTimecode(mounted.timecode, next.timecode);

  // Persona readout — glanceable mirror of the drawer's persona writes.
  // Cheap textContent pokes, gated on the four fields the readout shows so
  // an unchanged 30Hz tick is a no-op.
  const pPrev = mounted.current.persona;
  const pNext = next.persona;
  if (
    pPrev.mood !== pNext.mood ||
    pPrev.skill !== pNext.skill ||
    pPrev.genre !== pNext.genre ||
    pPrev.voice !== pNext.voice
  ) {
    setPersonaStatus(mounted.personaStatus, next);
  }

  // === Rebuild-on-ref-change paths ========================================
  // These bodies are heavier (DOM rebuild) so we gate them on array ref
  // identity (===) — the bridge only allocates a new array when the
  // underlying state actually changed, so an unchanged 30Hz tick is a
  // no-op here.

  if (mounted.current.phase.chunks !== next.phase.chunks) {
    setPhaseTape(mounted.phaseTape, next.phase);
  }

  // Drop chip — mount/unmount based on bars.
  const dropChanged =
    mounted.current.drop.bars !== next.drop.bars ||
    mounted.current.drop.bpmPeriodMs !== next.drop.bpmPeriodMs;
  if (dropChanged) {
    mounted.dropSlot.replaceChildren();
    const chip = renderDropChip(next.drop);
    if (chip) mounted.dropSlot.append(chip);
  }

  // Event ribbon — array-ref check; only rebuild when state.midiEvents
  // actually changed (append-helper returns a new array on append).
  if (mounted.current.events !== next.events) {
    setEventRibbon(mounted.eventRibbon, { events: next.events });
  }

  // Wave 6 (H9) — track grounded=false dwell time. Transitions reset the
  // timer; the elapsed delta is passed to the cohost which flips to the
  // failure surface once it crosses GROUNDING_FAILURE_MS (5s).
  if (mounted.current.cohost.grounded !== next.cohost.grounded) {
    mounted.groundedFalseSinceMs = next.cohost.grounded ? null : Date.now();
  }
  const failureElapsedMs =
    mounted.groundedFalseSinceMs != null
      ? Date.now() - mounted.groundedFalseSinceMs
      : null;

  // Cohost — array-ref check on transcript; status/grounded/latency
  // mutations are cheap and rebuilt unconditionally inside setCohost.
  // muted + failureElapsedMs are also part of the diff trigger so the
  // hot-path picks up cmd+m presses and crossings of the 5s threshold.
  // Phase 44-03 / LAUNCH-02 — also diff on reactions map ref so a new
  // chip-strip arriving via ipc.session.cohost-reaction repaints the
  // transcript (the render-loop projects a fresh ReactionsByTs map
  // every tick, but the ref only changes when reactions length changes).
  const cohostTranscriptChanged =
    mounted.current.cohost.transcript !== next.cohost.transcript ||
    mounted.current.cohost.reactions !== next.cohost.reactions;
  const cohostStatusChanged =
    mounted.current.cohost.status !== next.cohost.status ||
    mounted.current.cohost.grounded !== next.cohost.grounded ||
    mounted.current.cohost.latencyMs !== next.cohost.latencyMs ||
    mounted.current.status.muted !== next.status.muted ||
    // Failure threshold crossing — recompute on every frame so the foot
    // flips exactly once at t+5s. Cheap because setCohost only mutates
    // textContent + data-attrs.
    crossesFailureThreshold(mounted, failureElapsedMs);
  if (cohostTranscriptChanged || cohostStatusChanged) {
    // Sync data-sticky onto the transcript so setCohost auto-scrolls
    // only when the user hasn't scrolled up. Plan §1 — sticky-bottom
    // unless user scrolled >40px from bottom.
    const trEl = mounted.cohost.querySelector<HTMLElement>(
      ".vmx-cohost__transcript",
    );
    if (trEl) {
      trEl.dataset.sticky = mounted.userScrolledUp ? "false" : "true";
    }
    setCohost(mounted.cohost, {
      ...next.cohost,
      muted: next.status.muted,
      failureElapsedMs,
      onRetry: next.cohost.onRetry,
    });
  }

  // Muted state: the cohost inline pill is now the sole breathing indicator
  // for mute; the banner slot stays empty (kept as a mount stub so future
  // urgent banners can land here). Critique 2026-05-14 pass 2 collapsed the
  // triple-mute stack to one signal.

  // Status bar — rebuild only if any badge state changed (cheap; bar is small)
  const sbPrev = mounted.current.status;
  const sbNext = next.status;
  const sbDirty =
    sbPrev.livekit !== sbNext.livekit ||
    sbPrev.gemini !== sbNext.gemini ||
    sbPrev.midi !== sbNext.midi ||
    sbPrev.screen !== sbNext.screen ||
    sbPrev.muted !== sbNext.muted;
  if (sbDirty) {
    const fresh = renderStatusBar({
      livekit: sbNext.livekit,
      gemini: sbNext.gemini,
      midi: sbNext.midi,
      screen: sbNext.screen,
      muted: sbNext.muted,
      hotkey: sbNext.hotkey,
      errors: sbNext.errors,
    });
    mounted.statusBar.replaceWith(fresh);
    mounted.statusBar = fresh;
  }

  mounted.current = next;
}

/** Wave 6 (H9) — detect frames where the grounding-failure elapsed delta
 *  crossed the 5s threshold in either direction since the previous frame.
 *  We can't store the prior elapsed (the render-loop doesn't expose it),
 *  so we conservatively flag whenever the current elapsed is non-null and
 *  the foot's current data-failed state disagrees with what the elapsed
 *  implies. Cheap (one DOM read + one numeric compare). */
function crossesFailureThreshold(
  mounted: Mounted,
  failureElapsedMs: number | null,
): boolean {
  const foot = mounted.cohost.querySelector<HTMLElement>(".vmx-cohost__foot");
  if (!foot) return false;
  const currentlyFailed = foot.dataset.failed === "true";
  const shouldFail =
    failureElapsedMs != null && failureElapsedMs >= GROUNDING_FAILURE_MS;
  return currentlyFailed !== shouldFail;
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
