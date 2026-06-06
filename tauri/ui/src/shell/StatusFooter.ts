// SPDX-License-Identifier: Apache-2.0
//
// The quiet floating session status (bottom-right, 10px). It is the honest
// indicator that distinguishes "idle, no music yet" from "broken" (cardinal
// invariant #5): the connection dot is steady-lit when connected, pulses while
// reconnecting, dims when disconnected, and the label states the activation.
//
// Activation is read-only here. The live session bridge owns activation and
// connection; the footer must never simulate a live state.

import type {
  ActivationState,
  ConnectionState,
  ShellStore,
  SurfaceId,
} from "./shell-store.js";

// Terse instrument-readout states. Kept distinct from the deck hero copy
// ("listening for the mix…") so the footer reads as a status line, not an echo.
const ACTIVATION_LABEL: Record<ActivationState, string> = {
  idle: "idle",
  listening: "listening",
  live: "live",
};

const CONNECTION_LABEL: Record<ConnectionState, string> = {
  connected: "",
  reconnecting: "co-host reconnecting",
  disconnected: "co-host offline",
};

const LOCAL_SURFACE_LABEL: Partial<Record<SurfaceId, string>> = {
  learn: "learn local",
  viber: "viber local",
};

function footerLabel(
  activation: ActivationState,
  connection: ConnectionState,
  surface: SurfaceId,
): string {
  const localLabel = LOCAL_SURFACE_LABEL[surface];
  if (localLabel) return localLabel;
  return CONNECTION_LABEL[connection] || ACTIVATION_LABEL[activation];
}

function footerTitle(connection: ConnectionState, surface: SurfaceId): string | null {
  if (surface === "learn") {
    return connection === "connected"
      ? "Learn runs locally; use the Learn status bar for tutor voice and practice input."
      : "Sven is offline; Learn still accepts on-screen practice and subtitles.";
  }
  if (surface === "viber") {
    return "Viber runs local library and set-prep work; Sven status only matters on Deck.";
  }
  if (connection === "connected") return null;
  if (connection === "reconnecting") {
    return "The co-host is reconnecting to the audio engine.";
  }
  return "The co-host cannot speak until the connection comes back.";
}

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
    const model = store.getState();
    const nextLabel = footerLabel(
      model.activation,
      model.connection,
      model.activeSurface,
    );
    const nextTitle = footerTitle(model.connection, model.activeSurface);
    label.textContent = nextLabel;
    footer.dataset.conn = model.connection;
    footer.dataset.surface = model.activeSurface;
    footer.setAttribute("aria-label", `Session status: ${nextLabel}`);
    if (nextTitle === null) {
      footer.removeAttribute("title");
    } else {
      footer.setAttribute("title", nextTitle);
    }
  };
  store.subscribe(render);
  render();

  return footer;
}
