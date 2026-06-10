/* Phase 14-04 — Settings drawer PERFORMANCE group.
 *
 * Single row:
 *   - LIGHTER BLUR: recessed OFF|ON rocker (the drawer's one boolean
 *     vocabulary — same shape as the mascot ENABLE/CLICK-THROUGH rows).
 *     When ON, writes `html[data-blur-perf="on"]` which the perf-fallback
 *     CSS block in tokens.css (shipped Wave 2) reads to swap the heavy v5
 *     backdrop blurs (`--blur-glass*`) for lighter variants. Persists via
 *     the existing ipc.settings.set envelope (field "lighter_blur") through
 *     SettingsApplier → ConfigStore so the boot-time read in main.ts
 *     restores the user's preference on next launch.
 *
 * Local-first apply: the rocker handler flips the document attribute
 * IMMEDIATELY (zero round-trip) so the user sees the blur change before
 * the sidecar acks. Persistence runs in the background; if it fails the
 * attribute stays applied (the next ipc.settings.state ack will rewrite
 * SessionState authoritatively).
 */

import { registerStyle } from "../../session/components/_style-registry.js";
import { renderRocker } from "../../session/components/rocker.js";
import { sendSettings } from "../../session/ws-bridge.js";
import { renderSettingsGroup } from "./group.js";

const CSS = `
  [data-component="performance-group"] {
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
    font-family: var(--type-body);
  }
  [data-component="performance-group"] .vmx-perf-row {
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
  }
  [data-component="performance-group"] .vmx-perf-row__label {
    font-family: var(--type-mono);
    font-weight: 600;
    font-size: 9.5px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--text-muted);
    line-height: 1;
    text-shadow: var(--text-emboss);
  }
`;

registerStyle("vmx-performance-group", CSS);

/** Apply the lighter-blur preference to the document immediately by
 *  writing/clearing the `data-blur-perf` attribute on <html>. The
 *  tokens.css cascade (Wave 2) reads this and swaps the heavy blurs for
 *  lighter variants. Idempotent — calling twice with the same value is
 *  a no-op visually.
 *
 *  Mirrors `applyBlurPerfPreference` in main.ts; defined here too so the
 *  Performance toggle can apply locally without a round-trip back through
 *  boot wiring. */
export function applyBlurPerfPreference(enabled: boolean): void {
  if (enabled) {
    document.documentElement.setAttribute("data-blur-perf", "on");
  } else {
    document.documentElement.removeAttribute("data-blur-perf");
  }
}

/** Toggle handler — applies locally for instant feedback, then persists
 *  via the existing settings.set IPC. If the sidecar isn't reachable
 *  (Vite dev, sidecar down) we keep the local apply — the user still
 *  gets the lighter blur for this session; next launch reads the field
 *  defensively defaulting to off. */
export async function toggleBlurPerf(enabled: boolean): Promise<void> {
  applyBlurPerfPreference(enabled);
  try {
    await sendSettings("lighter_blur", enabled);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("[performance-group] persist failed:", err);
  }
}

/** Render the PERFORMANCE settings group. Pure-function — the caller
 *  (SettingsDrawer.renderDrawerBody) rebuilds on every refresh, so a
 *  fresh `currentValue` propagates through the next paint. The rocker
 *  repaints optimistically (renderRocker flips data-active locally before
 *  the ipc round-trip — the drawer convention). */
export function PerformanceGroup(currentValue: boolean): HTMLElement {
  const row = document.createElement("div");
  row.className = "vmx-perf-row";

  const label = document.createElement("div");
  label.className = "vmx-perf-row__label";
  label.textContent = "LIGHTER BLUR";
  row.append(label);

  row.append(
    renderRocker({
      ariaLabel: "lighter blur",
      options: [
        { id: "off", label: "OFF" },
        { id: "on", label: "ON" },
      ],
      active: currentValue ? "on" : "off",
      variant: "rocker",
      onChange: (id) => {
        void toggleBlurPerf(id === "on");
      },
    }),
  );

  const group = renderSettingsGroup({
    header: "PERFORMANCE",
    children: row,
  });
  group.setAttribute("data-component", "performance-group");
  return group;
}
