/**
 * Phase 44-03 / LAUNCH-02 — citation-strip component contract.
 *
 * Pins the anti-slop receipt surface: each AI reaction in the cohost
 * stream renders a tiny chip strip below the message, format
 * `[<verb> @ <mm:ss>]` per chip. Click → invokes the caller's
 * `onChipClick` handler (the parent wires that to the Tauri
 * `open_debrief_window` IPC + deep_link payload).
 *
 * Mirrors the meter.test.ts pattern: jsdom env (routed by
 * vitest.config.ts `src/session/components/*.test.ts` glob), pure DOM
 * assertions against the rendered HTMLElement structure.
 *
 * Component contract under test (citation-strip.ts):
 *
 *   renderCitationStrip(props) → <div class="vmx-citation-strip">
 *     with <button class="vmx-citation-chip">[verb @ mm:ss]</button> × N
 *   Returns `null` when chips array is empty (caller does NOT need to
 *   guard against an empty container in the cohost stream).
 *
 *   `CitationChip = { event_id: string; verb: string; timestamp_s: number }`
 *
 *   Click handler invokes `onChipClick(chip)`; SessionLayout routes that
 *   to `invoke("open_debrief_window", { sessionDir, deepLink: { eventId,
 *   timestampS } })`.
 */
import { describe, test, expect, beforeEach, vi } from "vitest";
import {
  renderCitationStrip,
  formatMmSs,
  type CitationChip,
  _CSS_FOR_TEST,
} from "./citation-strip.js";

const SAMPLE_CHIPS: CitationChip[] = [
  { event_id: "ev:KICK_SWAP@45.2", verb: "kick swap", timestamp_s: 45.2 },
  { event_id: "ev:LAYER_DROP@153.6", verb: "layer drop", timestamp_s: 153.6 },
];

describe("citation-strip — LAUNCH-02 contract", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  test("1 — renders one .vmx-citation-chip per CitationChip in order", () => {
    const onChipClick = vi.fn();
    const root = renderCitationStrip({ chips: SAMPLE_CHIPS, onChipClick });
    expect(root).not.toBeNull();
    const chips = root!.querySelectorAll<HTMLButtonElement>(".vmx-citation-chip");
    expect(chips.length).toBe(2);
    // Order preserved (matches the backend's text-order chip list).
    expect(chips[0]?.textContent).toContain("kick swap");
    expect(chips[1]?.textContent).toContain("layer drop");
  });

  test("2 — chip text format is `[<verb> @ <mm:ss>]`", () => {
    const root = renderCitationStrip({
      chips: SAMPLE_CHIPS,
      onChipClick: vi.fn(),
    });
    const chips = root!.querySelectorAll<HTMLButtonElement>(".vmx-citation-chip");
    // 45.2s → 0:45 (mm:ss with single-digit minute, no leading zero).
    expect(chips[0]?.textContent).toBe("[kick swap @ 0:45]");
    // 153.6s → 2:33 (153 / 60 = 2 min 33 sec, integer-truncated).
    expect(chips[1]?.textContent).toBe("[layer drop @ 2:33]");
  });

  test("3 — click handler invokes onChipClick with the matching chip", () => {
    const onChipClick = vi.fn();
    const root = renderCitationStrip({ chips: SAMPLE_CHIPS, onChipClick });
    const chips = root!.querySelectorAll<HTMLButtonElement>(".vmx-citation-chip");
    chips[1]?.click();
    expect(onChipClick).toHaveBeenCalledTimes(1);
    // The handler receives the FULL chip dict — not just the event_id —
    // so the caller has timestamp_s for the debrief deep-link without a
    // second lookup pass.
    expect(onChipClick).toHaveBeenCalledWith({
      event_id: "ev:LAYER_DROP@153.6",
      verb: "layer drop",
      timestamp_s: 153.6,
    });
  });

  test("4 — empty chips array returns null (no empty container)", () => {
    const root = renderCitationStrip({
      chips: [],
      onChipClick: vi.fn(),
    });
    expect(root).toBeNull();
  });

  test("5 — chip is a real <button> (keyboard-accessible)", () => {
    // Accessibility: chips MUST be buttons, not divs — Enter/Space
    // should activate them, focus ring should land, screen readers
    // should announce them as buttons. Pins this so a future refactor
    // doesn't silently demote to a span+onclick.
    const root = renderCitationStrip({
      chips: SAMPLE_CHIPS,
      onChipClick: vi.fn(),
    });
    const chips = root!.querySelectorAll<HTMLButtonElement>(".vmx-citation-chip");
    chips.forEach((chip) => {
      expect(chip.tagName).toBe("BUTTON");
      expect(chip.getAttribute("type")).toBe("button");
    });
  });

  test("6 — CSS is fully token-driven (no rgba/hex literals)", () => {
    // Frontend-enforcement skill: components MUST NOT declare hex / rgba
    // colors. Only tokens.css is allowed to carry literal colors. The
    // citation-strip CSS reads --amber-* / --silk-* / --glow-* tokens.
    //
    // Allowed: rgba(0, 0, 0, ...) for inset shadow darkening (literal-
    // black is a structural shadow color the existing event-ribbon /
    // drop-chip patterns also use). Block: any `#xxx` hex color and
    // any rgba(255, ...) / rgba(214, ...) / non-black rgba (amber +
    // silk must come from tokens).
    const css = _CSS_FOR_TEST;
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,6}\b/);
    // Allow black-only rgba (structural shadows / hairlines); block any
    // non-black rgba which would indicate amber/silk hard-coded instead
    // of token-sourced.
    const nonBlackRgba = css.match(/rgba\((?!0,\s*0,\s*0,)[^)]+\)/g) ?? [];
    expect(nonBlackRgba).toEqual([]);
    // Positive: the strip MUST reference the amber chip tokens lifted
    // to tokens.css. The exact var names are part of the LAUNCH-02
    // contract — if these tokens are renamed, the renderer's CSS must
    // re-source.
    expect(css).toMatch(/var\(--c-citation-chip-fg\)/);
    expect(css).toMatch(/var\(--c-citation-chip-bg\)/);
    expect(css).toMatch(/var\(--glow-faint\)/);
    expect(css).toMatch(/var\(--glow-soft\)/);
  });
});

describe("formatMmSs — chip timestamp formatter", () => {
  test("0 → 0:00", () => expect(formatMmSs(0)).toBe("0:00"));
  test("45.2 → 0:45 (truncates fractional seconds)", () =>
    expect(formatMmSs(45.2)).toBe("0:45"));
  test("60 → 1:00 (boundary)", () => expect(formatMmSs(60)).toBe("1:00"));
  test("153.6 → 2:33 (multi-minute, fractional truncated)", () =>
    expect(formatMmSs(153.6)).toBe("2:33"));
  test("3599 → 59:59 (last second under an hour)", () =>
    expect(formatMmSs(3599)).toBe("59:59"));
  test("3600 → 60:00 (no hour rollover — DJ sets exceed an hour)", () =>
    expect(formatMmSs(3600)).toBe("60:00"));
  test("negative → 0:00 (defensive — clamp)", () =>
    expect(formatMmSs(-5)).toBe("0:00"));
});
