// SPDX-License-Identifier: Apache-2.0
//
// FocusLayer — routes ipc.learn.teaching_focus + ipc.learn.control_rect
// into the particle organism's focus mechanic.
//
// The mascot is a separate Tauri webview from the learn window, so it cannot
// read the learn control's getBoundingClientRect() directly. The learn window
// relays the screen-space center as ipc.learn.control_rect; this layer stores
// it in a registry keyed "<control_id>:<deck>" and, on a teaching_focus
// "focus" event, converts that screen point to world space and aims the
// organism's dissolve→stream there. On "reform" it pulls the organism home.
//
// Grounding contract (the whole point): the organism animates ONLY on a real
// teaching_focus event. No timers, no un-caused motion. When no rect is
// registered yet (the relay hasn't landed), we still fire the mechanic at the
// mask centroid — a self-focus pulse — so a real teaching event is never
// silently dropped.
//
// Purity: this module imports no THREE runtime — the organism and the
// screen→world projector are injected, so the whole layer is unit-testable
// without WebGL.

import { FACE_PLANE_Z, MASK_CENTER_Y } from "./particle-organism.js";

export interface FocusWorldPoint {
  readonly x: number;
  readonly y: number;
  readonly z: number;
}

/** The slice of the organism this layer drives. Injected so tests can pass a
 *  fake. ParticleOrganism satisfies this structurally. */
export interface FocusableOrganism {
  focusAt(target: FocusWorldPoint, nowMs: number): void;
  reform(nowMs: number): void;
}

/** Maps a screen-space pixel center to a world point on the face plane. The
 *  renderer supplies the real implementation (camera unproject); tests pass a
 *  deterministic stub. */
export type ScreenToWorld = (cx: number, cy: number) => FocusWorldPoint;

export interface TeachingFocusPayload {
  readonly control_id: string;
  readonly deck: string;
  readonly band: string | null;
  readonly phase: "focus" | "reform";
}

export interface ControlRectPayload {
  readonly control_id: string;
  readonly deck: string;
  readonly cx: number;
  readonly cy: number;
}

interface RegisteredRect {
  readonly cx: number;
  readonly cy: number;
}

/** The mask centroid fallback — a self-focus pulse when no control rect is
 *  registered yet. Mirrors the organism's idle focus-target default. */
const MASK_CENTROID: FocusWorldPoint = {
  x: 0,
  y: MASK_CENTER_Y,
  z: FACE_PLANE_Z,
};

function registryKey(controlId: string, deck: string): string {
  return `${controlId}:${deck}`;
}

export class FocusLayer {
  /** Screen-space rect centers keyed "<control_id>:<deck>". Populated by the
   *  learn window's control_rect relay; read on teaching_focus. */
  readonly controlRectRegistry = new Map<string, RegisteredRect>();

  /** Store (or refresh) a control's screen-space center. */
  setControlRect(payload: ControlRectPayload): void {
    this.controlRectRegistry.set(
      registryKey(payload.control_id, payload.deck),
      { cx: payload.cx, cy: payload.cy },
    );
  }

  /** Drive the organism from a teaching_focus event. On "focus", aim the
   *  dissolve at the registered control rect (or the mask centroid when the
   *  rect relay hasn't arrived); on "reform", pull the organism home. */
  onTeachingFocus(
    payload: TeachingFocusPayload,
    organism: FocusableOrganism,
    screenToWorld: ScreenToWorld,
    nowMs: number,
  ): void {
    if (payload.phase === "reform") {
      organism.reform(nowMs);
      return;
    }
    // phase === "focus"
    const rect = this.controlRectRegistry.get(
      registryKey(payload.control_id, payload.deck),
    );
    const target = rect
      ? screenToWorld(rect.cx, rect.cy)
      : MASK_CENTROID;
    organism.focusAt(target, nowMs);
  }
}
