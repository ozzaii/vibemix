/* permissions-card.ts — Step 1 horizontal card (UI-SPEC §6 / CDJ Whisper v5).
 *
 * Glass shell from `.vmx-tile` (tokens.css). This component owns the
 * 56px row layout + icon-tinting + label/sub typography + the state
 * readout. Critique 2026-05-14: dropped the duplicate shadow stack.
 *
 * Left: OS-tinted icon (shield = screen recording, mic = microphone).
 * Center: silkscreen label (Saira wdth 85 wght 600 9px UPPERCASE) +
 *   sub-line (Saira body 11px --silk-65).
 * Right: state indicator
 *   - pending: [ Grant ] secondary button
 *   - granted: ● GRANTED — silkscreen label in --led-ok with green dome
 *   - denied:  ● DENIED — open Settings ↗ in --led-fault
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
    gap: var(--sp-4);
    height: 56px;
    padding: 0 var(--sp-4);
  }
  .cmp-perm-card__icon {
    color: var(--silk-65);
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
  }
  .cmp-perm-card[data-state="granted"] .cmp-perm-card__icon { color: var(--led-ok); }
  .cmp-perm-card[data-state="denied"]  .cmp-perm-card__icon { color: var(--led-fault); }
  .cmp-perm-card__text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  .cmp-perm-card__label {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 9px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    line-height: 1;
  }
  .cmp-perm-card__sub {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 11px;
    color: var(--silk-65);
    line-height: 1.35;
  }
  .cmp-perm-card__right {
    display: flex;
    align-items: center;
    gap: var(--sp-2);
  }
  .cmp-perm-card__state-readout {
    display: inline-flex;
    align-items: center;
    gap: var(--sp-1);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 9px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    cursor: default;
  }
  .cmp-perm-card__state-readout[data-tone="ok"]  { color: var(--led-ok); }
  .cmp-perm-card__state-readout[data-tone="rec"] { color: var(--led-fault); cursor: pointer; }
  .cmp-perm-card__led {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
  }
  .cmp-perm-card__state-readout[data-tone="ok"]  .cmp-perm-card__led { background: var(--led-ok);    box-shadow: 0 0 6px var(--led-ok); }
  .cmp-perm-card__state-readout[data-tone="rec"] .cmp-perm-card__led { background: var(--led-fault); box-shadow: 0 0 6px var(--led-fault); }
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
  root.className = "cmp-perm-card vmx-tile";
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
    txt.textContent = "DENIED · open Settings ↗";
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
