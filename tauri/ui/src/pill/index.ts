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
  renderNextSuggestion,
  type NextAlternativeView,
  type NextSuggestionFeedbackKind,
  type NextSuggestionWire,
} from "./next-suggestion.js";
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

  // WRITER — cohost-reaction (either the bare or the ipc-prefixed type).
  if (type === "cohost-reaction" || type === "ipc.session.cohost-reaction") {
    const text = typeof m.text === "string" ? m.text : "";
    // WR-06: validate the per-element shape before trusting the wire — a blind
    // `as CitationChip[]` cast lets a malformed frame (`[42, null, {}]`) render
    // `[undefined @ 0:00]` slop. The pill is the trust boundary for what it
    // paints, so filter to well-formed chips (not an injection vector — all
    // chip text is rendered via textContent — but it keeps the strip honest).
    const chips = Array.isArray(m.citation_strip)
      ? (m.citation_strip as unknown[]).filter(isCitationChip)
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
 * Per-element shape guard for a citation chip off the wire (WR-06). The
 * renderer reads `event_id`/`verb`/`timestamp_s` directly, so a chip missing
 * any of them (or of the wrong type) would paint `[undefined @ 0:00]` slop —
 * filter those out at the trust boundary instead of a blind cast.
 */
function isCitationChip(c: unknown): c is CitationChip {
  return (
    c != null &&
    typeof c === "object" &&
    typeof (c as Record<string, unknown>).event_id === "string" &&
    typeof (c as Record<string, unknown>).verb === "string" &&
    typeof (c as Record<string, unknown>).timestamp_s === "number"
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
  /** Latest next_suggestion read off the wire (read-only meta — held on the
   *  view). null = no grounded suggestion (honest silence → no card). */
  nextSuggestion: NextSuggestionWire | null;
  lastNextKey: string;
  /** Render-memo key for the collapsed peek card (Phase-1b). Held per-view (WR-05)
   *  so a peek rebuild only fires when the suggestion changes, not every frame. */
  lastPeekKey: string;
  /** Render-memo keys for the cheap rebuild-only-on-change guards. WR-05: held
   *  PER-VIEW (not module globals) so two pill instances — or two vitest mounts
   *  — can't leak each other's last-render key and skip a legitimate rebuild. */
  lastChipsKey: string;
  lastDeckKey: string;
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
  // While expanded the collapsed label keeps the base state's caption; the
  // expand panel carries the reaction text. We re-derive the base label in
  // render() so "expand" never paints a literal "EXPAND" string.
  expand: "",
};

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
  track_id: "folder:0ef767248648506c",
  title: "UnderCover - Balikali On Acid (Blazy & Doktor Froid Bootleg)",
  artist: "",
  similarity: 0.5817,
  why: "similar vibe",
  camelot: null,
  bpm: null,
};

// Resize-to-content (Phase-1b): the pill window ships fixed at 280×44; the
// expand panel grows via CSS BELOW the collapsed row and would clip against the
// 44px shell. On expand we grow the window down to fit (set_pill_height), back
// to 44 on collapse — so the reaction + citation + next-track never clip. These
// mirror pill_window.rs (PILL_COLLAPSED_H / PILL_MAX_H) and pill.css (the
// .pill__expand max-height cap). The hover peek uses the same resize path so
// the liquid-glass drawer can unfold below the lozenge in the real overlay.
const PILL_COLLAPSED_H = 44;
const PILL_EXPAND_CAP = 220; // matches .pill[data-state="expand"] .pill__expand max-height
const PILL_PEEK_CAP = 156;

function render(view: PillView, state: PillState, baseLabel: string): void {
  // data-state drives the dot pulse cadence + the expand panel visibility (CSS).
  view.root.dataset.state = state.mode;
  view.label.textContent = baseLabel;

  const effectiveNext = effectiveNextSuggestion(view);
  const hasNext = hasRenderableSuggestion(effectiveNext);
  const demoNext = effectiveNext === DEMO_NEXT_SUGGESTION;
  view.root.dataset.hasNext = hasNext ? "true" : "false";
  view.root.dataset.demoNext = demoNext ? "true" : "false";
  const peekVisible =
    COLLAPSED_PEEK_ENABLED && hasNext && state.peek && state.mode !== "expand";
  view.root.dataset.peek = peekVisible ? "true" : "false";
  syncPeekCard(view);

  if (state.mode === "expand") {
    // Reaction text rendered VERBATIM as a text node (T-62-11 — never innerHTML).
    view.reaction.textContent = state.reactionText;
    // Citation strip rendered VERBATIM via the shipped component (T-62-12).
    syncCitationStrip(view, state.chips);
    // Deck-context chips from the LAST seen deck_state — honest unknown when a
    // deck/key is unresolved (PILL-03). renderDeckChips owns the honest-null +
    // amber-only-when-resolved rendering; the pill never fabricates a key (T-62-15).
    syncDeckChips(view);
    // Next-track suggestion card below the deck chips. Honest silence: a null
    // suggestion renders nothing.
    syncNextSuggestion(view);
  }

  // Grow/shrink the window to fit the current content (expand panel) so the
  // reaction + citation + next-track never clip against the 44px shell. Runs
  // after the expand block so the measurement sees the just-rendered content.
  syncWindowHeight(view, state);
}

/** Resize the pill window to fit its content (expand panel) — collapsed 44px
 *  otherwise. Memoised on a cheap layout key so the rAF render never forces a
 *  reflow (scrollHeight) or a redundant Tauri invoke when nothing changed. */
function syncWindowHeight(view: PillView, state: PillState): void {
  const peekOpen = view.root.dataset.peek === "true";
  const key = [
    state.mode,
    peekOpen ? "peek" : "no-peek",
    view.lastChipsKey,
    view.lastPeekKey,
    view.lastNextKey,
    state.reactionText.length,
  ].join("|");
  if (key === view.lastWindowHKey) return;
  view.lastWindowHKey = key;
  let target = PILL_COLLAPSED_H;
  if (state.mode === "expand") {
    // .pill__expand reports full content height via scrollHeight even while the
    // CSS animates max-height open; clamp to the cap, add the collapsed row.
    target = PILL_COLLAPSED_H + Math.min(view.expand.scrollHeight, PILL_EXPAND_CAP);
  } else if (peekOpen) {
    target = PILL_COLLAPSED_H + Math.min(view.peekMount.scrollHeight, PILL_PEEK_CAP);
  }
  if (target === view.lastWindowH) return;
  view.lastWindowH = target;
  void invoke("set_pill_height", { height: target }).catch((e: unknown) =>
    vmxLog("[vmx:error]", "set_pill_height failed", { error: String(e) }),
  );
}

function syncCitationStrip(view: PillView, chips: CitationChip[]): void {
  const expandEl = view.expand;
  // Only rebuild the strip when the chip set changes (cheap key) — the rAF
  // loop calls render() every frame. The memo key lives on the view (WR-05).
  const key = chips.map((c) => `${c.event_id}@${c.timestamp_s}`).join("|");
  if (key === view.lastChipsKey) return;
  view.lastChipsKey = key;
  expandEl.querySelector(".vmx-citation-strip")?.remove();
  expandEl.querySelector(".pill__receipt-rule")?.remove();
  const strip = renderCitationStrip({
    chips,
    // v1: no-op. A future plan deep-links to the debrief at the cited moment.
    onChipClick: () => {},
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
    rule.setAttribute("aria-hidden", "true");
    expandEl.insertBefore(rule, decks);
    expandEl.insertBefore(strip, decks);
  }
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
  mount.replaceChildren();
  const card = renderNextSuggestion(s, {
    showAlternatives: true,
    maxAlternatives: 2,
    onAlternativeSelect: chooseNextSuggestionAlternative,
    onFeedback: sendNextSuggestionFeedback,
  });
  if (card) {
    card.setAttribute("data-no-drag", "");
    mount.append(card);
  }
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
  mount.replaceChildren();
  const card = renderNextSuggestion(s, { showAlternatives: false });
  if (card) {
    card.setAttribute("data-no-drag", "");
    mount.append(card);
  }
}

function effectiveNextSuggestion(view: PillView): NextSuggestionWire | null {
  if (hasRenderableSuggestion(view.nextSuggestion)) return view.nextSuggestion;
  return DEMO_NEXT_ENABLED ? DEMO_NEXT_SUGGESTION : null;
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

function chooseNextSuggestionAlternative(alt: NextAlternativeView): void {
  const message = nextSuggestionChoiceMessage(alt);
  vmxLog("[vmx:ipc>]", "choose next-suggestion backup", message);
  void invoke("forward_ipc_to_sidecar", { message }).catch((err: unknown) => {
    vmxLog("[vmx:error]", "next-suggestion backup choose failed", {
      error: String(err),
    });
  });
}

function sendNextSuggestionFeedback(feedback: NextSuggestionFeedbackKind): void {
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
  const reaction = document.getElementById("pill-reaction");
  const expand = document.getElementById("pill-expand");
  const waveMount = document.getElementById("pill-wave");
  const dragStrip = document.getElementById("pill-drag");
  const decksMount = document.getElementById("pill-decks");
  const peekMount = document.getElementById("pill-peek");
  if (
    !root ||
    !label ||
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
  nextMount.setAttribute("data-no-drag", "");
  decksMount.insertAdjacentElement("afterend", nextMount);

  const view: PillView = {
    root,
    label,
    reaction,
    expand,
    waveMount,
    waveEl,
    decksMount,
    deckState: null,
    nextMount,
    peekMount,
    nextSuggestion: null,
    lastChipsKey: "",
    lastDeckKey: "",
    lastNextKey: "",
    lastPeekKey: "",
    lastWindowHKey: "",
    // Force the first render to send set_pill_height(44). Dev/hot reload can
    // leave the native overlay at the prior expanded height; seeding this with
    // 44 would skip the reset as "unchanged".
    lastWindowH: 0,
  };

  let state = initialPillState(performance.now());

  // ── Collapsed-hover PEEK (Phase-1b) — pointer-enter/leave flips the pure
  // `peek` flag; render() reads it into data-peek for the CSS ease-out reveal.
  // We hover the whole pill (not just a sub-element) so the next-track glance is
  // reachable anywhere on the lozenge. peek is orthogonal to the expand state
  // machine — it only toggles the floating peek card, never the expand panel. ──
  root.addEventListener("pointerenter", () => {
    state = setPeek(state, true);
  });
  root.addEventListener("pointerleave", () => {
    state = setPeek(state, false);
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
      if (ds !== null) view.deckState = ds;
      // next_suggestion rides the SAME flat 30Hz frame. Tri-state read: omitted
      // (undefined) → hold last; explicit null → clear (honest silence); object
      // → the grounded pick. Only an object/null UPDATES the held value, so a
      // bridged snapshot (which omits the field) never wipes the suggestion.
      const ns = readNextSuggestion(msg);
      if (ns !== undefined) view.nextSuggestion = ns;
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
    // Category 4 — data-driven expand→collapse transition.
    if (state.mode !== prevMode) {
      vmxLog("[vmx:state]", `pill ${prevMode} → ${state.mode}`, {
        trigger: "collapse-timeout",
        cohostStatus: state.cohostStatus,
      });
    }

    // Base label tracks the underlying status even while expanded.
    const baseLabel =
      state.mode === "expand"
        ? labelForStatus(state.cohostStatus)
        : (STATE_LABEL[state.mode] ?? "IDLE");
    render(view, state, baseLabel);

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
