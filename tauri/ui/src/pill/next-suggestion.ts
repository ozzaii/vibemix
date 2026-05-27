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
 * 20/80 amber discipline (frontend-enforcement hard rule 2): the ONLY amber on
 * this card is the `↑` next-glyph — the single actionable signal "this is your
 * next move". Everything else is silk ink. Amber appears nowhere else on the
 * card. This is a deliberate reserved accent, the same role amber plays for the
 * resolved-key glyph on deck-chips.ts.
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

export interface NextSuggestionRenderOptions {
  showAlternatives?: boolean;
  maxAlternatives?: number;
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
    padding-top: 1px;
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
  }
  return bits.join(" · ");
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
  if (bits.length > 0) return bits.join(" · ");
  return cleanDecisionText(d.spoken_text);
}

export interface NextAlternativeView {
  key: string;
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
    t?.cue_slot ?? "",
    t?.start_in_bars ?? "",
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

  const root = document.createElement("div");
  root.className = "vmx-next-card";
  root.setAttribute("aria-label", "next track suggestion");

  const label = document.createElement("div");
  label.className = "vmx-next-card__label";
  const glyph = document.createElement("span");
  glyph.className = "vmx-next-card__glyph";
  glyph.textContent = "↑"; // ↑ — the single amber actionable accent
  label.append(glyph, document.createTextNode("next"));
  root.append(label);

  const title = document.createElement("div");
  title.className = "vmx-next-card__title";
  title.textContent = s.title; // verbatim text node — never markup
  root.append(title);

  const meta = document.createElement("div");
  meta.className = "vmx-next-card__meta";
  meta.textContent = nextMetaText(s);
  root.append(meta);

  const actionText = nextDecisionText(s.decision, s.transition) || nextTransitionText(s.transition);
  if (actionText) {
    const transition = document.createElement("div");
    transition.className = "vmx-next-card__transition";
    transition.textContent = actionText;
    root.append(transition);
  }

  if (options.showAlternatives !== false) {
    const alternatives = nextAlternativeViews(s, options.maxAlternatives ?? 2);
    if (alternatives.length > 0) {
      const group = document.createElement("div");
      group.className = "vmx-next-card__alternatives";
      group.setAttribute("aria-label", "backup transition options");

      const altLabel = document.createElement("div");
      altLabel.className = "vmx-next-card__alt-label";
      altLabel.textContent = "backup";
      group.append(altLabel);

      for (const alt of alternatives) {
        const row = document.createElement("div");
        row.className = "vmx-next-card__alt-row";
        row.dataset.candidateId = alt.key;

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

  return root;
}
