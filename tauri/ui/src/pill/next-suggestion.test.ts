/**
 * @vitest-environment jsdom
 *
 * Pill next-suggestion card contract (PILL next-suggestion, Phase 1).
 *
 * Pins the load-bearing rules: HONEST SILENCE (null → no card, never a
 * fabricated track), verbatim title/why via textContent, the artist-drop in the
 * meta line, and the token-only / 20/80-amber CSS (frontend-enforcement). The
 * single amber accent is the `↑` next-glyph; the title is silk (hierarchy via
 * tone, not a second color).
 *
 * Wire contract: the flat 30Hz frame carries `next_suggestion: {track_id, title,
 * artist, similarity, why, camelot, bpm}` or `null`. `camelot`/`bpm` are null
 * for folder-only libraries — the `why` already encodes that honestly.
 *
 * Mirrors deck-chips.test.ts: jsdom env (renderNextSuggestion → registerStyle
 * touches document.head), the `_CSS_FOR_TEST` no-hex / amber-token grep, and
 * pure DOM assertions against the rendered HTMLElement.
 */

import { describe, test, expect } from "vitest";

import {
  nextMetaText,
  renderNextSuggestion,
  _CSS_FOR_TEST,
  type NextSuggestionWire,
} from "./next-suggestion.js";

function _sugg(over: Partial<NextSuggestionWire> = {}): NextSuggestionWire {
  return {
    track_id: "t1",
    title: "Strobe",
    artist: "deadmau5",
    similarity: 0.83,
    why: "similar vibe · 8a · 128",
    camelot: "8A",
    bpm: 128,
    ...over,
  };
}

describe("nextMetaText — artist · why (honest, drops empty artist)", () => {
  test("artist present → `artist · why`", () => {
    expect(nextMetaText({ artist: "deadmau5", why: "similar vibe · 8a · 128" })).toBe(
      "deadmau5 · similar vibe · 8a · 128",
    );
  });

  test("empty artist (folder track) → just the why, no dangling separator", () => {
    expect(nextMetaText({ artist: "", why: "similar vibe" })).toBe("similar vibe");
    expect(nextMetaText({ artist: "   ", why: "similar vibe" })).toBe("similar vibe");
  });
});

describe("renderNextSuggestion — honest silence + verbatim render", () => {
  test("null → renders NOTHING (honest silence, never a fabricated track)", () => {
    expect(renderNextSuggestion(null)).toBeNull();
    expect(renderNextSuggestion(undefined)).toBeNull();
  });

  test("missing track_id / title → null (incomplete = no card)", () => {
    expect(renderNextSuggestion(_sugg({ track_id: "" }))).toBeNull();
    expect(renderNextSuggestion(_sugg({ title: "" }))).toBeNull();
  });

  test("suggestion → a card with the `next ↑` label, title, and meta", () => {
    const card = renderNextSuggestion(_sugg())!;
    expect(card).not.toBeNull();
    expect(card.querySelector(".vmx-next-card__glyph")?.textContent).toBe("↑");
    expect(card.querySelector(".vmx-next-card__title")?.textContent).toBe("Strobe");
    expect(card.querySelector(".vmx-next-card__meta")?.textContent).toBe(
      "deadmau5 · similar vibe · 8a · 128",
    );
  });

  test("title is a TEXT node — no HTML injection from the wire (T-62-11 style)", () => {
    const card = renderNextSuggestion(_sugg({ title: "<img src=x onerror=alert(1)>" }))!;
    const titleEl = card.querySelector(".vmx-next-card__title")!;
    // textContent carries the literal string; no element was injected.
    expect(titleEl.textContent).toBe("<img src=x onerror=alert(1)>");
    expect(titleEl.querySelector("img")).toBeNull();
  });

  test("folder-only (no key/bpm) → meta is just `similar vibe`", () => {
    const card = renderNextSuggestion(
      _sugg({ artist: "", why: "similar vibe", camelot: null, bpm: null }),
    )!;
    expect(card.querySelector(".vmx-next-card__meta")?.textContent).toBe("similar vibe");
  });

  test("card is tagged for assistive tech", () => {
    const card = renderNextSuggestion(_sugg())!;
    expect(card.getAttribute("aria-label")).toBe("next track suggestion");
  });
});

describe("next-suggestion CSS — frontend-enforcement (token-only, 20/80 amber)", () => {
  test("zero hex literals (token-only)", () => {
    expect(_CSS_FOR_TEST).not.toMatch(/#[0-9a-fA-F]{3,6}\b/);
  });

  test("zero non-black rgba literals (amber/silk must come from tokens)", () => {
    const offenders = _CSS_FOR_TEST.match(/rgba\((?!0,\s*0,\s*0,)[^)]+\)/g) ?? [];
    expect(offenders).toEqual([]);
  });

  test("font-family is the brand mono token, never a raw face (design-slop gate)", () => {
    const decls = _CSS_FOR_TEST.match(/font-family:\s*([^;]+)/g) ?? [];
    expect(decls.length).toBeGreaterThan(0);
    for (const d of decls) expect(d).toMatch(/var\(--type-mono\)/);
  });

  test("20/80 — the ONLY amber is the next-glyph; title is silk, not a 2nd accent", () => {
    const glyphRule = _CSS_FOR_TEST.match(/\.vmx-next-card__glyph\s*\{[^}]*\}/);
    expect(glyphRule).not.toBeNull();
    expect(glyphRule![0]).toMatch(/var\(--amber\)/);

    const titleRule = _CSS_FOR_TEST.match(/\.vmx-next-card__title\s*\{[^}]*\}/);
    expect(titleRule).not.toBeNull();
    expect(titleRule![0]).not.toMatch(/var\(--amber/); // hierarchy via silk tone
    expect(titleRule![0]).toMatch(/var\(--silk-90\)/);
  });
});
