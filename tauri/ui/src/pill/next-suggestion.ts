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
 * 20/80 accent discipline: the ONLY amber on this card is the `↑` next-glyph,
 * the single actionable signal "this is your next move". Earned move-grade
 * data uses rose for the grade and gold only for the XP heat number.
 *
 * Cloned from deck-chips.ts: the same `registerStyle` once-per-scope injection,
 * the JetBrains-Mono tabular-nums data vocabulary via `var(--type-mono)` (never
 * a raw font name — design-slop gate), tokens-only CSS (no raw hex), the
 * `_CSS_FOR_TEST` grep-able assert, and `textContent`-only rendering (no
 * innerHTML — no HTML-injection path from wire values). Pure DOM construction,
 * no timers/state. Vitest under jsdom.
 */

import { registerStyle } from "../session/components/_style-registry.js";
import {
  PILL_MOVE_GRADE_VOCABULARY,
  normalizePillMoveGradeSlug,
  type MoveGradeSlug,
} from "./move-grade-vocabulary.js";

export type { MoveGradeSlug } from "./move-grade-vocabulary.js";

export interface MoveGradeWire {
  slug?: string;
  label?: string;
  xp?: number | null;
  intensity?: number | null;
  sentiment?: "negative" | "neutral" | "positive" | string;
  reason?: string | null;
  deserved?: boolean;
  overdrive?: boolean;
  confidence?: number | null;
}

export interface MoveGradeView {
  slug: MoveGradeSlug;
  label: string;
  xp: number;
  intensity: number;
  reason: string;
  deserved: boolean;
  overdrive: boolean;
}

export interface MoveGradeProgressView {
  streak: number;
  totalXp: number;
  lastXp: number;
  earned: boolean;
  heat: number;
  level?: number;
  levelXp?: number;
  nextLevelXp?: number;
  levelProgress?: number;
  levelUp?: boolean;
  levelsGained?: number;
}

export interface MoveGradeProgressWire {
  streak?: number | null;
  total_xp?: number | null;
  totalXp?: number | null;
  last_xp?: number | null;
  lastXp?: number | null;
  earned?: boolean | null;
  heat?: number | null;
  level?: number | null;
  level_xp?: number | null;
  levelXp?: number | null;
  next_level_xp?: number | null;
  nextLevelXp?: number | null;
  level_progress?: number | null;
  levelProgress?: number | null;
  level_up?: boolean | null;
  levelUp?: boolean | null;
  levels_gained?: number | null;
  levelsGained?: number | null;
}

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
  cue_confidence?: number | null;
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
  move_grade?: MoveGradeWire | null;
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

export interface NextSuggestionAlternativeWire {
  candidate_id?: string;
  rank?: number;
  selected?: boolean;
  track_id?: string;
  title?: string;
  artist?: string;
  similarity?: number;
  why?: string;
  camelot?: string | null;
  bpm?: number | null;
  transition?: NextSuggestionTransitionWire | null;
}

export type NextSuggestionFeedbackKind = "accept" | "not_now" | "wrong_timing";

export interface NextSuggestionRenderOptions {
  density?: "full" | "peek";
  showAlternatives?: boolean;
  showFeedback?: boolean;
  maxAlternatives?: number;
  gradeProgress?: MoveGradeProgressView | null;
  onAlternativeSelect?: (alt: NextAlternativeView) => void;
  onPrimaryAction?: () => void;
  onFeedback?: (kind: NextSuggestionFeedbackKind) => void;
}

export interface NextSuggestionFeedbackControl {
  kind: NextSuggestionFeedbackKind;
  text: string;
  ariaLabel: string;
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
  transition_alternatives?: NextSuggestionAlternativeWire[];
  grade_progress?: MoveGradeProgressWire | null;
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
   * single amber accent on the card (20/80 — the actionable "do this next"
   * signal, the one place the eye is guided). */
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
    color: var(--amber);
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
  .vmx-next-card__cue-confidence {
    flex: 0 0 auto;
    min-width: 0;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    border: 1px solid color-mix(in srgb, var(--brand) 16%, transparent);
    border-radius: 4px;
    padding: 1px 4px;
    background: color-mix(in srgb, var(--brand) 5%, transparent);
    color: var(--silk-65);
    font-family: var(--type-mono);
    font-size: 9px;
    letter-spacing: 0.04em;
    line-height: 1.2;
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
  .vmx-next-card__cue-rail::after {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--brand), var(--gold));
    opacity: 0.72;
    transform: scaleX(var(--cue-rail-scale, 0));
    transform-origin: left center;
  }
  .vmx-next-card__grade {
    position: relative;
    display: grid;
    grid-template-columns: auto auto minmax(0, 1fr);
    align-items: center;
    gap: var(--sp-1);
    min-width: 0;
    padding-top: 1px;
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-size: 9px;
    line-height: 1.1;
    text-transform: uppercase;
    padding-bottom: 3px;
  }
  .vmx-next-card__grade::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 1px;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--brand), var(--gold));
    transform: scaleX(var(--grade-heat-scale, 0));
    transform-origin: left center;
    opacity: 0.64;
  }
  .vmx-next-card__grade-label {
    position: relative;
    color: var(--brand);
    font-weight: 600;
  }
  .vmx-next-card__grade-xp {
    position: relative;
    color: var(--gold);
  }
  .vmx-next-card__grade-reason {
    position: relative;
    min-width: 0;
    color: var(--silk-40);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .vmx-next-card[data-move-grade="negative"] .vmx-next-card__grade-label {
    color: var(--led-fault);
  }
  .vmx-next-card[data-move-grade="negative"] .vmx-next-card__grade::after {
    background: var(--led-fault);
  }
  .vmx-next-card[data-move-grade="mid"] .vmx-next-card__grade-label {
    color: var(--silk-65);
  }
  .vmx-next-card[data-move-grade="clean"] .vmx-next-card__grade-label,
  .vmx-next-card[data-move-grade="sexy"] .vmx-next-card__grade-label {
    color: var(--brand);
  }
  .vmx-next-card[data-move-grade="bomb"] .vmx-next-card__grade-label,
  .vmx-next-card[data-move-grade="lit_aff"] .vmx-next-card__grade-label {
    color: var(--brand);
  }
  .vmx-next-card[data-grade-overdrive="true"] {
    border-color: var(--brand-40);
    box-shadow:
      inset 0 1px 0 var(--lg-spec-mid),
      inset 0 -1px 0 var(--lg-rim-void),
      0 0 14px var(--brand-22);
  }
  .vmx-next-card[data-grade-level-up="true"] .vmx-next-card__combo-level {
    color: var(--gold);
    text-shadow: 0 0 10px var(--gold-glow);
  }
  .vmx-next-card__combo {
    position: relative;
    display: grid;
    grid-template-columns: auto auto auto minmax(28px, 1fr);
    align-items: center;
    gap: var(--sp-1);
    min-width: 0;
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-size: 9px;
    line-height: 1;
    text-transform: uppercase;
    color: var(--silk-40);
  }
  .vmx-next-card__combo-label {
    color: var(--brand);
  }
  .vmx-next-card__combo-xp {
    color: var(--gold);
  }
  .vmx-next-card__combo-level {
    color: var(--silk-65);
  }
  .vmx-next-card__combo-rail {
    position: relative;
    min-width: 0;
    height: 3px;
    border-radius: 999px;
    background: var(--glass-2);
    overflow: hidden;
  }
  .vmx-next-card__combo-rail::after {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--brand), var(--gold));
    transform: scaleX(var(--combo-level-scale, var(--combo-heat-scale, 0)));
    transform-origin: left center;
  }
  .vmx-next-card__alternatives {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: var(--sp-1);
    margin-top: var(--sp-1);
    padding-top: var(--sp-1);
    border-top: 1px solid var(--glass-edge);
  }
  .vmx-next-card__alt-label {
    font-family: var(--type-mono);
    font-size: 9px;
    letter-spacing: 0.12em;
    line-height: 1;
    text-transform: uppercase;
    color: var(--silk-40);
  }
  .vmx-next-card__alt-row {
    display: flex;
    flex-direction: column;
    gap: 1px;
    min-width: 0;
    width: 100%;
    margin: 0;
    padding: 0;
    border: 0;
    border-radius: var(--rad-sm);
    background: transparent;
    text-align: left;
  }
  button.vmx-next-card__alt-row {
    cursor: pointer;
  }
  button.vmx-next-card__alt-row:hover {
    background: var(--glass-2);
  }
  button.vmx-next-card__alt-row:focus-visible {
    outline: 1px solid var(--silk-40);
    outline-offset: 2px;
  }
  .vmx-next-card__feedback {
    position: relative;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--sp-1);
    margin-top: var(--sp-1);
    padding-top: var(--sp-1);
    border-top: 1px solid var(--glass-edge);
  }
  .vmx-next-card__feedback-btn {
    min-width: 0;
    height: 20px;
    padding: 0 var(--sp-1);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    background: transparent;
    color: var(--silk-40);
    font-family: var(--type-mono);
    font-size: 8px;
    letter-spacing: 0.08em;
    line-height: 1;
    text-transform: uppercase;
    cursor: pointer;
  }
  .vmx-next-card__feedback-btn:hover {
    background: var(--glass-2);
    color: var(--silk-65);
  }
  .vmx-next-card__feedback-btn[aria-pressed="true"],
  .pill[data-feedback="accept"] .vmx-next-card__feedback-btn[data-feedback-kind="accept"],
  .pill[data-feedback="not_now"] .vmx-next-card__feedback-btn[data-feedback-kind="not_now"],
  .pill[data-feedback="wrong_timing"] .vmx-next-card__feedback-btn[data-feedback-kind="wrong_timing"] {
    background: var(--brand-08);
    border-color: var(--brand-40);
    color: var(--brand);
    box-shadow:
      inset 0 1px 0 var(--lg-spec-mid),
      0 0 10px var(--brand-22);
  }
  .vmx-next-card__feedback-btn[data-feedback-kind="not_now"][aria-pressed="true"],
  .pill[data-feedback="not_now"] .vmx-next-card__feedback-btn[data-feedback-kind="not_now"] {
    background: var(--glass-2);
    border-color: var(--glass-edge-up);
    color: var(--silk);
    box-shadow: inset 0 1px 0 var(--lg-spec-mid);
  }
  .vmx-next-card__feedback-btn[data-feedback-kind="wrong_timing"][aria-pressed="true"],
  .pill[data-feedback="wrong_timing"] .vmx-next-card__feedback-btn[data-feedback-kind="wrong_timing"] {
    border-color: var(--led-warn);
    color: var(--led-warn);
    box-shadow:
      inset 0 1px 0 var(--lg-spec-mid),
      0 0 10px var(--glass-edge-up);
  }
  .vmx-next-card__feedback-btn:focus-visible {
    outline: 1px solid var(--silk-40);
    outline-offset: 2px;
  }
  .vmx-next-card__alt-title,
  .vmx-next-card__alt-meta {
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .vmx-next-card__alt-title {
    font-size: 10px;
    letter-spacing: 0.04em;
    line-height: 1.2;
    color: var(--silk-65);
  }
  .vmx-next-card__alt-meta {
    font-size: 9px;
    letter-spacing: 0.04em;
    line-height: 1.2;
    color: var(--silk-40);
    text-transform: lowercase;
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

function cueSourceLabel(source: string): string {
  const normalized = source.trim().toLowerCase().replace(/[\s-]+/g, "_");
  if (normalized === "dj" || normalized === "user" || normalized === "hotcue") {
    return "DJ cue";
  }
  if (normalized === "rekordbox" || normalized === "rb") return "Rekordbox cue";
  if (normalized === "auto") return "auto cue";
  if (normalized === "fallback") return "fallback entry";
  if (normalized === "anlz") return "analysis cue";
  return "cue";
}

function cueConfidencePhrase(
  source: string,
  confidence: number | null | undefined,
): string {
  const normalized = source.trim().toLowerCase().replace(/[\s-]+/g, "_");
  if (typeof confidence !== "number" || !Number.isFinite(confidence)) {
    if (
      normalized === "dj"
      || normalized === "user"
      || normalized === "rekordbox"
      || normalized === "rb"
    ) {
      return "locked";
    }
    return "confidence unknown";
  }
  const value = Math.max(0, Math.min(1, confidence));
  if (value >= 0.85) return "locked";
  if (value >= 0.65) return "usable";
  if (value >= 0.45) return "needs review";
  return "low confidence";
}

export function nextCueConfidenceReceipt(
  t: NextSuggestionTransitionWire | null | undefined,
): string {
  if (!t) return "";
  const source = cleanDecisionText(t.cue_source);
  const cue = typeof t.cue_slot === "string" ? t.cue_slot.trim() : "";
  const hasConfidence = typeof t.cue_confidence === "number" && Number.isFinite(t.cue_confidence);
  if (!source && !hasConfidence) return "";
  const label = cueSourceLabel(source || "cue");
  const cueLabel = cue ? ` ${cue.toUpperCase()}` : "";
  return `${label}${cueLabel} ${cueConfidencePhrase(source, t.cue_confidence)}`;
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
  options: Pick<NextSuggestionRenderOptions, "density" | "gradeProgress"> = {},
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
  const grade = nextMoveGrade(s);
  const gradeProgress = grade ? nextMoveGradeProgress(s, options.gradeProgress ?? null) : null;
  const parts = [`next: ${cleanDecisionText(s.title)}`];
  if (!isPeek) {
    const meta = nextMetaText(s);
    if (meta) parts.push(meta);
  }
  if (actionText) parts.push(`action: ${actionText}`);
  const cueReceipt = nextCueConfidenceReceipt(s.transition);
  if (cueReceipt) parts.push(`cue: ${cueReceipt}`);
  if (reasonReceipt) parts.push(`why: ${reasonReceipt}`);
  if (fullActionText && fullActionText !== actionText) parts.push(`detail: ${fullActionText}`);
  if (grade) {
    parts.push(
      grade.deserved
        ? `grade: ${grade.label}, ${grade.xp} xp, ${grade.reason}`
        : `care: ${grade.reason}`,
    );
  }
  if (!isPeek && gradeProgress?.earned) {
    parts.push(
      `session: ${gradeProgress.totalXp} xp, combo ${Math.max(1, gradeProgress.streak)}`,
    );
  }
  return parts.join(". ");
}

export function nextSuggestionPrimaryActionAriaLabel(
  s: NextSuggestionWire,
  options: Pick<NextSuggestionRenderOptions, "density" | "gradeProgress"> = {},
): string {
  const base = nextSuggestionAriaLabel(s, options);
  const grade = nextMoveGrade(s);
  const intent = nextSuggestionPrimaryActionText(grade) === "care"
    ? "activate to accept with care"
    : "activate to keep suggestion";
  return `${base}. ${intent}`;
}

export function nextSuggestionPrimaryActionText(grade: MoveGradeView | null): "care" | "keep" {
  return grade !== null && !grade.deserved ? "care" : "keep";
}

export function nextMoveGrade(
  s: NextSuggestionWire | null | undefined,
): MoveGradeView | null {
  if (!s) return null;
  return moveGradeViewFromTransition(s.transition);
}

export function nextMoveGradeProgress(
  s: NextSuggestionWire | null | undefined,
  fallback: MoveGradeProgressView | null = null,
): MoveGradeProgressView | null {
  const raw = s?.grade_progress;
  if (!raw || typeof raw !== "object") return fallback;
  const streak = clampInt(raw.streak, 0, 999, fallback?.streak ?? 0);
  const totalXp = clampInt(raw.total_xp ?? raw.totalXp, 0, 999_999, fallback?.totalXp ?? 0);
  const lastXp = clampInt(raw.last_xp ?? raw.lastXp, 0, 999, fallback?.lastXp ?? 0);
  const heat = clampInt(raw.heat, 0, 100, fallback?.heat ?? 0);
  const earned = typeof raw.earned === "boolean" ? raw.earned : streak > 0 && lastXp > 0;
  const derivedLevel = pillXpLevel(totalXp);
  const nextLevelXp = clampInt(
    raw.next_level_xp ?? raw.nextLevelXp,
    1,
    999_999,
    fallback?.nextLevelXp ?? derivedLevel.nextLevelXp,
  );
  const levelXp = clampInt(
    raw.level_xp ?? raw.levelXp,
    0,
    nextLevelXp,
    fallback?.levelXp ?? Math.min(derivedLevel.levelXp, nextLevelXp),
  );
  const levelProgress = clampInt(
    raw.level_progress ?? raw.levelProgress,
    0,
    100,
    fallback?.levelProgress ?? Math.round((levelXp / nextLevelXp) * 100),
  );
  const levelUp =
    typeof raw.level_up === "boolean"
      ? raw.level_up
      : typeof raw.levelUp === "boolean"
        ? raw.levelUp
        : false;
  return {
    streak,
    totalXp,
    lastXp,
    earned,
    heat,
    level: clampInt(raw.level, 1, 999, fallback?.level ?? derivedLevel.level),
    levelXp,
    nextLevelXp,
    levelProgress,
    levelUp,
    levelsGained: clampInt(
      raw.levels_gained ?? raw.levelsGained,
      0,
      999,
      levelUp ? 1 : 0,
    ),
  };
}

export function nextSuggestionFeedbackControls(
  grade: MoveGradeView | null,
): NextSuggestionFeedbackControl[] {
  const primaryAction = nextSuggestionPrimaryActionText(grade);
  return [
    {
      kind: "accept",
      text: primaryAction,
      ariaLabel:
        primaryAction === "care" ? "mark suggestion accepted with care" : "mark suggestion accepted",
    },
    {
      kind: "not_now",
      text: "later",
      ariaLabel: "mark suggestion not now",
    },
    {
      kind: "wrong_timing",
      text: "timing",
      ariaLabel: "mark suggestion timing wrong",
    },
  ];
}

export const PILL_XP_LEVEL_STEP = 250;

export function pillXpLevel(totalXp: number): Required<
  Pick<MoveGradeProgressView, "level" | "levelXp" | "nextLevelXp" | "levelProgress">
> {
  const total = clampInt(totalXp, 0, 999_999, 0);
  const level = Math.min(999, Math.floor(total / PILL_XP_LEVEL_STEP) + 1);
  const levelXp = total % PILL_XP_LEVEL_STEP;
  return {
    level,
    levelXp,
    nextLevelXp: PILL_XP_LEVEL_STEP,
    levelProgress: Math.round((levelXp / PILL_XP_LEVEL_STEP) * 100),
  };
}

export function moveGradeViewFromTransition(
  t: NextSuggestionTransitionWire | null | undefined,
): MoveGradeView | null {
  const raw = t?.move_grade;
  if (!raw || typeof raw !== "object") return null;
  const slug = normalizePillMoveGradeSlug(raw.slug);
  if (!slug) return null;
  const vocabulary = PILL_MOVE_GRADE_VOCABULARY[slug];
  const intensity = clampInt(raw.intensity, 0, 100, vocabulary.intensity);
  return {
    slug,
    label: moveGradeLabel(raw.label, slug),
    xp: clampInt(raw.xp, 0, 999, vocabulary.xp),
    intensity,
    reason: cleanDecisionText(raw.reason) || vocabulary.reason,
    deserved:
      typeof raw.deserved === "boolean"
        ? raw.deserved
        : vocabulary.deserved,
    overdrive: typeof raw.overdrive === "boolean" ? raw.overdrive : vocabulary.overdrive,
  };
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

function moveGradeLabel(raw: string | undefined, slug: MoveGradeSlug): string {
  const label = cleanDecisionText(raw).toUpperCase();
  if (!label) return PILL_MOVE_GRADE_VOCABULARY[slug].label;
  return label.slice(0, 12);
}

function clampInt(raw: unknown, min: number, max: number, fallback: number): number {
  if (typeof raw !== "number" || !Number.isFinite(raw)) return fallback;
  return Math.max(min, Math.min(max, Math.round(raw)));
}

export interface NextAlternativeView {
  key: string;
  candidateId: string;
  trackId: string;
  title: string;
  meta: string;
}

export function nextAlternativeViews(
  s: NextSuggestionWire | null | undefined,
  limit = 2,
): NextAlternativeView[] {
  if (!s || limit <= 0) return [];
  const selectedCandidate = cleanDecisionText(s.decision?.candidate_id)
    || cleanDecisionText(s.transition?.candidate_id);
  const selectedTrack = cleanDecisionText(s.track_id);
  const rows: NextAlternativeView[] = [];
  for (const alt of s.transition_alternatives ?? []) {
    if (rows.length >= limit) break;
    if (!alt || alt.selected === true) continue;
    const candidateId = cleanDecisionText(alt.candidate_id);
    const trackId = cleanDecisionText(alt.track_id);
    if (candidateId && candidateId === selectedCandidate) continue;
    if (trackId && trackId === selectedTrack) continue;
    const title = cleanDecisionText(alt.title);
    if (!candidateId || !title) continue;
    const rank = typeof alt.rank === "number" && Number.isFinite(alt.rank)
      ? Math.max(1, Math.round(alt.rank))
      : rows.length + 2;
    rows.push({
      key: candidateId,
      candidateId,
      trackId,
      title: `${String(rank).padStart(2, "0")} · ${title}`,
      meta: nextAlternativeMeta(alt),
    });
  }
  return rows;
}

export function nextSuggestionRenderKey(
  s: NextSuggestionWire | null | undefined,
): string {
  if (!s) return "";
  const t = s.transition;
  const d = s.decision;
  const p = s.grade_progress;
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
    t?.cue_confidence ?? "",
    t?.start_in_bars ?? "",
    t?.move_grade?.slug ?? "",
    t?.move_grade?.label ?? "",
    t?.move_grade?.xp ?? "",
    t?.move_grade?.intensity ?? "",
    t?.move_grade?.reason ?? "",
    t?.move_grade?.deserved ?? "",
    t?.move_grade?.overdrive ?? "",
    p?.streak ?? "",
    p?.total_xp ?? p?.totalXp ?? "",
    p?.last_xp ?? p?.lastXp ?? "",
    p?.earned ?? "",
    p?.heat ?? "",
    p?.level ?? "",
    p?.level_xp ?? p?.levelXp ?? "",
    p?.next_level_xp ?? p?.nextLevelXp ?? "",
    p?.level_progress ?? p?.levelProgress ?? "",
    p?.level_up ?? p?.levelUp ?? "",
    p?.levels_gained ?? p?.levelsGained ?? "",
    ...(t?.risk_flags ?? []),
    ...(t?.reasons ?? []),
    d?.emitted ?? "",
    d?.validation_status ?? "",
    d?.action ?? "",
    d?.candidate_id ?? "",
    d?.cue_slot ?? "",
    d?.timing_text ?? "",
    d?.spoken_text ?? "",
    ...(s.transition_alternatives ?? []).flatMap((alt) => [
      alt?.candidate_id ?? "",
      alt?.rank ?? "",
      alt?.selected ?? "",
      alt?.track_id ?? "",
      alt?.title ?? "",
      alt?.camelot ?? "",
      alt?.bpm ?? "",
      alt?.transition?.candidate_id ?? "",
      alt?.transition?.target_deck ?? "",
      alt?.transition?.to_start_s ?? "",
      alt?.transition?.cue_slot ?? "",
      alt?.transition?.start_in_bars ?? "",
      alt?.transition?.move_grade?.slug ?? "",
      alt?.transition?.move_grade?.label ?? "",
      alt?.transition?.move_grade?.xp ?? "",
      alt?.transition?.move_grade?.intensity ?? "",
      alt?.transition?.move_grade?.reason ?? "",
    ]),
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

function nextAlternativeMeta(alt: NextSuggestionAlternativeWire): string {
  const bits: string[] = [];
  const transitionText = nextTransitionText(alt.transition);
  if (transitionText) bits.push(transitionText.replace(/^load [AB] · /, ""));
  const camelot = cleanDecisionText(alt.camelot).toLowerCase();
  if (camelot) bits.push(camelot);
  if (typeof alt.bpm === "number" && Number.isFinite(alt.bpm)) {
    bits.push(String(Math.round(alt.bpm)));
  }
  if (bits.length > 0) return bits.join(" · ");
  return cleanDecisionText(alt.why);
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
  const moveGrade = nextMoveGrade(s);
  const gradeProgress = moveGrade ? nextMoveGradeProgress(s, options.gradeProgress ?? null) : null;
  const assistiveLabel = isPeek && options.onPrimaryAction
    ? nextSuggestionPrimaryActionAriaLabel(s, { density, gradeProgress })
    : nextSuggestionAriaLabel(s, { density, gradeProgress });
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
  if (moveGrade) {
    root.dataset.moveGrade = moveGrade.slug;
    root.dataset.gradeDeserved = moveGrade.deserved ? "true" : "false";
    root.dataset.gradeOverdrive = moveGrade.overdrive ? "true" : "false";
    root.style.setProperty("--grade-heat-scale", (moveGrade.intensity / 100).toFixed(2));
    if (gradeProgress) {
      root.dataset.gradeLevelUp = gradeProgress.levelUp ? "true" : "false";
      root.style.setProperty("--combo-heat-scale", (gradeProgress.heat / 100).toFixed(2));
      root.style.setProperty(
        "--combo-level-scale",
        ((gradeProgress.levelProgress ?? pillXpLevel(gradeProgress.totalXp).levelProgress) / 100)
          .toFixed(2),
      );
    }
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
  if (isPeek && options.onPrimaryAction) {
    const primaryAction = nextSuggestionPrimaryActionText(moveGrade);
    const action = document.createElement("span");
    action.className = "vmx-next-card__peek-action";
    action.dataset.care = primaryAction === "care" ? "true" : "false";
    action.setAttribute("aria-hidden", "true");
    action.textContent = primaryAction.toUpperCase();
    label.append(action);
  }
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
  const cueReceipt = nextCueConfidenceReceipt(s.transition);
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

  if (reasonReceipt || cueReceipt) {
    const why = document.createElement("div");
    why.className = "vmx-next-card__why";
    if (reasonReceipt) {
      why.dataset.nextWhy = "true";
      why.setAttribute("title", reasonReceipt);
    }
    if (cueReceipt) {
      const cue = document.createElement("span");
      cue.className = "vmx-next-card__cue-confidence";
      cue.dataset.nextCueConfidence = "true";
      cue.textContent = cueReceipt;
      cue.setAttribute("title", cueReceipt);
      why.append(cue);
    }
    for (const item of reasonItems) {
      const chip = document.createElement("span");
      chip.className = "vmx-next-card__why-chip";
      chip.textContent = item;
      why.append(chip);
    }
    root.append(why);
  }

  if (moveGrade) {
    const grade = document.createElement("div");
    grade.className = "vmx-next-card__grade";
    grade.dataset.wire = "pill.next-grade";

    if (isPeek) {
      const label = document.createElement("span");
      label.className = "vmx-next-card__grade-label";
      label.textContent = moveGrade.label;
      grade.append(label);

      const xp = document.createElement("span");
      xp.className = "vmx-next-card__grade-xp";
      xp.textContent = moveGrade.xp > 0 ? `+${moveGrade.xp}xp` : "0xp";
      grade.append(xp);

      if (!moveGrade.deserved) {
        const reason = document.createElement("span");
        reason.className = "vmx-next-card__grade-reason";
        reason.textContent = moveGrade.reason;
        reason.setAttribute("title", moveGrade.reason);
        grade.append(reason);
      }
      root.append(grade);
    } else {
      const label = document.createElement("span");
      label.className = "vmx-next-card__grade-label";
      label.textContent = moveGrade.label;

      const xp = document.createElement("span");
      xp.className = "vmx-next-card__grade-xp";
      xp.textContent = moveGrade.xp > 0 ? `+${moveGrade.xp}xp` : "0xp";

      const reason = document.createElement("span");
      reason.className = "vmx-next-card__grade-reason";
      reason.textContent = moveGrade.reason;
      reason.setAttribute("title", moveGrade.reason);
      grade.append(label, xp, reason);
      root.append(grade);
    }
  }

  if (moveGrade && gradeProgress && gradeProgress.earned && !isPeek) {
    const combo = document.createElement("div");
    combo.className = "vmx-next-card__combo";
    combo.dataset.wire = "pill.next-combo";

    const label = document.createElement("span");
    label.className = "vmx-next-card__combo-label";
    label.textContent = `combo x${Math.max(1, gradeProgress.streak)}`;

    const xp = document.createElement("span");
    xp.className = "vmx-next-card__combo-xp";
    xp.textContent = `${gradeProgress.totalXp}xp`;

    const level = document.createElement("span");
    level.className = "vmx-next-card__combo-level";
    level.textContent = `lv ${gradeProgress.level ?? pillXpLevel(gradeProgress.totalXp).level}`;

    const rail = document.createElement("span");
    rail.className = "vmx-next-card__combo-rail";
    rail.setAttribute("aria-hidden", "true");

    combo.append(label, xp, level, rail);
    root.append(combo);
  }

  if (options.showAlternatives !== false) {
    const alternatives = nextAlternativeViews(s, options.maxAlternatives ?? 2);
    if (alternatives.length > 0) {
      const group = document.createElement("div");
      group.className = "vmx-next-card__alternatives";
      group.dataset.wire = "pill.next-backups";
      group.setAttribute("aria-label", "backup transition options");

      const altLabel = document.createElement("div");
      altLabel.className = "vmx-next-card__alt-label";
      altLabel.textContent = "backup";
      group.append(altLabel);

      for (const alt of alternatives) {
        const row = document.createElement(options.onAlternativeSelect ? "button" : "div");
        row.className = "vmx-next-card__alt-row";
        row.dataset.candidateId = alt.key;
        if (alt.trackId) row.dataset.trackId = alt.trackId;
        if (options.onAlternativeSelect && row instanceof HTMLButtonElement) {
          row.type = "button";
          row.setAttribute("aria-label", `choose backup ${alt.title}`);
          row.setAttribute("data-no-drag", "");
          row.addEventListener("click", () => options.onAlternativeSelect?.(alt));
        }

        const title = document.createElement("div");
        title.className = "vmx-next-card__alt-title";
        title.textContent = alt.title;

        const meta = document.createElement("div");
        meta.className = "vmx-next-card__alt-meta";
        meta.textContent = alt.meta;

        row.append(title, meta);
        group.append(row);
      }
      root.append(group);
    }
  }

  const showFeedback = options.showFeedback ?? (isPeek ? false : options.showAlternatives !== false);
  if (showFeedback && options.onFeedback) {
    const group = document.createElement("div");
    group.className = "vmx-next-card__feedback";
    group.dataset.wire = "pill.next-feedback";
    group.setAttribute("aria-label", "suggestion feedback");
    for (const { kind, text, ariaLabel } of nextSuggestionFeedbackControls(moveGrade)) {
      const button = document.createElement("button");
      button.className = "vmx-next-card__feedback-btn";
      button.type = "button";
      button.dataset.feedbackKind = kind;
      button.textContent = text;
      button.setAttribute("aria-label", ariaLabel);
      button.setAttribute("aria-pressed", "false");
      button.setAttribute("data-no-drag", "");
      button.addEventListener("click", () => {
        group
          .querySelectorAll<HTMLButtonElement>(".vmx-next-card__feedback-btn")
          .forEach((control) => control.setAttribute("aria-pressed", "false"));
        button.setAttribute("aria-pressed", "true");
        options.onFeedback?.(kind);
      });
      group.append(button);
    }
    root.append(group);
  }

  return root;
}
