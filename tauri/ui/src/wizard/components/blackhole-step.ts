/* blackhole-step.ts — Phase 33 / INSTALL-03.
 *
 * Thin step renderer for the one-click install wizard's BlackHole gate.
 * Wraps the existing `BlackHoleBanner` (Phase 11) with probe-state
 * driven rendering:
 *
 *   - probe.installed === false → render BlackHoleBanner (install affordance)
 *   - probe.installed === true  → render nothing (banner hidden)
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

/**
 * Render the BlackHole step body for the given probe result.
 *
 * Returns a container with EITHER the install banner (when absent) OR
 * an empty container (when present). The caller picks whether to also
 * show a follow-on success indicator.
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
  }

  return root;
}

/** Public URL — kept in sync with the Tauri shell-open allowlist + the
 *  sidecar's BLACKHOLE_INSTALL_URL constant. */
export const BLACKHOLE_INSTALL_URL = "https://existential.audio/blackhole/";
