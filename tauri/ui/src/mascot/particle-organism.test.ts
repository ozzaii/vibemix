// SPDX-License-Identifier: Apache-2.0

import { describe, expect, it } from "vitest";

import { MorphController } from "./morph-controller.js";

describe("Particle organism morph controller", () => {
  it("drives focus from dissolve to hold to reform", () => {
    const morph = new MorphController();
    morph.focusAt({ x: 0.2, y: 1.1, z: 0.7 }, 1000, 400);

    const midFocus = morph.update(1200);
    expect(midFocus.focusPhase).toBe("dissolving");
    expect(midFocus.focusWeight).toBeGreaterThan(0);
    expect(midFocus.focusWeight).toBeLessThan(1);

    const holding = morph.update(1400);
    expect(holding.focusPhase).toBe("holding");
    expect(holding.focusWeight).toBe(1);
    expect(holding.focusTarget).toEqual({ x: 0.2, y: 1.1, z: 0.7 });

    morph.reform(1500, 600);
    const reforming = morph.update(1800);
    expect(reforming.focusPhase).toBe("reforming");
    expect(reforming.focusWeight).toBeGreaterThan(0);
    expect(reforming.focusWeight).toBeLessThan(1);

    const done = morph.update(2100);
    expect(done.focusPhase).toBe("idle");
    expect(done.focusWeight).toBe(0);
    expect(done.focusTarget).toBeNull();
  });

  it("morphs between mask and pill with stable endpoints", () => {
    const morph = new MorphController();
    morph.morphTo("pill", 0, 600);

    const mid = morph.update(300);
    expect(mid.fromPose).toBe("mask");
    expect(mid.toPose).toBe("pill");
    expect(mid.poseProgress).toBeGreaterThan(0);
    expect(mid.poseProgress).toBeLessThan(1);

    const pill = morph.update(600);
    expect(pill.pose).toBe("pill");
    expect(pill.poseProgress).toBe(0);

    morph.morphTo("mask", 700, 900);
    const returning = morph.update(1150);
    expect(returning.fromPose).toBe("pill");
    expect(returning.toPose).toBe("mask");
    expect(returning.poseProgress).toBeGreaterThan(0);
    expect(returning.poseProgress).toBeLessThan(1);
  });

  it("interrupts a morph by choosing the nearest endpoint", () => {
    const morph = new MorphController();
    morph.morphTo("pill", 0, 1000);
    morph.morphTo("mask", 760, 600);
    const snapshot = morph.update(900);

    expect(snapshot.fromPose).toBe("pill");
    expect(snapshot.toPose).toBe("mask");
    expect(snapshot.poseProgress).toBeGreaterThan(0);
  });
});
