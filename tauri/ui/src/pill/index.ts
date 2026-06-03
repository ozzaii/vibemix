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
 * only sends grounded live actions: choosing a rendered backup transition and
 * labeling the visible suggestion.
 */

import { renderCitationStrip, type CitationChip } from "../session/components/citation-strip.js";
import { renderDeckChips, type DeckStateWire } from "./deck-chips.js";
import {
  nextSuggestionRenderKey,
  nextMoveGrade,
  nextMoveGradeProgress,
  nextSuggestionPrimaryActionAriaLabel,
  renderNextSuggestion,
  pillXpLevel,
  type MoveGradeProgressView,
  type MoveGradeView,
  type NextAlternativeView,
  type NextSuggestionFeedbackKind,
  type NextSuggestionWire,
} from "./next-suggestion.js";
import {
  PILL_DEMO_REACTION_KEYS,
  PILL_DEMO_REACTION_TEXT,
  PILL_MOVE_GRADE_VOCABULARY,
  type PillDemoReactionKey,
} from "./move-grade-vocabulary.js";
export {
  PILL_DEMO_REACTION_KEYS,
  type PillDemoReactionKey,
} from "./move-grade-vocabulary.js";
import {
  applyFrame,
  initialPillState,
  setPeek,
  tickCollapse,
  type CohostStatus,
  type PillFrame,
  type PillState,
} from "./state-machine.js";
import { renderWaveform, setWaveform } from "./waveform.js";
import { connectMascotBus, type MascotBusClient } from "./ws-client.js";
import { vmxLog } from "../debug-log.js";
import { invoke } from "@tauri-apps/api/core";

const TAG = "[pill]";
const PILL_ROOT_ARIA_LABEL = "vibemix cohost pill";
const PILL_FEEDBACK_ECHO_MS = 1400;
const PILL_REACTION_ECHO_MS = 1800;

/**
 * Silent-baseline RMS the waveform settles to between phrases while speaking
 * (62-UI-SPEC §Waveform: "the bars settle to a flat low baseline, not zero").
 */
const WAVE_BASELINE_RMS = 0.06;

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
  // Read voice/status before the writer branch so a cohost-reaction can still
  // preserve the live TALKING waveform when that same frame carries status.
  const meters = (m.meters as Record<string, unknown> | undefined) ?? undefined;
  const metersVoice = meters?.voice as Record<string, unknown> | undefined;
  const flatVoice =
    typeof m.voice === "number" && Number.isFinite(m.voice) ? m.voice : undefined;
  const nestedVoice =
    typeof metersVoice?.rms === "number" && Number.isFinite(metersVoice.rms)
      ? (metersVoice.rms as number)
      : undefined;
  const voiceRms = flatVoice ?? nestedVoice;

  const flatPeak =
    typeof m.peak === "number" && Number.isFinite(m.peak) ? m.peak : undefined;
  const nestedPeak =
    typeof metersVoice?.peak === "number" && Number.isFinite(metersVoice.peak)
      ? (metersVoice.peak as number)
      : undefined;
  const voicePeak = flatPeak ?? nestedPeak;

  const cohostStatus = isCohostStatus(m.cohost_status) ? m.cohost_status : undefined;

  // WRITER — cohost-reaction (either the bare or the ipc-prefixed type).
  if (type === "cohost-reaction" || type === "ipc.session.cohost-reaction") {
    const source = cohostReactionPayload(m);
    const text = typeof source.text === "string" ? source.text : "";
    // WR-06: validate the per-element shape before trusting the wire — a blind
    // `as CitationChip[]` cast lets a malformed frame (`[42, null, {}]`) render
    // `[undefined @ 0:00]` slop. The pill is the trust boundary for what it
    // paints, so filter to well-formed chips (not an injection vector — all
    // chip text is rendered via textContent — but it keeps the strip honest).
    const chips = Array.isArray(source.citation_strip)
      ? (source.citation_strip as unknown[]).filter(isCitationChip)
      : [];
    return { type, text, chips, cohostStatus, voiceRms, voicePeak };
  }

  // READER — snapshot / flat live frame. Read voice defensively (LIVE-05a):
  // flat `voice` on the live frame OR nested `meters.voice.rms` on the bridged
  // snapshot. Leave undefined (→ prior value) when neither is present.
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

function cohostReactionPayload(m: Record<string, unknown>): Record<string, unknown> {
  const payload = m.payload;
  if (payload != null && typeof payload === "object" && !Array.isArray(payload)) {
    return payload as Record<string, unknown>;
  }
  return m;
}

function isCohostStatus(v: unknown): v is CohostStatus {
  return v === "IDLE" || v === "LISTENING" || v === "TALKING";
}

/**
 * Per-element shape guard for a citation chip off the wire (WR-06). The
 * renderer reads `event_id`/`verb`/`timestamp_s` directly, so a chip missing
 * any of them (or of the wrong type) would paint `[undefined @ 0:00]` slop —
 * filter those out at the trust boundary instead of a blind cast.
 */
function isCitationChip(c: unknown): c is CitationChip {
  if (c == null || typeof c !== "object") return false;
  const row = c as Record<string, unknown>;
  return (
    typeof row.event_id === "string" &&
    typeof row.verb === "string" &&
    typeof row.timestamp_s === "number" &&
    Number.isFinite(row.timestamp_s)
  );
}

/**
 * Read the 62-03 `deck_state` wire field off a raw frame, defensively
 * (`msg.deck_state ?? {}` per the wire contract — DECK-04 / `_serialize_deck_state`).
 *
 * WR-03 — latest-frame, replace-not-merge. The return distinguishes two cases:
 *   - frame OMITS `deck_state` (a bridged ipc.session.snapshot says nothing
 *     about decks) → `null` → the caller HOLDS the last flat-frame map (so an
 *     interleaved snapshot never thrashes the chips).
 *   - frame CARRIES `deck_state` (the authoritative flat 30Hz frame, which the
 *     producer ALWAYS emits) → the map verbatim, INCLUDING `{}` on a deck
 *     unload → the caller REPLACES `view.deckState` with it, so an emptied
 *     deck_state CLEARS the chips back to `decks · unknown` and a stale resolved
 *     key never lingers after a track unload.
 *
 * The deck_state is the per-deck `{title, camelot, key, bpm, confidence}` map
 * keyed by deck side; `camelot`/`key` are JSON null when unresolved (honest-null,
 * never a fabricated key — the pill passes the value through to renderDeckChips
 * verbatim). Exported for index.test.ts to keep the read deterministic + DOM-free.
 */
export function readDeckState(msg: unknown): DeckStateWire | null {
  if (msg == null || typeof msg !== "object") return null;
  const m = msg as Record<string, unknown>;
  const ds = m.deck_state;
  if (ds == null || typeof ds !== "object") return null;
  // Pass the contract-shaped map through verbatim — renderDeckChips owns the
  // honest-unknown / amber-only-when-resolved rendering. NEVER fabricated here.
  return ds as DeckStateWire;
}

/**
 * Read the `next_suggestion` wire field off a raw frame. THREE outcomes, so
 * the tri-state return is load-bearing (cf. readDeckState, where `null` doubles
 * as "hold last"; here `null` is a real value — the explicit "no suggestion"):
 *   - frame OMITS `next_suggestion` (a bridged ipc.session.snapshot says nothing
 *     about it) → `undefined` → the caller HOLDS the last suggestion.
 *   - frame carries `next_suggestion: null` (the SuggestionService has no
 *     grounded pick — honest silence) → `null` → the caller CLEARS the card.
 *   - frame carries the object → the suggestion (passed through verbatim;
 *     renderNextSuggestion owns the honest-null render, never fabricates).
 */
export function readNextSuggestion(
  msg: unknown,
): NextSuggestionWire | null | undefined {
  if (msg == null || typeof msg !== "object") return undefined;
  const m = msg as Record<string, unknown>;
  if (!("next_suggestion" in m)) return undefined; // omitted → hold last
  const ns = m.next_suggestion;
  if (ns == null || typeof ns !== "object") return null; // explicit clear
  return ns as NextSuggestionWire;
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
  gradeMount: HTMLElement;
  levelMount: HTMLElement;
  burstMount: HTMLElement;
  overdriveMount: HTMLElement;
  streakMount: HTMLElement;
  fxCanvas: HTMLCanvasElement;
  fxAnimationFrame: number | null;
  reaction: HTMLElement;
  expand: HTMLElement;
  waveMount: HTMLElement;
  waveEl: HTMLElement;
  /** The #pill-decks mount (62-04 stubbed it hidden; 62-05 un-hides + fills it). */
  decksMount: HTMLElement;
  /** Latest deck_state read off the wire (read-only meta — held on the view, not
   *  PillState). null until the first frame carrying deck_state arrives. */
  deckState: DeckStateWire | null;
  /** The #pill-next mount (created in boot, appended below #pill-decks). */
  nextMount: HTMLElement;
  /** The #pill-peek mount (collapsed-hover next-track card, Phase-1b). Floats
   *  below the collapsed row; reveals on hover via .pill[data-peek]. */
  peekMount: HTMLElement;
  /** Dev-only demo trigger pad. null in production/normal preview. */
  demoControls: HTMLElement | null;
  /** Latest next_suggestion read off the wire (read-only meta — held on the
   *  view). null = no grounded suggestion (honest silence → no card). */
  nextSuggestion: NextSuggestionWire | null;
  /** Stable completion key for a suggestion the operator already handled
   *  locally. Suppresses stale backend echoes until a new suggestion arrives. */
  handledNextKey: string;
  /** Render key for a locally handled suggestion. Covers completion-key
   *  edge cases while the backend/demo source still exposes the same card. */
  handledNextRenderKey: string;
  onPeekPrimaryAction: (() => void) | null;
  gradeStreak: PillGradeProgressState;
  feedbackEcho: PillFeedbackEcho | null;
  reactionEcho: PillReactionEcho | null;
  lastReactionEchoKey: string;
  lastGradeKey: string;
  lastNextKey: string;
  lastNextPulseKey: string;
  nextPulseRevision: number;
  /** Render-memo key for the collapsed peek card (Phase-1b). Held per-view (WR-05)
   *  so a peek rebuild only fires when the suggestion changes, not every frame. */
  lastPeekKey: string;
  /** Render-memo keys for the cheap rebuild-only-on-change guards. WR-05: held
   *  PER-VIEW (not module globals) so two pill instances — or two vitest mounts
   *  — can't leak each other's last-render key and skip a legitimate rebuild. */
  lastChipsKey: string;
  lastDeckKey: string;
  /** Memo for reaction body DOM. Without this, the rAF repaint replaces the
   *  hero reaction span every frame while expanded, which makes a live overlay
   *  feel less stable than a hardware surface. The key includes the live
   *  reaction revision so repeated identical BOMB calls still update the polite
   *  status region once per fresh event. Reset on collapse. */
  lastReactionKey: string;
  /** Alternating CSS replay key for the pill shell. Kept separate from the
   *  timestamp used for particles because fast repeat clicks can land on the
   *  same millisecond parity. */
  reactionPulseRevision: number;
  /** Resize-to-content memo (Phase-1b). `lastWindowHKey` gates re-measuring
   *  (scrollHeight forces a reflow — never per rAF frame), `lastWindowH` skips a
   *  redundant set_pill_height invoke when the target height is unchanged. */
  lastWindowHKey: string;
  lastWindowH: number;
}

const STATE_LABEL: Record<PillState["mode"], string> = {
  idle: "IDLE",
  listening: "LISTENING",
  speaking: "SPEAKING",
  // expand is reaction-open mode; pillFaceLabel maps it to COHOST.
  expand: "",
};

export function pillFaceLabel(mode: PillState["mode"], cohostStatus: CohostStatus): string {
  if (mode === "expand") return "COHOST";
  return STATE_LABEL[mode] || labelForStatus(cohostStatus);
}

export type PillReactionDensity = "normal" | "long";
export type PillReactionTone = "negative" | "mid" | "clean" | "sexy" | "bomb" | "lit_aff";

export interface PillReactionLeadParts {
  tone: PillReactionTone | null;
  prefix: string;
  lead: string;
  rest: string;
}

export interface PillReactionFxProfile {
  particleCount: number;
  ringCount: number;
  durationMs: number;
  glow: number;
}

const REACTION_LEAD_PATTERNS: Array<{ tone: PillReactionTone; re: RegExp }> = [
  { tone: "lit_aff", re: /^(\s*)(lit\s+aff)(?=$|[\s.!?:,;-])/i },
  { tone: "negative", re: /^(\s*)(neg(?:ative(?:s)?)?)(?=$|[\s.!?:,;-])/i },
  { tone: "clean", re: /^(\s*)(clean)(?=$|[\s.!?:,;-])/i },
  { tone: "sexy", re: /^(\s*)(sexy)(?=$|[\s.!?:,;-])/i },
  { tone: "bomb", re: /^(\s*)(bomb)(?=$|[\s.!?:,;-])/i },
  { tone: "mid", re: /^(\s*)(mid)(?=$|[\s.!?:,;-])/i },
];

export function pillReactionDensity(text: string): PillReactionDensity {
  return text.replace(/\s+/g, " ").trim().length > 96 ? "long" : "normal";
}

export function pillReactionDisplayText(
  text: string,
  density: PillReactionDensity = pillReactionDensity(text),
): string {
  if (density !== "long") return text;
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= 92) return clean;
  const parts = pillReactionLeadParts(clean);
  const lead = parts.lead ? `${parts.prefix}${parts.lead}` : "";
  const rest = (parts.lead ? parts.rest : clean).trimStart();
  const available = Math.max(32, 88 - lead.length - (lead ? 1 : 0));
  let body = rest.slice(0, available).trimEnd();
  const wordBreak = body.lastIndexOf(" ");
  if (wordBreak >= 36) body = body.slice(0, wordBreak).trimEnd();
  body = body.replace(/[.,;:!?]+$/, "");
  return `${lead ? `${lead} ` : ""}${body}...`;
}

export function pillReactionLeadParts(text: string): PillReactionLeadParts {
  for (const { tone, re } of REACTION_LEAD_PATTERNS) {
    const match = re.exec(text);
    if (!match) continue;
    const prefix = match[1] ?? "";
    const word = match[2] ?? "";
    const afterWord = text.slice(prefix.length + word.length);
    const punctuation = afterWord.match(/^[.!?:,;]/)?.[0] ?? "";
    const lead = `${word}${punctuation}`;
    return {
      tone,
      prefix,
      lead,
      rest: text.slice(prefix.length + lead.length),
    };
  }
  return { tone: null, prefix: "", lead: "", rest: text };
}

const EMPTY_REACTION_FX_PROFILE: PillReactionFxProfile = {
  particleCount: 0,
  ringCount: 0,
  durationMs: 0,
  glow: 0,
};

const REACTION_FX_PROFILES: Record<PillReactionTone, PillReactionFxProfile> = {
  clean: { particleCount: 10, ringCount: 1, durationMs: 560, glow: 0.44 },
  sexy: { particleCount: 24, ringCount: 1, durationMs: 720, glow: 0.78 },
  mid: { particleCount: 6, ringCount: 0, durationMs: 500, glow: 0.3 },
  bomb: { particleCount: 42, ringCount: 2, durationMs: 820, glow: 1 },
  lit_aff: { particleCount: 46, ringCount: 2, durationMs: 860, glow: 1 },
  negative: { particleCount: 18, ringCount: 1, durationMs: 620, glow: 0.68 },
};

export function pillReactionFxProfile(tone: PillReactionTone | null): PillReactionFxProfile {
  if (!tone) return { ...EMPTY_REACTION_FX_PROFILE };
  return { ...REACTION_FX_PROFILES[tone] };
}

export function pillReactionPulseSlot(reactionRevision: number): "a" | "b" {
  if (typeof reactionRevision !== "number" || !Number.isFinite(reactionRevision)) return "a";
  return Math.round(reactionRevision) % 2 === 0 ? "a" : "b";
}

export function pillDemoPadHitPulseSlot(revision: number): "a" | "b" {
  if (typeof revision !== "number" || !Number.isFinite(revision)) return "a";
  return Math.round(revision) % 2 === 0 ? "a" : "b";
}

export function pillNextPulseSlot(revision: number): "a" | "b" {
  if (typeof revision !== "number" || !Number.isFinite(revision)) return "a";
  return Math.round(revision) % 2 === 0 ? "a" : "b";
}

export function pillReactionEchoLabel(text: string): string {
  const parts = pillReactionLeadParts(text);
  if (!parts.tone || !parts.lead) return "";
  return parts.lead
    .replace(/[.!?:,;]+$/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .toUpperCase();
}

export function pillReactionEchoVisible(
  echo: PillReactionEcho | null,
  mode: PillState["mode"],
  now: number,
): boolean {
  return Boolean(echo && mode !== "expand" && mode !== "speaking" && now <= echo.until);
}

/** Repaint the DOM from the pill state. Idempotent; called from the rAF loop. */
// Collapsed-hover PEEK (Phase-1b) — live. Pointer hover opens a liquid-glass
// drawer only when a grounded next_suggestion exists. The Tauri window is
// resized down on hover via set_pill_height so the drawer is visible instead
// of being clipped by the 44px collapsed overlay shell.
const COLLAPSED_PEEK_ENABLED = true;

// Demo fallback: explicit booth-only opt-in. A real wire suggestion always wins.
// Default production behavior is honest silence: no grounded suggestion means no
// card, not a fabricated track.
const DEMO_NEXT_ENABLED = import.meta.env.VITE_VIBEMIX_DEMO_NEXT === "1";
const DEMO_NEXT_SUGGESTION: NextSuggestionWire = {
  track_id: "demo:velvet-pressure",
  title: "Velvet Pressure",
  artist: "Mira Vale",
  similarity: 0.8817,
  why: "same late-night pulse",
  camelot: "9A",
  bpm: 126,
  transition: {
    candidate_id: "demo:transition:velvet-pressure",
    target_deck: "B",
    cue_slot: "A",
    start_in_bars: 8,
    from_role: "outro",
    to_role: "intro",
    move_grade: {
      slug: "sexy",
      label: "SEXY",
      xp: 48,
      intensity: 66,
      reason: "smooth blend, clean bass handoff",
      deserved: PILL_MOVE_GRADE_VOCABULARY.sexy.deserved,
    },
  },
};

const DEMO_REACTION_SHORTCUT: Record<PillDemoReactionKey, string> = {
  clean: "1",
  sexy: "2",
  mid: "3",
  bomb: "4",
  lit_aff: "5",
  negative: "6",
};
const PILL_DEMO_STAGE_ID = "pill-demo-stage";
const PILL_DEMO_STAGE_HIT_CLASS = "pill-demo-stage__hit";
const PILL_DEMO_STAGE_HIT_MS = 860;
const PILL_DEMO_PAD_RELEASE_MS = 260;

const DEMO_DECK_STATE: DeckStateWire = {
  A: {
    title: "Velvet Pressure",
    camelot: "8A",
    key: "Am",
    bpm: 124,
    confidence: 0.96,
  },
  B: {
    title: "Night Bloom",
    camelot: "9A",
    key: "Em",
    bpm: 126,
    confidence: 0.91,
  },
};

export function pillDemoReactionFrame(key: PillDemoReactionKey): PillFrame {
  return {
    type: "cohost-reaction",
    cohostStatus: "TALKING",
    voiceRms: 0.48,
    voicePeak: 0.76,
    text: PILL_DEMO_REACTION_TEXT[key],
    chips: [
      {
        event_id: `demo:${key}:128.0`,
        verb: PILL_MOVE_GRADE_VOCABULARY[key].label,
        timestamp_s: 128,
      },
    ],
  };
}

export function pillDemoReturnFrame(): PillFrame {
  return {
    cohostStatus: "IDLE",
    voiceRms: 0,
    voicePeak: null,
  };
}

export function pillDemoReactionKeyForShortcut(key: string): PillDemoReactionKey | null {
  const index = Number(key) - 1;
  if (!Number.isInteger(index) || index < 0 || index >= PILL_DEMO_REACTION_KEYS.length) {
    return null;
  }
  return PILL_DEMO_REACTION_KEYS[index] ?? null;
}

function pillDemoControlsEnabled(): boolean {
  if (!import.meta.env.DEV || !DEMO_NEXT_ENABLED) return false;
  const params = new URLSearchParams(window.location.search);
  return params.get("controls") !== "0";
}

function installPillDemoControls(
  onReaction: (key: PillDemoReactionKey) => void,
): HTMLElement | null {
  if (!pillDemoControlsEnabled()) {
    teardownPillDemoControls();
    return null;
  }
  installPillDemoStage();
  const existing = document.getElementById("pill-demo-controls");
  const controls = existing ?? document.createElement("div");
  teardownPillDemoShortcutListener();
  controls.replaceChildren();

  controls.id = "pill-demo-controls";
  controls.className = "pill-demo-controls";
  controls.setAttribute("data-no-drag", "");
  controls.setAttribute("role", "toolbar");
  controls.setAttribute("aria-label", "demo reaction triggers");
  controls.setAttribute("aria-hidden", "false");
  controls.removeAttribute("inert");

  for (const key of PILL_DEMO_REACTION_KEYS) {
    const button = document.createElement("button");
    const shortcut = DEMO_REACTION_SHORTCUT[key];
    const label = PILL_MOVE_GRADE_VOCABULARY[key].label;
    button.type = "button";
    button.textContent = label;
    button.dataset.demoTone = key;
    button.dataset.demoKey = shortcut;
    button.setAttribute("aria-pressed", "false");
    button.setAttribute(
      "aria-label",
      `trigger ${label} pill reaction, shortcut ${shortcut}`,
    );
    button.setAttribute("aria-keyshortcuts", shortcut);
    button.title = `${label} (${shortcut})`;
    button.addEventListener("pointerenter", () => {
      syncPillDemoControlsHover(controls, key, button);
    });
    button.addEventListener("pointermove", (ev) => {
      syncPillDemoPadPointer(button, ev.clientX, ev.clientY);
    });
    button.addEventListener("pointerleave", () => {
      resetPillDemoPadPointer(button);
      syncPillDemoControlsHover(controls, null);
    });
    button.addEventListener("focus", () => {
      syncPillDemoControlsHover(controls, key, button);
    });
    button.addEventListener("blur", () => {
      resetPillDemoPadPointer(button);
      syncPillDemoControlsHover(controls, null);
    });
    button.addEventListener("click", () => {
      syncPillDemoControlsActive(controls, key);
      onReaction(key);
    });
    controls.append(button);
  }

  const onKeyDown = (ev: KeyboardEvent): void => {
    pillDemoControlsHandleShortcutKey(controls, ev);
  };
  document.addEventListener("keydown", onKeyDown);
  pillDemoRuntime().cleanup = () => {
    document.removeEventListener("keydown", onKeyDown);
  };

  if (!existing) document.body.append(controls);
  return controls;
}

function installPillDemoStage(): void {
  const existing = document.getElementById(PILL_DEMO_STAGE_ID);
  if (existing) return;
  const stage = document.createElement("div");
  stage.id = PILL_DEMO_STAGE_ID;
  stage.className = "pill-demo-stage";
  stage.setAttribute("aria-hidden", "true");
  document.body.prepend(stage);
}

function teardownPillDemoControls(): void {
  teardownPillDemoShortcutListener();
  document.getElementById("pill-demo-controls")?.remove();
  document.getElementById(PILL_DEMO_STAGE_ID)?.remove();
}

function teardownPillDemoShortcutListener(): void {
  const runtime = pillDemoRuntime();
  runtime.cleanup?.();
  delete runtime.cleanup;
}

function pillDemoRuntime(): { cleanup?: () => void } {
  const w = window as Window & { __vmxPillDemo?: { cleanup?: () => void } };
  w.__vmxPillDemo ??= {};
  return w.__vmxPillDemo;
}

export function syncPillDemoControlsActive(
  controls: HTMLElement,
  activeKey: PillDemoReactionKey | null,
): void {
  if (activeKey) controls.dataset.activeTone = activeKey;
  else {
    delete controls.dataset.activeTone;
    delete controls.dataset.hitPulseRevision;
  }
  const hitPulseRevision = activeKey ? pillDemoControlsNextHitPulseRevision(controls) : 0;
  let releasePulseRevision = 0;
  let activeButton: HTMLButtonElement | null = null;
  controls.querySelectorAll<HTMLButtonElement>("button[data-demo-tone]").forEach((button) => {
    const wasActive = button.getAttribute("aria-pressed") === "true";
    const active = activeKey !== null && button.dataset.demoTone === activeKey;
    button.setAttribute("aria-pressed", active ? "true" : "false");
    if (active) {
      button.dataset.hitPulse = pillDemoPadHitPulseSlot(hitPulseRevision);
      delete button.dataset.releasePulse;
      activeButton = button;
    } else {
      delete button.dataset.hitPulse;
      if (wasActive) {
        releasePulseRevision ||= pillDemoControlsNextReleasePulseRevision(controls);
        syncPillDemoPadReleasePulse(button, releasePulseRevision);
      }
    }
  });
  if (activeKey) {
    syncPillDemoStageActive(activeKey, activeButton);
    return;
  }
  const hoverKey = pillDemoReactionKeyFromDataset(controls.dataset.hoverTone);
  if (hoverKey) {
    const hoverButton = controls.querySelector<HTMLElement>(
      `button[data-demo-tone="${hoverKey}"]`,
    );
    syncPillDemoControlsHover(controls, hoverKey, hoverButton);
    return;
  }
  syncPillDemoStageActive(null);
}

function pillDemoControlsNextHitPulseRevision(controls: HTMLElement): number {
  const previous = Number(controls.dataset.hitPulseRevision ?? 0);
  const next = Number.isFinite(previous) ? previous + 1 : 1;
  controls.dataset.hitPulseRevision = String(next);
  return next;
}

function pillDemoControlsNextReleasePulseRevision(controls: HTMLElement): number {
  const previous = Number(controls.dataset.releasePulseRevision ?? 0);
  const next = Number.isFinite(previous) ? previous + 1 : 1;
  controls.dataset.releasePulseRevision = String(next);
  return next;
}

function syncPillDemoPadReleasePulse(button: HTMLElement, releasePulseRevision: number): void {
  if (pillPrefersReducedMotion()) return;
  const slot = pillDemoPadHitPulseSlot(releasePulseRevision);
  button.dataset.releasePulse = slot;
  const cleanup = (): void => {
    if (button.dataset.releasePulse === slot) delete button.dataset.releasePulse;
  };
  button.addEventListener("animationend", cleanup, { once: true });
  window.setTimeout(cleanup, PILL_DEMO_PAD_RELEASE_MS);
}

export function syncPillDemoControlsHover(
  controls: HTMLElement,
  hoverKey: PillDemoReactionKey | null,
  hoverButton: HTMLElement | null = null,
): void {
  const stage = document.getElementById(PILL_DEMO_STAGE_ID);
  if (hoverKey) {
    controls.dataset.hoverTone = hoverKey;
    if (stage) {
      stage.dataset.hoverTone = hoverKey;
      if (hoverButton) syncPillDemoStageAnchor(stage, hoverButton);
    }
    return;
  }

  delete controls.dataset.hoverTone;
  if (!stage) return;
  delete stage.dataset.hoverTone;

  const activeButton = controls.querySelector<HTMLElement>('button[aria-pressed="true"]');
  if (stage.dataset.activeTone && activeButton) {
    syncPillDemoStageAnchor(stage, activeButton);
    return;
  }
  if (!stage.dataset.activeTone) clearPillDemoStageAnchor(stage);
}

function pillDemoReactionKeyFromDataset(value: string | undefined): PillDemoReactionKey | null {
  if (!value) return null;
  return PILL_DEMO_REACTION_KEYS.includes(value as PillDemoReactionKey)
    ? (value as PillDemoReactionKey)
    : null;
}

function syncPillDemoStageActive(
  activeKey: PillDemoReactionKey | null,
  activeButton: HTMLElement | null = null,
): void {
  const stage = document.getElementById(PILL_DEMO_STAGE_ID);
  if (!stage) return;
  if (activeKey) {
    stage.dataset.activeTone = activeKey;
    if (activeButton) {
      syncPillDemoStageAnchor(stage, activeButton);
      syncPillDemoStageImpulse(stage, activeKey);
    }
    return;
  }
  delete stage.dataset.activeTone;
  clearPillDemoStageAnchor(stage);
}

function syncPillDemoStageAnchor(stage: HTMLElement, anchor: HTMLElement): void {
  const rect = anchor.getBoundingClientRect();
  const viewportWidth =
    window.innerWidth || document.documentElement.clientWidth || document.body.clientWidth || 1;
  const viewportHeight =
    window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight || 1;
  const centerX = clamp01((rect.left + rect.width / 2) / Math.max(1, viewportWidth));
  const centerY = clamp01((rect.top + rect.height / 2) / Math.max(1, viewportHeight));
  stage.style.setProperty("--stage-pad-x", `${(centerX * 100).toFixed(2)}%`);
  stage.style.setProperty("--stage-pad-y", `${(centerY * 100).toFixed(2)}%`);
}

function clearPillDemoStageAnchor(stage: HTMLElement): void {
  stage.style.removeProperty("--stage-pad-x");
  stage.style.removeProperty("--stage-pad-y");
  clearPillDemoStageImpulses(stage);
}

function syncPillDemoStageImpulse(stage: HTMLElement, activeKey: PillDemoReactionKey): void {
  clearPillDemoStageImpulses(stage);
  if (pillPrefersReducedMotion()) return;
  const hit = document.createElement("span");
  hit.className = PILL_DEMO_STAGE_HIT_CLASS;
  hit.dataset.tone = activeKey;
  hit.setAttribute("aria-hidden", "true");
  const cleanup = (): void => {
    hit.remove();
  };
  hit.addEventListener("animationend", cleanup, { once: true });
  window.setTimeout(cleanup, PILL_DEMO_STAGE_HIT_MS);
  stage.append(hit);
}

function clearPillDemoStageImpulses(stage: HTMLElement): void {
  stage.querySelectorAll(`.${PILL_DEMO_STAGE_HIT_CLASS}`).forEach((hit) => hit.remove());
}

export function syncPillDemoStageFeedback(feedback: PillFeedbackEcho | null): void {
  const stage = document.getElementById(PILL_DEMO_STAGE_ID);
  if (!stage) return;
  if (feedback) {
    stage.dataset.feedback = feedback.kind;
    stage.dataset.feedbackCare = feedback.care ? "true" : "false";
  } else {
    delete stage.dataset.feedback;
    delete stage.dataset.feedbackCare;
  }
}

export function syncPillDemoPadPointer(button: HTMLElement, clientX: number, clientY: number): void {
  const rect = button.getBoundingClientRect();
  const width = Math.max(1, rect.width);
  const height = Math.max(1, rect.height);
  const x = clamp01((clientX - rect.left) / width);
  const y = clamp01((clientY - rect.top) / height);
  button.style.setProperty("--pad-x", `${formatPillDemoPadPercent(x)}%`);
  button.style.setProperty("--pad-y", `${formatPillDemoPadPercent(y)}%`);
  button.style.setProperty("--pad-tilt-x", String(roundPillDemoPadValue((x - 0.5) * 7)));
  button.style.setProperty("--pad-tilt-y", String(roundPillDemoPadValue((y - 0.5) * 5)));
}

export function syncPillDemoShortcutPadAim(
  controls: HTMLElement,
  key: PillDemoReactionKey,
): boolean {
  const button = controls.querySelector<HTMLElement>(`button[data-demo-tone="${key}"]`);
  if (!button) return false;
  const rect = button.getBoundingClientRect();
  syncPillDemoPadPointer(button, rect.left + rect.width / 2, rect.top + rect.height / 2);
  return true;
}

export function pillDemoControlsHandleShortcutKey(
  controls: HTMLElement,
  ev: KeyboardEvent,
): boolean {
  if (ev.metaKey || ev.ctrlKey || ev.altKey || ev.shiftKey) return false;
  if (!pillDemoShortcutTargetCanHandle(ev.target)) return false;
  if (!pillDemoControlsCanHandleShortcut(controls)) return false;
  const key = pillDemoReactionKeyForShortcut(ev.key);
  if (!key) return false;
  const button = controls.querySelector<HTMLButtonElement>(`button[data-demo-tone="${key}"]`);
  if (!button) return false;
  ev.preventDefault();
  syncPillDemoShortcutPadAim(controls, key);
  button.click();
  return true;
}

export function resetPillDemoPadPointer(button: HTMLElement): void {
  button.style.removeProperty("--pad-x");
  button.style.removeProperty("--pad-y");
  button.style.removeProperty("--pad-tilt-x");
  button.style.removeProperty("--pad-tilt-y");
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0.5;
  return Math.min(1, Math.max(0, value));
}

function formatPillDemoPadPercent(value: number): string {
  return String(roundPillDemoPadValue(value * 100));
}

function roundPillDemoPadValue(value: number): number {
  return Math.round(value * 100) / 100;
}

export function pillDemoControlsShouldBeFocusable(
  _mode: PillState["mode"],
  _narrowViewport: boolean,
): boolean {
  return true;
}

export function pillDemoControlsCanHandleShortcut(controls: HTMLElement): boolean {
  return !controls.hasAttribute("inert") && controls.getAttribute("aria-hidden") !== "true";
}

export function pillDemoShortcutTargetCanHandle(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return true;
  if (target.isContentEditable) return false;
  for (let node: HTMLElement | null = target; node; node = node.parentElement) {
    const propertyMode = typeof node.contentEditable === "string" ? node.contentEditable : null;
    const contentEditable =
      node.getAttribute("contenteditable") ??
      (propertyMode !== null && propertyMode !== "inherit" ? propertyMode : null);
    if (contentEditable === null) continue;
    if (contentEditable.trim().toLowerCase() !== "false") return false;
  }
  const tag = target.tagName.toLowerCase();
  return tag !== "input" && tag !== "textarea" && tag !== "select";
}

// Resize-to-content (Phase-1b): the pill window ships fixed at 280×44; the
// expand panel grows via CSS BELOW the collapsed row and would clip against the
// 44px shell. On expand we grow the window down to fit (set_pill_height), back
// to 44 on collapse — so the reaction + grounded receipts never clip. These
// mirror pill_window.rs (PILL_COLLAPSED_H / PILL_MAX_H) and pill.css (the
// .pill__expand max-height cap). The hover peek uses the same resize path so
// the liquid-glass drawer can unfold below the lozenge in the real overlay.
const PILL_COLLAPSED_H = 44;
const PILL_EXPAND_CAP = 248; // matches .pill[data-state="expand"] .pill__expand max-height
const PILL_PEEK_CAP = 150; // matches .pill[data-peek="true"] .pill__peek max-height

export interface PillGradeProgressState extends MoveGradeProgressView {
  key: string;
  slug: string;
  xp: number;
}

export interface PillFeedbackEcho {
  kind: NextSuggestionFeedbackKind;
  label: string;
  suggestionKey: string;
  completionKey?: string;
  grade?: MoveGradeView | null;
  progress?: PillGradeProgressState | null;
  care: boolean;
  until: number;
}

export interface PillReactionEcho {
  label: string;
  tone: PillReactionTone;
  key: string;
  until: number;
}

export type PillIntelState =
  | "idle"
  | "listening"
  | "speaking"
  | "reaction"
  | "knows"
  | "care"
  | "earned"
  | "overdrive"
  | "feedback";

export type PillBurstMode = "none" | "level_up" | "overdrive";

export interface PillBurstProfile {
  mode: PillBurstMode;
  shardCount: number;
  ringCount: number;
}

function boundedContentHeight(value: number, cap: number): number {
  if (!Number.isFinite(value) || value <= 0) return 0;
  return Math.min(value, cap);
}

export function pillWindowHeightForContent(
  mode: PillState["mode"],
  peekOpen: boolean,
  expandScrollHeight: number,
  peekScrollHeight: number,
): number {
  if (mode === "expand") {
    return PILL_COLLAPSED_H + boundedContentHeight(expandScrollHeight, PILL_EXPAND_CAP);
  }
  if (peekOpen) {
    return PILL_COLLAPSED_H + boundedContentHeight(peekScrollHeight, PILL_PEEK_CAP);
  }
  return PILL_COLLAPSED_H;
}

export interface PillWindowHeightRenderKeyInput {
  mode: PillState["mode"];
  peekOpen: boolean;
  chipsKey: string;
  deckKey: string;
  peekKey: string;
  nextKey: string;
  reactionText: string;
}

export function pillWindowHeightRenderKey(input: PillWindowHeightRenderKeyInput): string {
  return JSON.stringify([
    input.mode,
    input.peekOpen ? "peek" : "no-peek",
    input.chipsKey,
    input.deckKey,
    input.peekKey,
    input.nextKey,
    input.mode === "expand" ? input.reactionText : "",
  ]);
}

export function pillOpenState(mode: PillState["mode"], peekOpen: boolean): boolean {
  return mode === "expand" || peekOpen;
}

export function pillHoverCanOpen(mode: PillState["mode"]): boolean {
  return mode !== "expand" && mode !== "speaking";
}

export function pillPeekCloseKey(key: string): boolean {
  return key === "Escape" || key === "Esc";
}

export function pillPeekHandleCloseKey(peek: boolean, ev: KeyboardEvent): boolean {
  if (!peek || !pillPeekCloseKey(ev.key)) return false;
  ev.preventDefault();
  ev.stopPropagation();
  return true;
}

export function pillPeekPrimaryActionKey(key: string): boolean {
  return key === "Enter" || key === " ";
}

export function pillPeekHandlePrimaryActionKey(
  root: HTMLElement,
  peek: boolean,
  hasSuggestion: boolean,
  ev: KeyboardEvent,
): boolean {
  if (ev.target !== root || !peek || !hasSuggestion || !pillPeekPrimaryActionKey(ev.key)) {
    return false;
  }
  ev.preventDefault();
  ev.stopPropagation();
  return true;
}

export function pillPeekHandlePrimaryActionClick(
  root: HTMLElement,
  peek: boolean,
  hasSuggestion: boolean,
  ev: MouseEvent,
): boolean {
  if (!peek || !hasSuggestion || ev.button !== 0) return false;
  const target = ev.target instanceof Element ? ev.target : null;
  if (!target || !root.contains(target)) return false;
  if (
    target.closest(
      [
        ".pill__drag",
        ".pill__expand",
        ".pill__peek",
        "[data-no-drag]",
        "button",
        "a",
        "input",
        "select",
        "textarea",
        "[contenteditable='true']",
      ].join(","),
    )
  ) {
    return false;
  }
  if (target !== root && !target.closest(".pill__row, .pill__notch, .pill__streak")) {
    return false;
  }
  ev.preventDefault();
  ev.stopPropagation();
  return true;
}

export function pillShouldExposePeekFocus(peekVisible: boolean, hasNext: boolean): boolean {
  return peekVisible && hasNext;
}

export function pillRootPrimaryActionAvailable(
  peekVisible: boolean,
  hasNext: boolean,
  feedback: PillFeedbackEcho | null,
): boolean {
  return !feedback && pillShouldExposePeekFocus(peekVisible, hasNext);
}

export function syncPillRootActionability(root: HTMLElement, available: boolean): void {
  root.dataset.actionable = available ? "true" : "false";
  if (available) {
    root.setAttribute("aria-keyshortcuts", "Enter Space");
    root.setAttribute("aria-controls", "pill-peek");
    root.setAttribute("aria-expanded", "true");
  } else {
    root.removeAttribute("aria-keyshortcuts");
    root.removeAttribute("aria-controls");
    root.removeAttribute("aria-expanded");
  }
}

export function pillShouldExposeNextChrome(mode: PillState["mode"]): boolean {
  return mode !== "expand";
}

export function pillShouldShowFaceWave(
  mode: PillState["mode"],
  cohostStatus: string | null,
): boolean {
  return mode !== "expand" || cohostStatus === "TALKING";
}

export function pillShouldSuppressNextFocusPeek(
  root: HTMLElement,
  active: Element | null,
): boolean {
  return active !== null && active !== root && root.contains(active);
}

export function pillShouldReturnFocusToRootAfterSuggestionSurfaceRemoval(
  active: Element | null,
  root: HTMLElement,
  mounts: HTMLElement[],
): boolean {
  if (active === null || active === root || !root.contains(active)) return false;
  return mounts.some((mount) => mount.contains(active));
}

export function pillNextCompletionKey(
  s: NextSuggestionWire | null | undefined,
): string {
  if (!hasRenderableSuggestion(s)) return "";
  const transition = s.transition;
  const decision = s.decision;
  return JSON.stringify([
    s.track_id.trim(),
    s.title.trim(),
    decision?.candidate_id ?? transition?.candidate_id ?? "",
    transition?.target_deck ?? "",
    transition?.cue_slot ?? "",
    transition?.start_in_bars ?? "",
  ]);
}

export function pillSuggestionIsHandled(
  s: NextSuggestionWire | null | undefined,
  handledCompletionKey: string,
  handledRenderKey: string,
): boolean {
  if (!hasRenderableSuggestion(s)) return false;
  const completionKey = pillNextCompletionKey(s);
  if (completionKey && completionKey === handledCompletionKey) return true;
  const renderKey = nextSuggestionRenderKey(s);
  return Boolean(renderKey && renderKey === handledRenderKey);
}

export function nextPillGradeProgress(
  prev: PillGradeProgressState,
  suggestionKey: string,
  grade: MoveGradeView | null,
): PillGradeProgressState {
  if (!grade || !suggestionKey) {
    const level = pillXpLevel(prev.totalXp);
    return {
      key: "",
      slug: "",
      streak: 0,
      xp: 0,
      totalXp: prev.totalXp,
      lastXp: 0,
      earned: false,
      heat: 0,
      levelUp: false,
      levelsGained: 0,
      ...level,
    };
  }
  if (prev.key === suggestionKey && prev.slug === grade.slug) return prev;
  const earned = grade.deserved && grade.slug !== "mid" && grade.slug !== "negative";
  const previousLevel = pillXpLevel(prev.totalXp).level;
  const streak = earned ? prev.streak + 1 : 0;
  const totalXp = earned ? prev.totalXp + grade.xp : prev.totalXp;
  const level = pillXpLevel(totalXp);
  const levelsGained = earned ? Math.max(0, level.level - previousLevel) : 0;
  return {
    key: suggestionKey,
    slug: grade.slug,
    streak,
    xp: grade.xp,
    totalXp,
    lastXp: earned ? grade.xp : 0,
    earned,
    heat: earned ? Math.min(100, Math.max(grade.intensity, streak * 18)) : 0,
    levelUp: levelsGained > 0,
    levelsGained,
    ...level,
  };
}

export const nextPillGradeStreak = nextPillGradeProgress;

export function pillMoveGradeRenderKey(
  grade: MoveGradeView | null,
  progress: PillGradeProgressState,
): string {
  return grade
    ? [
        progress.key,
        grade.slug,
        grade.label,
        grade.xp,
        grade.reason,
        grade.deserved,
        grade.overdrive,
        progress.streak,
        progress.totalXp,
        progress.lastXp,
        progress.earned,
        progress.heat,
        progress.level ?? "",
        progress.levelXp ?? "",
        progress.nextLevelXp ?? "",
        progress.levelProgress ?? "",
        progress.levelUp ?? "",
        progress.levelsGained ?? "",
      ].join("|")
    : "";
}

export function pillGradeXpText(grade: MoveGradeView | null): string {
  if (!grade) return "";
  return grade.xp > 0 ? `+${grade.xp}xp` : "0xp";
}

export function pillGradeFaceText(grade: MoveGradeView | null): string {
  if (!grade) return "";
  return `${grade.label} ${pillGradeXpText(grade)}`;
}

export function pillLevelText(progress: MoveGradeProgressView): string {
  if (progress.totalXp <= 0) return "";
  const level = progress.level ?? pillXpLevel(progress.totalXp).level;
  return `LV${level}`;
}

export function pillLevelAriaLabel(progress: MoveGradeProgressView): string {
  const text = pillLevelText(progress);
  if (!text) return "";
  const fallback = pillXpLevel(progress.totalXp);
  const level = progress.level ?? fallback.level;
  const levelXp = progress.levelXp ?? fallback.levelXp;
  const nextLevelXp = progress.nextLevelXp ?? fallback.nextLevelXp;
  return `level ${level}, ${levelXp} of ${nextLevelXp} xp${
    progress.levelUp ? ", level up" : ""
  }`;
}

export function pillIntelState(input: {
  mode: PillState["mode"];
  hasNext: boolean;
  hovered?: boolean;
  peekVisible: boolean;
  feedback: PillFeedbackEcho | null;
  grade: MoveGradeView | null;
  progress: MoveGradeProgressView | null;
}): PillIntelState {
  if (input.mode === "expand") return "reaction";
  if (input.mode === "speaking") return "speaking";
  if (input.feedback?.care) return "care";
  if (input.feedback) return "feedback";
  if (input.grade && input.progress && !input.progress.earned) return "care";
  if (input.peekVisible) return "knows";
  if ((input.grade?.overdrive || input.progress?.levelUp) && input.progress?.earned) {
    return "overdrive";
  }
  if (input.progress?.earned) return "earned";
  if (input.hasNext) return "knows";
  if (input.mode === "listening") return "listening";
  return "idle";
}

export function pillBurstProfile(
  grade: MoveGradeView | null,
  progress: MoveGradeProgressView | null,
): PillBurstProfile {
  if (!grade || progress?.earned !== true) {
    return { mode: "none", shardCount: 0, ringCount: 0 };
  }
  if (grade.overdrive) {
    return { mode: "overdrive", shardCount: 10, ringCount: 4 };
  }
  if (progress.levelUp) {
    return { mode: "level_up", shardCount: 6, ringCount: 3 };
  }
  return { mode: "none", shardCount: 0, ringCount: 0 };
}

export function pillFeedbackEchoLabel(
  kind: NextSuggestionFeedbackKind,
  grade: MoveGradeView | null = null,
): string {
  if (kind === "accept") return grade && !grade.deserved ? "CARE" : "KEEP";
  if (kind === "not_now") return "LATER";
  return "TIMING";
}

export function pillFeedbackAriaText(feedback: PillFeedbackEcho): string {
  if (feedback.care) return "suggestion accepted with care";
  if (feedback.kind === "accept") return "suggestion kept";
  if (feedback.kind === "not_now") return "suggestion postponed";
  return "suggestion timing marked wrong";
}

export function pillFeedbackShouldSend(
  echo: PillFeedbackEcho | null,
  kind: NextSuggestionFeedbackKind,
  suggestionKey: string,
  now: number,
): boolean {
  return !(
    echo &&
    now <= echo.until &&
    echo.kind === kind &&
    echo.suggestionKey === suggestionKey
  );
}

export function pillFeedbackShouldClearForSuggestion(
  echo: PillFeedbackEcho | null,
  suggestion: NextSuggestionWire | null | undefined,
): boolean {
  if (!echo || !hasRenderableSuggestion(suggestion)) return false;
  const completionKey = pillNextCompletionKey(suggestion);
  if (completionKey && echo.completionKey) return completionKey !== echo.completionKey;
  return nextSuggestionRenderKey(suggestion) !== echo.suggestionKey;
}

export function pillShouldClearHandledNextOnNull(demoFallbackEnabled: boolean): boolean {
  return !demoFallbackEnabled;
}

export function pillRenderLabel(
  baseLabel: string,
  hoverActive: boolean,
  peekVisible: boolean,
  feedback: PillFeedbackEcho | null,
): string {
  if (feedback) return feedback.label;
  return hoverActive && peekVisible ? "DJ KNOWS" : baseLabel;
}

export function pillRootAriaLabel(input: {
  peekVisible: boolean;
  suggestion: NextSuggestionWire | null | undefined;
  feedback: PillFeedbackEcho | null;
  gradeProgress?: MoveGradeProgressView | null;
}): string {
  if (input.feedback) return `${PILL_ROOT_ARIA_LABEL}. ${pillFeedbackAriaText(input.feedback)}.`;
  if (input.peekVisible && hasRenderableSuggestion(input.suggestion)) {
    const action = nextSuggestionPrimaryActionAriaLabel(input.suggestion, {
      density: "peek",
      gradeProgress: input.gradeProgress ?? null,
    });
    return `${PILL_ROOT_ARIA_LABEL}. ${action}`;
  }
  return PILL_ROOT_ARIA_LABEL;
}

function render(view: PillView, state: PillState, baseLabel: string, now: number): void {
  // data-state drives the dot pulse cadence + the expand panel visibility (CSS).
  view.root.dataset.state = state.mode;

  const effectiveNext = effectiveNextSuggestion(view);
  const nextKey = nextSuggestionRenderKey(effectiveNext);
  const moveGrade = nextMoveGrade(effectiveNext);
  const exposeNextChrome = pillShouldExposeNextChrome(state.mode);
  const localProgress = nextPillGradeProgress(view.gradeStreak, nextKey, moveGrade);
  const wireProgress = nextMoveGradeProgress(effectiveNext, null);
  const nextProgress = wireProgress && moveGrade
    ? {
        key: nextKey,
        slug: moveGrade.slug,
        xp: moveGrade.xp,
        ...wireProgress,
      }
    : localProgress;
  const feedbackEcho = activeFeedbackEcho(view, now);
  const faceFeedback = state.mode === "expand" || state.mode === "speaking" ? null : feedbackEcho;
  const faceGrade =
    exposeNextChrome && !moveGrade && faceFeedback?.grade ? faceFeedback.grade : moveGrade;
  const faceProgress =
    exposeNextChrome && !moveGrade && faceFeedback?.progress
      ? faceFeedback.progress
      : nextProgress;
  view.gradeStreak = faceProgress;
  syncMoveGrade(view, exposeNextChrome ? faceGrade : null);
  const hasNext = exposeNextChrome && hasRenderableSuggestion(effectiveNext);
  const demoNext = exposeNextChrome && effectiveNext === DEMO_NEXT_SUGGESTION;
  view.root.dataset.hasNext = hasNext ? "true" : "false";
  view.root.dataset.demoNext = demoNext ? "true" : "false";
  syncNextPulse(view, hasNext, nextKey);
  const storedReactionEcho = activeReactionEcho(view, state.mode, now);
  const echoCanYieldToPeek =
    state.peek && hasNext && COLLAPSED_PEEK_ENABLED && pillHoverCanOpen(state.mode);
  const reactionEcho = echoCanYieldToPeek ? null : storedReactionEcho;
  const hoverActive =
    COLLAPSED_PEEK_ENABLED && state.peek && pillHoverCanOpen(state.mode) && !reactionEcho;
  const peekVisible = hoverActive && hasNext;
  view.root.dataset.hover = hoverActive ? "true" : "false";
  view.root.dataset.peek = peekVisible ? "true" : "false";
  view.root.dataset.open = pillOpenState(state.mode, peekVisible) ? "true" : "false";
  view.root.dataset.faceWave = pillShouldShowFaceWave(state.mode, state.cohostStatus)
    ? "visible"
    : "quiet";
  if (faceFeedback) {
    view.root.dataset.feedback = faceFeedback.kind;
    view.root.dataset.feedbackCare = faceFeedback.care ? "true" : "false";
  } else {
    delete view.root.dataset.feedback;
    delete view.root.dataset.feedbackCare;
  }
  syncPillDemoStageFeedback(faceFeedback);
  if (reactionEcho && !faceFeedback) {
    view.root.dataset.reactionEcho = reactionEcho.tone;
  } else {
    delete view.root.dataset.reactionEcho;
  }
  view.root.dataset.intel = pillIntelState({
    mode: state.mode,
    hasNext,
    hovered: hoverActive,
    peekVisible,
    feedback: faceFeedback,
    grade: exposeNextChrome ? faceGrade : null,
    progress: view.gradeStreak,
  });
  view.label.textContent =
    reactionEcho && !faceFeedback
      ? reactionEcho.label
      : pillRenderLabel(baseLabel, hoverActive, peekVisible, faceFeedback);
  view.root.setAttribute(
    "aria-label",
    pillRootAriaLabel({
      peekVisible,
      suggestion: effectiveNext,
      feedback: faceFeedback,
      gradeProgress: nextProgress,
    }),
  );
  if (exposeNextChrome) {
    syncPeekCard(view);
  } else {
    clearPeekCard(view);
  }
  const exposePeek = pillShouldExposePeekFocus(peekVisible, hasNext);
  syncPillRootActionability(
    view.root,
    pillRootPrimaryActionAvailable(peekVisible, hasNext, faceFeedback),
  );
  syncPeekAssistiveVisibility(view, exposePeek);
  syncPeekFocus(view, exposePeek);

  if (state.mode === "expand") {
    const reactionDensity = pillReactionDensity(state.reactionText);
    view.root.dataset.reactionDensity = reactionDensity;
    renderReactionText(
      view,
      pillReactionDisplayText(state.reactionText, reactionDensity),
      state.collapseAt ?? 0,
    );
    syncReactionEcho(view, state.reactionText, state.collapseAt ?? 0);
    view.reaction.setAttribute("aria-label", state.reactionText);
    if (reactionDensity === "long") view.reaction.setAttribute("title", state.reactionText);
    else view.reaction.removeAttribute("title");
    // Citation strip rendered VERBATIM via the shipped component (T-62-12).
    syncCitationStrip(view, state.chips, state.reactionText, state.collapseAt ?? 0);
    // Deck-context chips from the LAST seen deck_state — honest unknown when a
    // deck/key is unresolved (PILL-03). renderDeckChips owns the honest-null +
    // amber-only-when-resolved rendering; the pill never fabricates a key (T-62-15).
    syncDeckChips(view);
    if (view.nextMount.childElementCount > 0) {
      view.nextMount.replaceChildren();
      view.lastNextKey = "";
    }
    syncExpandFocus(view, true);
  } else {
    delete view.root.dataset.reactionDensity;
    delete view.root.dataset.reactionTone;
    delete view.root.dataset.reactionPulse;
    stopReactionFx(view);
    view.lastReactionKey = "";
    view.lastChipsKey = "";
    view.reaction.textContent = "";
    view.reaction.removeAttribute("aria-label");
    view.reaction.removeAttribute("title");
    syncExpandFocus(view, false);
  }

  // Grow/shrink the window to fit the current content (expand panel) so the
  // reaction + grounded receipts never clip against the 44px shell. Runs
  // after the expand block so the measurement sees the just-rendered content.
  syncPillDemoControls(view, state.mode);
  syncWindowHeight(view, state);
}

function renderReactionText(view: PillView, text: string, reactionRevision: number): void {
  const key = JSON.stringify([text, reactionRevision]);
  if (key === view.lastReactionKey) return;
  view.lastReactionKey = key;
  const parts = pillReactionLeadParts(text);
  view.reaction.replaceChildren();
  if (!parts.tone) {
    delete view.root.dataset.reactionTone;
    delete view.root.dataset.reactionPulse;
    stopReactionFx(view);
    view.reaction.textContent = text;
    return;
  }
  view.root.dataset.reactionTone = parts.tone;
  view.root.dataset.reactionPulse = pillReactionPulseSlot(view.reactionPulseRevision);
  view.reactionPulseRevision += 1;
  if (parts.prefix) view.reaction.append(document.createTextNode(parts.prefix));

  const lead = document.createElement("span");
  lead.className = "pill__reaction-lead";
  lead.textContent = parts.lead;

  const rest = document.createElement("span");
  rest.className = "pill__reaction-rest";
  rest.textContent = parts.rest;

  view.reaction.append(lead, rest);
  syncReactionFx(view, parts.tone, reactionRevision);
}

interface PillFxRgb {
  r: number;
  g: number;
  b: number;
}

interface PillFxPalette {
  primary: PillFxRgb;
  secondary: PillFxRgb;
  accent: PillFxRgb;
}

interface PillFxParticle {
  x: number;
  y: number;
  angle: number;
  travel: number;
  size: number;
  delay: number;
  life: number;
  stretch: number;
  secondary: boolean;
}

function syncReactionFx(
  view: PillView,
  tone: PillReactionTone | null,
  reactionRevision: number,
): void {
  stopReactionFx(view);
  const profile = pillReactionFxProfile(tone);
  if (!tone || profile.durationMs <= 0 || pillPrefersReducedMotion()) return;
  const context = view.fxCanvas.getContext("2d");
  if (!context) return;

  const particles = pillReactionFxParticles(tone, reactionRevision, profile);
  const palette = pillReactionFxPalette(view);
  const start = performance.now();
  view.root.dataset.fx = tone;
  view.fxCanvas.dataset.fxRevision = String(Math.round(reactionRevision));

  const tick = (now: number): void => {
    const progress = pillClamp01((now - start) / profile.durationMs);
    drawReactionFxFrame(
      context,
      view.fxCanvas,
      view.expand,
      profile,
      particles,
      palette,
      progress,
    );
    if (progress < 1) {
      view.fxAnimationFrame = window.requestAnimationFrame(tick);
      return;
    }
    clearReactionFxCanvas(view.fxCanvas);
    delete view.root.dataset.fx;
    delete view.fxCanvas.dataset.fxRevision;
    view.fxAnimationFrame = null;
  };

  view.fxAnimationFrame = window.requestAnimationFrame(tick);
}

function stopReactionFx(view: PillView): void {
  if (view.fxAnimationFrame !== null) {
    window.cancelAnimationFrame(view.fxAnimationFrame);
    view.fxAnimationFrame = null;
  }
  clearReactionFxCanvas(view.fxCanvas);
  delete view.root.dataset.fx;
  delete view.fxCanvas.dataset.fxRevision;
}

function clearReactionFxCanvas(canvas: HTMLCanvasElement): void {
  const context = canvas.getContext("2d");
  if (!context) return;
  context.clearRect(0, 0, canvas.width, canvas.height);
}

function pillPrefersReducedMotion(): boolean {
  return (
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

function pillReactionFxParticles(
  tone: PillReactionTone,
  reactionRevision: number,
  profile: PillReactionFxProfile,
): PillFxParticle[] {
  const random = pillFxRandom(pillReactionFxSeed(tone, reactionRevision));
  const hot = tone === "bomb" || tone === "lit_aff";
  const count = profile.particleCount;
  return Array.from({ length: count }, (_, index) => {
    const lane = count > 1 ? index / (count - 1) : 0.5;
    const x = pillClamp(0.08 + lane * 0.84 + (random() - 0.5) * 0.08, 0.06, 0.94);
    const side = x < 0.5 ? -1 : 1;
    return {
      x,
      y: 0.62 + random() * 0.28,
      angle: -Math.PI / 2 + side * (0.18 + random() * 0.48),
      travel: (hot ? 58 : 38) * (0.54 + random() * profile.glow),
      size: (hot ? 0.85 : 0.75) + random() * (hot ? 1.85 : 1.25),
      delay: random() * 0.22,
      life: 0.54 + random() * 0.32,
      stretch: 1 + random() * 0.85,
      secondary: random() > 0.54,
    };
  });
}

function pillReactionFxSeed(tone: PillReactionTone, reactionRevision: number): number {
  let seed = Math.max(1, Math.round(reactionRevision));
  for (const char of tone) seed = (seed * 31 + char.charCodeAt(0)) >>> 0;
  return seed || 1;
}

function pillFxRandom(seed: number): () => number {
  let value = seed >>> 0;
  return () => {
    value = (value * 1664525 + 1013904223) >>> 0;
    return value / 4294967296;
  };
}

function pillReactionFxPalette(view: PillView): PillFxPalette {
  const styles = getComputedStyle(view.root);
  return {
    primary: pillFxRgb(styles.getPropertyValue("--pill-fx-primary"), {
      r: 255,
      g: 170,
      b: 224,
    }),
    secondary: pillFxRgb(styles.getPropertyValue("--pill-fx-secondary"), {
      r: 235,
      g: 197,
      b: 128,
    }),
    accent: pillFxRgb(styles.getPropertyValue("--pill-fx-accent"), {
      r: 255,
      g: 232,
      b: 196,
    }),
  };
}

function pillFxRgb(value: string, fallback: PillFxRgb): PillFxRgb {
  const parts = value
    .trim()
    .split(/[,\s/]+/)
    .map((part) => Number(part))
    .filter((part) => Number.isFinite(part));
  if (parts.length < 3) return fallback;
  return {
    r: Math.round(pillClamp(parts[0] ?? fallback.r, 0, 255)),
    g: Math.round(pillClamp(parts[1] ?? fallback.g, 0, 255)),
    b: Math.round(pillClamp(parts[2] ?? fallback.b, 0, 255)),
  };
}

function drawReactionFxFrame(
  context: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  expand: HTMLElement,
  profile: PillReactionFxProfile,
  particles: PillFxParticle[],
  palette: PillFxPalette,
  progress: number,
): void {
  const size = syncReactionFxCanvasSize(canvas, expand);
  context.clearRect(0, 0, size.width, size.height);
  context.save();
  context.globalCompositeOperation = "lighter";
  drawReactionFxBloom(context, size.width, size.height, profile, palette, progress);
  drawReactionFxLightTrails(context, size.width, size.height, profile, palette, progress);
  drawReactionFxRings(context, size.width, size.height, profile, palette, progress);
  drawReactionFxParticles(context, size.width, size.height, profile, particles, palette, progress);
  context.restore();
}

function syncReactionFxCanvasSize(
  canvas: HTMLCanvasElement,
  expand: HTMLElement,
): { width: number; height: number } {
  const rect = expand.getBoundingClientRect();
  const cssWidth = Math.max(1, Math.round(rect.width || canvas.clientWidth || 280));
  const cssHeight = Math.max(
    1,
    Math.round(rect.height || expand.scrollHeight || canvas.clientHeight || 180),
  );
  const dpr = Math.min(Math.max(window.devicePixelRatio || 1, 1), 2);
  const targetWidth = Math.round(cssWidth * dpr);
  const targetHeight = Math.round(cssHeight * dpr);
  if (canvas.width !== targetWidth) canvas.width = targetWidth;
  if (canvas.height !== targetHeight) canvas.height = targetHeight;
  const context = canvas.getContext("2d");
  context?.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { width: cssWidth, height: cssHeight };
}

function drawReactionFxBloom(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  profile: PillReactionFxProfile,
  palette: PillFxPalette,
  progress: number,
): void {
  const eased = pillEaseOutQuart(progress);
  const fade = Math.pow(1 - progress, 1.18);
  const centerX = width * 0.36;
  const centerY = height * 0.56;
  const radius = Math.max(width, height) * (0.34 + eased * 0.32);
  const bloom = context.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius);
  bloom.addColorStop(0, pillFxRgba(palette.primary, 0.2 * profile.glow * fade));
  bloom.addColorStop(0.34, pillFxRgba(palette.secondary, 0.12 * profile.glow * fade));
  bloom.addColorStop(0.72, pillFxRgba(palette.accent, 0.05 * profile.glow * fade));
  bloom.addColorStop(1, pillFxRgba(palette.primary, 0));
  context.fillStyle = bloom;
  context.fillRect(0, 0, width, height);
}

function drawReactionFxLightTrails(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  profile: PillReactionFxProfile,
  palette: PillFxPalette,
  progress: number,
): void {
  if (profile.glow < 0.45) return;
  const eased = pillEaseOutQuart(progress);
  const fade = Math.pow(1 - progress, 1.5);
  for (let trail = 0; trail < 3; trail += 1) {
    const y = height * (0.68 + trail * 0.075);
    const lift = Math.sin((progress + trail * 0.18) * Math.PI) * height * 0.025;
    context.beginPath();
    context.moveTo(width * 0.08, y + lift);
    context.bezierCurveTo(
      width * (0.24 + eased * 0.05),
      y - height * (0.1 + trail * 0.025),
      width * (0.55 + eased * 0.1),
      y + height * (0.03 + trail * 0.02),
      width * 0.95,
      y - lift * 0.5,
    );
    context.lineWidth = 0.8 + (1 - progress) * 1.2;
    context.strokeStyle = pillFxRgba(
      trail % 2 === 0 ? palette.primary : palette.secondary,
      0.18 * profile.glow * fade,
    );
    context.shadowBlur = 12;
    context.shadowColor = pillFxRgba(palette.primary, 0.16 * profile.glow * fade);
    context.stroke();
  }
  context.shadowBlur = 0;
}

function drawReactionFxRings(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  profile: PillReactionFxProfile,
  palette: PillFxPalette,
  progress: number,
): void {
  for (let ring = 0; ring < profile.ringCount; ring += 1) {
    const offset = ring * 0.11;
    const local = pillClamp01((progress - offset) / (1 - offset));
    if (local <= 0) continue;
    const fade = Math.pow(1 - local, 2.15);
    context.beginPath();
    context.lineWidth = 1.1 + (1 - local) * 1.7;
    context.strokeStyle = pillFxRgba(
      ring % 2 === 0 ? palette.primary : palette.secondary,
      0.28 * profile.glow * fade,
    );
    context.ellipse(
      width * 0.42,
      height * 0.68,
      26 + local * width * 0.58,
      10 + local * height * 0.24,
      -0.1,
      0,
      Math.PI * 2,
    );
    context.stroke();
  }
}

function drawReactionFxParticles(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  profile: PillReactionFxProfile,
  particles: PillFxParticle[],
  palette: PillFxPalette,
  progress: number,
): void {
  const eventFade = 1 - progress * 0.32;
  for (const particle of particles) {
    const local = pillClamp01((progress - particle.delay) / particle.life);
    if (local <= 0 || local >= 1) continue;
    const eased = 1 - Math.pow(1 - local, 3);
    const color = particle.secondary ? palette.secondary : palette.primary;
    const alpha = Math.sin(local * Math.PI) * (0.16 + profile.glow * 0.24) * eventFade;
    const x = width * particle.x + Math.cos(particle.angle) * particle.travel * eased;
    const y = height * particle.y + Math.sin(particle.angle) * particle.travel * eased;
    const size = particle.size * (0.74 + eased * 0.72);

    context.save();
    context.translate(x, y);
    context.rotate(particle.angle + Math.PI / 2);
    context.shadowBlur = 7 + size * 4;
    context.shadowColor = pillFxRgba(color, alpha);
    context.fillStyle = pillFxRgba(color, alpha);
    context.beginPath();
    context.ellipse(0, 0, size * particle.stretch, size, 0, 0, Math.PI * 2);
    context.fill();
    context.restore();
  }
}

function pillFxRgba(color: PillFxRgb, alpha: number): string {
  return `rgba(${color.r}, ${color.g}, ${color.b}, ${pillClamp01(alpha)})`;
}

function pillEaseOutQuart(value: number): number {
  return 1 - Math.pow(1 - pillClamp01(value), 4);
}

function pillClamp01(value: number): number {
  return pillClamp(value, 0, 1);
}

function pillClamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function activeFeedbackEcho(view: PillView, now: number): PillFeedbackEcho | null {
  const echo = view.feedbackEcho;
  if (echo === null) return null;
  if (now <= echo.until) return echo;
  view.feedbackEcho = null;
  return null;
}

function activeReactionEcho(
  view: PillView,
  mode: PillState["mode"],
  now: number,
): PillReactionEcho | null {
  const echo = view.reactionEcho;
  if (echo === null) return null;
  if (pillReactionEchoVisible(echo, mode, now)) return echo;
  if (now > echo.until) view.reactionEcho = null;
  return null;
}

function syncNextPulse(view: PillView, hasNext: boolean, nextKey: string): void {
  const pulseKey = hasNext && nextKey ? nextKey : "";
  if (!pulseKey) {
    view.lastNextPulseKey = "";
    delete view.root.dataset.nextPulse;
    return;
  }
  if (pulseKey === view.lastNextPulseKey) return;
  view.lastNextPulseKey = pulseKey;
  view.root.dataset.nextPulse = pillNextPulseSlot(view.nextPulseRevision);
  view.nextPulseRevision += 1;
}

function syncReactionEcho(
  view: PillView,
  reactionText: string,
  reactionRevision: number,
): void {
  const key = JSON.stringify([reactionText, reactionRevision]);
  if (key === view.lastReactionEchoKey) return;
  view.lastReactionEchoKey = key;
  const parts = pillReactionLeadParts(reactionText);
  const label = pillReactionEchoLabel(reactionText);
  if (!parts.tone || !label) {
    view.reactionEcho = null;
    return;
  }
  view.reactionEcho = {
    label,
    tone: parts.tone,
    key,
    until: reactionRevision + PILL_REACTION_ECHO_MS,
  };
}

/** Resize the pill window to fit its content (expand panel) — collapsed 44px
 *  otherwise. Memoised on a cheap layout key so the rAF render never forces a
 *  reflow (scrollHeight) or a redundant Tauri invoke when nothing changed. */
function syncWindowHeight(view: PillView, state: PillState): void {
  const peekOpen = view.root.dataset.peek === "true";
  const key = pillWindowHeightRenderKey({
    mode: state.mode,
    peekOpen,
    chipsKey: view.lastChipsKey,
    deckKey: view.lastDeckKey,
    peekKey: view.lastPeekKey,
    nextKey: view.lastNextKey,
    reactionText: state.reactionText,
  });
  if (key === view.lastWindowHKey) return;
  view.lastWindowHKey = key;
  const target = pillWindowHeightForContent(
    state.mode,
    peekOpen,
    view.expand.scrollHeight,
    view.peekMount.scrollHeight,
  );
  if (target === view.lastWindowH) return;
  view.lastWindowH = target;
  void invoke("set_pill_height", { height: target }).catch((e: unknown) =>
    vmxLog("[vmx:error]", "set_pill_height failed", { error: String(e) }),
  );
}

function syncMoveGrade(view: PillView, grade: MoveGradeView | null): void {
  const streak = view.gradeStreak;
  const key = pillMoveGradeRenderKey(grade, streak);
  if (key === view.lastGradeKey) return;
  view.lastGradeKey = key;

  if (!grade) {
    delete view.root.dataset.moveGrade;
    delete view.root.dataset.gradeEarned;
    delete view.root.dataset.gradeOverdrive;
    delete view.root.dataset.gradeStreak;
    delete view.root.dataset.gradeTotalXp;
    delete view.root.dataset.gradeLevel;
    delete view.root.dataset.gradeLevelUp;
    delete view.root.dataset.gradeBurst;
    view.gradeMount.style.removeProperty("--pill-grade-heat-scale");
    view.levelMount.style.removeProperty("--pill-level-scale");
    view.streakMount.style.removeProperty("--pill-streak-heat-scale");
    view.gradeMount.replaceChildren();
    view.gradeMount.removeAttribute("aria-label");
    view.gradeMount.removeAttribute("title");
    view.levelMount.replaceChildren();
    view.levelMount.removeAttribute("aria-label");
    view.burstMount.replaceChildren();
    view.overdriveMount.replaceChildren();
    return;
  }

  const level = pillXpLevel(streak.totalXp);
  const levelProgress = streak.levelProgress ?? level.levelProgress;
  view.root.dataset.moveGrade = grade.slug;
  view.root.dataset.gradeEarned = streak.earned ? "true" : "false";
  view.root.dataset.gradeOverdrive = grade.overdrive ? "true" : "false";
  view.root.dataset.gradeStreak = String(streak.streak);
  view.root.dataset.gradeTotalXp = String(streak.totalXp);
  view.root.dataset.gradeLevel = String(streak.level ?? level.level);
  view.root.dataset.gradeLevelUp = streak.levelUp ? "true" : "false";
  view.gradeMount.style.setProperty(
    "--pill-grade-heat-scale",
    (grade.intensity / 100).toFixed(2),
  );
  view.levelMount.style.setProperty(
    "--pill-level-scale",
    (levelProgress / 100).toFixed(2),
  );
  view.streakMount.style.setProperty(
    "--pill-streak-heat-scale",
    (streak.heat / 100).toFixed(2),
  );

  const label = document.createElement("span");
  label.className = "pill__grade-label";
  label.textContent = grade.label;

  const xp = document.createElement("span");
  xp.className = "pill__grade-xp";
  xp.textContent = pillGradeXpText(grade);

  const spacer = document.createElement("span");
  spacer.className = "pill__grade-spacer";
  spacer.setAttribute("aria-hidden", "true");
  spacer.textContent = " ";

  view.gradeMount.replaceChildren(label, spacer, xp);
  view.gradeMount.setAttribute("title", pillGradeFaceText(grade));
  view.gradeMount.setAttribute(
    "aria-label",
    `${grade.label} move, ${grade.xp} xp, ${grade.reason}${
      streak.streak > 1 ? `, ${streak.streak} move streak` : ""
    }${streak.totalXp > 0 ? `, ${streak.totalXp} session xp, ${pillLevelAriaLabel(streak)}` : ""}`,
  );
  const levelText = streak.earned ? pillLevelText(streak) : "";
  view.levelMount.textContent = levelText;
  if (levelText) {
    view.levelMount.setAttribute("aria-label", pillLevelAriaLabel(streak));
  } else {
    view.levelMount.removeAttribute("aria-label");
  }

  view.burstMount.replaceChildren();
  view.overdriveMount.replaceChildren();
  const burst = pillBurstProfile(grade, streak);
  if (burst.mode === "none") {
    delete view.root.dataset.gradeBurst;
  } else {
    view.root.dataset.gradeBurst = burst.mode;
    const spanStep = burst.shardCount > 1 ? 72 / (burst.shardCount - 1) : 0;
    const delayStepMs = burst.mode === "overdrive" ? 24 : 34;
    const rotation = burst.mode === "overdrive" ? 32 : 24;
    for (let index = 0; index < burst.shardCount; index += 1) {
      const shard = document.createElement("span");
      shard.style.setProperty("--x", `${14 + index * spanStep}%`);
      shard.style.setProperty("--delay", `${index * delayStepMs}ms`);
      shard.style.setProperty("--rot", `${index % 2 === 0 ? rotation : -rotation}deg`);
      view.burstMount.append(shard);
    }
    for (let index = 0; index < burst.ringCount; index += 1) {
      view.overdriveMount.append(document.createElement("span"));
    }
  }
}

function syncCitationStrip(
  view: PillView,
  chips: CitationChip[],
  reactionText: string,
  reactionRevision: number,
): void {
  const expandEl = view.expand;
  // Only rebuild the strip when the visible receipt changes (cheap key) — the
  // rAF loop calls render() every frame. The key includes the reaction revision
  // so the receipt-rule draw replays on every fresh BOMB/LIT/etc reaction over
  // the same cited moment, even if the cohost repeats the exact same words.
  const key = pillReceiptRenderKey(chips, reactionText, reactionRevision);
  if (key === view.lastChipsKey) return;
  view.lastChipsKey = key;
  expandEl.querySelector(".vmx-citation-strip")?.remove();
  expandEl.querySelector(".pill__receipt-rule")?.remove();
  const strip = renderCitationStrip({
    chips,
    variant: "pill",
    onChipClick: openDebriefFromPillChip,
  });
  if (strip) {
    // Tag the strip so a chip click does not start a window drag.
    strip.setAttribute("data-no-drag", "");
    // Insert before the deck-chips mount (the deck chips sit BELOW the citation
    // strip per 62-UI-SPEC §States).
    const decks = expandEl.querySelector("#pill-decks");
    // "The Deck Speaks" receipt echo (2026-05-26 rebuild): a 1px amber rule
    // draws in above the citation — the session deck's signature gesture
    // ("it spoke, then drew its receipt") carried to the pill in miniature.
    // Inserted fresh per reaction so the draw replays on each new reaction.
    const rule = document.createElement("span");
    rule.className = "pill__receipt-rule";
    rule.dataset.wire = "pill.receipt";
    rule.setAttribute("aria-hidden", "true");
    strip.dataset.wire = "pill.citations";
    expandEl.insertBefore(rule, decks);
    expandEl.insertBefore(strip, decks);
  }
}

export function pillCitationChipsRenderKey(chips: CitationChip[]): string {
  return JSON.stringify(chips.map((c) => [c.event_id, c.timestamp_s, c.verb]));
}

export function pillReceiptRenderKey(
  chips: CitationChip[],
  reactionText: string,
  reactionRevision = 0,
): string {
  return JSON.stringify([pillCitationChipsRenderKey(chips), reactionText, reactionRevision]);
}

function openDebriefFromPillChip(chip: CitationChip): void {
  void invoke("open_debrief_window", pillDebriefInvokeArgs(chip)).catch((err: unknown) => {
    vmxLog("[vmx:error]", "pill citation open_debrief_window failed", {
      error: String(err),
    });
  });
}

/**
 * Populate the #pill-decks mount with the honest deck-context chips from the
 * latest deck_state (62-UI-SPEC §States — deck chips sit below the citation
 * strip). Un-hides the mount (62-04 stubbed it `display:none`) and only rebuilds
 * when the deck_state changes (cheap key) — the rAF loop calls render() every
 * frame. Tags the strip `[data-no-drag]` so a chip area never starts a window
 * drag. renderDeckChips always returns at least the honest `decks · unknown`
 * chip, so the mount always shows the truthful deck context while expanded.
 */
function syncDeckChips(view: PillView): void {
  const decksMount = view.decksMount;
  const deckState = view.deckState;
  // Cheap change key over EVERY field the chip renders (side + camelot + key +
  // bpm + confidence) so an in-place value change (e.g. a key resolving while
  // camelot/bpm hold, or a confidence shift that flips the WR-04 dim) rebuilds
  // the DOM. The memo key lives on the view, not a module global (WR-05).
  const key = deckState
    ? Object.entries(deckState)
        .map(
          ([side, d]) =>
            `${side}:${d.camelot ?? "-"}:${d.key ?? "-"}:${d.bpm ?? "-"}:${d.confidence ?? "-"}`,
        )
        .join("|")
    : "";
  if (key === view.lastDeckKey && decksMount.childElementCount > 0) return;
  view.lastDeckKey = key;
  decksMount.replaceChildren();
  const strip = renderDeckChips(deckState);
  if (strip) {
    strip.setAttribute("data-no-drag", "");
    decksMount.append(strip);
  }
  // Un-hide the mount (62-04 stubbed `.pill__decks { display: none }`); the
  // explicit inline flex survives the stylesheet rule.
  decksMount.style.display = "flex";
}

/**
 * Populate the #pill-next mount with the next-track suggestion card. Rebuilds
 * only when the rendered suggestion changes, including live transition timing,
 * while the rAF loop calls render() every frame. Honest silence: a null
 * suggestion clears the mount and renders nothing. Tagged
 * [data-no-drag] so the card never starts a window drag.
 */
function syncNextSuggestion(view: PillView): void {
  const mount = view.nextMount;
  const s = effectiveNextSuggestion(view);
  const key = nextSuggestionRenderKey(s);
  if (key === view.lastNextKey) return;
  view.lastNextKey = key;
  const restoreRootFocus = pillShouldReturnFocusToRootAfterSuggestionSurfaceRemoval(
    document.activeElement,
    view.root,
    [mount],
  );
  mount.replaceChildren();
  const card = renderNextSuggestion(s, {
    showAlternatives: true,
    maxAlternatives: 2,
    gradeProgress: view.gradeStreak,
    onAlternativeSelect: chooseNextSuggestionAlternative,
    onFeedback: (kind) => sendNextSuggestionFeedback(kind, view),
  });
  if (card) {
    card.setAttribute("data-no-drag", "");
    mount.append(card);
  }
  if (restoreRootFocus) view.root.focus({ preventScroll: true });
}

/**
 * Populate the collapsed-hover #pill-peek mount with the next-track suggestion
 * card (Phase-1b). REUSES renderNextSuggestion with backups hidden so the hover
 * glance stays compact. Rebuilds only when the
 * rendered suggestion changes, including live transition timing, while the rAF
 * loop calls render() every frame. HONEST SILENCE: a null/undefined suggestion
 * clears the mount and renders nothing (renderNextSuggestion returns null) — the pill never
 * fabricates a "next" on hover; an empty mount stays invisible via the CSS
 * `:not(:empty)` guard. The card is tagged [data-no-drag] so hovering it never
 * starts a window drag. The mount is always present; only its visibility is
 * gated by .pill[data-peek] (set in render()), so this can run every frame.
 */
function syncPeekCard(view: PillView): void {
  const mount = view.peekMount;
  const s = effectiveNextSuggestion(view);
  const key = nextSuggestionRenderKey(s);
  if (key === view.lastPeekKey) return;
  view.lastPeekKey = key;
  const restoreRootFocus = pillShouldReturnFocusToRootAfterSuggestionSurfaceRemoval(
    document.activeElement,
    view.root,
    [mount],
  );
  mount.replaceChildren();
  mount.removeAttribute("aria-label");
  const card = renderNextSuggestion(s, {
    density: "peek",
    showAlternatives: false,
    showFeedback: false,
    gradeProgress: view.gradeStreak,
    onPrimaryAction: () => view.onPeekPrimaryAction?.(),
    onFeedback: (kind) => sendNextSuggestionFeedback(kind, view),
  });
  if (card) {
    card.setAttribute("data-no-drag", "");
    const label = card.getAttribute("aria-label");
    if (label) mount.setAttribute("aria-label", label);
    mount.append(card);
  }
  if (restoreRootFocus) view.root.focus({ preventScroll: true });
}

function clearPeekCard(view: PillView): void {
  if (view.peekMount.childElementCount === 0 && !view.peekMount.hasAttribute("aria-label")) {
    view.lastPeekKey = "";
    return;
  }
  const restoreRootFocus = pillShouldReturnFocusToRootAfterSuggestionSurfaceRemoval(
    document.activeElement,
    view.root,
    [view.peekMount],
  );
  view.peekMount.replaceChildren();
  view.peekMount.removeAttribute("aria-label");
  view.lastPeekKey = "";
  if (restoreRootFocus) view.root.focus({ preventScroll: true });
}

const FOCUSABLE_DESCENDANT_SELECTOR = [
  "[tabindex]",
  "button",
  "[href]",
  "input",
  "select",
  "textarea",
  "[contenteditable='true']",
].join(",");

export function syncFocusableDescendants(root: HTMLElement, focusable: boolean): void {
  root.toggleAttribute("inert", !focusable);
  root.querySelectorAll<HTMLElement>(FOCUSABLE_DESCENDANT_SELECTOR)
    .forEach((el) => {
      if (focusable) {
        const stored = el.dataset.pillTabIndex;
        if (stored === "none") {
          el.removeAttribute("tabindex");
        } else if (stored !== undefined) {
          el.tabIndex = Number(stored);
        }
        delete el.dataset.pillTabIndex;
      } else {
        if (el.dataset.pillTabIndex === undefined) {
          const attr = el.getAttribute("tabindex");
          el.dataset.pillTabIndex = attr ?? "none";
        }
        el.tabIndex = -1;
      }
    });
}

function syncPeekFocus(view: PillView, focusable: boolean): void {
  syncFocusableDescendants(view.peekMount, focusable);
}

function syncPillDemoControls(view: PillView, mode: PillState["mode"]): void {
  const controls = view.demoControls;
  if (!controls) return;
  const focusable = pillDemoControlsShouldBeFocusable(mode, pillDemoControlsNarrowViewport());
  controls.setAttribute("aria-hidden", focusable ? "false" : "true");
  syncFocusableDescendants(controls, focusable);
}

function pillDemoControlsNarrowViewport(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(max-width: 560px)").matches;
}

function syncExpandFocus(view: PillView, focusable: boolean): void {
  if (focusable) {
    view.expand.setAttribute("aria-hidden", "false");
  } else {
    view.expand.setAttribute("aria-hidden", "true");
  }
  syncFocusableDescendants(view.expand, focusable);
}

function syncPeekAssistiveVisibility(view: PillView, visible: boolean): void {
  if (visible) {
    view.peekMount.removeAttribute("aria-hidden");
  } else {
    view.peekMount.setAttribute("aria-hidden", "true");
  }
}

function effectiveNextSuggestion(view: PillView): NextSuggestionWire | null {
  const suggestion = hasRenderableSuggestion(view.nextSuggestion)
    ? view.nextSuggestion
    : DEMO_NEXT_ENABLED
      ? DEMO_NEXT_SUGGESTION
      : null;
  if (!suggestion) return null;
  if (pillSuggestionIsHandled(suggestion, view.handledNextKey, view.handledNextRenderKey)) {
    return null;
  }
  return suggestion;
}

function hasRenderableSuggestion(
  s: NextSuggestionWire | null | undefined,
): s is NextSuggestionWire {
  return Boolean(s?.track_id && s?.title);
}

export function nextSuggestionChoiceMessage(alt: NextAlternativeView): Record<string, unknown> {
  return {
    action: "next_suggestion.choose",
    candidate_id: alt.candidateId,
    track_id: alt.trackId || null,
  };
}

export function nextSuggestionFeedbackMessage(
  feedback: NextSuggestionFeedbackKind,
): Record<string, unknown> {
  return {
    action: "next_suggestion.feedback",
    feedback,
  };
}

export function pillDebriefInvokeArgs(chip: CitationChip): Record<string, unknown> {
  return {
    sessionDir: "",
    deepLink: {
      eventId: chip.event_id,
      timestampS: chip.timestamp_s,
    },
  };
}

function chooseNextSuggestionAlternative(alt: NextAlternativeView): void {
  const message = nextSuggestionChoiceMessage(alt);
  vmxLog("[vmx:ipc>]", "choose next-suggestion backup", message);
  void invoke("forward_ipc_to_sidecar", { message }).catch((err: unknown) => {
    vmxLog("[vmx:error]", "next-suggestion backup choose failed", {
      error: String(err),
    });
  });
}

function sendNextSuggestionFeedback(
  feedback: NextSuggestionFeedbackKind,
  view?: PillView,
): void {
  let suggestionKey = "";
  if (view) {
    const suggestion = effectiveNextSuggestion(view);
    const grade = nextMoveGrade(suggestion);
    suggestionKey = nextSuggestionRenderKey(suggestion);
    const completionKey = pillNextCompletionKey(suggestion);
    const progress = grade ? view.gradeStreak : null;
    const now = performance.now();
    if (!pillFeedbackShouldSend(view.feedbackEcho, feedback, suggestionKey, now)) return;
    const label = pillFeedbackEchoLabel(feedback, grade);
    view.feedbackEcho = {
      kind: feedback,
      label,
      suggestionKey,
      completionKey,
      grade,
      progress,
      care: label === "CARE",
      until: now + PILL_FEEDBACK_ECHO_MS,
    };
    if (suggestionKey) view.handledNextRenderKey = suggestionKey;
    if (completionKey) {
      view.handledNextKey = completionKey;
    }
    if (completionKey || suggestionKey) {
      const restoreRootFocus = pillShouldReturnFocusToRootAfterSuggestionSurfaceRemoval(
        document.activeElement,
        view.root,
        [view.nextMount, view.peekMount],
      );
      view.nextMount.replaceChildren();
      view.peekMount.replaceChildren();
      view.peekMount.removeAttribute("aria-label");
      view.lastNextKey = "";
      view.lastPeekKey = "";
      if (restoreRootFocus) view.root.focus({ preventScroll: true });
    }
  }
  const message = nextSuggestionFeedbackMessage(feedback);
  vmxLog("[vmx:ipc>]", "label next-suggestion", message);
  void invoke("forward_ipc_to_sidecar", { message }).catch((err: unknown) => {
    vmxLog("[vmx:error]", "next-suggestion feedback failed", {
      error: String(err),
    });
  });
}

// ── Boot ──────────────────────────────────────────────────────────────────

function boot(): void {
  const root = document.getElementById("pill");
  const label = document.getElementById("pill-label");
  const gradeMount = document.getElementById("pill-grade");
  const levelMount = document.getElementById("pill-level");
  const burstMount = document.getElementById("pill-burst");
  const overdriveMount = document.getElementById("pill-overdrive");
  const streakMount = document.getElementById("pill-streak");
  const fxCanvas = document.getElementById("pill-fx");
  const reaction = document.getElementById("pill-reaction");
  const expand = document.getElementById("pill-expand");
  const waveMount = document.getElementById("pill-wave");
  const dragStrip = document.getElementById("pill-drag");
  const decksMount = document.getElementById("pill-decks");
  const peekMount = document.getElementById("pill-peek");
  if (
    !root ||
    !label ||
    !gradeMount ||
    !levelMount ||
    !burstMount ||
    !overdriveMount ||
    !streakMount ||
    !(fxCanvas instanceof HTMLCanvasElement) ||
    !reaction ||
    !expand ||
    !waveMount ||
    !dragStrip ||
    !decksMount ||
    !peekMount
  ) {
    console.error(`${TAG} pill DOM skeleton missing — cannot mount`);
    return;
  }

  // Mount the waveform (meter.ts reuse) into the collapsed-row mount. Tag
  // no-drag — it lives below the drag strip, but belt-and-braces.
  const waveEl = renderWaveform();
  waveEl.setAttribute("data-no-drag", "");
  waveMount.append(waveEl);

  // The next-suggestion mount lives below the deck chips in the expand panel.
  // Created here (not in the HTML skeleton) so the skeleton stays minimal and
  // the missing-mount guard above is unaffected; tagged no-drag.
  const nextMount = document.createElement("div");
  nextMount.id = "pill-next";
  nextMount.dataset.wire = "pill.next";
  nextMount.setAttribute("data-no-drag", "");
  decksMount.insertAdjacentElement("afterend", nextMount);

  const view: PillView = {
    root,
    label,
    gradeMount,
    levelMount,
    burstMount,
    overdriveMount,
    streakMount,
    fxCanvas,
    fxAnimationFrame: null,
    reaction,
    expand,
    waveMount,
    waveEl,
    decksMount,
    deckState: null,
    nextMount,
    peekMount,
    demoControls: null,
    nextSuggestion: null,
    handledNextKey: "",
    handledNextRenderKey: "",
    onPeekPrimaryAction: null,
    gradeStreak: {
      key: "",
      slug: "",
      streak: 0,
      xp: 0,
      totalXp: 0,
      lastXp: 0,
      earned: false,
      heat: 0,
    },
    feedbackEcho: null,
    reactionEcho: null,
    lastReactionEchoKey: "",
    lastGradeKey: "",
    lastChipsKey: "",
    lastDeckKey: "",
    lastReactionKey: "",
    reactionPulseRevision: 0,
    lastNextKey: "",
    lastNextPulseKey: "",
    nextPulseRevision: 0,
    lastPeekKey: "",
    lastWindowHKey: "",
    // Force the first render to send set_pill_height(44). Dev/hot reload can
    // leave the native overlay at the prior expanded height; seeding this with
    // 44 would skip the reset as "unchanged".
    lastWindowH: 0,
  };

  let state = initialPillState(performance.now());
  let suppressNextFocusPeek = false;
  let demoReturnIdleAt: number | null = null;
  let demoDeckHoldUntil: number | null = null;
  const closePeekToRoot = (forceFocus = false): void => {
    state = setPeek(state, false);
    const active = document.activeElement;
    if (forceFocus) {
      suppressNextFocusPeek = true;
      root.focus({ preventScroll: true });
      return;
    }
    if (active instanceof Element && root.contains(active)) {
      suppressNextFocusPeek = pillShouldSuppressNextFocusPeek(root, active);
      root.focus({ preventScroll: true });
    }
  };
  view.onPeekPrimaryAction = () => {
    closePeekToRoot(true);
    sendNextSuggestionFeedback("accept", view);
  };
  view.demoControls = installPillDemoControls((key) => {
    const now = performance.now();
    state = setPeek(state, false);
    view.feedbackEcho = null;
    view.deckState = DEMO_DECK_STATE;
    view.nextSuggestion = DEMO_NEXT_SUGGESTION;
    view.handledNextKey = "";
    view.handledNextRenderKey = "";
    state = applyFrame(state, pillDemoReactionFrame(key), now);
    demoReturnIdleAt = state.collapseAt;
    demoDeckHoldUntil = state.collapseAt;
    root.focus({ preventScroll: true });
  });

  // ── Collapsed-hover / focus PEEK (Phase-1b) — pointer-enter/leave and
  // keyboard focus flip the pure `peek` flag; render() reads it into data-peek
  // for the CSS ease-out reveal. We target the whole pill so the next-track
  // glance is reachable anywhere on the lozenge, including keyboard focus.
  // peek is orthogonal to the expand state machine — it only toggles the
  // floating peek card, never the expand panel. ─────────────────────────────
  root.addEventListener("pointerenter", () => {
    state = setPeek(state, true);
  });
  root.addEventListener("pointerleave", () => {
    state = setPeek(state, false);
  });
  root.addEventListener("focusin", () => {
    if (suppressNextFocusPeek) {
      suppressNextFocusPeek = false;
      return;
    }
    state = setPeek(state, true);
  });
  root.addEventListener("focusout", (ev) => {
    const next = ev.relatedTarget instanceof Node ? ev.relatedTarget : null;
    if (next && root.contains(next)) return;
    state = setPeek(state, false);
  });
  root.addEventListener("keydown", (ev) => {
    if (
      !pillPeekHandlePrimaryActionKey(
        root,
        state.peek,
        hasRenderableSuggestion(effectiveNextSuggestion(view)),
        ev,
      )
    ) {
      return;
    }
    view.onPeekPrimaryAction?.();
  });
  root.addEventListener("click", (ev) => {
    if (
      !pillPeekHandlePrimaryActionClick(
        root,
        state.peek,
        hasRenderableSuggestion(effectiveNextSuggestion(view)),
        ev,
      )
    ) {
      return;
    }
    view.onPeekPrimaryAction?.();
  });
  document.addEventListener("keydown", (ev) => {
    if (!pillPeekHandleCloseKey(state.peek, ev)) return;
    closePeekToRoot();
  });

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
      const prevMode = state.mode;
      state = reduceFrame(state, msg, performance.now());
      // Category 4 — pill state-machine transition (frame-driven). Only logs
      // on an actual mode change so the 30Hz reader frames don't spam.
      if (state.mode !== prevMode) {
        vmxLog("[vmx:state]", `pill ${prevMode} → ${state.mode}`, {
          trigger: "frame",
          cohostStatus: state.cohostStatus,
        });
      }
      // deck_state is read-only meta riding the SAME flat 30Hz frame as
      // voice/cohost_status (62-03 _serialize_deck_state). WR-03: REPLACE (not
      // merge) view.deckState with the latest carried map — including an empty
      // {} on a deck unload, which CLEARS the chips back to `decks · unknown`
      // (no stale resolved key lingers). A frame that OMITS deck_state returns
      // null and we hold the last map (a bridged snapshot says nothing about
      // decks, so it must not wipe them).
      const ds = readDeckState(msg);
      if (
        ds !== null &&
        (demoDeckHoldUntil === null || performance.now() >= demoDeckHoldUntil)
      ) {
        view.deckState = ds;
      }
      // next_suggestion rides the SAME flat 30Hz frame. Tri-state read: omitted
      // (undefined) → hold last; explicit null → clear (honest silence); object
      // → the grounded pick. Only an object/null UPDATES the held value, so a
      // bridged snapshot (which omits the field) never wipes the suggestion.
      const ns = readNextSuggestion(msg);
      if (ns !== undefined) {
        if (pillFeedbackShouldClearForSuggestion(view.feedbackEcho, ns)) {
          view.feedbackEcho = null;
        }
        view.nextSuggestion = ns;
        if (ns === null && pillShouldClearHandledNextOnNull(DEMO_NEXT_ENABLED)) {
          view.handledNextKey = "";
          view.handledNextRenderKey = "";
        }
      }
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
    const prevMode = state.mode;
    state = tickCollapse(state, now);
    if (demoReturnIdleAt !== null && now >= demoReturnIdleAt && state.mode !== "expand") {
      state = applyFrame(state, pillDemoReturnFrame(), now);
      state = setPeek(state, false);
      if (view.demoControls) syncPillDemoControlsActive(view.demoControls, null);
      demoReturnIdleAt = null;
      demoDeckHoldUntil = null;
    }
    // Category 4 — data-driven expand→collapse transition.
    if (state.mode !== prevMode) {
      vmxLog("[vmx:state]", `pill ${prevMode} → ${state.mode}`, {
        trigger: "collapse-timeout",
        cohostStatus: state.cohostStatus,
      });
    }

    render(view, state, pillFaceLabel(state.mode, state.cohostStatus), now);

    // Waveform: real voice.rms while speaking (or expanded over a speaking
    // base), floored to a low baseline between phrases — never zero, never a
    // fake loop. Suppressed (0) otherwise.
    const speakingNow =
      state.mode === "speaking" ||
      (state.mode === "expand" && state.cohostStatus === "TALKING");
    if (speakingNow) {
      const rms = Math.max(WAVE_BASELINE_RMS, state.voiceRms);
      setWaveform(view.waveEl, rms, state.voicePeak);
    } else {
      setWaveform(view.waveEl, 0, null);
    }

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
