// SPDX-License-Identifier: Apache-2.0
//
// The quiet floating session status (bottom-right, 10px). It is the honest
// indicator that distinguishes "idle, no music yet" from "broken" (cardinal
// invariant #5): the connection dot is steady-lit when connected, pulses while
// reconnecting, dims when disconnected, and the label states the activation.
//
// Until the audio pipeline is wired (a later phase), clicking the footer cycles
// activation idle -> listening -> live so the self-arranging layout is
// demonstrable without a backend. That click handler is the only thing here
// that goes away once real audio drives activation.

import type { ActivationState, ShellStore } from "./shell-store.js";

// Terse instrument-readout states. Kept distinct from the deck hero copy
// ("listening for the mix…") so the footer reads as a status line, not an echo.
const ACTIVATION_LABEL: Record<ActivationState, string> = {
  idle: "idle",
  listening: "listening",
  live: "live",
};

const NEXT_ACTIVATION: Record<ActivationState, ActivationState> = {
  idle: "listening",
  listening: "live",
  live: "idle",
};

export function createStatusFooter(store: ShellStore): HTMLElement {
  const footer = document.createElement("button");
  footer.type = "button";
  footer.className = "shell-footer";
  footer.setAttribute("data-wire", "shell.status");
  // User-facing name: the visible dot + label already convey the live state,
  // and the click-to-cycle is demo scaffolding that retires once audio drives
  // activation, so the accessible name names the control, not the mechanism.
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

  // Demo-only: drive the activation state machine without audio.
  footer.addEventListener("click", () => {
    const current = store.getState().activation;
    const next = NEXT_ACTIVATION[current];
    store.setActivation(next);
    // Mirror a plausible connection state so the dot reads honestly.
    store.setConnection(next === "idle" ? "disconnected" : "connected");
  });

  const render = (): void => {
    label.textContent = ACTIVATION_LABEL[store.getState().activation];
  };
  store.subscribe(render);
  render();

  return footer;
}
