/* mode-picker.ts — top-level 4-mode picker on the main session window.
 *
 * Phase 97 / ONBOARD-01: surfaces COHOST / LEARN / BUILD / DEBRIEF as a
 * segmented switch above the persona block. Mirrors the rocker.ts pattern
 * (BEG/INT/PRO + HYPE/TEACH/COACH) but stays a SEPARATE module so the mode
 * picker can evolve independently (different segment count, different
 * mount point, distinct ARIA semantics — mode is app-level state, the
 * rocker variants are persona attributes).
 *
 * Optimistic repaint (CLAUDE.md rule): the click handler flips data-active
 * LOCALLY before invoking onChange(id). The parent then writes
 * setSessionState({ mode: id }) and emits ipc.session.set_mode — both in
 * the same tick. The sidecar persists; if it rejects (it never should for
 * a closed-enum field), the next ipc.settings.state snapshot would
 * authoritatively repaint. Without the optimistic flip the control would
 * look dead for the ~3ms round-trip — the recurring "no buttons work" bug
 * this discipline closes.
 *
 * Visual: amber-bleed-through-frost pressed-segment recipe identical to
 * rocker.ts (var(--amber) + var(--amber-22) inset glow + var(--amber-40)
 * hairline) so the mode picker reads as a sibling control, not a second
 * palette. Saira + JetBrains Mono only; no hex literals. */

import { vmxLog } from "../../debug-log.js";
import { registerStyle } from "./_style-registry.js";

export type ModePickerMode = "cohost" | "learn" | "build" | "debrief";

export interface ModePickerOption {
  id: ModePickerMode;
  label: string;
}

export interface ModePickerProps {
  active: ModePickerMode;
  onChange?: (mode: ModePickerMode) => void;
  ariaLabel?: string;
}

/** Static option set — order is the LEFT-TO-RIGHT visual order on the
 *  picker. cohost first (the v4-era default), debrief last (the
 *  post-session review surface). */
export const MODE_PICKER_OPTIONS: ReadonlyArray<ModePickerOption> = [
  { id: "cohost", label: "COHOST" },
  { id: "learn", label: "LEARN" },
  { id: "build", label: "BUILD" },
  { id: "debrief", label: "DEBRIEF" },
];

const CSS = `
  .vmx-mode-picker {
    display: inline-flex;
    align-items: stretch;
    gap: 0;
    background: var(--glass-3);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    padding: 3px;
    box-shadow:
      inset 0 2px 5px rgba(0, 0, 0, 0.85),
      inset 0 0 0 1px rgba(0, 0, 0, 0.5),
      inset 0 -1px 0 rgba(255, 255, 255, 0.028);
    height: 34px;
    width: 100%;
  }
  .vmx-mode-picker__seg {
    flex: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 0 var(--sp-2);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 10.5px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    line-height: 1;
    border: none;
    border-radius: var(--rad-sm);
    background: transparent;
    color: var(--silk-65);
    cursor: pointer;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    transition: background var(--motion-snap) ease-out,
                color var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out,
                text-shadow var(--motion-snap) ease-out;
  }
  .vmx-mode-picker__seg:hover,
  .vmx-mode-picker__seg:focus-visible {
    color: var(--silk);
    box-shadow: var(--glow-faint);
  }
  .vmx-mode-picker__seg[data-active="true"] {
    color: var(--amber);
    background: linear-gradient(180deg, rgba(255, 165, 223, 0.095) 0%, rgba(255, 165, 223, 0.026) 100%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 rgba(255, 165, 223, 0.30),
      inset 0 0 9px var(--amber-22),
      0 0 0 1px rgba(255, 165, 223, 0.13);
    text-shadow: 0 0 3px var(--amber-40);
  }
`;

registerStyle("vmx-mode-picker", CSS);

export function renderModePicker(props: ModePickerProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "vmx-mode-picker";
  root.setAttribute("role", "radiogroup");
  root.setAttribute("aria-label", props.ariaLabel ?? "vibemix mode");

  for (const opt of MODE_PICKER_OPTIONS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "vmx-mode-picker__seg";
    btn.dataset.id = opt.id;
    btn.dataset.active = opt.id === props.active ? "true" : "false";
    btn.setAttribute("role", "radio");
    btn.setAttribute("aria-checked", opt.id === props.active ? "true" : "false");

    const lbl = document.createElement("span");
    lbl.textContent = opt.label;
    btn.append(lbl);

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      // Read the LIVE active segment from the DOM, not props.active —
      // setModePickerActive() flips data-active without updating that
      // closure (rocker.ts has the same precedent and the same bug
      // history).
      const liveActive = root.querySelector<HTMLElement>(
        '.vmx-mode-picker__seg[data-active="true"]',
      )?.dataset.id as ModePickerMode | undefined;
      vmxLog("[vmx:click]", `mode-picker · ${props.ariaLabel ?? "mode"}`, {
        id: opt.id,
        noop: opt.id === liveActive,
      });
      if (opt.id === liveActive) return;
      // Optimistic repaint — flip the lit segment NOW so the user sees
      // the result of their click instantly. ipc.session.set_mode round-
      // trips in ~3ms; without the local flip the control looks dead
      // until the round-trip lands (and the sidecar's settings.state
      // echo never specifically targets the mode field today, so the
      // local flip IS the user-visible source of truth — the wire
      // envelope is purely persistence).
      setModePickerActive(root, opt.id);
      props.onChange?.(opt.id);
    });
    root.append(btn);
  }

  return root;
}

/** Update active segment without rebuilding the picker. Mirrors
 *  setRockerActive() so external sync (cold-boot ipc.settings.state →
 *  setSessionState({mode}) → re-render) can flip the lit segment in
 *  place. */
export function setModePickerActive(el: HTMLElement, id: ModePickerMode): void {
  el.querySelectorAll<HTMLElement>(".vmx-mode-picker__seg").forEach((seg) => {
    const isActive = seg.dataset.id === id;
    seg.dataset.active = isActive ? "true" : "false";
    seg.setAttribute("aria-checked", isActive ? "true" : "false");
  });
}
