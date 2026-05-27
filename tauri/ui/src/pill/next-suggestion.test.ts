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
 * artist, similarity, why, camelot, bpm, transition?}` or `null`.
 * `camelot`/`bpm` are null for folder-only libraries; the `why` already encodes
 * that honestly.
 *
 * Mirrors deck-chips.test.ts: jsdom env (renderNextSuggestion → registerStyle
 * touches document.head), the `_CSS_FOR_TEST` no-hex / amber-token grep, and
 * pure DOM assertions against the rendered HTMLElement.
 */

import { describe, test, expect } from "vitest";

import {
  nextDecisionText,
  nextAlternativeViews,
  nextSuggestionRenderKey,
  nextMetaText,
  nextTransitionText,
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

describe("nextTransitionText — cue + grounded timing", () => {
  test("cue with exact bars → compact instruction", () => {
    expect(nextTransitionText({ cue_slot: "A", start_in_bars: 13 })).toBe(
      "cue A · in 13 bars",
    );
  });

  test("zero bars → now", () => {
    expect(nextTransitionText({ cue_slot: "B", start_in_bars: 0 })).toBe("cue B · now");
  });

  test("target deck renders as the first actionable instruction", () => {
    expect(
      nextTransitionText({ target_deck: "B", cue_slot: "A", start_in_bars: 13 }),
    ).toBe("load B · cue A · in 13 bars");
  });

  test("cue start time renders when the transition carries section timing", () => {
    expect(
      nextTransitionText({
        target_deck: "B",
        cue_slot: "A",
        to_start_s: 64,
        start_in_bars: 13,
      }),
    ).toBe("load B · cue A @ 1:04 · in 13 bars");
  });

  test("grounded section roles render as a compact pair", () => {
    expect(
      nextTransitionText({
        target_deck: "B",
        cue_slot: "A",
        from_role: "outro",
        to_role: "intro",
        start_in_bars: 4,
      }),
    ).toBe("load B · cue A · outro→intro · in 4 bars");
  });

  test("cue without timing still renders the actionable cue", () => {
    expect(nextTransitionText({ cue_slot: "F", start_in_bars: null })).toBe("cue F");
  });

  test("no grounded transition evidence → empty string", () => {
    expect(nextTransitionText(null)).toBe("");
    expect(nextTransitionText({})).toBe("");
  });
});

describe("nextDecisionText — validator-checked live action", () => {
  test("accepted emitted select decision becomes the primary action line", () => {
    expect(
      nextDecisionText(
        {
          emitted: true,
          validation_status: "accepted",
          action: "select",
          candidate_id: "tr_001",
          cue_slot: "A",
          timing_text: "in 13 bars",
          spoken_text: "Next good entry: t1 cue A at 1:04, outro into intro, in 13 bars.",
        },
        {
          candidate_id: "tr_001",
          target_deck: "B",
          from_role: "outro",
          to_role: "intro",
          to_start_s: 64,
          cue_slot: "A",
          start_in_bars: 12,
        },
      ),
    ).toBe("load B · cue A @ 1:04 · outro→intro · in 13 bars");
  });

  test("accepted decision can fall back to spoken text when no compact fields exist", () => {
    expect(
      nextDecisionText({
        emitted: true,
        validation_status: "accepted",
        action: "select",
        candidate_id: "tr_001",
        spoken_text: "  Next good entry: cue A.  ",
      }),
    ).toBe("Next good entry: cue A.");
  });

  test("rejected or non-emitted decisions render nothing", () => {
    expect(
      nextDecisionText({
        emitted: false,
        validation_status: "accepted",
        action: "select",
        candidate_id: "tr_001",
        cue_slot: "A",
      }),
    ).toBe("");
    expect(
      nextDecisionText({
        emitted: true,
        validation_status: "rejected",
        action: "select",
        candidate_id: "tr_001",
        cue_slot: "A",
      }),
    ).toBe("");
  });

  test("accepted select without a candidate id is still not renderable", () => {
    expect(
      nextDecisionText({
        emitted: true,
        validation_status: "accepted",
        action: "select",
        cue_slot: "A",
      }),
    ).toBe("");
  });

  test("candidate mismatch does not render the stale decision", () => {
    expect(
      nextDecisionText(
        {
          emitted: true,
          validation_status: "accepted",
          action: "select",
          candidate_id: "tr_old",
          cue_slot: "A",
          timing_text: "in 13 bars",
        },
        { candidate_id: "tr_001", cue_slot: "A", start_in_bars: 13 },
      ),
    ).toBe("");
  });
});

describe("nextAlternativeViews — grounded backup choices", () => {
  test("filters the selected candidate and returns bounded backup rows", () => {
    expect(
      nextAlternativeViews(
        _sugg({
          transition: { candidate_id: "tr_001" },
          transition_alternatives: [
            {
              candidate_id: "tr_001",
              rank: 1,
              selected: true,
              track_id: "t1",
              title: "Strobe",
            },
            {
              candidate_id: "tr_002",
              rank: 2,
              track_id: "t2",
              title: "Backup Heat",
              camelot: "9A",
              bpm: 127.4,
              transition: {
                candidate_id: "tr_002",
                target_deck: "B",
                cue_slot: "B",
                to_start_s: 64,
                start_in_bars: 8,
              },
            },
            {
              candidate_id: "tr_003",
              rank: 3,
              track_id: "t3",
              title: "Third Door",
              transition: { candidate_id: "tr_003", cue_slot: "C" },
            },
          ],
        }),
        1,
      ),
    ).toEqual([
      {
        key: "tr_002",
        candidateId: "tr_002",
        trackId: "t2",
        title: "02 · Backup Heat",
        meta: "cue B @ 1:04 · in 8 bars · 9a · 127",
      },
    ]);
  });

  test("requires a candidate id and title before showing a backup", () => {
    expect(
      nextAlternativeViews(
        _sugg({
          transition_alternatives: [
            { rank: 2, track_id: "t2", title: "No Candidate" },
            { candidate_id: "tr_003", rank: 3, track_id: "t3", title: "" },
          ],
        }),
      ),
    ).toEqual([]);
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

  test("set-aware transition payload renders cue and bars as its own line", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition: {
          candidate_id: "tr_001",
          source_deck: "A",
          target_deck: "B",
          from_track_id: "t0",
          to_track_id: "t1",
          from_section_id: "t0#s001",
          to_section_id: "t1#s000",
          from_role: "outro",
          to_role: "intro",
          cue_slot: "A",
          start_in_bars: 13,
          timing_basis: "section_playhead",
        },
      }),
    )!;
    expect(card.querySelector(".vmx-next-card__transition")?.textContent).toBe(
      "load B · cue A · outro→intro · in 13 bars",
    );
  });

  test("accepted decision owns the action line over the raw transition countdown", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition: {
          candidate_id: "tr_001",
          target_deck: "B",
          from_role: "outro",
          to_role: "intro",
          cue_slot: "A",
          to_start_s: 64,
          start_in_bars: 12,
        },
        decision: {
          emitted: true,
          validation_status: "accepted",
          action: "select",
          candidate_id: "tr_001",
          cue_slot: "A",
          timing_text: "in 13 bars",
          spoken_text: "Next good entry: t1 cue A at 1:04, outro into intro, in 13 bars.",
        },
      }),
    )!;
    expect(card.querySelector(".vmx-next-card__transition")?.textContent).toBe(
      "load B · cue A @ 1:04 · outro→intro · in 13 bars",
    );
  });

  test("unsafe decision falls back to transition text", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition: { candidate_id: "tr_001", target_deck: "B", cue_slot: "A", start_in_bars: 4 },
        decision: {
          emitted: true,
          validation_status: "rejected",
          action: "select",
          candidate_id: "tr_001",
          cue_slot: "A",
          timing_text: "in 16 bars",
        },
      }),
    )!;
    expect(card.querySelector(".vmx-next-card__transition")?.textContent).toBe(
      "load B · cue A · in 4 bars",
    );
  });

  test("backup alternatives render under the primary action", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition: { candidate_id: "tr_001", cue_slot: "A", start_in_bars: 4 },
        transition_alternatives: [
          {
            candidate_id: "tr_001",
            rank: 1,
            selected: true,
            track_id: "t1",
            title: "Strobe",
          },
          {
            candidate_id: "tr_002",
            rank: 2,
            track_id: "t2",
            title: "Backup Heat",
            camelot: "9A",
            bpm: 127,
            transition: { candidate_id: "tr_002", cue_slot: "B", start_in_bars: 8 },
          },
        ],
      }),
    )!;
    expect(card.querySelector(".vmx-next-card__alternatives")?.getAttribute("aria-label")).toBe(
      "backup transition options",
    );
    expect(card.querySelector(".vmx-next-card__alt-label")?.textContent).toBe("backup");
    expect(card.querySelector(".vmx-next-card__alt-title")?.textContent).toBe(
      "02 · Backup Heat",
    );
    expect(card.querySelector(".vmx-next-card__alt-meta")?.textContent).toBe(
      "cue B · in 8 bars · 9a · 127",
    );
  });

  test("backup alternatives become buttons when a selection handler is provided", () => {
    const selected: unknown[] = [];
    const card = renderNextSuggestion(
      _sugg({
        transition_alternatives: [
          {
            candidate_id: "tr_002",
            rank: 2,
            track_id: "t2",
            title: "Backup Heat",
            transition: { candidate_id: "tr_002", cue_slot: "B" },
          },
        ],
      }),
      { onAlternativeSelect: (alt) => selected.push(alt) },
    )!;
    const row = card.querySelector(".vmx-next-card__alt-row") as HTMLButtonElement;
    expect(row.tagName).toBe("BUTTON");
    expect(row.dataset.candidateId).toBe("tr_002");
    expect(row.dataset.trackId).toBe("t2");
    row.click();
    expect(selected).toEqual([
      {
        key: "tr_002",
        candidateId: "tr_002",
        trackId: "t2",
        title: "02 · Backup Heat",
        meta: "cue B",
      },
    ]);
  });

  test("backup alternatives can be hidden for the collapsed hover peek", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition_alternatives: [
          {
            candidate_id: "tr_002",
            rank: 2,
            track_id: "t2",
            title: "Backup Heat",
            transition: { candidate_id: "tr_002", cue_slot: "B" },
          },
        ],
      }),
      { showAlternatives: false },
    )!;
    expect(card.querySelector(".vmx-next-card__alternatives")).toBeNull();
  });

  test("backup alternative titles are text nodes, never injected markup", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition_alternatives: [
          {
            candidate_id: "tr_002",
            rank: 2,
            track_id: "t2",
            title: "<img src=x onerror=alert(1)>",
            transition: { candidate_id: "tr_002", cue_slot: "B" },
          },
        ],
      }),
    )!;
    const title = card.querySelector(".vmx-next-card__alt-title")!;
    expect(title.textContent).toBe("02 · <img src=x onerror=alert(1)>");
    expect(title.querySelector("img")).toBeNull();
  });

  test("render key changes when the live transition countdown changes", () => {
    const a = _sugg({ transition: { cue_slot: "A", start_in_bars: 13 } });
    const b = _sugg({ transition: { cue_slot: "A", start_in_bars: 12 } });
    expect(nextSuggestionRenderKey(a)).not.toBe(nextSuggestionRenderKey(b));
  });

  test("render key changes when the validated decision timing changes", () => {
    const a = _sugg({
      transition: { candidate_id: "tr_001", cue_slot: "A", start_in_bars: 13 },
      decision: {
        emitted: true,
        validation_status: "accepted",
        action: "select",
        candidate_id: "tr_001",
        cue_slot: "A",
        timing_text: "in 13 bars",
      },
    });
    const b = _sugg({
      transition: { candidate_id: "tr_001", cue_slot: "A", start_in_bars: 13 },
      decision: {
        emitted: true,
        validation_status: "accepted",
        action: "select",
        candidate_id: "tr_001",
        cue_slot: "A",
        timing_text: "in 12 bars",
      },
    });
    expect(nextSuggestionRenderKey(a)).not.toBe(nextSuggestionRenderKey(b));
  });

  test("render key changes when a backup transition changes", () => {
    const a = _sugg({
      transition_alternatives: [
        {
          candidate_id: "tr_002",
          rank: 2,
          track_id: "t2",
          title: "Backup Heat",
          transition: { candidate_id: "tr_002", cue_slot: "B", start_in_bars: 8 },
        },
      ],
    });
    const b = _sugg({
      transition_alternatives: [
        {
          candidate_id: "tr_002",
          rank: 2,
          track_id: "t2",
          title: "Backup Heat",
          transition: { candidate_id: "tr_002", cue_slot: "C", start_in_bars: 8 },
        },
      ],
    });
    expect(nextSuggestionRenderKey(a)).not.toBe(nextSuggestionRenderKey(b));
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
    expect(titleRule![0]).toMatch(/var\(--silk\)/);
  });
});
