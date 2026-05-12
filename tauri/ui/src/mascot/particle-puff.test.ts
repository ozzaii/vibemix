/* Phase 13 Plan 07 — particle-puff.ts vitest spec (Task 2, 7 tests).
 *
 * Three.js BufferGeometry + PointsMaterial + Points construct fine under
 * vitest's jsdom env (no WebGL context required for the geometry+material
 * layer — only WebGLRenderer needs an actual canvas). We assert against
 * the geometry attribute counts + alpha + lifecycle rather than rendered
 * output.
 *
 * The sprite texture path is gated in production code behind a feature
 * detect so the test environment (no OffscreenCanvas in jsdom) gets a
 * 1×1 DataTexture fallback. We don't assert on the texture object itself
 * — only on the alive/end/dispose contract.
 */

import { describe, expect, it, vi } from "vitest";
import {
  BufferGeometry,
  Color,
  PointsMaterial,
  Scene,
  Vector3,
} from "three";

import { spawnParticlePuff } from "./particle-puff.js";

describe("particle-puff — spawnParticlePuff", () => {
  it("Test 1: returns a controller with alive=true on spawn", () => {
    const scene = new Scene();
    const ctrl = spawnParticlePuff(
      scene,
      new Vector3(0, 0, 0),
      new Color(0xffa12e),
    );
    expect(ctrl.alive).toBe(true);
  });

  it("Test 2: update(0.25) (half-lifetime) keeps alive=true; opacity ≈ 0.5", () => {
    const scene = new Scene();
    const ctrl = spawnParticlePuff(
      scene,
      new Vector3(0, 0, 0),
      new Color(0xffa12e),
      { lifetimeMs: 500 },
    );
    // 0.25s = 250ms = half of the 500ms lifetime budget.
    ctrl.update(0.25);
    expect(ctrl.alive).toBe(true);
    // Opacity is a side-effect on the underlying material — get it via
    // the scene's last child (the Points we just added).
    const last = scene.children[scene.children.length - 1] as {
      material?: { opacity?: number };
    };
    expect(last.material?.opacity).toBeGreaterThan(0.4);
    expect(last.material?.opacity).toBeLessThan(0.6);
  });

  it("Test 3: update past lifetime sets alive=false", () => {
    const scene = new Scene();
    const ctrl = spawnParticlePuff(
      scene,
      new Vector3(0, 0, 0),
      new Color(0xffa12e),
      { lifetimeMs: 500 },
    );
    // 0.6s = 600ms = past the 500ms lifetime.
    ctrl.update(0.6);
    expect(ctrl.alive).toBe(false);
  });

  it("Test 4: end() removes Points from scene (scene.remove called)", () => {
    const scene = new Scene();
    const removeSpy = vi.spyOn(scene, "remove");
    const ctrl = spawnParticlePuff(
      scene,
      new Vector3(0, 0, 0),
      new Color(0xffa12e),
    );
    expect(scene.children.length).toBe(1);
    ctrl.end();
    expect(removeSpy).toHaveBeenCalledTimes(1);
    expect(scene.children.length).toBe(0);
  });

  it("Test 5: end() disposes geometry + material", () => {
    const scene = new Scene();
    const ctrl = spawnParticlePuff(
      scene,
      new Vector3(0, 0, 0),
      new Color(0xffa12e),
    );
    const points = scene.children[0] as {
      geometry: BufferGeometry;
      material: PointsMaterial;
    };
    const geomSpy = vi.spyOn(points.geometry, "dispose");
    const matSpy = vi.spyOn(points.material, "dispose");
    ctrl.end();
    expect(geomSpy).toHaveBeenCalledTimes(1);
    expect(matSpy).toHaveBeenCalledTimes(1);
  });

  it("Test 6: explicit count override produces a geometry with that many positions", () => {
    const scene = new Scene();
    spawnParticlePuff(
      scene,
      new Vector3(0, 0, 0),
      new Color(0xffa12e),
      { count: 30 },
    );
    const points = scene.children[0] as {
      geometry: BufferGeometry;
    };
    const positionAttr = points.geometry.getAttribute("position");
    expect(positionAttr.count).toBe(30);
  });

  it("Test 7: positions move outward over time (non-zero velocity)", () => {
    const scene = new Scene();
    const origin = new Vector3(0, 0, 0);
    const ctrl = spawnParticlePuff(scene, origin, new Color(0xffa12e), {
      count: 50,
    });
    const points = scene.children[0] as { geometry: BufferGeometry };
    const beforeAttr = points.geometry.getAttribute("position");
    const beforeArr = (beforeAttr.array as Float32Array).slice();
    // Tick — even a small dt should move every particle if velocities
    // are non-zero (the geometry start was at origin, but the velocity
    // attribute is random outward so at least some axes change).
    ctrl.update(0.1);
    const afterArr = points.geometry.getAttribute("position")
      .array as Float32Array;
    let movedCount = 0;
    for (let i = 0; i < beforeArr.length; i++) {
      if (beforeArr[i] !== afterArr[i]) movedCount++;
    }
    expect(movedCount).toBeGreaterThan(0);
  });
});
