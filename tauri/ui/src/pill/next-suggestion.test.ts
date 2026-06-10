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
  nextSuggestionAriaLabel,
  nextSuggestionPrimaryActionAriaLabel,
  nextCueRailScale,
  nextSuggestionRenderKey,
  nextMetaText,
  nextTransitionText,
  nextReasonItems,
  nextReasonReceipt,
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

describe("nextCueRailScale — hover timing glance", () => {
  test("maps structured bars into a bounded visual urgency rail", () => {
    expect(nextCueRailScale(null)).toBeNull();
    expect(nextCueRailScale({ start_in_bars: Number.NaN })).toBeNull();
    expect(nextCueRailScale({ start_in_bars: 0 })).toBe(1);
    expect(nextCueRailScale({ start_in_bars: 1 })).toBe(1);
    expect(nextCueRailScale({ start_in_bars: 8 })).toBe(0.5625);
    expect(nextCueRailScale({ start_in_bars: 24 })).toBe(0.08);
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

  test("recent source loop explains why exact timing is withheld", () => {
    expect(
      nextTransitionText({
        target_deck: "B",
        cue_slot: "A",
        from_role: "groove",
        to_role: "intro",
        start_in_bars: null,
        source_selection: "loop_hold_section",
        risk_flags: ["source_loop_recent"],
      }),
    ).toBe("load B · cue A · groove→intro · loop held");
  });

  test("no grounded transition evidence → empty string", () => {
    expect(nextTransitionText(null)).toBe("");
    expect(nextTransitionText({})).toBe("");
  });
});

describe("nextReasonReceipt — grounded engine reasons", () => {
  test("returns the top grounded reason items without fabrication", () => {
    expect(
      nextReasonItems({
        reasons: [
          "Camelot relationship is clean",
          "tempo delta is workable",
          "entry lands on a phrase boundary",
        ],
      }),
    ).toEqual(["Camelot relationship is clean", "tempo delta is workable"]);
  });

  test("returns the top grounded reason clauses joined", () => {
    expect(
      nextReasonReceipt({
        reasons: [
          "Camelot relationship is clean",
          "tempo delta is workable",
          "entry lands on a phrase boundary",
        ],
      }),
    ).toBe("Camelot relationship is clean · tempo delta is workable");
  });

  test("returns empty string when reasons are missing or empty", () => {
    expect(nextReasonReceipt(undefined)).toBe("");
    expect(nextReasonReceipt({})).toBe("");
    expect(nextReasonReceipt({ reasons: [] })).toBe("");
  });

  test("does not fabricate or numericize the receipt", () => {
    const input = [
      "Camelot relationship is clean",
      "entry lands on a phrase boundary",
    ];
    const receipt = nextReasonReceipt({
      reasons: input,
      scores: { harmonic: 0.91, timing: 0.88 },
    });
    expect(input).toContain(receipt.split(" · ")[0]);
    expect(input).toContain(receipt.split(" · ")[1]);
    expect(receipt).not.toMatch(/\d/);
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

  test("accepted no-timing decision keeps the loop-held posture visible", () => {
    expect(
      nextDecisionText(
        {
          emitted: true,
          validation_status: "accepted",
          action: "select",
          candidate_id: "tr_001",
          cue_slot: "A",
          timing_text: null,
        },
        {
          candidate_id: "tr_001",
          target_deck: "B",
          from_role: "groove",
          to_role: "intro",
          cue_slot: "A",
          source_selection: "loop_hold_section",
          risk_flags: ["source_loop_recent"],
        },
      ),
    ).toBe("load B · cue A · groove→intro · loop held");
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
    expect(card.dataset.wire).toBe("pill.next-card");
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

  test("action line renders no-break chunks for glanceable timing", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition: {
          candidate_id: "tr_001",
          target_deck: "B",
          from_role: "outro",
          to_role: "intro",
          cue_slot: "A",
          start_in_bars: 8,
        },
      }),
    )!;
    const bits = Array.from(card.querySelectorAll(".vmx-next-card__transition-bit"));
    expect(bits.map((bit) => bit.textContent)).toEqual([
      "load B",
      " · cue A",
      " · outro→intro",
      " · in 8 bars",
    ]);
  });

  test("set-aware reasons render as a grounded why receipt", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition: {
          candidate_id: "tr_001",
          target_deck: "B",
          cue_slot: "A",
          start_in_bars: 8,
          reasons: [
            "Camelot relationship is clean",
            "tempo delta is workable",
            "entry lands on a phrase boundary",
          ],
        },
      }),
    )!;
    const receipt = card.querySelector<HTMLElement>("[data-next-why]");
    const chips = Array.from(receipt?.querySelectorAll(".vmx-next-card__why-chip") ?? []);
    expect(chips.map((chip) => chip.textContent)).toEqual([
      "Camelot relationship is clean",
      "tempo delta is workable",
    ]);
    expect(receipt?.getAttribute("title")).toBe(
      "Camelot relationship is clean · tempo delta is workable",
    );
  });

  test("empty reasons render no why receipt", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition: {
          candidate_id: "tr_001",
          target_deck: "B",
          cue_slot: "A",
          start_in_bars: 8,
          reasons: [],
        },
      }),
    )!;
    expect(card.querySelector("[data-next-why]")).toBeNull();
  });

  test("peek density still shows the grounded why receipt", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition: {
          candidate_id: "tr_001",
          target_deck: "B",
          start_in_bars: 8,
          reasons: [
            "Camelot relationship is clean",
            "tempo delta is workable",
          ],
        },
      }),
      { density: "peek" },
    )!;
    const chips = Array.from(card.querySelectorAll(".vmx-next-card__why-chip"));
    expect(chips.map((chip) => chip.textContent)).toEqual([
      "Camelot relationship is clean",
      "tempo delta is workable",
    ]);
    expect(card.getAttribute("aria-label")).toContain(
      "why: Camelot relationship is clean · tempo delta is workable",
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

  test("collapsed hover peek completes the suggestion via the primary action", () => {
    const actions: string[] = [];
    const peek = renderNextSuggestion(_sugg(), {
      density: "peek",
      onPrimaryAction: () => actions.push("act"),
    })!;

    expect(peek.dataset.interactive).toBe("true");
    expect(peek.getAttribute("role")).toBe("button");
    expect(peek.getAttribute("aria-label")).toBe(
      "next: Strobe. activate to pin this next",
    );
    expect(peek.getAttribute("aria-keyshortcuts")).toBe("Enter Space");
    expect(peek.tabIndex).toBe(0);

    peek.click();
    const wrapper = document.createElement("div");
    wrapper.append(peek);
    let bubbledKeys = 0;
    wrapper.addEventListener("keydown", () => {
      bubbledKeys += 1;
    });

    const enter = new KeyboardEvent("keydown", {
      key: "Enter",
      bubbles: true,
      cancelable: true,
    });
    const space = new KeyboardEvent("keydown", {
      key: " ",
      bubbles: true,
      cancelable: true,
    });
    peek.dispatchEvent(enter);
    peek.dispatchEvent(space);
    expect(actions).toEqual(["act", "act", "act"]);
    expect(enter.defaultPrevented).toBe(true);
    expect(space.defaultPrevented).toBe(true);
    expect(bubbledKeys).toBe(0);
  });

  test("peek density keeps the hover drawer to a readable glance", () => {
    const card = renderNextSuggestion(
      _sugg({
        artist: "very wordy crate source",
        why: "similar vibe · harmonic but too long for a hover receipt",
        transition: {
          target_deck: "B",
          cue_slot: "A",
          from_role: "outro",
          to_role: "intro",
          start_in_bars: 8,
        },
        decision: {
          cue_slot: "A",
          timing_text: "in 8 bars",
          spoken_text: "load B · cue A · outro to intro · in 8 bars",
        },
      }),
      {
        density: "peek",
      },
    )!;

    expect(card.dataset.density).toBe("peek");
    expect(card.querySelector(".vmx-next-card__meta")).toBeNull();
    expect(card.querySelector(".vmx-next-card__transition")?.textContent).toBe(
      "load B · in 8 bars",
    );
    expect(card.querySelector(".vmx-next-card__transition")?.getAttribute("title")).toBe(
      "load B · cue A · outro→intro · in 8 bars",
    );
    expect(card.getAttribute("aria-label")).toBe([
      "next: Strobe",
      "action: load B · in 8 bars",
      "detail: load B · cue A · outro→intro · in 8 bars",
    ].join(". "));
    expect(card.querySelector(".vmx-next-card__cue-rail")?.getAttribute("aria-hidden")).toBe(
      "true",
    );
    expect(
      (card.querySelector(".vmx-next-card__cue-rail") as HTMLElement).style.getPropertyValue(
        "--cue-rail-scale",
      ),
    ).toBe("0.56");
  });

  test("peek preserves the full grounded transition as the compact line title", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition: {
          candidate_id: "tr_001",
          target_deck: "B",
          cue_slot: "A",
          from_role: "outro",
          to_role: "intro",
          start_in_bars: 16,
        },
        decision: {
          candidate_id: "tr_001",
          timing_text: "in 16 bars",
          spoken_text: "load B in 16 bars",
        },
      }),
      { density: "peek" },
    )!;

    const transition = card.querySelector(".vmx-next-card__transition");
    expect(transition?.textContent).toBe("load B · in 16 bars");
    expect(transition?.getAttribute("title")).toBe(
      "load B · cue A · outro→intro · in 16 bars",
    );
    expect(card.getAttribute("aria-label")).toBe([
      "next: Strobe",
      "action: load B · in 16 bars",
      "detail: load B · cue A · outro→intro · in 16 bars",
    ].join(". "));
  });

  test("render key changes when the live transition countdown changes", () => {
    const a = _sugg({ transition: { cue_slot: "A", start_in_bars: 13 } });
    const b = _sugg({ transition: { cue_slot: "A", start_in_bars: 12 } });
    expect(nextSuggestionRenderKey(a)).not.toBe(nextSuggestionRenderKey(b));
  });

  test("render key changes when rendered receipt reasons change", () => {
    const a = _sugg({
      transition: {
        candidate_id: "tr_001",
        reasons: ["Camelot relationship is clean"],
      },
    });
    const b = _sugg({
      transition: {
        candidate_id: "tr_001",
        reasons: ["tempo delta is workable"],
      },
    });
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

  test("card carries a useful assistive label, not generic chrome copy", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition: {
          candidate_id: "tr_001",
          target_deck: "B",
          cue_slot: "A",
          start_in_bars: 8,
        },
      }),
    )!;
    expect(card.getAttribute("aria-label")).toBe(
      "next: Strobe. deadmau5 · similar vibe · 8a · 128. action: load B · cue A · in 8 bars",
    );
    expect(card.querySelector(".vmx-next-card__glyph")?.getAttribute("aria-hidden")).toBe(
      "true",
    );
    expect(card.querySelector(".vmx-next-card__title")?.getAttribute("title")).toBe("Strobe");
  });

  test("peek assistive label stays compact", () => {
    const suggestion = _sugg({
      transition: {
        target_deck: "B",
        start_in_bars: 4,
      },
    });

    expect(nextSuggestionAriaLabel(suggestion, { density: "peek" })).toBe(
      "next: Strobe. action: load B · in 4 bars",
    );
    const card = renderNextSuggestion(suggestion, { density: "peek" })!;
    expect(card.getAttribute("aria-label")).toBe(
      "next: Strobe. action: load B · in 4 bars",
    );
    expect(card.getAttribute("role")).toBe("status");
    expect(card.getAttribute("aria-live")).toBe("polite");
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

  test("20/80 — brand rose stays on the next glyph; the title leans on silk tone", () => {
    const glyphRule = _CSS_FOR_TEST.match(/\.vmx-next-card__glyph\s*\{[^}]*\}/);
    expect(glyphRule).not.toBeNull();
    expect(glyphRule![0]).toMatch(/var\(--brand\)/);
    // The legacy --amber alias silently resolves to rose — intent must be
    // spelled with the real token.
    expect(_CSS_FOR_TEST).not.toMatch(/var\(--amber/);

    const titleRule = _CSS_FOR_TEST.match(/\.vmx-next-card__title\s*\{[^}]*\}/);
    expect(titleRule).not.toBeNull();
    expect(titleRule![0]).not.toMatch(/var\(--brand\)/); // hierarchy via silk tone
    expect(titleRule![0]).toMatch(/var\(--silk\)/);
  });

  test("gold lane — the cue rail rides the brand ladder, gold stays Camelot/heat-only", () => {
    const railRule = _CSS_FOR_TEST.match(
      /\.vmx-next-card__cue-rail::after\s*\{[^}]*\}/,
    );
    expect(railRule).not.toBeNull();
    expect(railRule![0]).toMatch(/var\(--brand\)/);
    expect(_CSS_FOR_TEST).not.toMatch(/var\(--gold/);
  });

  test("action line keeps deck and cue case visible and can wrap timing", () => {
    const transitionRule = _CSS_FOR_TEST.match(/\.vmx-next-card__transition\s*\{[^}]*\}/);
    expect(transitionRule).not.toBeNull();
    expect(transitionRule![0]).toMatch(/flex-wrap:\s*wrap/);
    expect(transitionRule![0]).toMatch(/white-space:\s*normal/);
    expect(transitionRule![0]).not.toMatch(/text-transform:\s*lowercase/);
    expect(transitionRule![0]).not.toMatch(/text-overflow:\s*ellipsis/);
    const transitionBitRule = _CSS_FOR_TEST.match(
      /\.vmx-next-card__transition-bit\s*\{[^}]*\}/,
    );
    expect(transitionBitRule).not.toBeNull();
    expect(transitionBitRule![0]).toMatch(/white-space:\s*nowrap/);
  });
});
