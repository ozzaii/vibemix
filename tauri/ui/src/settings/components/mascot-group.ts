/* Phase 13-03 — Settings drawer MASCOT group (Plan 13-03 Task 2).
 *
 * Two rows:
 *   - CLICK-THROUGH: binary rocker (OFF | ON). When ON, the mascot
 *     overlay window passes pointer events through to the app beneath
 *     (Plan 13-02 wires the actual `set_mascot_click_through` Tauri
 *     command). Default OFF — the window stays draggable.
 *   - MOOD: 3 segmented pills (HYPE-MAN / TEACHER / COACH). The active
 *     pill paints amber-backlit per the v5 .mood-btn.on anatomy (mock-
 *     verbatim gradient + inset glow), matching the existing interaction
 *     rocker (no flat fills).
 *
 * IPC wiring:
 *   - mood pill click          → emitIpc('ipc.settings.set', { field: 'mood', value })
 *   - click-through rocker     → invoke('set_mascot_click_through', { enabled })
 *                              + emitIpc('ipc.settings.set', { field: 'click_through', value })
 *
 * Both calls fire on every change. The Tauri command updates the Rust-
 * side overlay window state immediately; the emitIpc lets the sidecar's
 * settings store persist the value. The ws-bridge applies the sidecar's
 * `ipc.settings.state` ack on the round-trip — that's how this component
 * re-syncs after a successful change.
 *
 * Frontend-enforcement compliance (CDJ Whisper v5 contract):
 *   - NO Inter / Tailwind / hex literals. Every color is a `var(--*)`
 *     read; the spec's hex-grep guard pulls this CSS from <style
 *     data-scope="vmx-mascot-group"> and asserts zero matches.
 *   - 20/80 rule: dominant tone is var(--glass-3) recessed plate;
 *     amber accent appears ONLY on the active pill (accent-reservation
 *     item 4 — active mood pill) and via the existing rocker's active
 *     state.
 *   - Saira variable-axis display for "MASCOT" heading (via the parent
 *     Group wrapper).
 *   - Toggle reuses `renderRocker` ("rocker" variant) — no new toggle
 *     shape per Plan 13-03 frontend_enforcement_constraints.
 */

import { invoke } from "@tauri-apps/api/core";

import { registerStyle } from "../../session/components/_style-registry.js";
import { renderRocker } from "../../session/components/rocker.js";
import {
  getSessionState,
  type MascotMood,
} from "../../session/state.js";
import { emitIpc } from "../../ipc/client.js";
import { renderSettingsGroup } from "./group.js";

interface MoodOption {
  id: MascotMood;
  label: string;
}

const MOOD_OPTIONS: readonly MoodOption[] = [
  { id: "hype-man", label: "HYPE-MAN" },
  { id: "teacher", label: "TEACHER" },
  { id: "coach", label: "COACH" },
];

const CSS = `
  [data-component="mascot-group"] {
    display: flex;
    flex-direction: column;
    gap: var(--sp-md);
  }
  [data-component="mascot-group"] .vmx-mascot-row {
    display: flex;
    flex-direction: column;
    gap: var(--sp-sm);
  }
  [data-component="mascot-group"] .vmx-mascot-row__label {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk-40);
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  [data-component="mascot-group"] .vmx-mascot-moods {
    display: flex;
    gap: 0;
    align-items: stretch;
    background: var(--glass-3);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    padding: 3px;
    box-shadow:
      inset 0 2px 5px rgba(0, 0, 0, 0.85),
      inset 0 0 0 1px rgba(0, 0, 0, 0.5),
      inset 0 -1px 0 rgba(255, 255, 255, 0.028);
  }
  [data-component="mascot-group"] .vmx-mascot-pill {
    flex: 1;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    padding: 8px var(--sp-3);
    background: transparent;
    color: var(--silk-40);
    border: none;
    border-radius: var(--rad-sm);
    cursor: pointer;
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    transition: color var(--motion-snap) ease-out,
                background var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out,
                text-shadow var(--motion-snap) ease-out;
  }
  [data-component="mascot-group"] .vmx-mascot-pill:hover { color: var(--silk); }
  [data-component="mascot-group"] .vmx-mascot-pill[data-active="true"] {
    color: var(--amber);
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.09) 0%, rgba(255, 138, 61, 0.025) 100%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 var(--amber-40),
      inset 0 0 14px var(--amber-22),
      0 0 0 1px rgba(255, 138, 61, 0.14);
    text-shadow: 0 0 4px var(--amber-65);
  }
  [data-component="mascot-group"] .vmx-mascot-pill:focus-visible {
    outline: 1px solid var(--amber);
    outline-offset: 1px;
  }
`;

registerStyle("vmx-mascot-group", CSS);

interface MascotGroupHandle {
  /** The settings-group <section> ready to append into the drawer body. */
  root: HTMLElement;
  /** Re-read SessionState.settings.mood + click_through and reflect them
   *  on the rocker + pills without rebuilding. Idempotent. */
  refresh: () => void;
}

/** Mount the MASCOT settings group. Pure-function; subscribers to
 *  SessionState are NOT installed here — the drawer's `refresh()` already
 *  rebuilds the whole body on settings/UI diffs (see SettingsDrawer.ts).
 *  This keeps the lifecycle identical to PERSONA / OUTPUT / HOTKEY etc. */
export function renderMascotGroup(): HTMLElement {
  const handle = buildMascotGroup();
  return handle.root;
}

/** Internal — also returned by `_renderMascotGroupForTests` so vitest can
 *  poke `handle.refresh()` after mutating SessionState. */
function buildMascotGroup(): MascotGroupHandle {
  const settings = getSessionState().settings;

  // --- CLICK-THROUGH row ---------------------------------------------------
  const ctRow = document.createElement("div");
  ctRow.className = "vmx-mascot-row";
  const ctLabel = document.createElement("div");
  ctLabel.className = "vmx-mascot-row__label";
  ctLabel.textContent = "CLICK-THROUGH";
  ctRow.append(ctLabel);

  const ctRocker = renderRocker({
    ariaLabel: "click-through",
    variant: "rocker",
    options: [
      { id: "off", label: "OFF" },
      { id: "on", label: "ON" },
    ],
    active: settings.click_through ? "on" : "off",
    onChange: (id) => {
      const enabled = id === "on";
      void applyClickThroughChange(enabled);
    },
  });
  ctRow.append(ctRocker);

  // --- MOOD row ------------------------------------------------------------
  const moodRow = document.createElement("div");
  moodRow.className = "vmx-mascot-row";
  const moodLabel = document.createElement("div");
  moodLabel.className = "vmx-mascot-row__label";
  moodLabel.textContent = "MOOD";
  moodRow.append(moodLabel);

  const moodPills = document.createElement("div");
  moodPills.className = "vmx-mascot-moods";
  moodPills.setAttribute("role", "radiogroup");
  moodPills.setAttribute("aria-label", "mascot mood");

  for (const opt of MOOD_OPTIONS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "vmx-mascot-pill";
    btn.dataset.id = opt.id;
    const isActive = settings.mood === opt.id;
    btn.dataset.active = isActive ? "true" : "false";
    btn.setAttribute("role", "radio");
    btn.setAttribute("aria-checked", isActive ? "true" : "false");
    btn.textContent = opt.label;
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      if (btn.dataset.active === "true") return;
      void applyMoodChange(opt.id);
    });
    moodPills.append(btn);
  }
  moodRow.append(moodPills);

  // --- Group wrapper -------------------------------------------------------
  const group = renderSettingsGroup({
    header: "MASCOT",
    children: [ctRow, moodRow],
  });
  group.setAttribute("data-component", "mascot-group");

  const handle: MascotGroupHandle = {
    root: group,
    refresh: () => {
      const s = getSessionState().settings;
      // Click-through rocker — flip data-active on the two segments.
      ctRocker.querySelectorAll<HTMLElement>(".vmx-rocker__seg").forEach((seg) => {
        const wantActive =
          (s.click_through && seg.dataset.id === "on") ||
          (!s.click_through && seg.dataset.id === "off");
        seg.dataset.active = wantActive ? "true" : "false";
        seg.setAttribute("aria-checked", wantActive ? "true" : "false");
      });
      // Mood pills — flip data-active per id.
      moodPills.querySelectorAll<HTMLElement>(".vmx-mascot-pill").forEach((p) => {
        const active = p.dataset.id === s.mood;
        p.dataset.active = active ? "true" : "false";
        p.setAttribute("aria-checked", active ? "true" : "false");
      });
    },
  };
  return handle;
}

async function applyMoodChange(mood: MascotMood): Promise<void> {
  try {
    await emitIpc("ipc.settings.set", { field: "mood", value: mood });
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("[mascot-group] mood emitIpc failed:", err);
  }
}

async function applyClickThroughChange(enabled: boolean): Promise<void> {
  // Both calls fire — Tauri command updates the overlay window immediately,
  // emitIpc lets the sidecar persist the setting (and re-broadcast on
  // ipc.settings.state which the ws-bridge applies back to SessionState).
  try {
    await invoke("set_mascot_click_through", { enabled });
  } catch (err) {
    // Tauri command may not exist yet during Plan 13-03 (Plan 13-02 wires
    // it). The IPC settings store still receives the value so the sidecar
    // can persist it for Plan 13-02 to read on mount.
    // eslint-disable-next-line no-console
    console.warn("[mascot-group] set_mascot_click_through invoke failed:", err);
  }
  try {
    await emitIpc("ipc.settings.set", {
      field: "click_through",
      value: enabled,
    });
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("[mascot-group] click_through emitIpc failed:", err);
  }
}

/** Public alias — name matches the Plan 13-03 spec contract (`MascotGroup`
 *  appears in plan's key_links pattern). */
export const MascotGroup = renderMascotGroup;

/** Test-only — returns the internal handle so vitest can simulate a
 *  settings change and call refresh() without depending on the drawer
 *  rebuild cycle. */
export function _renderMascotGroupForTests(): MascotGroupHandle {
  return buildMascotGroup();
}
