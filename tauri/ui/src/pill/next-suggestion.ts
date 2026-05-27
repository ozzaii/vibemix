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
  cue_slot?: string | null;
  start_in_bars?: number | null;
  score?: number | null;
  confidence?: number | null;
  timing_basis?: string | null;
  risk_flags?: string[];
  reasons?: string[];
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
  if (cue) bits.push(`cue ${cue.toUpperCase()}`);
  if (typeof t.start_in_bars === "number" && Number.isFinite(t.start_in_bars)) {
    const bars = Math.max(0, Math.round(t.start_in_bars));
    if (bars === 0) bits.push("now");
    else bits.push(`in ${bars} ${bars === 1 ? "bar" : "bars"}`);
  }
  return bits.join(" · ");
}

export function nextSuggestionRenderKey(
  s: NextSuggestionWire | null | undefined,
): string {
  if (!s) return "";
  const t = s.transition;
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
    t?.cue_slot ?? "",
    t?.start_in_bars ?? "",
  ].join("|");
}

function deckLabel(raw: string | null | undefined): string {
  if (typeof raw !== "string") return "";
  const deck = raw.trim().toUpperCase();
  return deck === "A" || deck === "B" ? deck : "";
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

  const transitionText = nextTransitionText(s.transition);
  if (transitionText) {
    const transition = document.createElement("div");
    transition.className = "vmx-next-card__transition";
    transition.textContent = transitionText;
    root.append(transition);
  }

  return root;
}
