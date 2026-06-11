/* Settings drawer group wrapper.
 *
 * A "group" is one labelled section inside the slide-over drawer
 * (PERSONA, OUTPUT, HOTKEY, RECORDING, CALIBRATION, MASCOT). Visually a
 * subdued v5 plate — glass-2 backdrop with silkscreen Saira header,
 * glass-edge hairline, no streak (the drawer is already one big glass
 * surface; stacking sheens inside it reads noisy).
 *
 * Pure-function — accepts {header, children, badge?, footer?} and returns
 * an HTMLElement. No state.
 */

import { registerStyle } from "../../session/components/_style-registry.js";

export interface SettingsGroupProps {
  header: string;
  children: HTMLElement | HTMLElement[];
  /** Stable mock-transfer / integration anchor. Defaults to settings.group.<header>. */
  wireId?: string;
  /** Optional UPPER-pill on the right of the header (e.g. "CFG"). */
  badge?: string;
  /** Optional footer slot (e.g. inline error message). */
  footer?: HTMLElement | null;
}

const CSS = `
  /* Forged-Obsidian level-up (2026-05-30): the prior "rows on hairlines" group
   * read as a flat wireframe list — the owner's "saçmalık" verdict. A group is
   * now a LIT RECESSED MODULE on the drawer void: a faintly-raised machined slab
   * with a top sheen + a crisp leading hairline catching the room's rose light,
   * a milled inset floor so the controls sit DOWN inside it, and a header with
   * real presence (a brand tick, a strong tracked Saira label, a hairline rule
   * with a rose ignition at its origin). Spacing rhythm varies between header,
   * body and footer — no monotone padding. Material reads via tokens only. */
  .vmx-settings-group {
    position: relative;
    flex: 0 0 auto;
    margin: 12px 0;
    border-radius: var(--rad-sm);
    border: 0;
    background:
      linear-gradient(180deg, rgba(246, 243, 245, 0.032) 0%, transparent 18%, rgba(0, 0, 0, 0.20) 100%),
      rgba(48, 42, 46, 0.50);
    box-shadow:
      var(--bevel-raised),
      inset 0 0 0 1px rgba(255, 255, 255, 0.014);
    overflow: hidden;
  }
  .vmx-settings-group:first-child {
    margin-top: 0;
  }
  .vmx-settings-group:last-child {
    margin-bottom: 0;
  }
  .vmx-settings-group__header {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-3);
    padding: 13px var(--sp-4) 11px 18px;
    /* Engraved-hardware voice: every machined label in the contract mock is
     * Geist Mono + wide tracking. Geist Sans here read softer/webbier. */
    font-family: var(--type-mono);
    font-weight: 600;
    font-size: 10px;
    letter-spacing: 0.26em;
    text-transform: uppercase;
    color: var(--text-muted);
    line-height: 1;
    text-shadow: var(--text-emboss);
    background:
      linear-gradient(180deg, rgba(246, 243, 245, 0.016) 0%, transparent 62%),
      rgba(0, 0, 0, 0.13);
    box-shadow: inset 0 -1px 0 rgba(0, 0, 0, 0.26);
  }
  /* Brand tick before the label — the section's heartbeat dot, same vocabulary
   * as the grounding panel-section-label (mock §1084-1095). */
  .vmx-settings-group__header > span:first-child {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 11px;
  }
  /* The header floor hairline — a quiet warm-white seam, no rose dot per header
     (12+ simultaneous brand dots read as decoration, not signal). */
  .vmx-settings-group__header::after {
    content: "";
    position: absolute;
    left: 18px;
    right: var(--sp-4);
    bottom: 0;
    height: 1px;
    background: linear-gradient(90deg, var(--silk-12) 0%, rgba(246, 243, 245, 0.045) 18%, transparent 64%);
    opacity: 0.52;
  }
  /* Engraved chip, not a lit one — the badge is a static caption, and a
   * brand-filled pill here competed with the actual active controls for the
   * eye (20/80). State stays rose; furniture stays ink. */
  .vmx-settings-group__badge {
    font-family: var(--type-mono);
    font-size: 9px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    padding: 3px var(--sp-2);
    border-radius: var(--rad-sm);
    color: var(--text-muted);
    line-height: 1;
    text-shadow: var(--text-emboss);
    box-shadow:
      inset 0 0 0 1px rgba(255, 255, 255, 0.045),
      inset 0 -1px 0 rgba(0, 0, 0, 0.30);
  }
  /* Milled inset floor — the controls sit DOWN inside the recessed module.
   * Taller top breathing room than the tight bottom seat = internal rhythm. */
  .vmx-settings-group__body {
    padding: 16px 18px 18px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    background:
      linear-gradient(180deg, rgba(0, 0, 0, 0.12) 0%, transparent 34%),
      linear-gradient(90deg, rgba(246, 243, 245, 0.018), transparent 28%);
    box-shadow: inset 0 1px 0 rgba(246, 243, 245, 0.030);
  }
  /* Mono numerics inside any group read in warm ink, tabular — the hardware
   * readout vocabulary (gold stays quarantined to Camelot/heat/energy). */
  .vmx-settings-group__body :is(output, .vmx-mono, [data-numeric]) {
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    color: var(--text-secondary);
  }
  .vmx-settings-group__footer {
    padding: 10px var(--sp-5);
    border-top: 1px solid rgba(212, 65, 58, 0.28);
    background: linear-gradient(180deg, rgba(212, 65, 58, 0.07) 0%, rgba(212, 65, 58, 0.03) 100%);
    font-family: var(--type-mono);
    font-size: 11px;
    color: var(--led-fault);
    line-height: 1.35;
    text-shadow: 0 0 4px rgba(212, 65, 58, 0.18);
    box-shadow: inset 0 1px 0 rgba(212, 65, 58, 0.10);
  }

  /* P1-b finding #2 — two-stage mechanical slide-in: STAGE 2 (the settle).
   * Stage 1 is the drawer body's 250ms translateX (owned by SettingsDrawer
   * .vmx-settings-drawer). When the drawer lands, each group row does a short
   * ~120ms micro-settle (10px up → seat) on a per-group stagger so the tray
   * reads as sliding in THEN seating into place — a mechanical drawer, not a
   * single CSS slide. The trigger is data-settling="true", set on the drawer
   * ONLY by openSettings() and cleared after the run, so mid-session body
   * rebuilds (genre reload, recordings refresh) do NOT replay it.
   *
   * Stage-2 delays START at ~250ms (after stage 1 has landed) and step by
   * 28ms per group. GPU-cheap (transform + opacity only).
   *
   * prefers-reduced-motion GATE: the settle (and its stagger) is wrapped in
   * the no-preference media query, so reduced-motion users get the seated end
   * state with no transform at all. */
  @media (prefers-reduced-motion: no-preference) {
    @keyframes vmx-group-settle {
      from { transform: translateY(10px); opacity: 0; }
      to   { transform: translateY(0);    opacity: 1; }
    }
    .vmx-settings-drawer[data-settling="true"] .vmx-settings-group {
      animation: vmx-group-settle 120ms ease-out both;
    }
    .vmx-settings-drawer[data-settling="true"] .vmx-settings-group:nth-child(1) { animation-delay: 250ms; }
    .vmx-settings-drawer[data-settling="true"] .vmx-settings-group:nth-child(2) { animation-delay: 278ms; }
    .vmx-settings-drawer[data-settling="true"] .vmx-settings-group:nth-child(3) { animation-delay: 306ms; }
    .vmx-settings-drawer[data-settling="true"] .vmx-settings-group:nth-child(4) { animation-delay: 334ms; }
    .vmx-settings-drawer[data-settling="true"] .vmx-settings-group:nth-child(5) { animation-delay: 362ms; }
    .vmx-settings-drawer[data-settling="true"] .vmx-settings-group:nth-child(6) { animation-delay: 390ms; }
    .vmx-settings-drawer[data-settling="true"] .vmx-settings-group:nth-child(n+7) { animation-delay: 418ms; }
  }
`;

registerStyle("vmx-settings-group", CSS);

function groupWireId(header: string): string {
  const slug = header
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `settings.group.${slug || "section"}`;
}

export function renderSettingsGroup(props: SettingsGroupProps): HTMLElement {
  const root = document.createElement("section");
  root.className = "vmx-settings-group";
  root.dataset.wire = props.wireId ?? groupWireId(props.header);

  const head = document.createElement("div");
  head.className = "vmx-settings-group__header";
  head.dataset.wire = `${root.dataset.wire}.header`;
  const title = document.createElement("span");
  title.textContent = props.header;
  head.append(title);
  if (props.badge) {
    const b = document.createElement("span");
    b.className = "vmx-settings-group__badge";
    b.textContent = props.badge;
    head.append(b);
  }
  root.append(head);

  const body = document.createElement("div");
  body.className = "vmx-settings-group__body";
  body.dataset.wire = `${root.dataset.wire}.body`;
  const kids = Array.isArray(props.children) ? props.children : [props.children];
  for (const k of kids) body.append(k);
  root.append(body);

  if (props.footer) {
    const footer = document.createElement("div");
    footer.className = "vmx-settings-group__footer";
    footer.dataset.wire = `${root.dataset.wire}.footer`;
    footer.append(props.footer);
    root.append(footer);
  }

  return root;
}
