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
  nextMoveGrade,
  nextMoveGradeProgress,
  pillXpLevel,
  nextSuggestionFeedbackControls,
  nextSuggestionAriaLabel,
  nextSuggestionPrimaryActionAriaLabel,
  nextSuggestionPrimaryActionText,
  nextCueRailScale,
  nextSuggestionRenderKey,
  nextMetaText,
  nextTransitionText,
  renderNextSuggestion,
  _CSS_FOR_TEST,
  type MoveGradeView,
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

describe("pillXpLevel — earned XP level readout", () => {
  test("derives a bounded level from total transition XP", () => {
    expect(pillXpLevel(0)).toEqual({
      level: 1,
      levelXp: 0,
      nextLevelXp: 250,
      levelProgress: 0,
    });
    expect(pillXpLevel(288)).toEqual({
      level: 2,
      levelXp: 38,
      nextLevelXp: 250,
      levelProgress: 15,
    });
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
    expect(card.dataset.wire).toBe("pill.next-card");
    expect(card.querySelector(".vmx-next-card__glyph")?.textContent).toBe("↑");
    expect(card.querySelector(".vmx-next-card__title")?.textContent).toBe("Strobe");
    expect(card.querySelector(".vmx-next-card__meta")?.textContent).toBe(
      "deadmau5 · similar vibe · 8a · 128",
    );
  });

  test("backup and feedback regions expose transfer anchors", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition: { candidate_id: "tr_001" },
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
      {
        onAlternativeSelect: () => {},
        onFeedback: () => {},
      },
    )!;
    expect(card.querySelector('[data-wire="pill.next-backups"]')).not.toBeNull();
    expect(card.querySelector('[data-wire="pill.next-feedback"]')).not.toBeNull();
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

  test("move grade renders as earned data, not markup", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition: {
          candidate_id: "tr_001",
          cue_slot: "A",
          move_grade: {
            slug: "lit_aff",
            label: "LIT AFF",
            xp: 100,
            reason: "<img src=x>",
            deserved: true,
            overdrive: true,
          },
        },
      }),
    )!;
    expect(card.dataset.moveGrade).toBe("lit_aff");
    expect(card.dataset.gradeOverdrive).toBe("true");
    expect(card.style.getPropertyValue("--grade-heat-scale")).toBe("1.00");
    expect(card.querySelector('[data-wire="pill.next-grade"]')).not.toBeNull();
    expect(card.querySelector(".vmx-next-card__grade-label")?.textContent).toBe("LIT AFF");
    expect(card.querySelector(".vmx-next-card__grade-xp")?.textContent).toBe("+100xp");
    expect(card.querySelector(".vmx-next-card__grade-reason")?.textContent).toBe(
      "<img src=x>",
    );
    expect(card.querySelector(".vmx-next-card__grade-reason img")).toBeNull();
  });

  test("earned combo renders from supplied session progress only", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition: {
          candidate_id: "tr_001",
          cue_slot: "A",
          move_grade: {
            slug: "bomb",
            label: "BOMB",
            xp: 72,
            intensity: 84,
            reason: "big payoff",
            deserved: true,
          },
        },
      }),
      {
        gradeProgress: {
          streak: 3,
          totalXp: 188,
          lastXp: 72,
          earned: true,
          heat: 84,
        },
      },
    )!;

    expect(card.style.getPropertyValue("--combo-heat-scale")).toBe("0.84");
    expect(card.querySelector('[data-wire="pill.next-combo"]')).not.toBeNull();
    expect(card.querySelector(".vmx-next-card__combo-label")?.textContent).toBe("combo x3");
    expect(card.querySelector(".vmx-next-card__combo-xp")?.textContent).toBe("188xp");
    expect(card.querySelector(".vmx-next-card__combo-level")?.textContent).toBe("lv 1");
    expect(card.style.getPropertyValue("--combo-level-scale")).toBe("0.75");

    const mid = renderNextSuggestion(
      _sugg({
        transition: {
          move_grade: { slug: "mid", xp: 8, deserved: false },
        },
      }),
      {
        gradeProgress: {
          streak: 0,
          totalXp: 188,
          lastXp: 0,
          earned: false,
          heat: 0,
        },
      },
    )!;
    expect(mid.querySelector('[data-wire="pill.next-combo"]')).toBeNull();
  });

  test("backend grade_progress wins over local fallback and supports snake_case", () => {
    const suggestion = _sugg({
      grade_progress: {
        streak: 4,
        total_xp: 288,
        last_xp: 100,
        earned: true,
        heat: 100,
        level_up: true,
        levels_gained: 1,
      },
      transition: {
        candidate_id: "tr_001",
        cue_slot: "A",
        move_grade: {
          slug: "lit_aff",
          label: "LIT AFF",
          xp: 100,
          intensity: 100,
          reason: "everything clicks",
          deserved: true,
        },
      },
    });

    expect(
      nextMoveGradeProgress(suggestion, {
        streak: 1,
        totalXp: 28,
        lastXp: 28,
        earned: true,
        heat: 48,
      }),
    ).toEqual({
      streak: 4,
      totalXp: 288,
      lastXp: 100,
      earned: true,
      heat: 100,
      level: 2,
      levelXp: 38,
      nextLevelXp: 250,
      levelProgress: 15,
      levelUp: true,
      levelsGained: 1,
    });

    const card = renderNextSuggestion(suggestion, {
      gradeProgress: {
        streak: 1,
        totalXp: 28,
        lastXp: 28,
        earned: true,
        heat: 48,
      },
    })!;
    expect(card.querySelector(".vmx-next-card__combo-label")?.textContent).toBe("combo x4");
    expect(card.querySelector(".vmx-next-card__combo-xp")?.textContent).toBe("288xp");
    expect(card.querySelector(".vmx-next-card__combo-level")?.textContent).toBe("lv 2");
    expect(card.dataset.gradeLevelUp).toBe("true");
    expect(card.style.getPropertyValue("--combo-heat-scale")).toBe("1.00");
    expect(card.style.getPropertyValue("--combo-level-scale")).toBe("0.15");
  });

  test("nextMoveGrade ignores unknown grade slugs and normalises defaults", () => {
    expect(nextMoveGrade(_sugg({ transition: { move_grade: { slug: "nope" } } }))).toBeNull();
    expect(
      nextMoveGrade(
        _sugg({
          transition: { move_grade: { slug: "clean", label: "", xp: Number.NaN } },
        }),
      ),
    ).toMatchObject({ slug: "clean", label: "CLEAN", xp: 28, intensity: 48, deserved: true });
    expect(
      nextMoveGrade(
        _sugg({
          transition: { move_grade: { slug: "bomb", intensity: 84 } },
        }),
      ),
    ).toMatchObject({ slug: "bomb", intensity: 84 });
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

  test("feedback controls render only when a handler is provided", () => {
    const feedback: string[] = [];
    const card = renderNextSuggestion(_sugg(), {
      onFeedback: (kind) => feedback.push(kind),
    })!;
    const buttons = Array.from(card.querySelectorAll(".vmx-next-card__feedback-btn"));

    expect(buttons.map((button) => button.textContent)).toEqual(["keep", "later", "timing"]);
    expect(buttons.map((button) => (button as HTMLButtonElement).dataset.feedbackKind)).toEqual([
      "accept",
      "not_now",
      "wrong_timing",
    ]);
    expect(buttons.map((button) => button.getAttribute("aria-pressed"))).toEqual([
      "false",
      "false",
      "false",
    ]);
    (buttons[1] as HTMLButtonElement).click();
    expect(feedback).toEqual(["not_now"]);
    expect(buttons.map((button) => button.getAttribute("aria-pressed"))).toEqual([
      "false",
      "true",
      "false",
    ]);

    const peek = renderNextSuggestion(_sugg(), {
      showAlternatives: false,
      onFeedback: (kind) => feedback.push(kind),
    })!;
    expect(peek.querySelector(".vmx-next-card__feedback")).toBeNull();
  });

  test("feedback controls mark risky accepted moves as care", () => {
    const negativeGrade: MoveGradeView = {
      slug: "negative",
      label: "NEG",
      xp: 0,
      intensity: 22,
      reason: "key clash",
      deserved: false,
      overdrive: false,
    };

    expect(nextSuggestionFeedbackControls(null).map((control) => control.text)).toEqual([
      "keep",
      "later",
      "timing",
    ]);
    expect(nextSuggestionFeedbackControls(negativeGrade)[0]).toMatchObject({
      kind: "accept",
      text: "care",
      ariaLabel: "mark suggestion accepted with care",
    });
  });

  test("primary action text mirrors the compact keep/care completion command", () => {
    expect(nextSuggestionPrimaryActionText(null)).toBe("keep");
    expect(
      nextSuggestionPrimaryActionText({
        slug: "negative",
        label: "NEG",
        xp: 0,
        intensity: 22,
        reason: "key clash",
        deserved: false,
        overdrive: false,
      }),
    ).toBe("care");
  });

  test("care feedback still sends the accept intent", () => {
    const feedback: string[] = [];
    const card = renderNextSuggestion(
      _sugg({
        transition: {
          move_grade: {
            slug: "negative",
            reason: "key clash",
            deserved: false,
          },
        },
      }),
      { onFeedback: (kind) => feedback.push(kind) },
    )!;
    const buttons = Array.from(card.querySelectorAll(".vmx-next-card__feedback-btn"));

    expect(buttons.map((button) => button.textContent)).toEqual(["care", "later", "timing"]);
    expect((buttons[0] as HTMLButtonElement).dataset.feedbackKind).toBe("accept");
    expect(buttons[0]?.getAttribute("aria-label")).toBe("mark suggestion accepted with care");
    (buttons[0] as HTMLButtonElement).click();
    expect(feedback).toEqual(["accept"]);
  });

  test("collapsed hover peek can opt into compact feedback without backups", () => {
    const feedback: string[] = [];
    const peek = renderNextSuggestion(
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
      {
        showAlternatives: false,
        showFeedback: true,
        onFeedback: (kind) => feedback.push(kind),
      },
    )!;

    expect(peek.querySelector(".vmx-next-card__alternatives")).toBeNull();
    const buttons = Array.from(peek.querySelectorAll(".vmx-next-card__feedback-btn"));
    expect(buttons.map((button) => button.textContent)).toEqual(["keep", "later", "timing"]);
    (buttons[0] as HTMLButtonElement).click();
    expect(feedback).toEqual(["accept"]);
  });

  test("collapsed hover peek can complete the suggestion without visible controls", () => {
    const actions: string[] = [];
    const peek = renderNextSuggestion(_sugg(), {
      density: "peek",
      showAlternatives: false,
      showFeedback: false,
      onPrimaryAction: () => actions.push("keep"),
    })!;

    expect(peek.dataset.interactive).toBe("true");
    expect(peek.getAttribute("role")).toBe("button");
    expect(peek.getAttribute("aria-label")).toBe(
      "next: Strobe. activate to keep suggestion",
    );
    expect(peek.getAttribute("aria-keyshortcuts")).toBe("Enter Space");
    expect(peek.tabIndex).toBe(0);
    expect(peek.querySelector(".vmx-next-card__feedback")).toBeNull();
    expect(peek.querySelector(".vmx-next-card__peek-action")?.textContent).toBe("KEEP");
    expect(peek.querySelector(".vmx-next-card__peek-action")?.getAttribute("aria-hidden")).toBe(
      "true",
    );

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
    expect(actions).toEqual(["keep", "keep", "keep"]);
    expect(enter.defaultPrevented).toBe(true);
    expect(space.defaultPrevented).toBe(true);
    expect(bubbledKeys).toBe(0);
  });

  test("collapsed hover primary action names care when the move is risky", () => {
    const suggestion = _sugg({
      transition: {
        target_deck: "B",
        start_in_bars: 4,
        move_grade: {
          slug: "negative",
          label: "NEG",
          xp: 0,
          reason: "key clash",
          deserved: false,
        },
      },
    });
    const expected = [
      "next: Strobe",
      "action: load B · in 4 bars",
      "care: key clash",
      "activate to accept with care",
    ].join(". ");

    expect(nextSuggestionPrimaryActionAriaLabel(suggestion, { density: "peek" })).toBe(
      expected,
    );
    const peek = renderNextSuggestion(suggestion, {
      density: "peek",
      showAlternatives: false,
      showFeedback: false,
      onPrimaryAction: () => undefined,
    })!;
    expect(peek.dataset.interactive).toBe("true");
    expect(peek.dataset.moveGrade).toBe("negative");
    expect(peek.dataset.gradeDeserved).toBe("false");
    expect(peek.getAttribute("aria-label")).toBe(expected);
    expect(peek.getAttribute("role")).toBe("button");
    expect(peek.querySelector(".vmx-next-card__peek-action")?.textContent).toBe("CARE");
    expect(peek.querySelector(".vmx-next-card__peek-action")?.getAttribute("data-care")).toBe(
      "true",
    );
  });

  test("auto cue review grade makes the collapsed action care", () => {
    const suggestion = _sugg({
      transition: {
        target_deck: "B",
        cue_slot: "A",
        start_in_bars: 4,
        risk_flags: ["auto_cue_review"],
        move_grade: {
          slug: "mid",
          label: "MID",
          xp: 8,
          reason: "auto cue needs review",
          deserved: false,
        },
      },
    });

    const peek = renderNextSuggestion(suggestion, {
      density: "peek",
      showAlternatives: false,
      showFeedback: false,
      onPrimaryAction: () => undefined,
    })!;

    expect(nextSuggestionPrimaryActionText(nextMoveGrade(suggestion))).toBe("care");
    expect(peek.querySelector(".vmx-next-card__peek-action")?.textContent).toBe("CARE");
    expect(peek.querySelector(".vmx-next-card__peek-action")?.getAttribute("data-care")).toBe(
      "true",
    );
    expect(peek.querySelector(".vmx-next-card__grade-reason")?.textContent).toBe(
      "auto cue needs review",
    );
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
          move_grade: {
            slug: "bomb",
            label: "BOMB",
            xp: 72,
            reason: "perfect phrase",
            deserved: true,
          },
        },
        decision: {
          cue_slot: "A",
          timing_text: "in 8 bars",
          spoken_text: "load B · cue A · outro to intro · in 8 bars",
        },
      }),
      {
        density: "peek",
        showAlternatives: false,
        gradeProgress: {
          streak: 3,
          totalXp: 188,
          lastXp: 72,
          earned: true,
          heat: 84,
        },
        onFeedback: () => undefined,
      },
    )!;

    expect(card.dataset.density).toBe("peek");
    expect(card.querySelector(".vmx-next-card__meta")).toBeNull();
    expect(card.querySelector(".vmx-next-card__feedback")).toBeNull();
    expect(card.querySelector(".vmx-next-card__alternatives")).toBeNull();
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
      "grade: BOMB, 72 xp, perfect phrase",
    ].join(". "));
    expect(card.querySelector(".vmx-next-card__cue-rail")?.getAttribute("aria-hidden")).toBe(
      "true",
    );
    expect(
      (card.querySelector(".vmx-next-card__cue-rail") as HTMLElement).style.getPropertyValue(
        "--cue-rail-scale",
      ),
    ).toBe("0.56");
    expect(card.querySelector(".vmx-next-card__grade-label")?.textContent).toBe("BOMB");
    expect(card.querySelector(".vmx-next-card__grade-xp")?.textContent).toBe("+72xp");
    expect(card.querySelector(".vmx-next-card__grade-reason")).toBeNull();
    expect(card.querySelector(".vmx-next-card__combo")).toBeNull();
  });

  test("peek density keeps care reason for risky moves", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition: {
          target_deck: "B",
          start_in_bars: 4,
          move_grade: {
            slug: "negative",
            label: "NEG",
            xp: 0,
            reason: "key clash",
            deserved: false,
          },
        },
      }),
      { density: "peek", showAlternatives: false },
    )!;

    const reason = card.querySelector(".vmx-next-card__grade-reason");
    const transition = card.querySelector(".vmx-next-card__transition");
    expect(card.querySelector(".vmx-next-card__grade-label")?.textContent).toBe("NEG");
    expect(card.querySelector(".vmx-next-card__grade-xp")?.textContent).toBe("0xp");
    expect(card.querySelector(".vmx-next-card__grade")?.textContent).toBe("NEG0xpkey clash");
    expect(reason?.getAttribute("title")).toBe("key clash");
    expect(transition?.textContent).toBe("load B · in 4 bars");
    expect(transition?.getAttribute("title")).toBe("load B · in 4 bars");
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
      { density: "peek", showAlternatives: false },
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

  test("render key changes when the move grade changes", () => {
    const a = _sugg({
      transition: { move_grade: { slug: "clean", label: "CLEAN", xp: 28 } },
    });
    const b = _sugg({
      transition: { move_grade: { slug: "bomb", label: "BOMB", xp: 72 } },
    });
    expect(nextSuggestionRenderKey(a)).not.toBe(nextSuggestionRenderKey(b));
  });

  test("render key changes when backend grade_progress changes", () => {
    const a = _sugg({
      grade_progress: { streak: 2, total_xp: 96, last_xp: 48, earned: true, heat: 66 },
      transition: { move_grade: { slug: "sexy", label: "SEXY", xp: 48 } },
    });
    const b = _sugg({
      grade_progress: { streak: 3, total_xp: 188, last_xp: 100, earned: true, heat: 100 },
      transition: { move_grade: { slug: "sexy", label: "SEXY", xp: 48 } },
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

  test("card carries a useful assistive label, not generic chrome copy", () => {
    const card = renderNextSuggestion(
      _sugg({
        transition: {
          candidate_id: "tr_001",
          target_deck: "B",
          cue_slot: "A",
          start_in_bars: 8,
          move_grade: {
            slug: "bomb",
            label: "BOMB",
            xp: 72,
            reason: "phrase locks",
            deserved: true,
          },
        },
      }),
      {
        gradeProgress: {
          streak: 3,
          totalXp: 188,
          lastXp: 72,
          earned: true,
          heat: 84,
        },
      },
    )!;
    expect(card.getAttribute("aria-label")).toBe(
      "next: Strobe. deadmau5 · similar vibe · 8a · 128. action: load B · cue A · in 8 bars. grade: BOMB, 72 xp, phrase locks. session: 188 xp, combo 3",
    );
    expect(card.querySelector(".vmx-next-card__glyph")?.getAttribute("aria-hidden")).toBe(
      "true",
    );
    expect(card.querySelector(".vmx-next-card__title")?.getAttribute("title")).toBe("Strobe");
  });

  test("peek assistive label stays compact and calls out care reasons", () => {
    const suggestion = _sugg({
      transition: {
        target_deck: "B",
        start_in_bars: 4,
        move_grade: {
          slug: "negative",
          label: "NEG",
          xp: 0,
          reason: "key clash",
          deserved: false,
        },
      },
    });

    expect(nextSuggestionAriaLabel(suggestion, { density: "peek" })).toBe(
      "next: Strobe. action: load B · in 4 bars. care: key clash",
    );
    const card = renderNextSuggestion(suggestion, { density: "peek" })!;
    expect(card.getAttribute("aria-label")).toBe(
      "next: Strobe. action: load B · in 4 bars. care: key clash",
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

  test("20/80 — amber stays on the next glyph; grade heat uses rose/gold tokens", () => {
    const glyphRule = _CSS_FOR_TEST.match(/\.vmx-next-card__glyph\s*\{[^}]*\}/);
    expect(glyphRule).not.toBeNull();
    expect(glyphRule![0]).toMatch(/var\(--amber\)/);

    const titleRule = _CSS_FOR_TEST.match(/\.vmx-next-card__title\s*\{[^}]*\}/);
    expect(titleRule).not.toBeNull();
    expect(titleRule![0]).not.toMatch(/var\(--amber/); // hierarchy via silk tone
    expect(titleRule![0]).toMatch(/var\(--silk\)/);

    const gradeLabelRule = _CSS_FOR_TEST.match(/\.vmx-next-card__grade-label\s*\{[^}]*\}/);
    expect(gradeLabelRule).not.toBeNull();
    expect(gradeLabelRule![0]).toMatch(/var\(--brand\)/);
    expect(gradeLabelRule![0]).not.toMatch(/var\(--amber/);

    const gradeXpRule = _CSS_FOR_TEST.match(/\.vmx-next-card__grade-xp\s*\{[^}]*\}/);
    expect(gradeXpRule).not.toBeNull();
    expect(gradeXpRule![0]).toMatch(/var\(--gold\)/);
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
