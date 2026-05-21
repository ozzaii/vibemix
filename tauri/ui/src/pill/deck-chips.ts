/* deck-chips.ts — PILL-03 (Phase 62 Plan 62-05).
 *
 * Renders the pill's deck-context chips in the expand panel, BELOW the citation
 * strip. Each resolved deck on the 62-03 `deck_state` wire field becomes one
 * `<deck> · <key> · <bpm>` chip ("a · 8a · 128"). The honest-null contract
 * (Phase 59, carried to the UI) is the load-bearing rule: a deck whose `camelot`
 * is `null` on the wire renders `unknown` in dim ink — NEVER a fabricated key.
 * When NO deck resolves (empty `deck_state == {}`) a single `decks · unknown`
 * chip shows. The chip key is passed THROUGH verbatim — the pill never computes
 * or invents a key (the bus already normalized camelot via harmonics.to_camelot).
 *
 * 20/80 amber discipline (frontend-enforcement hard rule 2): the deck-key glyph
 * is amber ONLY when a real key resolved (`vmx-deck-chip__key--resolved`);
 * otherwise it is `--silk-40`. The deck-resolved key glyph is one of the four
 * reserved amber accents on the pill (state dot / waveform / citation chips /
 * resolved key glyph) — amber appears NOWHERE else.
 *
 * Cloned from the citation-strip.ts chip-strip skeleton: the same `registerStyle`
 * once-per-scope CSS injection, the mono tabular-nums chip language (JetBrains
 * Mono, 10px, lowercase), the resting-glow-OFF discipline, the `_CSS_FOR_TEST`
 * grep-able token assert, and the return-`null`-on-degenerate contract so the
 * caller can `if (strip) panel.append(strip)`. Unlike the citation strip the
 * deck strip ALWAYS shows at least the honest `decks · unknown` chip when
 * `deck_state` is present-but-empty (UI-SPEC: present-but-unresolved still shows
 * the honest chip).
 *
 * Wire shape (62-03 `_serialize_deck_state`, ws_bus.py): the flat 30Hz frame
 * carries `deck_state: { "<side>": {title, camelot, key, bpm, confidence} }`.
 * The deck SIDE is the dict key; `camelot`/`key` are `null` when unresolved.
 *
 * Frame content is rendered via `textContent` (text node), NEVER innerHTML'd
 * (T-62-16) — no HTML-injection path from the wire values.
 *
 * Pure DOM construction. No timers, no state, no side effects beyond the DOM
 * build + the one-time style registration. Vitest under jsdom.
 */

import { registerStyle } from "../session/components/_style-registry.js";

/** One deck's wire payload — mirrors `_serialize_deck_state` (ws_bus.py).
 *  `camelot`/`key` are `null` when the deck is unresolved (honest-null). */
export interface DeckWire {
  title: string | null;
  camelot: string | null;
  key: string | null;
  bpm: number | null;
  confidence: number | null;
}

/** The `deck_state` map on the flat frame: deck-side → its wire payload. */
export type DeckStateWire = Record<string, DeckWire>;

const CSS = `
  .vmx-deck-strip {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    /* Inter-chip gap = --sp-2 (8px), the 62-UI-SPEC §Spacing inter-chip token
     * (was an off-grid 6px literal — WR Fix 2). */
    gap: var(--sp-2);
    margin: 0;
    padding: 0;
  }
  .vmx-deck-chip {
    display: inline-flex;
    align-items: center;
    /* Chip content-row height: 20px is the same content row the drag-handle
     * exception is built on (62-UI-SPEC §Spacing: "28px = --sp-2 + 20px content
     * row"). It is a 4-multiple read-height, NOT a spacing token — kept as a
     * documented sub-token content-row height, mirroring how the spec carves
     * out the 20px content row. */
    height: 20px;
    /* Chip horizontal padding = --sp-2 (8px), tokenised (was a raw 8px). */
    padding: 0 var(--sp-2);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    background: var(--glass-3);
    color: var(--silk-65);
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-size: 10px;
    letter-spacing: 0.04em;
    line-height: 1;
    text-transform: lowercase;
    /* Resting glow OFF — like the citation strip, a permanent halo on every
     * deck chip would cumulate into an amber wash. The deck chips are read-only
     * meta, not interactive targets, so there is no hover-lift either. */
    flex-shrink: 0;
  }
  /* The deck-key glyph. Resting = dim --silk-40 (the honest 'unknown' read);
   * amber ONLY on the --resolved variant (20/80 — amber reserved for a real,
   * registry-observed key). */
  .vmx-deck-chip__key {
    color: var(--silk-40);
  }
  .vmx-deck-chip__key--resolved {
    color: var(--amber);
  }
  /* A LOW-confidence resolved key (< the deck cite-floor): the key text still
   * shows (we did resolve it) but amber authority is DROPPED — a barely-sure
   * camelot must not read with the same authority as a registry hit (WR-04,
   * anti-slop). Dim to --silk-40, same ink as the honest 'unknown'. This rule
   * wins over --resolved because --unsure is applied INSTEAD of --resolved when
   * confidence is below the floor. */
  .vmx-deck-chip__key--unsure {
    color: var(--silk-40);
  }
`;

registerStyle("vmx-deck-strip", CSS);

/** Test-only — exposed so the contract test can grep the registered CSS for
 *  token usage + reject hex / non-black rgba (frontend-enforcement). Mirrors
 *  citation-strip.ts / waveform.ts `_CSS_FOR_TEST`. */
export const _CSS_FOR_TEST = CSS;

/** The honest-`unknown` sentinel rendered when a deck/key/bpm is unresolved.
 *  A single source so the chip text + the glyph render the SAME word. */
const UNKNOWN = "unknown";

/** The deck cite-floor (WR-04). A resolved camelot whose `confidence` is BELOW
 *  this reads as dim (--unsure), not full-amber authority — mirrors the v2
 *  `derive_audible_track` `(unsure)` threshold. A `null` confidence is NOT a
 *  penalty (absence of a score ≠ low confidence — a legacy producer that omits
 *  the field keeps authority). */
const CONFIDENCE_FLOOR = 0.6;

/**
 * Build a resolved deck's chip text: `<deck> · <key> · <bpm>` ("a · 8a · 128").
 * Honest-null per PATTERNS / UI-SPEC: `camelot == null` → `unknown` (NEVER a
 * fabricated key); `bpm == null` → `unknown`. The deck side + camelot are
 * lowercased (the CDJ-panel mono data vocabulary); bpm is rounded to an int.
 */
export function deckChipText(d: {
  deck: string;
  camelot: string | null;
  bpm: number | null;
}): string {
  const key = d.camelot ?? UNKNOWN; // NEVER fabricate a key (anti-slop, Phase-59)
  // Honest-null: a non-positive bpm (0 = DeckTrack typed-empty default, or any
  // <=0 that slips the serialize edge) is UNKNOWN — never a fabricated "0 BPM"
  // (CR-02, mirrors the camelot honest-null above).
  const bpm = d.bpm != null && d.bpm > 0 ? Math.round(d.bpm) : UNKNOWN;
  return `${d.deck.toLowerCase()} · ${key.toLowerCase()} · ${bpm}`;
}

/** Build one deck chip element. The key glyph is a separate span so it can carry
 *  the amber-only-when-resolved class (20/80). All text via textContent. */
function buildDeckChip(deck: string, d: DeckWire): HTMLDivElement {
  const chip = document.createElement("div");
  chip.className = "vmx-deck-chip";
  chip.dataset.deck = deck;

  const resolved = d.camelot != null;
  // WR-04: a resolved key BELOW the cite-floor reads as dim (--unsure), not
  // amber. A null confidence keeps authority (absence of score ≠ low score).
  const unsure = resolved && d.confidence != null && d.confidence < CONFIDENCE_FLOOR;
  const keyText = resolved ? d.camelot!.toLowerCase() : UNKNOWN;
  // Honest-null: non-positive bpm is unknown — never a fabricated "0" (CR-02).
  const bpmText = d.bpm != null && d.bpm > 0 ? String(Math.round(d.bpm)) : UNKNOWN;
  const deckText = deck.toLowerCase();

  // `<deck> · ` (text node — never markup)
  chip.append(document.createTextNode(`${deckText} · `));

  // The key glyph — amber ONLY when a real key resolved AT or ABOVE the
  // cite-floor. A low-confidence resolved key is dimmed (--unsure); an
  // unresolved key is the base dim glyph.
  const keyEl = document.createElement("span");
  if (resolved && !unsure) {
    keyEl.className = "vmx-deck-chip__key vmx-deck-chip__key--resolved";
  } else if (unsure) {
    keyEl.className = "vmx-deck-chip__key vmx-deck-chip__key--unsure";
  } else {
    keyEl.className = "vmx-deck-chip__key";
  }
  keyEl.textContent = keyText;
  chip.append(keyEl);

  // ` · <bpm>`
  chip.append(document.createTextNode(` · ${bpmText}`));

  chip.setAttribute(
    "aria-label",
    `deck ${deckText}: key ${keyText}, ${bpmText} bpm`,
  );
  return chip;
}

/** The single honest fallback chip when no deck resolved: `decks · unknown`. */
function buildUnknownChip(): HTMLDivElement {
  const chip = document.createElement("div");
  chip.className = "vmx-deck-chip";
  chip.dataset.deck = "";
  // Text node — the whole chip is dim; it carries NO amber resolved-key glyph.
  chip.textContent = `decks · ${UNKNOWN}`;
  chip.setAttribute("aria-label", "decks: unknown");
  return chip;
}

/**
 * Render the deck-context chip strip from the 62-03 `deck_state` wire field.
 *
 * - One chip per resolved deck (deck-side order), `<deck> · <key> · <bpm>`.
 * - A deck whose `camelot` is null renders `unknown` in dim ink (never a fake
 *   key); its key glyph does NOT carry the amber resolved class.
 * - Empty / null / undefined `deck_state` → a single `decks · unknown` chip
 *   (UI-SPEC: present-but-unresolved still shows the honest chip).
 *
 * Returns an `HTMLDivElement` (always — there is always at least the honest
 * fallback chip). Typed as `| null` for parity with the citation-strip contract
 * so the caller's `if (strip) panel.append(strip)` guard is uniform.
 */
export function renderDeckChips(
  deckState: DeckStateWire | null | undefined,
): HTMLDivElement | null {
  const root = document.createElement("div");
  root.className = "vmx-deck-strip";
  root.setAttribute("aria-label", "deck context");

  const entries = deckState ? Object.entries(deckState) : [];
  if (entries.length === 0) {
    // Honest fallback — no deck resolved → a single dim `decks · unknown` chip.
    root.append(buildUnknownChip());
    return root;
  }

  for (const [deck, d] of entries) {
    root.append(buildDeckChip(deck, d));
  }
  return root;
}
