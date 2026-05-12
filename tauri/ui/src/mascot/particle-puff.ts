/* Phase 13 Plan 07 — ParticlePuff effect (THREE.Points).
 *
 * A short-lifetime additive-blended particle puff used to mask the rig
 * pose change during mood swaps. ~50 particles, 500ms lifetime, alpha
 * fade-out. Texture is a procedural radial-gradient sprite generated
 * once (module-level singleton) so re-spawning the puff is allocation-
 * cheap.
 *
 * Why THREE.Points and not a CSS overlay: the rig is rendered in WebGL;
 * a DOM-layer puff would composite under the canvas (since the mascot
 * window's canvas is transparent), looking flat against the 3D shading.
 * Additive blending in WebGL produces a material smoke feel that reads
 * as part of the scene.
 *
 * Frontend-enforcement constraints (per skill rule + PLAN
 * <frontend_enforcement_constraints>):
 *   - No hex literals — colour is the caller's THREE.Color (constructed
 *     in renderer.ts / index.ts from `getComputedStyle(--accent)`).
 *   - Additive blending + alpha falloff = material smoke, not flat fill.
 *
 * Public surface:
 *   - ParticlePuffController { alive, update(dt), end() }
 *   - spawnParticlePuff(scene, origin, color, opts?) → controller
 *
 * Texture lifecycle:
 *   - SPRITE is built ONCE, cached at module scope, NEVER disposed.
 *     Per Plan 13-07 threat T-13-07-04: per-puff geometry + material are
 *     disposed in end(); the shared sprite texture is leak-by-design.
 */

import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  CanvasTexture,
  Color,
  DataTexture,
  Points,
  PointsMaterial,
  RGBAFormat,
  Scene,
  Texture,
  UnsignedByteType,
  Vector3,
} from "three";

// ── Sprite texture (shared, module-level singleton) ──────────────────────

/**
 * Build a 32×32 procedural radial-gradient sprite. The sprite is
 * white-centre → transparent edge, additive-blended against whatever
 * THREE.Color the caller hands in.
 *
 * Falls back to a 1×1 DataTexture in test environments where
 * OffscreenCanvas / document.createElement('canvas') don't produce a
 * working 2D context (vitest's jsdom env exposes canvas but its 2D
 * context is a stub that returns nothing useful). The 1×1 texture is
 * enough to satisfy PointsMaterial without crashing the test runner.
 */
function buildSpriteTexture(): Texture {
  // Prefer the real canvas path when it works.
  const tryCanvas = (): Texture | null => {
    try {
      // Prefer OffscreenCanvas in browsers that support it; fall back to
      // an HTMLCanvasElement when not. jsdom exposes neither reliably.
      const w = 32;
      const h = 32;
      let canvas: OffscreenCanvas | HTMLCanvasElement;
      if (typeof OffscreenCanvas !== "undefined") {
        canvas = new OffscreenCanvas(w, h);
      } else if (typeof document !== "undefined") {
        const c = document.createElement("canvas");
        c.width = w;
        c.height = h;
        canvas = c;
      } else {
        return null;
      }
      const ctx = canvas.getContext("2d") as
        | OffscreenCanvasRenderingContext2D
        | CanvasRenderingContext2D
        | null;
      if (!ctx) return null;
      const gradient = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
      gradient.addColorStop(0, "rgba(255, 255, 255, 1)");
      gradient.addColorStop(0.4, "rgba(255, 255, 255, 0.6)");
      gradient.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, w, h);
      const tex = new CanvasTexture(canvas as unknown as HTMLCanvasElement);
      tex.needsUpdate = true;
      return tex;
    } catch {
      return null;
    }
  };

  const real = tryCanvas();
  if (real) return real;

  // Test-env fallback: 1×1 white-alpha DataTexture.
  const data = new Uint8Array([255, 255, 255, 255]);
  const dt = new DataTexture(data, 1, 1, RGBAFormat, UnsignedByteType);
  dt.needsUpdate = true;
  return dt;
}

const SPRITE: Texture = buildSpriteTexture();

// ── Tuning (CONTEXT Area 4 + PLAN <interfaces>) ──────────────────────────

const DEFAULT_COUNT = 50;
const DEFAULT_LIFETIME_MS = 500;
/** Outward radial speed (m/s) — chosen so a 500ms puff covers ~0.75m radius. */
const RADIAL_SPEED_MPS = 1.5;
/** Slight upward bias (m/s) so the puff drifts up rather than spheroid. */
const UPWARD_BIAS_MPS = 0.5;
/** Gravity applied to the Y velocity (m/s² downward) so the puff settles. */
const GRAVITY_MPS2 = 2.0;
/** Sprite size in scene units (Three.js m). */
const PARTICLE_SIZE = 0.12;

// ── Public types ─────────────────────────────────────────────────────────

export interface ParticlePuffController {
  /** True until lifetimeMs has elapsed (or end() is called explicitly). */
  readonly alive: boolean;
  /**
   * Advance particle positions + opacity by `deltaSeconds`.
   * Calls end() automatically when lifetime is exhausted.
   */
  update(deltaSeconds: number): void;
  /**
   * Tear-down: remove the Points from the scene, dispose the per-puff
   * geometry + material. The shared sprite texture is NOT disposed.
   */
  end(): void;
}

export interface ParticlePuffOptions {
  /** Particle count (default 50). */
  count?: number;
  /** Effect lifetime in ms (default 500). */
  lifetimeMs?: number;
}

// ── spawnParticlePuff ────────────────────────────────────────────────────

export function spawnParticlePuff(
  scene: Scene,
  origin: Vector3,
  color: Color,
  opts?: ParticlePuffOptions,
): ParticlePuffController {
  const count = opts?.count ?? DEFAULT_COUNT;
  const lifetimeMs = opts?.lifetimeMs ?? DEFAULT_LIFETIME_MS;

  // ── Geometry: position + velocity per particle ─────────────────────
  const positions = new Float32Array(count * 3);
  const velocities = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    positions[i * 3] = origin.x;
    positions[i * 3 + 1] = origin.y;
    positions[i * 3 + 2] = origin.z;
    // Random unit-vector outward (uniform on a sphere via Marsaglia-ish
    // method: pick z then theta around it). Speed is RADIAL_SPEED with
    // a +UPWARD_BIAS on y so the puff drifts up.
    const u = Math.random() * 2 - 1; // cos(latitude), uniform [-1, 1]
    const theta = Math.random() * Math.PI * 2;
    const r = Math.sqrt(1 - u * u);
    velocities[i * 3] = r * Math.cos(theta) * RADIAL_SPEED_MPS;
    velocities[i * 3 + 1] = u * RADIAL_SPEED_MPS + UPWARD_BIAS_MPS;
    velocities[i * 3 + 2] = r * Math.sin(theta) * RADIAL_SPEED_MPS;
  }

  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(positions, 3));

  // ── Material: additive-blended, sprite-textured, faded over lifetime ──
  const material = new PointsMaterial({
    map: SPRITE,
    color: color,
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
    size: PARTICLE_SIZE,
    sizeAttenuation: true,
  });
  material.opacity = 1.0;

  const points = new Points(geometry, material);
  scene.add(points);

  // ── Controller state ──────────────────────────────────────────────────
  let elapsedMs = 0;
  let alive = true;

  function update(deltaSeconds: number): void {
    if (!alive) return;
    elapsedMs += deltaSeconds * 1000;

    // Advance positions; apply gravity to y velocity.
    // (positions/velocities are Float32Arrays pre-allocated to count*3 in
    //  the spawn block above; indices in [0, count*3) are always defined.
    //  Cast via Float32Array to silence noUncheckedIndexedAccess.)
    const p = positions;
    const v = velocities;
    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      p[i3] = (p[i3] as number) + (v[i3] as number) * deltaSeconds;
      p[i3 + 1] = (p[i3 + 1] as number) + (v[i3 + 1] as number) * deltaSeconds;
      p[i3 + 2] = (p[i3 + 2] as number) + (v[i3 + 2] as number) * deltaSeconds;
      v[i3 + 1] = (v[i3 + 1] as number) - GRAVITY_MPS2 * deltaSeconds;
    }
    const positionAttr = geometry.attributes["position"];
    if (positionAttr) positionAttr.needsUpdate = true;

    // Fade alpha linearly over lifetime.
    material.opacity = Math.max(0, 1.0 - elapsedMs / lifetimeMs);

    if (elapsedMs >= lifetimeMs) {
      end();
    }
  }

  function end(): void {
    if (!alive) return;
    alive = false;
    scene.remove(points);
    geometry.dispose();
    material.dispose();
    // SPRITE is shared — do NOT dispose.
  }

  return {
    get alive() {
      return alive;
    },
    update,
    end,
  };
}
