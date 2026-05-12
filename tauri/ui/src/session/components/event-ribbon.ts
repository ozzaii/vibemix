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
    padding: 10px;
    background: var(--panel-deep);
    border: 1px solid var(--bezel-1);
    border-radius: 5px;
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.6);
    overflow: hidden;
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--ink-deep);
  }
  .vmx-event-chip {
    display: inline-flex;
    align-items: center;
    height: 24px;
    padding: 0 10px;
    border: 1px solid var(--bezel-2);
    border-radius: 4px;
    background: var(--ink-engraved);
    color: var(--ink-deep);
    line-height: 1;
    transition: color 250ms linear,
                background 250ms linear,
                border-color 250ms linear,
                text-shadow 250ms linear,
                box-shadow 250ms linear;
    flex-shrink: 0;
  }
  .vmx-event-chip[data-age="now"] {
    background: var(--phosphor-soft);
    border-color: var(--phosphor);
    color: var(--phosphor);
    text-shadow: 0 0 4px var(--phosphor);
    box-shadow: var(--phosphor-glow);
  }
  .vmx-event-chip[data-age="warm"] {
    background: var(--phosphor-soft);
    border-color: var(--phosphor-dim);
    color: var(--phosphor);
    text-shadow: 0 0 4px var(--phosphor-dim);
  }
  .vmx-event-chip[data-age="cool"] {
    background: var(--ink-engraved);
    border-color: var(--bezel-2);
    color: var(--phosphor-dim);
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
