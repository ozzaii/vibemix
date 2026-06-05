/* blackhole-step.ts — Phase 33 / INSTALL-03.
 *
 * Thin step renderer for the one-click install wizard's BlackHole gate.
 * Wraps the existing `BlackHoleBanner` (Phase 11) with probe-state
 * driven rendering:
 *
 *   - probe.installed === false → render BlackHoleBanner (install affordance)
 *   - probe.installed === true  → render route status (master-only or deck-capable)
 *
 * The wizard step calls into the sidecar via `install.blackhole_probe`
 * IPC (Plan 33-03 backend). The "Install BlackHole 2ch" button shells
 * to `https://existential.audio/blackhole/` — already on the Tauri
 * shell-open allowlist (capabilities/default.json).
 *
 * Skip-able with a warning toast: the wizard advances even when the
 * probe is absent, so a user who declines to install BlackHole still
 * lands in the main session UI. The session loop is the place that
 * surfaces the "no master output" state — not the wizard.
 */

import { BlackHoleBanner } from "./blackhole-banner.js";
import { registerStyle } from "./_style-registry.js";

export interface BlackHoleProbeResult {
  installed: boolean;
  device_name: string | null;
}

export interface BlackHoleStepCallbacks {
  onOpenInstall: () => void;
  onRecheck: () => void;
  /** Optional — true after the user clicked "Open install page ↗", so
   *  the recheck affordance gets the post-click caption. */
  postClickState?: boolean;
}

const CSS = `
  .cmp-bh-route {
    display: grid;
    gap: var(--sp-2);
    padding: var(--sp-4) var(--sp-5);
    margin-bottom: var(--sp-4);
  }
  .cmp-bh-route__label {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk);
  }
  .cmp-bh-route__body {
    max-width: 68ch;
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 14px;
    line-height: 1.5;
    color: var(--silk-65);
  }
  .cmp-bh-route__body strong {
    color: var(--silk);
    font-weight: 600;
  }
`;

registerStyle("cmp-bh-route", CSS);

/**
 * Render the BlackHole step body for the given probe result.
 *
 * Returns a container with EITHER the install banner (when absent) OR
 * the current route capability (when present).
 */
export function renderBlackHoleStep(
  probe: BlackHoleProbeResult,
  cb: BlackHoleStepCallbacks,
): HTMLElement {
  const root = document.createElement("div");
  root.className = "wizard-blackhole-step";
  root.dataset.installed = probe.installed ? "true" : "false";

  if (!probe.installed) {
    root.append(
      BlackHoleBanner({
        onOpenInstall: cb.onOpenInstall,
        onRecheck: cb.onRecheck,
        postClickState: cb.postClickState,
      }),
    );
  } else {
    root.append(renderRouteStatus(probe.device_name));
  }

  return root;
}

function renderRouteStatus(deviceName: string | null): HTMLElement {
  const root = document.createElement("div");
  root.className = "cmp-bh-route vmx-tile";
  root.dataset.tile = "hero";
  const normalized = (deviceName ?? "").toLowerCase();
  const deckCapable =
    normalized.includes("16ch") ||
    normalized.includes("64ch") ||
    normalized.includes("aggregate") ||
    normalized.includes("multi-output");
  root.dataset.deckCapable = deckCapable ? "true" : "false";

  const label = document.createElement("div");
  label.className = "cmp-bh-route__label";
  label.textContent = deckCapable ? "DECK ROUTE READY" : "MASTER ROUTE READY";

  const body = document.createElement("div");
  body.className = "cmp-bh-route__body";
  if (deckCapable) {
    body.innerHTML =
      "<strong>BlackHole 16ch or aggregate routing is present.</strong> Keep your DJ app on a Multi-Output/Aggregate device with the FLX4, and route deck 1 to channels 1/2 and deck 2 to 3/4 so Sven can tell your decks apart.";
  } else {
    body.innerHTML =
      "<strong>BlackHole 2ch lets vibemix hear the master output.</strong> To let Sven tell decks apart, use a Multi-Output/Aggregate device that includes the FLX4 plus BlackHole 16ch.";
  }
  root.append(label, body);
  return root;
}

/** Public URL — kept in sync with the Tauri shell-open allowlist + the
 *  sidecar's BLACKHOLE_INSTALL_URL constant. */
export const BLACKHOLE_INSTALL_URL = "https://existential.audio/blackhole/";
