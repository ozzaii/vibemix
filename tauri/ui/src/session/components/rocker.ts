/* rocker.ts — segmented rocker switch with two visual variants.
 *
 *   variant: "rocker"      — simple segmented (BEG / INT / PRO or HP / SPK).
 *   variant: "interaction" — mood block buttons (HYPE / TEACH / COACH).
 *
 * v5 CDJ Whisper: active segment lit with the canonical amber-bleed-
 * through-frost recipe (--amber gradient + --amber-22 inset glow +
 * --amber-40 hairline + --amber text with --glow-soft text-shadow);
 * inactive sits flat on --glass-3 + --silk-40. Rocker bezel uses inset
 * shadow to look pressed-in. Pure-function — accepts {options, active,
 * onChange, variant} and emits a click that fires onChange(optionId). */

import { vmxLog } from "../../debug-log.js";
import { registerStyle } from "./_style-registry.js";

export type RockerVariant = "rocker" | "interaction";

export interface RockerOption {
  id: string;
  label: string;
}

export interface RockerProps {
  options: RockerOption[];
  active: string;
  onChange?: (id: string) => void;
  variant?: RockerVariant;
  ariaLabel?: string;
}

/* VIS-02 (43-02): --glow-faint on hover/focus-visible per CONTEXT. The
 * rocker segments are the primary interactive control in the persona
 * panel (BEG/INT/PRO + HYPE/TEACH/COACH); closes session-audit finding
 * H-01 by adding `box-shadow: var(--glow-faint)` to the :hover state
 * and mirroring on :focus-visible for keyboard parity (WCAG 2.1). */
const CSS = `
  .vmx-rocker {
    display: inline-flex;
    align-items: stretch;
    gap: 0;
    background:
      linear-gradient(180deg, rgba(255, 222, 242, 0.018), transparent 60%),
      var(--glass-3);
    border: 1px solid var(--border-subtle);
    border-radius: var(--rad-sm);
    padding: 3px;
    box-shadow:
      inset 0 2px 5px rgba(0, 0, 0, 0.85),
      inset 0 0 0 1px rgba(0, 0, 0, 0.5),
      inset 0 -1px 0 rgba(255, 255, 255, 0.028),
      0 1px 0 rgba(255, 255, 255, 0.016);
    height: 34px;
    width: 100%;
  }
  .vmx-rocker__seg {
    flex: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 0 var(--sp-2);
    /* Mono = the engraved-hardware voice every machined label in the contract
     * mock speaks; the sans variant read webbier at the same size. */
    font-family: var(--type-mono);
    font-weight: 600;
    font-size: 10px;
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
  /* Hover = the interior of the key catches light. No outer halo: glow
   * around a segment sitting INSIDE a recessed well is physically wrong
   * (neon-sticker grammar) — DESIGN's Inset-Bezel-Over-Shadow rule. */
  .vmx-rocker__seg:hover,
  .vmx-rocker__seg:focus-visible {
    color: var(--silk);
    background: rgba(255, 255, 255, 0.035);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.050);
  }
  /* The body-level *:focus-visible already paints a 2px amber outline +
   * --glow-soft so we explicitly suppress the duplicate ring on the
   * segment (its glow comes from the rule above). */
  /* --- THE LIT KEY (2026-06-11 grammar): the selected segment is a
   * physically lit key — rose FILL under INK text, machined lips intact
   * (GO LIVE's material at control scale). The old recipe (rose text +
   * rose inset ring + rose text-glow) was the glowy-sticker grammar that
   * read "vibe coded"; both variants share the one hardware state. --- */
  .vmx-rocker[data-variant="rocker"] .vmx-rocker__seg[data-active="true"],
  .vmx-rocker[data-variant="interaction"] .vmx-rocker__seg[data-active="true"] {
    color: var(--text-primary);
    background: linear-gradient(180deg, var(--brand-22) 0%, var(--brand-08) 58%, var(--brand-04) 100%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.14),
      inset 0 -1px 0 rgba(0, 0, 0, 0.40);
    text-shadow: var(--text-emboss);
  }
  /* Legacy LED prefix kept rendering for backward-compat with the
   * existing renderRocker(variant="interaction") signature, but visually
   * suppressed — v5 mood-block uses concentrated text-glow, not a
   * separate LED ornament. */
  .vmx-rocker__led { display: none; }
`;

registerStyle("vmx-rocker", CSS);

export function renderRocker(props: RockerProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "vmx-rocker";
  root.setAttribute("role", "radiogroup");
  if (props.ariaLabel) root.setAttribute("aria-label", props.ariaLabel);
  root.dataset.variant = props.variant ?? "rocker";

  for (const opt of props.options) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "vmx-rocker__seg";
    btn.dataset.id = opt.id;
    btn.dataset.active = opt.id === props.active ? "true" : "false";
    btn.setAttribute("role", "radio");
    btn.setAttribute("aria-checked", opt.id === props.active ? "true" : "false");

    if (props.variant === "interaction") {
      const led = document.createElement("span");
      led.className = "vmx-rocker__led";
      led.setAttribute("aria-hidden", "true");
      btn.append(led);
    }
    const lbl = document.createElement("span");
    lbl.textContent = opt.label;
    btn.append(lbl);

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      // Read the LIVE active segment from the DOM, not the captured
      // `props.active` — setRockerActive() flips data-active without
      // updating that closure, so the mount-default segment (e.g. INT for
      // skill, HYPE for mood) would otherwise forever match the stale
      // props.active and no-op. (2026-05-25: this was the real "HYPE/INT
      // don't work" bug — both are the mount-default actives.)
      const liveActive = root.querySelector<HTMLElement>(
        '.vmx-rocker__seg[data-active="true"]',
      )?.dataset.id;
      vmxLog("[vmx:click]", `rocker · ${props.ariaLabel ?? props.variant ?? "rocker"}`, {
        id: opt.id,
        noop: opt.id === liveActive,
      });
      if (opt.id === liveActive) return;
      // Optimistic repaint — flip the lit segment NOW, before the async
      // ipc.settings.set round-trip. The drawer has no settings.state
      // refresh path (setSessionState has no pub/sub), so without this the
      // active segment never moves and the control looks dead even though
      // the change persists in ~3ms. Mirrors the picker's selectOption()
      // precedent. The round-trip is authoritative and self-corrects if the
      // sidecar rejects the value. (2026-05-26: the real "no buttons work".)
      setRockerActive(root, opt.id);
      props.onChange?.(opt.id);
    });
    root.append(btn);
  }

  return root;
}

/** Update active segment without rebuilding the rocker. */
export function setRockerActive(el: HTMLElement, id: string): void {
  el.querySelectorAll<HTMLElement>(".vmx-rocker__seg").forEach((seg) => {
    const isActive = seg.dataset.id === id;
    seg.dataset.active = isActive ? "true" : "false";
    seg.setAttribute("aria-checked", isActive ? "true" : "false");
  });
}
