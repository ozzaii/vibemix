/* picker.ts — dropdown row component (44px row, 240px dropdown).
 *
 * Used by voice picker, genre picker, output device picker (session
 * persona + output panels, and the settings drawer copies).
 *
 * v5 CDJ Whisper migration (2026-05-12): row reads as a sealed dark-glass
 * tile (mock §02 .btn), opens into a glass-1 popover (mock .tray-popover).
 * No bevel gradients, no FL-Studio brushed-metal residue. Avatar collapses
 * to a flat amber-disc seal; chevron is a JetBrains Mono caret that lifts
 * to amber on open. */

/* VIS-02 (43-02): --glow-faint on hover/focus-visible per CONTEXT.
 * Row + option both carry the faint amber halo on interactive states;
 * closes session-audit finding M-02 (inactive opt :hover was previously
 * inconsistent with the row trigger which already gained a glow). */

import { vmxLog } from "../../debug-log.js";
import { registerStyle } from "./_style-registry.js";

export interface PickerOption {
  id: string;
  label: string;
  sub?: string | null;
}

export interface PickerProps {
  label: string;
  value: string;
  options: PickerOption[];
  /** Inline SVG markup for the leading 24×24 icon (e.g. headphones). */
  iconSvg?: string;
  /** Optional avatar (radial-gradient circle) instead of icon — voice picker. */
  avatar?: boolean;
  /** Show the "AUTO" pill when the value is auto-selected by the sidecar. */
  autoPill?: boolean;
  onChange?: (id: string) => void;
}

const CSS = `
  .vmx-picker {
    position: relative;
    width: 100%;
  }
  .vmx-picker__row {
    display: flex;
    align-items: center;
    gap: var(--sp-3);
    height: 40px;
    padding: 0 12px 0 10px;
    background: var(--glass-2);
    backdrop-filter: var(--blur-glass-display);
    -webkit-backdrop-filter: var(--blur-glass-display);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.035),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45);
    cursor: pointer;
    color: var(--silk-65);
    transition: color var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out,
                background var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out;
  }
  /* VIS-02 (43-02) — picker row carries an additive --glow-faint on
   * hover+focus-visible alongside its pre-existing 10px amber inset
   * shadow. The outer halo lifts the row off the silk-22 frame the same
   * way the rocker does, keeping the affordance vocabulary uniform. */
  .vmx-picker__row:hover,
  .vmx-picker__row:focus-visible {
    color: var(--silk);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45),
      0 0 10px var(--amber-22),
      var(--glow-faint);
  }
  /* Picker row owns the outer halo above — kill the body-level
   * 2px amber outline so we don't stack two focus rings. */
  .vmx-picker__row:focus-visible { outline: none; }
  .vmx-picker[data-open="true"] .vmx-picker__row {
    color: var(--amber);
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.09) 0%, rgba(255, 138, 61, 0.025) 100%);
    border-color: rgba(255, 138, 61, 0.14);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 var(--amber-40),
      inset 0 0 14px var(--amber-22),
      0 0 0 1px rgba(255, 138, 61, 0.14);
    text-shadow: 0 0 4px var(--amber-65);
  }
  .vmx-picker__icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    color: var(--amber);
    flex-shrink: 0;
    filter: drop-shadow(0 0 3px var(--amber-22));
  }
  /* Avatar — a flat amber-pinpoint disc on a void-2 ground (the voice "seal").
   * v5 drops the bevel-radial-gradient that the FL-Studio direction used.
   * The amber dot reads as a single mascot eye — quiet but characterful. */
  .vmx-picker__avatar {
    width: 18px;
    height: 18px;
    flex-shrink: 0;
    border-radius: 50%;
    background: var(--void-2);
    border: 1px solid var(--glass-edge);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.04),
      inset 0 0 4px rgba(0, 0, 0, 0.55);
    position: relative;
  }
  .vmx-picker__avatar::after {
    content: '';
    position: absolute;
    inset: 0;
    margin: auto;
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--amber);
    box-shadow:
      0 0 3px var(--amber),
      0 0 6px var(--amber-40);
  }
  .vmx-picker__label {
    flex: 1;
    min-width: 0;
    font-family: var(--type-body);
    font-variation-settings: "wdth" 95, "wght" 500;
    font-size: 12px;
    letter-spacing: 0.04em;
    line-height: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    /* 2026-05-19 /impeccable critique fix: forced lowercase on row
     * labels and dropdown options was the SaaS/dev-tool fingerprint
     * (Vercel, Cron, Linear). Pioneer hardware labels carry their
     * source casing. Device names like "MacBook Pro Speakers" and
     * proper-name voices ("Aoede", "Charon") now render natively. */
    color: inherit;
  }
  .vmx-picker__auto {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 9px;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    padding: 3px 7px;
    border-radius: 1px;
    background: rgba(255, 138, 61, 0.08);
    border: 1px solid var(--amber-22);
    color: var(--amber);
    line-height: 1;
    text-shadow: 0 0 4px var(--amber-22);
  }
  .vmx-picker__chev {
    font-family: var(--type-mono);
    color: var(--silk-40);
    font-size: 10px;
    line-height: 1;
    transition: color var(--motion-snap) ease-out,
                transform var(--motion-snap) ease-out,
                text-shadow var(--motion-snap) ease-out;
  }
  .vmx-picker__row:hover .vmx-picker__chev { color: var(--silk-65); }
  .vmx-picker[data-open="true"] .vmx-picker__chev {
    color: var(--amber);
    transform: rotate(180deg);
    text-shadow: 0 0 4px var(--amber-22);
  }
  /* Dropdown — sealed glass-1 popover (mock .tray-popover treatment).
   *
   * 2026-05-24 release-blocker fix: the popover is anchored with
   * position:fixed (viewport coordinates supplied by openList() via
   * getBoundingClientRect) rather than position:absolute. The pickers
   * live inside .vmx-panel / .vmx-settings-group containers that carry
   * overflow:hidden + backdrop-filter (for the rounded glass shell) — an
   * absolutely-positioned child was clipped by that overflow and buried
   * beneath sibling panels below it (each backdrop-filter opens a new
   * stacking context, so the dropdown's z-index:30 was scoped to its own
   * container and lost the cross-container paint order). Fixed positioning
   * lifts the list into the viewport layer where nothing clips or occludes
   * it; the z-index then competes at the top level. The row JS keeps left/
   * top/width in sync on open + scroll/resize. */
  .vmx-picker__list {
    position: fixed;
    z-index: 1000;
    min-width: 200px;
    max-height: 280px;
    overflow: auto;
    background: var(--glass-1);
    backdrop-filter: var(--blur-glass);
    -webkit-backdrop-filter: var(--blur-glass);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    /* 2026-05-19 /impeccable critique fix: popover triple-shadow
     * collapsed to single drop. DESIGN.md §4 hero recipe is one
     * 0 16px 36px shadow + one 1px outer ring — anything beyond
     * that drifts toward Material-3 elevation. */
    box-shadow:
      inset 0 1px 0 var(--glass-top),
      0 16px 36px rgba(0, 0, 0, 0.55),
      0 0 0 1px rgba(255, 255, 255, 0.018);
    padding: 4px;
    opacity: 0;
    transform: translateY(-3px);
    pointer-events: none;
    transition: opacity var(--motion-transition) ease-out,
                transform var(--motion-transition) ease-out;
  }
  .vmx-picker[data-open="true"] .vmx-picker__list {
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
  }
  /* Custom scrollbar — keep the popover from breaking character. */
  .vmx-picker__list::-webkit-scrollbar { width: 4px; }
  .vmx-picker__list::-webkit-scrollbar-track { background: transparent; }
  .vmx-picker__list::-webkit-scrollbar-thumb {
    background: var(--silk-22);
    border-radius: 2px;
  }
  .vmx-picker__list::-webkit-scrollbar-thumb:hover { background: var(--amber-40); }
  .vmx-picker__opt {
    display: flex;
    align-items: center;
    gap: var(--sp-3);
    width: 100%;
    padding: 0 10px;
    height: 28px;
    border: none;
    background: transparent;
    color: var(--silk-65);
    font-family: var(--type-body);
    font-variation-settings: "wdth" 95, "wght" 500;
    font-size: 12px;
    letter-spacing: 0.04em;
    line-height: 1;
    text-align: left;
    cursor: pointer;
    border-radius: 1px;
    transition: color 120ms ease-out, background 120ms ease-out, text-shadow 120ms ease-out;
  }
  /* VIS-02 (43-02) — closes M-02. Previously the inactive opt :hover
   * relied on colour + background lift alone; the active-row variant
   * downstream already pairs --glow-faint with its tint dot, leaving
   * an inconsistency the audit flagged as confusing during scan.
   * Apply --glow-faint here too so the entire option row vocabulary
   * carries a faint amber halo on hover — the active-row still gains
   * the deeper --glow-soft glow exclusively via the dot+tint pairing. */
  .vmx-picker__opt:hover,
  .vmx-picker__opt:focus-visible {
    color: var(--amber);
    background: rgba(255, 138, 61, 0.06);
    text-shadow: 0 0 4px var(--amber-22);
    box-shadow: var(--glow-faint);
  }
  .vmx-picker__opt:focus-visible { outline: none; }
  .vmx-picker__opt[data-selected="true"] {
    color: var(--amber);
    background: rgba(255, 138, 61, 0.05);
    text-shadow: 0 0 4px var(--amber-22);
  }
  .vmx-picker__opt[data-selected="true"]::before {
    content: '';
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--amber);
    /* Active/selected row carries the DEEPER glow (the comment above + the
     * 20/80 active-state rule: the one selected option is where the eye lands).
     * Inactive :hover keeps --glow-faint; the selected dot gets --glow-soft. */
    box-shadow: var(--glow-soft);
    flex-shrink: 0;
    margin-right: 2px;
  }
  .vmx-picker__opt-sub {
    margin-left: auto;
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.04em;
    color: var(--silk-40);
    text-transform: none;
  }
`;

registerStyle("vmx-picker", CSS);

export function renderPicker(props: PickerProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "vmx-picker";
  root.dataset.open = "false";
  root.setAttribute("aria-label", props.label);

  const row = document.createElement("button");
  row.type = "button";
  row.className = "vmx-picker__row";
  row.setAttribute("aria-haspopup", "listbox");
  row.setAttribute("aria-expanded", "false");

  if (props.avatar) {
    const av = document.createElement("span");
    av.className = "vmx-picker__avatar";
    av.setAttribute("aria-hidden", "true");
    row.append(av);
  } else if (props.iconSvg) {
    const ic = document.createElement("span");
    ic.className = "vmx-picker__icon";
    ic.innerHTML = props.iconSvg;
    row.append(ic);
  }

  const lbl = document.createElement("span");
  lbl.className = "vmx-picker__label";
  lbl.textContent = props.value;
  row.append(lbl);

  if (props.autoPill) {
    const pill = document.createElement("span");
    pill.className = "vmx-picker__auto";
    pill.textContent = "AUTO";
    row.append(pill);
  }

  const chev = document.createElement("span");
  chev.className = "vmx-picker__chev";
  chev.textContent = "▾";
  chev.setAttribute("aria-hidden", "true");
  row.append(chev);

  root.append(row);

  const list = document.createElement("div");
  list.className = "vmx-picker__list";
  list.setAttribute("role", "listbox");
  for (const opt of props.options) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "vmx-picker__opt";
    btn.dataset.id = opt.id;
    btn.dataset.selected = opt.label === props.value ? "true" : "false";
    btn.setAttribute("role", "option");
    btn.setAttribute("aria-selected", opt.label === props.value ? "true" : "false");
    const t = document.createElement("span");
    t.textContent = opt.label;
    btn.append(t);
    if (opt.sub) {
      const sub = document.createElement("span");
      sub.className = "vmx-picker__opt-sub";
      sub.textContent = opt.sub;
      btn.append(sub);
    }
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      vmxLog("[vmx:click]", `picker option · ${props.label}`, {
        id: opt.id,
        label: opt.label,
      });
      closeList();
      // Optimistic select — the picker analog of rocker.setRockerActive.
      // Without this the row label stayed frozen until the sidecar
      // round-tripped ipc.settings.state; in dev (no live session) that
      // echo never arrives, so every dropdown read as dead even though
      // onChange fired. Flip the displayed value + selected marks the
      // instant a choice is made; the round-trip (when it comes) re-renders
      // the panel with the authoritative value and self-corrects any drift.
      selectOption(opt.label);
      props.onChange?.(opt.id);
    });
    list.append(btn);
  }
  root.append(list);

  // Optimistic select: update the row label + the option selected-marks to
  // reflect a freshly chosen value without waiting for a backend re-render.
  // Matches the displayed value by option LABEL (the row shows labels, and
  // option labels are unique within a picker). Exposed so callers can also
  // drive it from an authoritative ipc.settings.state echo if they want.
  function selectOption(label: string): void {
    lbl.textContent = label;
    list.querySelectorAll<HTMLElement>(".vmx-picker__opt").forEach((o) => {
      const t = o.querySelector("span")?.textContent ?? "";
      const sel = t === label;
      o.dataset.selected = sel ? "true" : "false";
      o.setAttribute("aria-selected", sel ? "true" : "false");
    });
  }

  // The dropdown is `position: fixed`, so its coordinates are viewport-
  // relative and must be recomputed from the row's live bounding rect each
  // time it opens (and whenever an ancestor scrolls/the window resizes
  // while open — the drawer body + session grid are both scroll containers).
  function positionList(): void {
    // getBoundingClientRect can be absent in non-DOM test envs — guard so a
    // headless render path never throws.
    if (typeof row.getBoundingClientRect !== "function") return;
    const r = row.getBoundingClientRect();
    list.style.left = `${r.left}px`;
    list.style.top = `${r.bottom + 5}px`;
    // Match the row width so the popover stays visually anchored to its
    // trigger (mirrors the old `width: 100%` against the row).
    list.style.width = `${r.width}px`;
  }

  function openList(): void {
    root.dataset.open = "true";
    row.setAttribute("aria-expanded", "true");
    positionList();
    window.addEventListener("scroll", positionList, true);
    window.addEventListener("resize", positionList);
  }
  function closeList(): void {
    root.dataset.open = "false";
    row.setAttribute("aria-expanded", "false");
    window.removeEventListener("scroll", positionList, true);
    window.removeEventListener("resize", positionList);
  }

  row.addEventListener("click", (e) => {
    e.preventDefault();
    const willOpen = root.dataset.open !== "true";
    vmxLog("[vmx:click]", `picker row · ${props.label}`, {
      action: willOpen ? "open" : "close",
      value: props.value,
    });
    if (willOpen) openList();
    else closeList();
  });

  // Close on outside click — registered once per picker. Because the list
  // is now `position: fixed` (lifted out of the picker's DOM-flow box but
  // still a DOM descendant of `root`), `root.contains(e.target)` continues
  // to match clicks inside the open popover, so an option click does NOT
  // self-dismiss before its own handler runs.
  document.addEventListener("click", (e) => {
    if (root.dataset.open !== "true") return;
    if (!(e.target instanceof Node) || !root.contains(e.target)) {
      closeList();
    }
  });

  return root;
}
