// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 05 — ControllerStage component (RENDER-01, RENDER-02).
//
// Hosts the inline-SVG schematic of the currently-detected controller.
// The middle 1fr region of the Learn-window grid. Single child: the
// SVG (or the generic fallback, or the empty-state slot).
//
// Mount lifecycle:
//   - On `ipc.learn.controller_detected { connected: true }`: dynamic
//     `import("../controllers/<id>.svg")` per RESEARCH §Pitfall 5
//     (Vite code-splits dynamic imports → only the matched controller
//     SVG fetches). Defends against id injection by mapping through a
//     hard-coded allowlist (T-91-05-02 mitigation).
//   - On `connected: false`: clears the stage (empty-state takes over).
//   - On `ipc.learn.midi_position`: walks `positions` and applies a
//     `transform`/`data-active` update per `<g data-control-id>` —
//     transform-only path means the compositor handles paint (RESEARCH
//     §Pitfall 2: 60fps guaranteed on 11 SVGs of this scale).
//
// Anti-flood guard (RESEARCH §Pitfall 6): the learn-window root
// coalesces multiple midi_position frames per repaint slot into the
// latest one. This component's `applyPositionFrame` is called from a
// requestAnimationFrame drainer, not directly from ws onmessage.

const KNOWN_CONTROLLERS = new Set<string>([
  "pioneer_ddj_flx4",
  "pioneer_ddj_flx6",
  "pioneer_ddj_flx10",
  "pioneer_ddj_400",
  "pioneer_ddj_1000",
  "pioneer_ddj_sx3",
  "pioneer_xdj_rx3",
  "numark_party_mix_live",
  "hercules_inpulse_300",
  "hercules_inpulse_500",
]);

interface ControllerSvgModule {
  [exportName: string]: string;
}

/**
 * Resolve a controller_id to its inline-SVG body string. Unknown ids
 * (or the explicit "_generic" / empty) fall back to the labeled-zone
 * generic schematic. Imports are dynamic so Vite code-splits the SVG
 * chunks (only the matched controller payload fetches).
 *
 * The allowlist is the single defence against import-string injection
 * (T-91-05-02): an envelope can claim any `controller_id` string but
 * only the 10 known ids reach the dynamic-import path.
 */
async function loadControllerSvg(controllerId: string): Promise<string> {
  if (!KNOWN_CONTROLLERS.has(controllerId)) {
    // Fall back to generic. Loaded eagerly (the import below resolves
    // synchronously after the first dynamic-import settle).
    const generic = (await import(
      "../controllers/_generic.svg.js"
    )) as ControllerSvgModule;
    return generic.GENERIC_CONTROLLER_SVG ?? "";
  }
  // Hand-roll the static-string switch — Vite needs literal module paths
  // (per RESEARCH §Pitfall 5) so each case resolves at build-time. Adding
  // a controller here = adding its branch in lockstep with the SVG file.
  switch (controllerId) {
    case "pioneer_ddj_flx4": {
      const m = (await import(
        "../controllers/pioneer_ddj_flx4.svg.js"
      )) as ControllerSvgModule;
      return m.PIONEER_DDJ_FLX4_SVG ?? "";
    }
    case "pioneer_ddj_flx6": {
      const m = (await import(
        "../controllers/pioneer_ddj_flx6.svg.js"
      )) as ControllerSvgModule;
      return m.PIONEER_DDJ_FLX6_SVG ?? "";
    }
    case "pioneer_ddj_400": {
      const m = (await import(
        "../controllers/pioneer_ddj_400.svg.js"
      )) as ControllerSvgModule;
      return m.PIONEER_DDJ_400_SVG ?? "";
    }
    case "hercules_inpulse_300": {
      const m = (await import(
        "../controllers/hercules_inpulse_300.svg.js"
      )) as ControllerSvgModule;
      return m.HERCULES_INPULSE_300_SVG ?? "";
    }
    // Plan 06 lands the remaining 6 — until then they fall through to
    // the generic branch (so a user plugging an FLX10 still sees the
    // labeled-zone fallback, not a blank stage).
    default: {
      const generic = (await import(
        "../controllers/_generic.svg.js"
      )) as ControllerSvgModule;
      return generic.GENERIC_CONTROLLER_SVG ?? "";
    }
  }
}

/**
 * Apply a midi_position frame to the live SVG. Walks `positions`,
 * finds the matching `<g data-control-id>` group, and mutates a
 * `transform`/`data-active` attribute — never repaints the SVG.
 *
 * - Knobs (presence of `data-cx`/`data-cy`): `transform="rotate(deg cx cy)"`
 *   where deg = (value/127)*270 - 135 (RESEARCH §Code Example 3).
 *   Maps the 7-bit MIDI range to the ±135° physical knob travel.
 * - Buttons (no `data-cx`): `data-active="0|1"` — CSS handles fill swap.
 *
 * The wire shape carries `jog_touched:A/B` (after ControllerState
 * normalisation in `state.py`) but the FLX4 SVG `data-control-id` is
 * `jog_touch:A/B` (matches the profile binding's `kind`). The lookup
 * tries the literal key first, then falls back to a `jog_touch`
 * substitution for the jog-touch family.
 */
export function applyPositionFrame(
  stage: HTMLElement,
  positions: Record<string, number>,
): void {
  for (const [rawKey, valueRaw] of Object.entries(positions)) {
    if (typeof valueRaw !== "number") continue;
    const value = valueRaw;
    // Resolve key: try literal, then strip `_touched` -> `_touch` for jog.
    let group = stage.querySelector(
      `[data-control-id="${rawKey}"]`,
    ) as SVGGElement | null;
    if (!group && rawKey.startsWith("jog_touched:")) {
      const alt = rawKey.replace("jog_touched:", "jog_touch:");
      group = stage.querySelector(
        `[data-control-id="${alt}"]`,
      ) as SVGGElement | null;
    }
    if (!group) continue;

    const cx = group.dataset.cx;
    const cy = group.dataset.cy;
    if (cx !== undefined && cy !== undefined) {
      // Knob / fader-thumb-with-pivot — rotate.
      const degrees = (value / 127) * 270 - 135;
      group.setAttribute(
        "transform",
        `rotate(${degrees} ${Number(cx)} ${Number(cy)})`,
      );
    } else {
      // Button — data-active 0/1 (CSS picks up the swap).
      group.setAttribute("data-active", value > 0 ? "1" : "0");
    }
  }
}

/**
 * The ControllerStage instance — wraps the host element + the
 * currently-mounted controller id (used to skip no-op remounts on
 * spammed `controller_detected` frames; T-91-05-03 mitigation).
 */
export class ControllerStage {
  private el: HTMLElement;
  private mountedControllerId: string | null = null;

  constructor(el: HTMLElement) {
    this.el = el;
  }

  /**
   * Mount the SVG for the given controller_id. Idempotent — calling
   * twice in a row with the same id is a no-op (T-91-05-03 — spammed
   * controller_detected envelopes don't remount).
   */
  async render(controllerId: string): Promise<void> {
    if (this.mountedControllerId === controllerId) return;
    const svg = await loadControllerSvg(controllerId);
    this.el.innerHTML = svg;
    this.mountedControllerId = controllerId;
  }

  /** Clear the stage — used when the controller disconnects. */
  clear(): void {
    this.el.innerHTML = "";
    this.mountedControllerId = null;
  }

  /** Apply a midi_position frame to the mounted SVG. */
  applyPositionFrame(positions: Record<string, number>): void {
    applyPositionFrame(this.el, positions);
  }

  /** Public read-only accessor for the currently-mounted controller id. */
  get currentControllerId(): string | null {
    return this.mountedControllerId;
  }
}
