/**
 * @vitest-environment jsdom
 *
 * Phase 62 Plan 05 — pill deck-context chips contract (Task 1, PILL-03).
 *
 * Pins the honest-unknown deck chip surface: each resolved deck on the 62-03
 * `deck_state` wire field renders one `<deck> · <key> · <bpm>` chip
 * ("a · 8a · 128"); an unresolved key/bpm renders `unknown` (NEVER a fabricated
 * key); when NO deck resolves a single `decks · unknown` chip shows. The deck-
 * key glyph is amber ONLY when a real key resolved (--silk-40 otherwise) — the
 * 20/80 amber discipline (frontend-enforcement hard rule 2).
 *
 * Mirrors citation-strip.test.ts / waveform.test.ts: jsdom env (renderDeckChips
 * calls registerStyle → touches document.head), the `_CSS_FOR_TEST` no-hex /
 * amber-token grep, and pure DOM assertions against the rendered HTMLElement.
 *
 * Wire contract (62-03 `_serialize_deck_state`, ws_bus.py): the flat 30Hz frame
 * carries `deck_state: { "<side>": {title, camelot, key, bpm, confidence} }`;
 * `camelot`/`key` are JSON `null` when the deck is unresolved (honest-null,
 * Phase-59 carried to the UI). Empty `deck_state == {}` when nothing resolved.
 */

import { describe, test, expect, beforeEach } from "vitest";

import {
  deckChipText,
  renderDeckChips,
  _CSS_FOR_TEST,
  type DeckStateWire,
} from "./deck-chips.js";

describe("deckChipText — honest-unknown chip text (PILL-03)", () => {
  test("resolved deck → `a · 8a · 128` (lowercase deck + camelot, rounded bpm)", () => {
    expect(deckChipText({ deck: "A", camelot: "8A", bpm: 128 })).toBe(
      "a · 8a · 128",
    );
  });

  test("unresolved key (camelot null) → `a · unknown · 128` (NEVER a fabricated key)", () => {
    expect(deckChipText({ deck: "A", camelot: null, bpm: 128 })).toBe(
      "a · unknown · 128",
    );
  });

  test("unresolved bpm (bpm null) → `a · 8a · unknown`", () => {
    expect(deckChipText({ deck: "A", camelot: "8A", bpm: null })).toBe(
      "a · 8a · unknown",
    );
  });

  test("bpm is rounded (decimal → integer)", () => {
    expect(deckChipText({ deck: "B", camelot: "5A", bpm: 127.6 })).toBe(
      "b · 5a · 128",
    );
  });
});

describe("renderDeckChips — deck_state → chip strip (PILL-03)", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  test("one chip per resolved deck, in deck-side order", () => {
    const deckState: DeckStateWire = {
      A: { title: "Track A", camelot: "8A", key: "C", bpm: 128, confidence: 0.9 },
      B: { title: "Track B", camelot: "5A", key: "G", bpm: 124, confidence: 0.8 },
    };
    const root = renderDeckChips(deckState);
    expect(root).not.toBeNull();
    const chips = root!.querySelectorAll(".vmx-deck-chip");
    expect(chips.length).toBe(2);
    expect(chips[0]?.textContent).toContain("a · 8a · 128");
    expect(chips[1]?.textContent).toContain("b · 5a · 124");
  });

  test("resolved key glyph carries the amber class (20/80 — amber only when resolved)", () => {
    const deckState: DeckStateWire = {
      A: { title: "Track A", camelot: "8A", key: "C", bpm: 128, confidence: 0.9 },
    };
    const root = renderDeckChips(deckState);
    const glyph = root!.querySelector<HTMLElement>(".vmx-deck-chip__key");
    expect(glyph).not.toBeNull();
    expect(glyph!.textContent).toBe("8a");
    expect(glyph!.classList.contains("vmx-deck-chip__key--resolved")).toBe(true);
  });

  test("unknown-key glyph does NOT carry the amber class (dim --silk-40)", () => {
    const deckState: DeckStateWire = {
      A: { title: "Track A", camelot: null, key: null, bpm: 128, confidence: 0.4 },
    };
    const root = renderDeckChips(deckState);
    const glyph = root!.querySelector<HTMLElement>(".vmx-deck-chip__key");
    expect(glyph).not.toBeNull();
    expect(glyph!.textContent).toBe("unknown");
    // 20/80: amber is RESERVED for a resolved key — the unknown glyph is dim.
    expect(glyph!.classList.contains("vmx-deck-chip__key--resolved")).toBe(false);
  });

  test("unknown-bpm renders `unknown` in the chip text", () => {
    const deckState: DeckStateWire = {
      A: { title: "Track A", camelot: "8A", key: "C", bpm: null, confidence: 0.9 },
    };
    const root = renderDeckChips(deckState);
    const chip = root!.querySelector(".vmx-deck-chip");
    expect(chip?.textContent).toContain("a · 8a · unknown");
  });

  test("empty deck_state → a SINGLE `decks · unknown` chip (honest, never a fake key)", () => {
    const root = renderDeckChips({});
    expect(root).not.toBeNull();
    const chips = root!.querySelectorAll(".vmx-deck-chip");
    expect(chips.length).toBe(1);
    expect(chips[0]?.textContent).toBe("decks · unknown");
    // The fallback chip is dim — it carries no amber resolved-key glyph.
    expect(root!.querySelector(".vmx-deck-chip__key--resolved")).toBeNull();
  });

  test("null/undefined deck_state → `decks · unknown` (defensive — `msg.deck_state ?? {}`)", () => {
    const rootNull = renderDeckChips(null as unknown as DeckStateWire);
    expect(rootNull).not.toBeNull();
    expect(rootNull!.querySelectorAll(".vmx-deck-chip").length).toBe(1);
    expect(rootNull!.querySelector(".vmx-deck-chip")?.textContent).toBe(
      "decks · unknown",
    );
  });

  test("chip text is set via textContent (no innerHTML injection path — T-62-16)", () => {
    // A hostile title/key never reaches the DOM as markup — the chip renders
    // deck/camelot/bpm verbatim as a text node. Inject a <script> shaped key:
    // it must render as literal text, not execute / create an element.
    const deckState: DeckStateWire = {
      A: {
        title: "<script>alert(1)</script>",
        camelot: "8A",
        key: "C",
        bpm: 128,
        confidence: 0.9,
      },
    };
    const root = renderDeckChips(deckState);
    expect(root!.querySelector("script")).toBeNull();
  });
});

describe("deck-chips CSS — frontend-enforcement (token-only, 20/80 amber)", () => {
  test("zero hex literals (token-only)", () => {
    expect(_CSS_FOR_TEST).not.toMatch(/#[0-9a-fA-F]{3,6}\b/);
  });

  test("zero non-black rgba literals (amber/silk must come from tokens)", () => {
    const nonBlackRgba =
      _CSS_FOR_TEST.match(/rgba\((?!0,\s*0,\s*0,)[^)]+\)/g) ?? [];
    expect(nonBlackRgba).toEqual([]);
  });

  test("the resolved-key glyph rule references the amber token", () => {
    const resolvedRule = _CSS_FOR_TEST.match(
      /\.vmx-deck-chip__key--resolved\s*\{[^}]*\}/,
    );
    expect(resolvedRule).not.toBeNull();
    expect(resolvedRule![0]).toMatch(/var\(--amber\)/);
  });

  test("20/80 — the base key glyph (unresolved) is dim silk, not amber", () => {
    const keyRule = _CSS_FOR_TEST.match(/\.vmx-deck-chip__key\s*\{[^}]*\}/);
    expect(keyRule).not.toBeNull();
    // The resting key glyph is --silk-40; amber lives only on --resolved.
    expect(keyRule![0]).toMatch(/var\(--silk-40\)/);
    expect(keyRule![0]).not.toMatch(/var\(--amber/);
  });
});
