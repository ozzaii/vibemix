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
import { renderRocker } from "./components/rocker.js";
import { renderPicker } from "./components/picker.js";
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
  type TranscriptLine,
} from "./components/cohost.js";
import { renderStatusBar, type BadgeState } from "./components/status-bar.js";
import { SCREW_SVG } from "./icons/screw.svg.js";
import { HEADPHONES_SVG } from "./icons/headphones.svg.js";

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
  };
  output: {
    device: string;
    profile: "HP" | "SPK";
  };
}

export interface Mounted {
  root: HTMLElement;
  titlebar: HTMLElement;
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
    --col-left: 320px;
    --col-center: 420px;
    --col-right: 420px;
    --gap-col: var(--sp-5);
    display: grid;
    grid-template-rows: var(--titlebar-h) 1fr var(--statusbar-h);
    height: 100vh;
    position: relative;
    overflow: hidden;
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
    grid-template-columns: var(--col-left) var(--col-center) var(--col-right);
    gap: var(--gap-col);
    padding: 32px; /* mock-verbatim — no v5 spacing equivalent for 32 */
    overflow: hidden;
    align-items: start;
  }
  .vmx-session__col {
    display: flex;
    flex-direction: column;
    gap: var(--sp-4);
    min-width: 0;
  }
  .vmx-session__col[data-col="right"] {
    height: 100%;
  }
  .vmx-session__meter-strip {
    display: flex;
    gap: var(--sp-4);
    align-items: flex-end;
    justify-content: space-around;
    padding: var(--sp-4) 0 0;
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

  // Left column
  const leftCol = document.createElement("section");
  leftCol.className = "vmx-session__col";
  leftCol.dataset.col = "left";

  const personaPanel = renderPanel({
    header: "PERSONA",
    badge: "CFG",
    spec: "GEMINI · TTS",
    children: buildPersonaPanelBody(state),
  });
  leftCol.append(personaPanel);

  const outputPanel = renderPanel({
    header: "OUTPUT",
    spec: "24-BIT · 48K",
    children: buildOutputPanelBody(state),
  });
  leftCol.append(outputPanel);

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

function buildPersonaPanelBody(state: SessionState): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "vmx-session__persona-body";
  wrap.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-md);";

  wrap.append(
    renderRocker({
      ariaLabel: "skill mode",
      options: [
        { id: "BEG", label: "BEG" },
        { id: "INT", label: "INT" },
        { id: "PRO", label: "PRO" },
      ],
      active: state.persona.skill,
      variant: "rocker",
    }),
  );

  wrap.append(
    renderRocker({
      ariaLabel: "mood",
      options: [
        { id: "HYPE", label: "HYPE" },
        { id: "TEACH", label: "TEACH" },
        { id: "COACH", label: "COACH" },
      ],
      active: state.persona.mood,
      variant: "interaction",
    }),
  );

  wrap.append(
    renderPicker({
      label: "VOICE",
      value: state.persona.voice,
      avatar: true,
      autoPill: true,
      options: [
        { id: "kore", label: "kore" },
        { id: "puck", label: "puck" },
        { id: "charon", label: "charon" },
        { id: "fenrir", label: "fenrir" },
        { id: "aoede", label: "aoede" },
        { id: "leda", label: "leda" },
        { id: "orus", label: "orus" },
        { id: "zephyr", label: "zephyr" },
      ],
    }),
  );

  wrap.append(
    renderPicker({
      label: "GENRE",
      value: state.persona.genre,
      autoPill: true,
      options: [
        { id: "house", label: "house" },
        { id: "tech-house", label: "tech-house" },
        { id: "techno", label: "techno" },
        { id: "dnb", label: "dnb" },
        { id: "trance", label: "trance" },
        { id: "hip-hop", label: "hip-hop" },
        { id: "edm-generic", label: "edm-generic" },
      ],
    }),
  );

  return wrap;
}

function buildOutputPanelBody(state: SessionState): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "vmx-session__output-body";
  wrap.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-md);";

  wrap.append(
    renderPicker({
      label: "DEVICE",
      value: state.output.device,
      iconSvg: HEADPHONES_SVG,
      autoPill: true,
      options: [], // Wave 3 (12-04) populates from ipc.settings.state
    }),
  );

  wrap.append(
    renderRocker({
      ariaLabel: "output profile",
      options: [
        { id: "HP", label: "HP" },
        { id: "SPK", label: "SPK" },
      ],
      active: state.output.profile,
      variant: "rocker",
    }),
  );

  return wrap;
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
  const cohostTranscriptChanged =
    mounted.current.cohost.transcript !== next.cohost.transcript;
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
    persona: { skill: "INT", interaction: "HYPE", mood: "HYPE", voice: "avery", genre: "techno" },
    output: { device: "MacBook Pro Speakers", profile: "HP" },
  };
}
