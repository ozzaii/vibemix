/* citation-strip.ts — LAUNCH-02 (Phase 44 Plan 44-03).
 *
 * Renders a small chip strip below each AI reaction in the cohost
 * transcript. Each chip carries `[<verb> @ <mm:ss>]` and is sourced
 * from the backend's `SessionCohostReaction` IPC message's
 * `citation_strip` array (built by `_build_citation_strip` in
 * `src/vibemix/agent/dj_cohost.py`).
 *
 * Click handler invokes `onChipClick(chip)` — the parent (SessionLayout
 * cohost wiring) routes that to the Tauri `open_debrief_window` IPC
 * with a `deep_link: { eventId, timestampS }` payload. The debrief
 * window then scrolls the timeline to the timestamp and highlights the
 * waveform region (Plan 44-03 Task 3).
 *
 * Design contract (CDJ Whisper + frontend-enforcement skill):
 *   - Token-driven CSS only — `--c-citation-chip-*` semantic tokens
 *     from tokens.css (added in the same plan). No hex / non-black rgba.
 *   - Resting glow = none (2026-05-19 critique: 30+ chip halos
 *     cumulated to amber decoration on the transcript surface).
 *   - Hover/focus glow = `--glow-soft` (amber-40 + amber-22).
 *   - 20/80 rule: chips are the ONLY amber accent in the cohost
 *     transcript body — dominant tone stays silk/glass.
 *   - Returns null when chips array is empty: caller doesn't need to
 *     guard against an empty container in the cohost stream.
 *
 * Pure function. No timers, no state, no side effects beyond DOM
 * construction. Vitest under jsdom (routed by `src/session/components/
 * *.test.ts` glob in vitest.config.ts).
 */

import { registerStyle } from "./_style-registry.js";

/** Chip payload — mirrors `vibemix.ui_bus.schemas.cohost_reaction.
 *  CitationChipPayload` on the Python side. The TS codegen would also
 *  produce this shape; declaring it locally here keeps the component
 *  decoupled from the wire-side wrapper while staying field-identical. */
export interface CitationChip {
  /** Stable citation atom in source-prefixed form, e.g.
   *  ``"ev:KICK_SWAP@45.2"``. Used as the debrief deep-link key. */
  event_id: string;
  /** 1-3 word lowercase verb the chip text renders (e.g. ``"kick
   *  swap"``). Backend caps at 3 words / 32 chars. */
  verb: string;
  /** Session-relative time of the cited event, seconds. Used for the
   *  ``mm:ss`` chip text + the click→debrief deep-link payload. */
  timestamp_s: number;
}

export interface CitationStripProps {
  chips: CitationChip[];
  /** Click handler — invoked with the FULL chip dict so the caller
   *  has `timestamp_s` for the debrief deep-link without re-lookup. */
  onChipClick: (chip: CitationChip) => void;
}

const CSS = `
  .vmx-citation-strip {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    /* Sits below the reaction line — small top margin pulls the chip
     * strip just under the reaction text but inside the same
     * "message" visual scope. Negative bottom margin keeps the next
     * reaction from drifting too far. */
    margin: 4px 0 8px 22px;
    padding: 0;
  }
  .vmx-citation-chip {
    display: inline-flex;
    align-items: center;
    height: 20px;
    padding: 0 8px;
    border: 1px solid var(--c-citation-chip-border);
    border-radius: var(--rad-sm);
    background: var(--c-citation-chip-bg);
    color: var(--c-citation-chip-fg);
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-size: 10px;
    letter-spacing: 0.04em;
    line-height: 1;
    text-transform: lowercase;
    /* 2026-05-19 /impeccable critique fix: resting glow dropped. Over
     * a transcript of 30+ AI reactions, the permanent --glow-faint
     * halo on every chip cumulates into a sustained amber wash on the
     * cohost transcript — the exact "amber decoration not deck-light"
     * regression the v5 distill cuts against. Hover/focus still lifts
     * to --glow-soft so the affordance reads on interaction. */
    cursor: pointer;
    transition: border-color var(--motion-snap) ease-out,
                background var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out,
                color var(--motion-snap) ease-out;
    flex-shrink: 0;
  }
  .vmx-citation-chip:hover,
  .vmx-citation-chip:focus-visible {
    border-color: var(--c-citation-chip-border-hover);
    background: var(--c-citation-chip-bg-hover);
    color: var(--amber);
    box-shadow: var(--glow-soft);
  }
  .vmx-citation-chip:focus-visible { outline: none; }
  .vmx-citation-chip:active {
    /* Inset press feedback — subtle, matches the existing CDJ panel
     * inset language. Black inset works against the amber wash. */
    box-shadow:
      var(--glow-soft),
      inset 0 1px 2px rgba(0, 0, 0, 0.4);
  }
`;

registerStyle("vmx-citation-strip", CSS);

/** Test-only — exposed so the contract test can grep the registered
 *  CSS for token usage + reject hex / non-black rgba regressions
 *  (frontend-enforcement skill). */
export const _CSS_FOR_TEST = CSS;

/**
 * Format a session-relative timestamp as `m:ss` (or `mm:ss` past 10
 * minutes). NO hour rollover — DJ sets routinely exceed an hour and
 * the chip stays readable as `64:12`. Negative input clamps to `0:00`
 * (defensive — citation_strip values from the backend are non-negative,
 * but the TS contract should never NaN out on bad data).
 */
export function formatMmSs(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  // Truncate fractional seconds — the wire payload carries sub-second
  // precision for the debrief deep-link, but the chip surface is
  // human-readable mm:ss.
  const total = Math.floor(seconds);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/**
 * Render the chip strip. Returns `null` (NOT an empty container) when
 * `chips` is empty — the caller can `if (strip) reactionEl.append(strip)`
 * without rendering a hanging div.
 */
export function renderCitationStrip(
  props: CitationStripProps,
): HTMLDivElement | null {
  if (props.chips.length === 0) return null;
  const root = document.createElement("div");
  root.className = "vmx-citation-strip";
  root.setAttribute("aria-label", "evidence citations");
  for (const chip of props.chips) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "vmx-citation-chip";
    btn.dataset.eventId = chip.event_id;
    btn.dataset.timestampS = String(chip.timestamp_s);
    const mmss = formatMmSs(chip.timestamp_s);
    btn.textContent = `[${chip.verb} @ ${mmss}]`;
    btn.setAttribute(
      "aria-label",
      `evidence: ${chip.verb} at ${mmss} · click to open debrief`,
    );
    btn.setAttribute(
      "title",
      `${chip.verb} @ ${mmss} · open debrief at this moment`,
    );
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      props.onChipClick(chip);
    });
    root.append(btn);
  }
  return root;
}
