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
  "hercules_inpulse_300_mk2",
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
    case "hercules_inpulse_300_mk2": {
      // Phase 97 / ONBOARD-03 — the MK2 reuses the legacy 300 SVG asset.
      // The two units are visually near-identical per Hercules product
      // photos (the MK2 refresh is internal — improved jog-touch
      // capacitance + firmware, not a new faceplate). §LEARN-MK2-DETECTION
      // ear-pass on real MK2 hardware (P98) will validate whether a
      // distinct SVG is needed; if yes, swap the import target here.
      const m = (await import(
        "../controllers/hercules_inpulse_300.svg.js"
      )) as ControllerSvgModule;
      return m.HERCULES_INPULSE_300_SVG ?? "";
    }
    case "hercules_inpulse_500": {
      const m = (await import(
        "../controllers/hercules_inpulse_500.svg.js"
      )) as ControllerSvgModule;
      return m.HERCULES_INPULSE_500_SVG ?? "";
    }
    case "numark_party_mix_live": {
      const m = (await import(
        "../controllers/numark_party_mix_live.svg.js"
      )) as ControllerSvgModule;
      return m.NUMARK_PARTY_MIX_LIVE_SVG ?? "";
    }
    case "pioneer_ddj_flx10": {
      const m = (await import(
        "../controllers/pioneer_ddj_flx10.svg.js"
      )) as ControllerSvgModule;
      return m.PIONEER_DDJ_FLX10_SVG ?? "";
    }
    case "pioneer_ddj_1000": {
      const m = (await import(
        "../controllers/pioneer_ddj_1000.svg.js"
      )) as ControllerSvgModule;
      return m.PIONEER_DDJ_1000_SVG ?? "";
    }
    case "pioneer_ddj_sx3": {
      const m = (await import(
        "../controllers/pioneer_ddj_sx3.svg.js"
      )) as ControllerSvgModule;
      return m.PIONEER_DDJ_SX3_SVG ?? "";
    }
    case "pioneer_xdj_rx3": {
      const m = (await import(
        "../controllers/pioneer_xdj_rx3.svg.js"
      )) as ControllerSvgModule;
      return m.PIONEER_XDJ_RX3_SVG ?? "";
    }
    // All 10 specific controllers landed (Plan 06 closed). Unknown ids
    // still fall through to the generic labeled-zone fallback below.
    default: {
      const generic = (await import(
        "../controllers/_generic.svg.js"
      )) as ControllerSvgModule;
      return generic.GENERIC_CONTROLLER_SVG ?? "";
    }
  }
}

/**
 * Classify a `data-control-id` into knob / fader / button.
 *
 * The classification drives the render dispatch in :func:`applyPositionFrame`
 * — knobs ROTATE around their `data-cx`/`data-cy` pivot, faders TRANSLATE
 * their thumb along the rail inferred from the SVG geometry, and buttons
 * flip a `data-active` flag for the stylesheet to swap fill.
 *
 * The dispatch lives in the renderer (rather than as a `data-control-type`
 * attribute on every SVG group) because the SVG-author surface is large
 * (~66 fader groups across 10 controllers) and the control-id naming
 * convention is already a stable contract pinned by the profile JSON
 * parity gate (`test_svg_profile_parity.spec.ts`). The full set of
 * known control-id prefixes is enumerated below; any new SKU that adds
 * a control-id outside this set falls through to "knob" (the safe
 * default — a missing `data-cx`/`data-cy` falls through to the button
 * path further down).
 *
 * Phase 91 REVIEW CR-02 fix — before this, every group with
 * `data-cx`/`data-cy` was rotated, so faders (which all carry `data-cx`/
 * `data-cy` for the original rotation-pivot design) visibly rotated
 * instead of translating; buttons (which also all carry `data-cx`/`data-cy`)
 * rotated by a few degrees on press (value 0 → -135°, value 1 → -132.87°,
 * a ~2° rotation per click). Both regressions failed the Kaan ear-pass
 * bar before the milestone could ship.
 */
function classifyControl(controlId: string): "knob" | "fader" | "button" {
  // Faders: linear position controls (vertical channel faders, the
  // crossfader, and the per-deck tempo / pitch fader).
  if (
    controlId.startsWith("vol:") ||
    controlId.startsWith("tempo:") ||
    controlId === "xfader"
  ) {
    return "fader";
  }
  // Buttons: discrete on/off (transports, loop in/out, hot cues, jog touch,
  // tap-tempo). `jog_touched` is the wire-shape spelling produced by
  // ControllerState normalisation; `jog_touch` is what the SVG groups use
  // — the lookup in applyPositionFrame already normalises the key before
  // calling this classifier (so we only need the SVG-side spelling here).
  if (
    controlId.startsWith("play:") ||
    controlId.startsWith("cue:") ||
    controlId.startsWith("sync:") ||
    controlId.startsWith("loop_in:") ||
    controlId.startsWith("loop_out:") ||
    controlId.startsWith("hotcue:") ||
    controlId.startsWith("jog_touch:") ||
    controlId === "tap_tempo"
  ) {
    return "button";
  }
  // Default: knob (eq_hi/mid/low:*, filter:*, filter_fx — all rotary).
  return "knob";
}

function svgNumber(el: SVGElement, attr: string): number | null {
  const raw = el.getAttribute(attr);
  if (raw === null) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function clampMidiValue(value: number): number {
  return Math.min(127, Math.max(0, value));
}

function formatDelta(value: number): string {
  return String(Number(value.toFixed(2)));
}

function translateFaderThumb(
  group: SVGGElement,
  controlId: string,
  value: number,
): boolean {
  const rects = Array.from(group.children).filter(
    (child): child is SVGRectElement => child.localName === "rect",
  );
  if (rects.length < 2) return false;

  const rail = rects[0] as SVGRectElement;
  const thumb = rects[rects.length - 1] as SVGRectElement;
  const ratio = clampMidiValue(value) / 127;
  const railX = svgNumber(rail, "x");
  const railY = svgNumber(rail, "y");
  const railWidth = svgNumber(rail, "width");
  const railHeight = svgNumber(rail, "height");
  const thumbX = svgNumber(thumb, "x");
  const thumbY = svgNumber(thumb, "y");
  const thumbWidth = svgNumber(thumb, "width");
  const thumbHeight = svgNumber(thumb, "height");
  if (
    railX === null ||
    railY === null ||
    railWidth === null ||
    railHeight === null ||
    thumbX === null ||
    thumbY === null ||
    thumbWidth === null ||
    thumbHeight === null
  ) {
    return false;
  }

  const horizontal = controlId === "xfader";
  let dx = 0;
  let dy = 0;
  if (horizontal) {
    const travel = Math.max(0, railWidth - thumbWidth);
    const targetX = railX + ratio * travel;
    dx = targetX - thumbX;
  } else {
    const travel = Math.max(0, railHeight - thumbHeight);
    const targetY = railY + (1 - ratio) * travel;
    dy = targetY - thumbY;
  }

  thumb.setAttribute("data-fader-thumb", "true");
  thumb.setAttribute(
    "transform",
    `translate(${formatDelta(dx)} ${formatDelta(dy)})`,
  );
  return true;
}

/**
 * Apply a midi_position frame to the live SVG. Walks `positions`,
 * finds the matching `<g data-control-id>` group, and mutates a
 * `transform`/`data-active`/`data-value` attribute — never repaints
 * the SVG.
 *
 * Dispatch (see :func:`classifyControl` for the prefix→type map):
 *
 * - **Knob** (eq_*, filter:*, filter_fx): `transform="rotate(deg cx cy)"`
 *   where deg = (value/127)*270 - 135 (RESEARCH §Code Example 3). Maps
 *   the 7-bit MIDI range to the ±135° physical knob travel.
 * - **Fader** (vol:*, tempo:*, xfader): `data-value="<n>"` is set on the
 *   group and the last direct child `<rect>` is treated as the thumb.
 *   Its transform is translated along the first direct child `<rect>`
 *   rail. This keeps the parent group stable for highlight/focus
 *   while the visible thumb moves.
 * - **Button** (play:*, cue:*, sync:*, loop_in/out:*, hotcue:*,
 *   jog_touch:*, tap_tempo): `data-active="0|1"` — CSS handles the
 *   fill swap. Previously buttons inherited the rotation path because
 *   they also carry `data-cx`/`data-cy` (a ~2° rotation per click —
 *   barely visible but wrong).
 *
 * The wire shape carries `jog_touched:A/B` (after ControllerState
 * normalisation in `state.py`) but the SVG `data-control-id` is
 * `jog_touch:A/B` (matches the profile binding's `kind`). The lookup
 * tries the literal key first, then falls back to a `jog_touch`
 * substitution for the jog-touch family before classifying.
 */
export function applyPositionFrame(
  stage: HTMLElement,
  positions: Record<string, number>,
): void {
  for (const [rawKey, valueRaw] of Object.entries(positions)) {
    if (typeof valueRaw !== "number") continue;
    const value = valueRaw;
    // Resolve key: try literal, then strip `_touched` -> `_touch` for jog.
    let resolvedKey = rawKey;
    let group = stage.querySelector(
      `[data-control-id="${rawKey}"]`,
    ) as SVGGElement | null;
    if (!group && rawKey.startsWith("jog_touched:")) {
      resolvedKey = rawKey.replace("jog_touched:", "jog_touch:");
      group = stage.querySelector(
        `[data-control-id="${resolvedKey}"]`,
      ) as SVGGElement | null;
    }
    if (!group && rawKey.startsWith("jog:")) {
      resolvedKey = rawKey.replace("jog:", "jog_touch:");
      group = stage.querySelector(
        `[data-control-id="${resolvedKey}"]`,
      ) as SVGGElement | null;
    }
    if (!group) continue;

    const controlType = classifyControl(resolvedKey);
    if (controlType === "knob") {
      const cx = group.dataset.cx;
      const cy = group.dataset.cy;
      if (cx !== undefined && cy !== undefined) {
        // Knob — rotate around the pivot.
        const degrees = (value / 127) * 270 - 135;
        group.setAttribute(
          "transform",
          `rotate(${degrees} ${Number(cx)} ${Number(cy)})`,
        );
      }
      // No pivot defined → silently skip (defensive — unknown rotary shape).
    } else if (controlType === "fader") {
      group.setAttribute("data-value", String(value));
      translateFaderThumb(group, resolvedKey, value);
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

  /** Phase 92 RENDER-04 — instance wrapper around the `applyHighlight`
   *  module-level function. Mirrors the `applyPositionFrame` instance
   *  method's relationship to the function-level export. */
  applyHighlight(payload: HighlightPayload): void {
    applyHighlight(this.el, payload);
  }

  /** Phase 92 — clears the active highlight from this stage. */
  clearHighlight(): void {
    clearHighlight(this.el);
  }
}

/**
 * Phase 92 (RENDER-04) — paints a highlight on the target
 * `<g data-control-id>` group by swapping the `data-cue-color` +
 * `data-cue-shape` attributes. The CSS-variable cascade in `learn.css`
 * does the actual paint via `currentColor -> var(--learn-highlight)` for
 * the color channel, then uses the cue-shape attribute to choose either a
 * calm glow or a pulsed glow. The visual cue stays on the control group so
 * existing SVG geometry remains the source of truth.
 *
 * Wire convention (matches P91 SVG `data-control-id` naming):
 *   - When `payload.deck` is set (A/B/C/D): selector targets
 *     `<g data-control-id="<control_id>:<deck>">` (per-deck controls —
 *     play/cue/sync/loop/hotcue/eq/vol/tempo/jog/filter).
 *   - When `payload.deck` is empty string: selector targets the bare
 *     `<g data-control-id="<control_id>">` (master-section controls —
 *     filter_fx, tap_tempo, xfader).
 *
 * Single-active invariant: only ONE control on the stage carries
 * `[data-cue-color]` at a time. Calling `applyHighlight` clears any
 * prior cue attributes BEFORE setting the new ones — the
 * `highlight-paint.test.ts` "clears any prior highlight before painting
 * new one" assertion pins this contract.
 *
 * Unknown control_id: console.warn + return (no throw, never crashes
 * the webview — T-92-05-02 mitigation).
 *
 * Performance budget: ≤16 ms P95 paint, pinned by
 * `tauri/ui/tests/learn/highlight-paint.test.ts` (240 samples). In jsdom
 * the paint is pure attribute swap so the measured P95 lands far under
 * the budget (the P91 transform-only path measured 0.66 ms in the same
 * harness).
 */
export interface HighlightPayload {
  control_id: string;
  deck: string;
  cue_color: "amber" | "warning";
  cue_shape: "pulse-ring" | "static-glow";
  annotation?: string;
  expected_action?: object;
}

const ACTIVE_HIGHLIGHT = new WeakMap<HTMLElement, SVGGElement>();
const CONTROL_GROUP_CACHE = new WeakMap<HTMLElement, Map<string, SVGGElement>>();

export function applyHighlight(
  stage: HTMLElement,
  payload: HighlightPayload,
): void {
  clearActiveHighlight(stage);
  // Resolve target id — bare control_id for master section, "<field>:<deck>"
  // for per-deck controls. Matches the SVG authoring convention from P91.
  const targetId = payload.deck
    ? `${payload.control_id}:${payload.deck}`
    : payload.control_id;
  const target = findControlGroup(stage, targetId);
  if (!target) {
    // eslint-disable-next-line no-console
    console.warn(`[learn] highlight: control_id "${targetId}" not found`);
    return;
  }
  target.setAttribute("data-cue-color", payload.cue_color);
  target.setAttribute("data-cue-shape", payload.cue_shape);
  ACTIVE_HIGHLIGHT.set(stage, target);
}

function controlIdCandidates(controlId: string): string[] {
  const [head, deck] = controlId.split(":");
  if (head === "jog" && deck) {
    return [controlId, `jog_touch:${deck}`, `jog_touched:${deck}`];
  }
  return [controlId];
}

/**
 * Phase 92 — clear the active highlight (single-active invariant).
 * Called on `ipc.learn.advance` when the runtime confirms the user
 * matched the expected action; the next highlight (if any) lands via
 * a fresh `ipc.learn.highlight` envelope.
 */
export function clearHighlight(stage: HTMLElement): void {
  clearActiveHighlight(stage);
  stage.querySelectorAll<SVGGElement>("[data-cue-color]").forEach((g) => {
    clearHighlightElement(g);
  });
}

function clearActiveHighlight(stage: HTMLElement): void {
  const active = ACTIVE_HIGHLIGHT.get(stage);
  if (active && active.isConnected && stage.contains(active)) {
    clearHighlightElement(active);
    ACTIVE_HIGHLIGHT.delete(stage);
    return;
  }
  ACTIVE_HIGHLIGHT.delete(stage);

  const stale = stage.querySelectorAll<SVGGElement>("[data-cue-color]");
  stale.forEach((g) => clearHighlightElement(g));
}

function clearHighlightElement(group: SVGGElement): void {
  group.removeAttribute("data-cue-color");
  group.removeAttribute("data-cue-shape");
  group.classList.remove("hint-active");
}

function findControlGroup(
  stage: HTMLElement,
  targetId: string,
): SVGGElement | null {
  let cache = CONTROL_GROUP_CACHE.get(stage);
  if (!cache) {
    cache = new Map<string, SVGGElement>();
    CONTROL_GROUP_CACHE.set(stage, cache);
  }

  const cached = cache.get(targetId);
  if (cached && cached.isConnected && stage.contains(cached)) {
    return cached;
  }

  for (const id of controlIdCandidates(targetId)) {
    const target = stage.querySelector<SVGGElement>(
      `[data-control-id="${id}"]`,
    );
    if (target) {
      cache.set(targetId, target);
      return target;
    }
  }
  cache.delete(targetId);
  return null;
}

/**
 * Phase 92 — toggle the `.hint-active` class on the currently-lit
 * `<g data-control-id>` group. Driven by the tutor-dock's
 * `data-state="hint"` transition. The CSS keyframe swap in `learn.css`
 * replaces the calm 1400ms breathing pulse with a snappier amplitude.
 * This is a secondary a11y channel signaling "the system is more
 * actively guiding you now" that a user perceives via peripheral vision
 * while reading the dock copy (UI-SPEC §Motion line 306).
 *
 * If no group is lit, this is a silent no-op (the next highlight
 * envelope picks up the hint-intensity via the data-state attribute
 * on the dock root — the class toggle here is for the active highlight).
 */
export function setHighlightHintIntensity(
  stage: HTMLElement,
  hintActive: boolean,
): void {
  const target = stage.querySelector<SVGGElement>("[data-cue-color]");
  if (!target) return;
  target.classList.toggle("hint-active", hintActive);
}
