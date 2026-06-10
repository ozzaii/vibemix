/* next-suggestion.ts — the pill "what's next" card (PILL next-suggestion, Phase 1).
 *
 * Renders ONE grounded next-track suggestion in the pill's expand panel, BELOW
 * the deck-context chips. The wire field `next_suggestion` (ws_bus.py serialize
 * edge, fed by runtime/suggestion.py::SuggestionService) carries either a
 * suggestion object or `null`. The load-bearing contract is HONEST SILENCE: a
 * `null` suggestion renders NOTHING (returns `null`) — the pill never shows a
 * fabricated "next track". Only ids the engine resolved in BOTH the vector store
 * AND the live library ever reach this renderer (Cardinal Invariant #2).
 *
 * 20/80 accent discipline: the ONLY brand-rose accent on this card is the `↑`
 * next-glyph, the single actionable signal "this is your next move". Gold is
 * quarantined to Camelot/heat numerics and never appears on this card.
 *
 * Cloned from deck-chips.ts: the same `registerStyle` once-per-scope injection,
 * the JetBrains-Mono tabular-nums data vocabulary via `var(--type-mono)` (never
 * a raw font name — design-slop gate), tokens-only CSS (no raw hex), the
 * `_CSS_FOR_TEST` grep-able assert, and `textContent`-only rendering (no
 * innerHTML — no HTML-injection path from wire values). Pure DOM construction,
 * no timers/state. Vitest under jsdom.
 */

import { registerStyle } from "../session/components/_style-registry.js";

export interface NextSuggestionTransitionWire {
  candidate_id?: string;
  source_deck?: string | null;
  target_deck?: string | null;
  from_track_id?: string;
  to_track_id?: string;
  from_section_id?: string;
  to_section_id?: string;
  from_role?: string | null;
  to_role?: string | null;
  from_start_s?: number | null;
  from_end_s?: number | null;
  to_start_s?: number | null;
  to_end_s?: number | null;
  from_bpm?: number | null;
  to_bpm?: number | null;
  from_camelot?: string | null;
  to_camelot?: string | null;
  cue_slot?: string | null;
  cue_source?: string | null;
  start_in_bars?: number | null;
  score?: number | null;
  confidence?: number | null;
  semantic_basis?: string | null;
  source_selection?: string | null;
  selection_score?: number | null;
  selection_basis?: string | null;
  scores?: Record<string, number | null>;
  timing_basis?: string | null;
  timing_anchor?: string | null;
  source_anchor_s?: number | null;
  risk_flags?: string[];
  reasons?: string[];
}

export interface NextSuggestionDecisionWire {
  decision_id?: string;
  decision_source?: string;
  emitted?: boolean;
  validation_status?: string;
  validation_errors?: string[];
  action?: "select" | "hold" | "suppress" | "ask" | string;
  candidate_id?: string | null;
  cue_slot?: string | null;
  timing_text?: string | null;
  spoken_text?: string;
  cited_claims?: string[];
  cited_claim_ids?: string[];
  confidence?: number | null;
}

export interface NextSuggestionRenderOptions {
  density?: "full" | "peek";
  onPrimaryAction?: () => void;
}

/** The `next_suggestion` wire payload — mirrors
 *  `vibemix.library.next_suggestion.NextSuggestion.to_dict()`.
 *  `camelot`/`bpm` are `null` for folder-only libraries (honest-null). */
export interface NextSuggestionWire {
  track_id: string;
  title: string;
  artist: string;
  similarity: number;
  why: string;
  camelot: string | null;
  bpm: number | null;
  transition?: NextSuggestionTransitionWire | null;
  decision?: NextSuggestionDecisionWire | null;
}

const CSS = `
  .vmx-next-card {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: var(--sp-1);
    margin: 0;
    padding: var(--sp-2);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    background: var(--glass-3);
    overflow: hidden;
    box-shadow:
      inset 0 1px 0 var(--lg-spec-mid),
      inset 0 -1px 0 var(--lg-rim-void);
  }
  .vmx-next-card::before {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(115deg, var(--lg-spec-lo), transparent 54%);
    pointer-events: none;
  }
  /* The micro-label row: "next ↑" — uppercase mono, dim. The ↑ glyph is the
   * single brand-rose accent on the card (20/80 — the actionable "do this
   * next" signal, the one place the eye is guided). */
  .vmx-next-card__label {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: var(--sp-1);
    font-family: var(--type-mono);
    font-size: 9px;
    letter-spacing: 0.12em;
    line-height: 1;
    text-transform: uppercase;
    color: var(--silk-40);
  }
  .vmx-next-card__glyph {
    color: var(--brand);
    font-variant-numeric: tabular-nums;
  }
  .vmx-next-card__peek-action {
    margin-left: auto;
    padding: 1px 5px 0;
    border: 1px solid var(--brand-22);
    border-radius: 999px;
    background: var(--brand-08);
    color: var(--brand-glow);
    font-size: 8px;
    line-height: 1.2;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    box-shadow: inset 0 1px 0 var(--lg-spec-mid);
  }
  .vmx-next-card__peek-action[data-care="true"] {
    border-color: var(--led-warn);
    background: var(--glass-2);
    color: var(--led-warn);
  }
  /* The track title — the brightest silk ink on the card (hierarchy via tone +
   * size, NOT a second accent color). Truncates rather than wrapping the pill. */
  .vmx-next-card__title {
    position: relative;
    font-family: var(--type-mono);
    font-size: 11px;
    line-height: 1.2;
    color: var(--silk);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  /* artist + "why" (similar vibe · 8a · 128) — dim mono meta, tabular for the
   * numbers. Honest-null is upstream: "similar vibe" alone when no key/bpm. */
  .vmx-next-card__meta {
    position: relative;
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-size: 10px;
    letter-spacing: 0.04em;
    line-height: 1.2;
    color: var(--silk-65);
    text-transform: lowercase;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .vmx-next-card__transition {
    position: relative;
    width: fit-content;
    max-width: 100%;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    column-gap: 0;
    row-gap: 2px;
    padding-top: 1px;
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-size: 10px;
    letter-spacing: 0.04em;
    line-height: 1.25;
    color: var(--silk-65);
    overflow: visible;
    text-overflow: clip;
    white-space: normal;
  }
  .vmx-next-card__transition-bit {
    white-space: nowrap;
  }
  .vmx-next-card__why {
    min-width: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 3px;
    overflow: hidden;
    color: var(--silk-40);
    font-family: var(--type-mono);
    font-size: 9px;
    letter-spacing: 0.04em;
    line-height: 1.2;
  }
  .vmx-next-card__why-chip {
    flex: 0 0 auto;
    min-width: 0;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    border: 1px solid color-mix(in srgb, var(--silk) 13%, transparent);
    border-radius: 4px;
    padding: 1px 4px;
    background: color-mix(in srgb, var(--silk) 4%, transparent);
  }
  .vmx-next-card__cue-rail {
    position: relative;
    display: block;
    width: 100%;
    height: 2px;
    margin-top: 1px;
    border-radius: 999px;
    background: var(--glass-2);
    overflow: hidden;
  }
  /* Cue progress stays in the brand lane (press -> rose). Gold is reserved
   * for Camelot/heat numerics; a progress fill is neither. */
  .vmx-next-card__cue-rail::after {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--brand-press), var(--brand));
    opacity: 0.72;
    transform: scaleX(var(--cue-rail-scale, 0));
    transform-origin: left center;
  }
`;

registerStyle("vmx-next-card", CSS);

/** Test-only — exposed so the contract test can grep the registered CSS for
 *  token usage + reject hex / non-black rgba (frontend-enforcement). Mirrors
 *  deck-chips.ts / waveform.ts `_CSS_FOR_TEST`. */
export const _CSS_FOR_TEST = CSS;

/**
 * Build the meta line: `<artist> · <why>` ("artist · similar vibe · 8a · 128").
 * The artist is dropped when empty (folder-only tracks often have none) so we
 * never render a dangling " · ". The `why` already carries the honest key/bpm
 * (or just "similar vibe") from the engine — passed through verbatim, never
 * recomputed or fabricated here.
 */
export function nextMetaText(s: {
  artist: string;
  why: string;
}): string {
  const artist = s.artist.trim();
  const why = s.why.trim();
  return artist ? `${artist} · ${why}` : why;
}

export function nextTransitionText(
  t: NextSuggestionTransitionWire | null | undefined,
): string {
  if (!t) return "";
  const targetDeck = deckLabel(t.target_deck);
  const cue = typeof t.cue_slot === "string" ? t.cue_slot.trim() : "";
  const bits: string[] = [];
  if (targetDeck) bits.push(`load ${targetDeck}`);
  if (cue) {
    const cueTime = formatCueTime(t.to_start_s);
    bits.push(cueTime ? `cue ${cue.toUpperCase()} @ ${cueTime}` : `cue ${cue.toUpperCase()}`);
  }
  const rolePair = rolePairLabel(t.from_role, t.to_role);
  if (rolePair) bits.push(rolePair);
  if (typeof t.start_in_bars === "number" && Number.isFinite(t.start_in_bars)) {
    const bars = Math.max(0, Math.round(t.start_in_bars));
    if (bars === 0) bits.push("now");
    else bits.push(`in ${bars} ${bars === 1 ? "bar" : "bars"}`);
  } else {
    const posture = timingPostureText(t);
    if (posture) bits.push(posture);
  }
  return bits.join(" · ");
}

export function nextReasonReceipt(
  t: NextSuggestionTransitionWire | null | undefined,
): string {
  return nextReasonItems(t).join(" · ");
}

export function nextReasonItems(
  t: NextSuggestionTransitionWire | null | undefined,
): string[] {
  if (!Array.isArray(t?.reasons)) return [];
  return t.reasons
    .map((reason) => cleanDecisionText(reason))
    .filter(Boolean)
    .slice(0, 2);
}

export function nextDecisionText(
  d: NextSuggestionDecisionWire | null | undefined,
  t?: NextSuggestionTransitionWire | null,
): string {
  if (!isRenderableDecision(d, t)) return "";
  const cue = typeof d.cue_slot === "string" ? d.cue_slot.trim() : "";
  const bits: string[] = [];
  const targetDeck = deckLabel(t?.target_deck);
  if (targetDeck) bits.push(`load ${targetDeck}`);
  if (cue) {
    const cueTime = formatCueTime(t?.to_start_s);
    bits.push(cueTime ? `cue ${cue.toUpperCase()} @ ${cueTime}` : `cue ${cue.toUpperCase()}`);
  }
  const rolePair = rolePairLabel(t?.from_role, t?.to_role);
  if (rolePair) bits.push(rolePair);
  const timing = cleanDecisionText(d.timing_text);
  if (timing) bits.push(timing);
  else {
    const posture = timingPostureText(t);
    if (posture) bits.push(posture);
  }
  if (bits.length > 0) return bits.join(" · ");
  return cleanDecisionText(d.spoken_text);
}

function nextFullActionText(
  d: NextSuggestionDecisionWire | null | undefined,
  t: NextSuggestionTransitionWire | null | undefined,
): string {
  return nextDecisionText(d, t) || nextTransitionText(t);
}

function nextPeekActionText(
  d: NextSuggestionDecisionWire | null | undefined,
  t: NextSuggestionTransitionWire | null | undefined,
): string {
  const bits: string[] = [];
  const targetDeck = deckLabel(t?.target_deck);
  if (targetDeck) bits.push(`load ${targetDeck}`);

  const timing = cleanDecisionText(d?.timing_text);
  if (timing) bits.push(timing);
  else if (typeof t?.start_in_bars === "number" && Number.isFinite(t.start_in_bars)) {
    const bars = Math.max(0, Math.round(t.start_in_bars));
    bits.push(bars === 0 ? "now" : `in ${bars} ${bars === 1 ? "bar" : "bars"}`);
  } else {
    const posture = timingPostureText(t);
    if (posture) bits.push(posture);
  }

  if (bits.length > 0) return bits.join(" · ");
  return nextDecisionText(d, t) || nextTransitionText(t);
}

export function nextCueRailScale(t: NextSuggestionTransitionWire | null | undefined): number | null {
  if (typeof t?.start_in_bars !== "number" || !Number.isFinite(t.start_in_bars)) return null;
  const bars = Math.max(0, Math.round(t.start_in_bars));
  if (bars <= 0) return 1;
  const clampedBars = Math.min(16, bars);
  return Math.max(0.08, Math.min(1, (17 - clampedBars) / 16));
}

export function nextSuggestionAriaLabel(
  s: NextSuggestionWire,
  options: Pick<NextSuggestionRenderOptions, "density"> = {},
): string {
  const density = options.density ?? "full";
  const isPeek = density === "peek";
  const actionText = isPeek
    ? nextPeekActionText(s.decision, s.transition)
    : nextDecisionText(s.decision, s.transition) || nextTransitionText(s.transition);
  const reasonItems = nextReasonItems(s.transition);
  const reasonReceipt = reasonItems.join(" · ");
  const fullActionText = isPeek
    ? nextFullActionText(s.decision, s.transition)
    : "";
  const parts = [`next: ${cleanDecisionText(s.title)}`];
  if (!isPeek) {
    const meta = nextMetaText(s);
    if (meta) parts.push(meta);
  }
  if (actionText) parts.push(`action: ${actionText}`);
  if (reasonReceipt) parts.push(`why: ${reasonReceipt}`);
  if (fullActionText && fullActionText !== actionText) parts.push(`detail: ${fullActionText}`);
  return parts.join(". ");
}

export function nextSuggestionPrimaryActionAriaLabel(
  s: NextSuggestionWire,
  options: Pick<NextSuggestionRenderOptions, "density"> = {},
): string {
  const base = nextSuggestionAriaLabel(s, options);
  return `${base}. activate to load suggestion`;
}

function timingPostureText(t: NextSuggestionTransitionWire | null | undefined): string {
  if (!t) return "";
  const sourceSelection = cleanDecisionText(t.source_selection).toLowerCase();
  const riskFlags = Array.isArray(t.risk_flags)
    ? t.risk_flags.map((flag) => cleanDecisionText(flag).toLowerCase())
    : [];
  if (sourceSelection === "loop_hold_section" || riskFlags.includes("source_loop_recent")) {
    return "loop held";
  }
  return "";
}

export function nextSuggestionRenderKey(
  s: NextSuggestionWire | null | undefined,
): string {
  if (!s) return "";
  const t = s.transition;
  const d = s.decision;
  return [
    s.track_id,
    s.title,
    s.artist,
    s.why,
    t?.candidate_id ?? "",
    t?.source_deck ?? "",
    t?.target_deck ?? "",
    t?.from_track_id ?? "",
    t?.to_track_id ?? "",
    t?.from_section_id ?? "",
    t?.to_section_id ?? "",
    t?.from_role ?? "",
    t?.to_role ?? "",
    t?.from_start_s ?? "",
    t?.from_end_s ?? "",
    t?.to_start_s ?? "",
    t?.to_end_s ?? "",
    t?.timing_anchor ?? "",
    t?.source_anchor_s ?? "",
    t?.source_selection ?? "",
    t?.cue_slot ?? "",
    t?.cue_source ?? "",
    t?.start_in_bars ?? "",
    ...(t?.risk_flags ?? []),
    ...(t?.reasons ?? []),
    d?.emitted ?? "",
    d?.validation_status ?? "",
    d?.action ?? "",
    d?.candidate_id ?? "",
    d?.cue_slot ?? "",
    d?.timing_text ?? "",
    d?.spoken_text ?? "",
  ].join("|");
}

function isRenderableDecision(
  d: NextSuggestionDecisionWire | null | undefined,
  t?: NextSuggestionTransitionWire | null,
): d is NextSuggestionDecisionWire {
  if (!d || d.emitted !== true) return false;
  if (d.validation_status !== "accepted") return false;
  if (d.action !== "select") return false;
  const decisionCandidate = cleanDecisionText(d.candidate_id);
  const transitionCandidate = cleanDecisionText(t?.candidate_id);
  if (!decisionCandidate) return false;
  return !transitionCandidate || decisionCandidate === transitionCandidate;
}

function deckLabel(raw: string | null | undefined): string {
  if (typeof raw !== "string") return "";
  const deck = raw.trim().toUpperCase();
  return deck === "A" || deck === "B" ? deck : "";
}

function cleanDecisionText(raw: string | null | undefined): string {
  if (typeof raw !== "string") return "";
  return raw.trim().replace(/\s+/g, " ");
}

function formatCueTime(raw: number | null | undefined): string {
  if (typeof raw !== "number" || !Number.isFinite(raw)) return "";
  const total = Math.max(0, Math.round(raw));
  const minutes = Math.floor(total / 60);
  const seconds = String(total % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function rolePairLabel(
  fromRole: string | null | undefined,
  toRole: string | null | undefined,
): string {
  const from = normalizeRoleLabel(fromRole);
  const to = normalizeRoleLabel(toRole);
  return from && to ? `${from}→${to}` : "";
}

function normalizeRoleLabel(raw: string | null | undefined): string {
  if (typeof raw !== "string") return "";
  const role = raw.trim().toLowerCase();
  if (!role || role === "unknown") return "";
  return role.replace(/[_-]+/g, " ");
}

/**
 * Render the next-suggestion card from the `next_suggestion` wire field.
 *
 * - `null` / `undefined` → returns `null`: HONEST SILENCE (the pill shows no
 *   card rather than a fabricated track). The caller's
 *   `if (card) mount.append(card)` guard handles it.
 * - A suggestion → a card: the "next ↑" label, the title, and the
 *   `<artist> · <why>` meta line. All text via `textContent` (no innerHTML).
 */
export function renderNextSuggestion(
  s: NextSuggestionWire | null | undefined,
  options: NextSuggestionRenderOptions = {},
): HTMLDivElement | null {
  if (!s || !s.track_id || !s.title) return null; // honest silence

  const density = options.density ?? "full";
  const isPeek = density === "peek";
  const root = document.createElement("div");
  root.className = "vmx-next-card";
  root.dataset.density = density;
  root.dataset.wire = "pill.next-card";
  const assistiveLabel = isPeek && options.onPrimaryAction
    ? nextSuggestionPrimaryActionAriaLabel(s, { density })
    : nextSuggestionAriaLabel(s, { density });
  root.setAttribute("aria-label", assistiveLabel);
  if (isPeek && options.onPrimaryAction) {
    root.dataset.interactive = "true";
    root.tabIndex = 0;
    root.setAttribute("role", "button");
    root.setAttribute("aria-keyshortcuts", "Enter Space");
    root.addEventListener("click", (ev) => {
      if ((ev.target as HTMLElement | null)?.closest("button")) return;
      ev.preventDefault();
      ev.stopPropagation();
      options.onPrimaryAction?.();
    });
    root.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter" && ev.key !== " ") return;
      ev.preventDefault();
      ev.stopPropagation();
      options.onPrimaryAction?.();
    });
  } else if (isPeek) {
    root.setAttribute("role", "status");
    root.setAttribute("aria-live", "polite");
  }

  const label = document.createElement("div");
  label.className = "vmx-next-card__label";
  const glyph = document.createElement("span");
  glyph.className = "vmx-next-card__glyph";
  glyph.setAttribute("aria-hidden", "true");
  glyph.textContent = "↑"; // ↑ — the single amber actionable accent
  const labelText = document.createElement("span");
  labelText.textContent = "next";
  label.append(glyph, labelText);
  root.append(label);

  const title = document.createElement("div");
  title.className = "vmx-next-card__title";
  title.textContent = s.title; // verbatim text node — never markup
  title.setAttribute("title", s.title);
  root.append(title);

  if (!isPeek) {
    const meta = document.createElement("div");
    meta.className = "vmx-next-card__meta";
    meta.textContent = nextMetaText(s);
    root.append(meta);
  }

  const reasonItems = nextReasonItems(s.transition);
  const reasonReceipt = reasonItems.join(" · ");
  const actionText = isPeek
    ? nextPeekActionText(s.decision, s.transition)
    : nextDecisionText(s.decision, s.transition) || nextTransitionText(s.transition);
  if (actionText) {
    const transition = document.createElement("div");
    transition.className = "vmx-next-card__transition";
    const fullActionText = nextFullActionText(s.decision, s.transition);
    transition.setAttribute("title", isPeek && fullActionText ? fullActionText : actionText);
    const bits = actionText.split(" · ").filter(Boolean);
    if (bits.length === 0) {
      transition.textContent = actionText;
    } else {
      bits.forEach((bit, index) => {
        const item = document.createElement("span");
        item.className = "vmx-next-card__transition-bit";
        item.textContent = index === 0 ? bit : ` · ${bit}`;
        transition.append(item);
      });
    }
    root.append(transition);

    if (isPeek) {
      const cueScale = nextCueRailScale(s.transition);
      if (cueScale !== null) {
        const rail = document.createElement("span");
        rail.className = "vmx-next-card__cue-rail";
        rail.setAttribute("aria-hidden", "true");
        rail.style.setProperty("--cue-rail-scale", cueScale.toFixed(2));
        root.append(rail);
      }
    }
  }

  if (reasonReceipt) {
    const why = document.createElement("div");
    why.className = "vmx-next-card__why";
    why.dataset.nextWhy = "true";
    why.setAttribute("title", reasonReceipt);
    for (const item of reasonItems) {
      const chip = document.createElement("span");
      chip.className = "vmx-next-card__why-chip";
      chip.textContent = item;
      why.append(chip);
    }
    root.append(why);
  }

  return root;
}
