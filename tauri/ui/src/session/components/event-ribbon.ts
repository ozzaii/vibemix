/* event-ribbon.ts — MIDI / phase event chip strip (UI-SPEC §8).
 *
 * Horizontal scroll, max 12 visible (newest right; older trimmed). Each
 * chip's age decides its CSS class: `.now` (< 600ms), `.warm` (< 4s),
 * `.cool` (4-12s) — older chips simply not in the trimmed list.
 *
 * Pure-function: takes events with `ageMs` already computed by the
 * caller (SessionLayout will compute ages during the rAF tick). NO
 * internal timers, NO setInterval. */

import { registerStyle } from "./_style-registry.js";

export interface MidiEvent {
  /** Stable id for diffing — same id across ticks is the same event. */
  id: string;
  /** Display label (already terse-DJ-friend formatted by caller). */
  label: string;
  /** Age in ms since the event fired. */
  ageMs: number;
}

export interface EventRibbonProps {
  events: MidiEvent[];
  /** Max chips visible. Defaults to 12 per UI-SPEC §8. */
  max?: number;
}

const MAX_DEFAULT = 12;

const CSS = `
  .vmx-event-ribbon {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 12px;
    background: var(--glass-3);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    box-shadow:
      inset 0 2px 6px rgba(0, 0, 0, 0.85),
      inset 0 0 0 1px rgba(0, 0, 0, 0.55),
      inset 0 0 18px rgba(255, 138, 61, 0.022),
      0 0 0 1px rgba(255, 255, 255, 0.022);
    overflow: hidden;
    overflow-x: auto;
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.04em;
    color: var(--silk-40);
    position: relative;
  }
  .vmx-event-ribbon::-webkit-scrollbar { height: 0; display: none; }
  .vmx-event-chip {
    display: inline-flex;
    align-items: center;
    height: 26px;
    padding: 0 12px;
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    background: rgba(0, 0, 0, 0.35);
    color: var(--silk-65);
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-size: 10px;
    letter-spacing: 0.04em;
    line-height: 1;
    text-transform: lowercase;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    transition: color 250ms linear,
                background 250ms linear,
                border-color 250ms linear,
                text-shadow 250ms linear,
                box-shadow 250ms linear,
                opacity 1200ms linear;
    flex-shrink: 0;
  }
  .vmx-event-chip[data-age="now"] {
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.10) 0%, rgba(255, 138, 61, 0.03) 100%);
    border-color: var(--amber-40);
    color: var(--amber-pale);
    text-shadow: 0 0 4px var(--amber-22);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 var(--amber-40),
      inset 0 0 12px var(--amber-22);
  }
  .vmx-event-chip[data-age="warm"] {
    background: rgba(255, 138, 61, 0.05);
    border-color: var(--amber-22);
    color: var(--amber);
    text-shadow: 0 0 4px var(--amber-22);
  }
  .vmx-event-chip[data-age="cool"] {
    background: rgba(0, 0, 0, 0.35);
    border-color: var(--silk-12);
    color: var(--silk-40);
    opacity: 0.85;
  }
`;

registerStyle("vmx-event-ribbon", CSS);

function ageBucket(ageMs: number): "now" | "warm" | "cool" {
  if (ageMs < 600) return "now";
  if (ageMs < 4000) return "warm";
  return "cool";
}

export function renderEventRibbon(props: EventRibbonProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "vmx-event-ribbon";
  root.setAttribute("aria-label", "recent events");
  populate(root, props);
  return root;
}

function populate(root: HTMLElement, props: EventRibbonProps): void {
  const max = props.max ?? MAX_DEFAULT;
  // Newest right — slice the last `max` from the events list (caller may
  // pass them oldest-first or newest-first; we standardise on the spec
  // which says "newest right, scrolls left as new events arrive").
  // Treat the input as oldest-first (typical append order).
  const visible = props.events.slice(-max);
  for (const evt of visible) {
    const chip = document.createElement("span");
    chip.className = "vmx-event-chip";
    chip.dataset.id = evt.id;
    chip.dataset.age = ageBucket(evt.ageMs);
    chip.textContent = evt.label;
    root.append(chip);
  }
}

/** Idempotent hot-update — rebuilds the chip list. Diff would be possible
 *  via dataset.id keys; for now the simple rebuild is fine because the
 *  ribbon is small (max 12 chips). */
export function setEventRibbon(el: HTMLElement, props: EventRibbonProps): void {
  el.replaceChildren();
  populate(el, props);
}
