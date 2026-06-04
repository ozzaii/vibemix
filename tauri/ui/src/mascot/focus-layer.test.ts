// SPDX-License-Identifier: Apache-2.0

import { describe, expect, it, vi } from "vitest";

import {
  FocusLayer,
  type FocusableOrganism,
  type FocusWorldPoint,
  type ScreenToWorld,
} from "./focus-layer.js";
import { FACE_PLANE_Z, MASK_CENTER_Y } from "./particle-organism.js";

interface FakeOrganism extends FocusableOrganism {
  focusAt: ReturnType<typeof vi.fn>;
  reform: ReturnType<typeof vi.fn>;
}

function makeOrganism(): FakeOrganism {
  return {
    focusAt: vi.fn<(target: FocusWorldPoint, nowMs: number) => void>(),
    reform: vi.fn<(nowMs: number) => void>(),
  };
}

// A deterministic screen→world stub: tags the world point with the input
// pixels so the test can assert the rect actually flowed through.
const stubScreenToWorld: ScreenToWorld = (cx, cy) => ({
  x: cx / 100,
  y: cy / 100,
  z: FACE_PLANE_Z,
});

describe("FocusLayer", () => {
  it("registers a control rect keyed by control_id:deck", () => {
    const layer = new FocusLayer();
    layer.setControlRect({ control_id: "eq_low", deck: "A", cx: 120, cy: 240 });

    expect(layer.controlRectRegistry.get("eq_low:A")).toEqual({
      cx: 120,
      cy: 240,
    });
  });

  it("keys master-section controls with a trailing empty deck", () => {
    const layer = new FocusLayer();
    layer.setControlRect({ control_id: "filter_fx", deck: "", cx: 10, cy: 20 });

    expect(layer.controlRectRegistry.get("filter_fx:")).toEqual({
      cx: 10,
      cy: 20,
    });
  });

  it("focuses the organism at the registered rect's world point", () => {
    const layer = new FocusLayer();
    const organism = makeOrganism();
    layer.setControlRect({ control_id: "eq_low", deck: "A", cx: 200, cy: 300 });

    layer.onTeachingFocus(
      { control_id: "eq_low", deck: "A", band: "low", phase: "focus" },
      organism,
      stubScreenToWorld,
      1000,
    );

    expect(organism.focusAt).toHaveBeenCalledTimes(1);
    expect(organism.focusAt).toHaveBeenCalledWith(
      { x: 2, y: 3, z: FACE_PLANE_Z },
      1000,
    );
    expect(organism.reform).not.toHaveBeenCalled();
  });

  it("falls back to the mask centroid when no rect is registered", () => {
    const layer = new FocusLayer();
    const organism = makeOrganism();
    const screenToWorld = vi.fn(stubScreenToWorld);

    // No setControlRect for this control — the relay has not landed yet.
    layer.onTeachingFocus(
      { control_id: "eq_hi", deck: "B", band: "hi", phase: "focus" },
      organism,
      screenToWorld,
      2000,
    );

    // The mechanic still fires (a real teaching event is never dropped),
    // at the self-focus mask centroid, WITHOUT calling screenToWorld.
    expect(screenToWorld).not.toHaveBeenCalled();
    expect(organism.focusAt).toHaveBeenCalledWith(
      { x: 0, y: MASK_CENTER_Y, z: FACE_PLANE_Z },
      2000,
    );
  });

  it("reforms the organism on phase=reform, ignoring the rect", () => {
    const layer = new FocusLayer();
    const organism = makeOrganism();
    layer.setControlRect({ control_id: "eq_low", deck: "A", cx: 200, cy: 300 });

    layer.onTeachingFocus(
      { control_id: "eq_low", deck: "A", band: "low", phase: "reform" },
      organism,
      stubScreenToWorld,
      3000,
    );

    expect(organism.reform).toHaveBeenCalledTimes(1);
    expect(organism.reform).toHaveBeenCalledWith(3000);
    expect(organism.focusAt).not.toHaveBeenCalled();
  });

  it("does not move the organism without a teaching_focus event", () => {
    const layer = new FocusLayer();
    const organism = makeOrganism();

    // Registering a rect alone must not animate anything — grounding: motion
    // is caused only by a teaching_focus event.
    layer.setControlRect({ control_id: "eq_low", deck: "A", cx: 1, cy: 1 });

    expect(organism.focusAt).not.toHaveBeenCalled();
    expect(organism.reform).not.toHaveBeenCalled();
  });
});
