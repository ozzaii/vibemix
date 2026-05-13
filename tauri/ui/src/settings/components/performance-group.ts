/* Phase 14-04 — Settings drawer PERFORMANCE group.
 *
 * Single row:
 *   - LIGHTER BLUR: binary toggle pill. When ON, writes
 *     `html[data-blur-perf="on"]` which the perf-fallback CSS block in
 *     tokens.css (shipped Wave 2) reads to swap the heavy v5 backdrop
 *     blurs (`--blur-glass*`) for lighter variants. Persists via the
 *     existing ipc.settings.set envelope (field "lighter_blur") through
 *     SettingsApplier → ConfigStore so the boot-time read in main.ts
 *     restores the user's preference on next launch.
 *
 * Local-first apply: the toggle handler flips the document attribute
 * IMMEDIATELY (zero round-trip) so the user sees the blur change before
 * the sidecar acks. Persistence runs in the background; if it fails the
 * attribute stays applied (the next ipc.settings.state ack will rewrite
 * SessionState authoritatively).
 *
 * v5 visual anatomy (lifts from SettingsDrawer.ts:198–222 button block):
 *   - Off state: var(--glass-3) recessed bg, var(--glass-edge) hairline,
 *     label var(--silk-65) silkscreen.
 *   - On state: linear-gradient(180deg, rgba(255,138,61,0.09),
 *     rgba(255,138,61,0.025)) amber backlight (mock-verbatim),
 *     1px var(--amber-40) border, inset 0 0 14px var(--amber-22) bloom,
 *     label var(--amber) with text-shadow 0 0 4px var(--amber-65).
 *
 * Accent-reservation compliance (UI-SPEC item 5 — active button state):
 *   chrome stays glass + silk recessive; amber paints only when ON.
 */

import { registerStyle } from "../../session/components/_style-registry.js";
import { sendSettings } from "../../session/ws-bridge.js";
import { renderSettingsGroup } from "./group.js";

const CSS = `
  [data-component="performance-group"] {
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
  }
  [data-component="performance-group"] .vmx-perf-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-4);
  }
  [data-component="performance-group"] .vmx-perf-row__label {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk-40);
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  [data-component="performance-group"] .vmx-perf-toggle {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    padding: 8px var(--sp-4);
    background: var(--glass-3);
    border: 1px solid var(--glass-edge);
    color: var(--silk-65);
    border-radius: var(--rad-sm);
    cursor: pointer;
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.035),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45);
    transition: color var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out,
                background var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out,
                text-shadow var(--motion-snap) ease-out;
  }
  [data-component="performance-group"] .vmx-perf-toggle:hover {
    color: var(--silk);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45),
      0 0 10px var(--amber-22);
  }
  [data-component="performance-group"] .vmx-perf-toggle[data-on="true"] {
    color: var(--amber);
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.09) 0%, rgba(255, 138, 61, 0.025) 100%);
    border-color: var(--amber-40);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 var(--amber-40),
      inset 0 0 14px var(--amber-22),
      0 0 0 1px rgba(255, 138, 61, 0.14);
    text-shadow: 0 0 4px var(--amber-65);
  }
  [data-component="performance-group"] .vmx-perf-toggle:focus-visible {
    outline: 1px solid var(--amber);
    outline-offset: 1px;
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
 *  fresh `currentValue` propagates through the next paint. */
export function PerformanceGroup(currentValue: boolean): HTMLElement {
  const row = document.createElement("div");
  row.className = "vmx-perf-row";

  const label = document.createElement("div");
  label.className = "vmx-perf-row__label";
  label.textContent = "LIGHTER BLUR";
  row.append(label);

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "vmx-perf-toggle";
  toggle.dataset.on = currentValue ? "true" : "false";
  toggle.setAttribute("role", "switch");
  toggle.setAttribute("aria-checked", currentValue ? "true" : "false");
  toggle.setAttribute("aria-label", "lighter blur");
  toggle.textContent = currentValue ? "ON" : "OFF";
  toggle.addEventListener("click", (e) => {
    e.preventDefault();
    const next = toggle.dataset.on !== "true";
    toggle.dataset.on = next ? "true" : "false";
    toggle.setAttribute("aria-checked", next ? "true" : "false");
    toggle.textContent = next ? "ON" : "OFF";
    void toggleBlurPerf(next);
  });
  row.append(toggle);

  const group = renderSettingsGroup({
    header: "PERFORMANCE",
    children: row,
  });
  group.setAttribute("data-component", "performance-group");
  return group;
}
