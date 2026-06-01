// SPDX-License-Identifier: Apache-2.0
//
// The quiet floating session status (bottom-right, 10px). It is the honest
// indicator that distinguishes "idle, no music yet" from "broken" (cardinal
// invariant #5): the connection dot is steady-lit when connected, pulses while
// reconnecting, dims when disconnected, and the label states the activation.
//
// Activation is read-only here. The live session bridge owns activation and
// connection; the footer must never simulate a live state.

import type { ActivationState, ShellStore } from "./shell-store.js";

// Terse instrument-readout states. Kept distinct from the deck hero copy
// ("listening for the mix…") so the footer reads as a status line, not an echo.
const ACTIVATION_LABEL: Record<ActivationState, string> = {
  idle: "idle",
  listening: "listening",
  live: "live",
};

export function createStatusFooter(store: ShellStore): HTMLElement {
  const footer = document.createElement("div");
  footer.className = "shell-footer";
  footer.setAttribute("data-wire", "shell.status");
  footer.setAttribute("role", "group");
  footer.setAttribute("aria-label", "Session status");

  const dot = document.createElement("span");
  dot.className = "conn-dot";
  dot.setAttribute("aria-hidden", "true");

  const label = document.createElement("span");
  label.className = "status-label";
  // role="status" (implicit aria-live=polite) announces idle -> listening ->
  // live transitions to assistive tech.
  label.setAttribute("role", "status");

  footer.append(dot, label);

  const render = (): void => {
    label.textContent = ACTIVATION_LABEL[store.getState().activation];
  };
  store.subscribe(render);
  render();

  return footer;
}
