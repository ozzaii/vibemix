/* permissions-card.ts — Step 1 horizontal card (UI-SPEC §6).
 *
 * 56px tall, full-width. Left = OS-tinted icon (shield = screen recording,
 * mic = microphone). Center = label (Workbench 9px UPPERCASE) + sub
 * (DM Mono 11px --ink-dim). Right = state indicator:
 *   - pending: [ Grant ] secondary button
 *   - granted: ● GRANTED Workbench 9px --ok with --ok LED
 *   - denied:  ● DENIED — open Settings ↗ in --rec
 *
 * Copy strings VERBATIM from UI-SPEC §6 / §Step 1 Permissions Strings. */

import { registerStyle } from "./_style-registry.js";
import { SHIELD_SVG } from "../icons/shield.svg.js";
import { MICROPHONE_SVG } from "../icons/microphone.svg.js";
import { Button } from "./button.js";

export type PermissionKind = "screen-recording" | "microphone";
export type PermissionState = "pending" | "granted" | "denied";

export interface PermissionsCardProps {
  kind: PermissionKind;
  state: PermissionState;
  onGrantClick?: () => void;
  onOpenSettings?: () => void;
}

const CSS = `
  .cmp-perm-card {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: var(--sp-md);
    height: 56px;
    padding: 0 var(--sp-md);
    background: linear-gradient(180deg, var(--panel-lift), var(--panel));
    border: 1px solid var(--bezel-1);
    border-radius: 6px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  }
  .cmp-perm-card__icon {
    color: var(--phosphor-dim);
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
  }
  .cmp-perm-card[data-state="granted"] .cmp-perm-card__icon { color: var(--ok); }
  .cmp-perm-card[data-state="denied"]  .cmp-perm-card__icon { color: var(--rec); }
  .cmp-perm-card__text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  .cmp-perm-card__label {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 0.32em;
    text-transform: uppercase;
    color: var(--ink);
    line-height: 1;
  }
  .cmp-perm-card__sub {
    font-family: "DM Mono", monospace;
    font-size: 11px;
    color: var(--ink-dim);
    line-height: 1.35;
  }
  .cmp-perm-card__right {
    display: flex;
    align-items: center;
    gap: var(--sp-sm);
  }
  .cmp-perm-card__state-readout {
    display: inline-flex;
    align-items: center;
    gap: var(--sp-xs);
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 0.32em;
    text-transform: uppercase;
    cursor: default;
  }
  .cmp-perm-card__state-readout[data-tone="ok"]  { color: var(--ok); }
  .cmp-perm-card__state-readout[data-tone="rec"] { color: var(--rec); cursor: pointer; }
  .cmp-perm-card__led {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
  }
  .cmp-perm-card__state-readout[data-tone="ok"]  .cmp-perm-card__led { background: var(--ok);  box-shadow: 0 0 6px var(--ok); }
  .cmp-perm-card__state-readout[data-tone="rec"] .cmp-perm-card__led { background: var(--rec); box-shadow: 0 0 6px var(--rec); }
`;

registerStyle("cmp-perm-card", CSS);

// UI-SPEC §6 + Step 1 strings — VERBATIM.
const COPY: Record<PermissionKind, { label: string; sub: string }> = {
  "screen-recording": {
    label: "SCREEN RECORDING",
    sub: "required to see your dj software window",
  },
  microphone: {
    label: "MICROPHONE",
    sub: "lets you talk back to avery — turn off mid-set anytime",
  },
};

const ICON: Record<PermissionKind, string> = {
  "screen-recording": SHIELD_SVG,
  microphone: MICROPHONE_SVG,
};

export function PermissionsCard(props: PermissionsCardProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "cmp-perm-card";
  root.dataset.kind = props.kind;
  root.dataset.state = props.state;

  const icon = document.createElement("div");
  icon.className = "cmp-perm-card__icon";
  icon.innerHTML = ICON[props.kind];

  const text = document.createElement("div");
  text.className = "cmp-perm-card__text";
  const label = document.createElement("span");
  label.className = "cmp-perm-card__label";
  label.textContent = COPY[props.kind].label;
  const sub = document.createElement("span");
  sub.className = "cmp-perm-card__sub";
  sub.textContent = COPY[props.kind].sub;
  text.append(label, sub);

  const right = document.createElement("div");
  right.className = "cmp-perm-card__right";

  if (props.state === "pending") {
    right.append(
      Button({
        variant: "secondary",
        state: "idle",
        label: "Grant",
        leadingGlyph: "[",
        trailingGlyph: "]",
        onClick: props.onGrantClick,
      })
    );
  } else if (props.state === "granted") {
    const ok = document.createElement("span");
    ok.className = "cmp-perm-card__state-readout";
    ok.dataset.tone = "ok";
    const led = document.createElement("span");
    led.className = "cmp-perm-card__led";
    led.setAttribute("aria-hidden", "true");
    const txt = document.createElement("span");
    // UI-SPEC §Step 1 — VERBATIM
    txt.textContent = "GRANTED";
    ok.append(led, txt);
    right.append(ok);
  } else if (props.state === "denied") {
    const denied = document.createElement("span");
    denied.className = "cmp-perm-card__state-readout";
    denied.dataset.tone = "rec";
    denied.setAttribute("role", "button");
    denied.setAttribute("tabindex", "0");
    const led = document.createElement("span");
    led.className = "cmp-perm-card__led";
    led.setAttribute("aria-hidden", "true");
    const txt = document.createElement("span");
    // UI-SPEC §Step 1 — VERBATIM
    txt.textContent = "DENIED — open Settings ↗";
    denied.append(led, txt);
    denied.addEventListener("click", () => props.onOpenSettings?.());
    denied.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        props.onOpenSettings?.();
      }
    });
    right.append(denied);
  }

  root.append(icon, text, right);
  return root;
}
