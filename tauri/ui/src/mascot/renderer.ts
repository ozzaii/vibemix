/* Phase 13 Plan 04 — Three.js renderer (MascotRenderer class).
 *
 * Owns:
 *   - WebGLRenderer with transparent clear, pixel-ratio cap @ 2.0
 *     (CONTEXT Area 2 — Retina perf guard).
 *   - Scene (no background, no skybox — the canvas is transparent so the
 *     Tauri window's transparent flag composites over the desktop).
 *   - PerspectiveCamera framed for bust + upper body (CONTEXT Area 2).
 *     Framing is computed post-load from the character's bounding box.
 *   - One AmbientLight + one DirectionalLight (CONTEXT Area 2 — minimum
 *     viable lighting; Plan 13-07 layers mood-dependent intensity).
 *   - The character mesh added to the scene.
 *   - AnimationMixer bound to the character's SkinnedMesh.
 *   - Lazy AnimationAction cache per MascotState — built on first
 *     crossFadeTo() so we don't allocate 25 actions at boot.
 *
 * Public surface:
 *   - constructor(canvas, assets)
 *   - crossFadeTo(state, blendMs): drive the visible animation switch
 *   - tick(deltaSeconds): called from index.ts rAF loop
 *   - resize(width, height): window-resize handler in index.ts
 *   - dispose(): full cleanup for hot-reload / module teardown
 *
 * Threading: all methods run on the main thread (Three.js does not
 * thread-safe). The rAF loop in index.ts is the only caller of tick().
 */

import {
  AmbientLight,
  AnimationAction,
  AnimationMixer,
  Box3,
  Color,
  DirectionalLight,
  Object3D,
  PerspectiveCamera,
  Scene,
  Vector3,
  WebGLRenderer,
} from "three";

import type { LoadedAssets } from "./asset-loader.js";
import type { MoodProfile } from "./mood.js";
import {
  spawnParticlePuff,
  type ParticlePuffController,
} from "./particle-puff.js";
import type { MascotState } from "./types.js";

// ── Tuning constants (CONTEXT Area 2) ─────────────────────────────────────

/** Cap pixel ratio at 2.0 to avoid Retina perf blowup. */
const MAX_PIXEL_RATIO = 2.0;
/** Bust-framing camera FOV — wide enough for full-body fallback. */
const CAMERA_FOV_DEG = 45;
/** Camera near plane. */
const CAMERA_NEAR = 0.1;
/** Camera far plane — character is ~2m, so 100 is generous. */
const CAMERA_FAR = 100;
/** AmbientLight intensity (key+fill bias). */
const AMBIENT_INTENSITY = 0.4;
/** DirectionalLight intensity (key light). */
const DIRECTIONAL_INTENSITY = 0.8;
/** DirectionalLight position (above + camera-side, mimics ring-light staging). */
const DIRECTIONAL_POSITION: [number, number, number] = [3, 5, 5];
/** Bust-frame Y bias: place focus ~15% of character height above the centre. */
const BUST_FOCUS_Y_BIAS = 0.15;
/** Bust-frame camera Z multiplier of character height (smaller = closer). */
const BUST_CAMERA_Z_MULT = 2.5;

// ── Internal helper: find the first SkinnedMesh in a scene tree ───────────

function findSkinnedMesh(root: Object3D): Object3D | null {
  let found: Object3D | null = null;
  root.traverse((node) => {
    if (found) return;
    if ((node as { isSkinnedMesh?: boolean }).isSkinnedMesh === true) {
      found = node;
    }
  });
  return found;
}

// ── MascotRenderer ────────────────────────────────────────────────────────

export class MascotRenderer {
  private readonly renderer: WebGLRenderer;
  private readonly scene: Scene;
  private readonly camera: PerspectiveCamera;
  private readonly mixer: AnimationMixer;
  private readonly assets: LoadedAssets;
  private readonly actions: Map<MascotState, AnimationAction> = new Map();
  private currentAction: AnimationAction | null = null;
  private disposed = false;

  // ── Plan 13-07 — mood + particle state ────────────────────────────────
  /** AmbientLight reference — Plan 13-07 setMoodLighting updates intensity. */
  private readonly ambientLight: AmbientLight;
  /** DirectionalLight reference — Plan 13-07 setMoodLighting updates intensity. */
  private readonly directionalLight: DirectionalLight;
  /** Character root — Plan 13-07 uses for head-position lookup. */
  private readonly characterRoot: Object3D;
  /** Cached head/torso position — computed lazily on first puff. */
  private cachedHeadPosition: Vector3 | null = null;
  /** Live ParticlePuff controllers; ticked each frame, filtered when dead. */
  private puffs: ParticlePuffController[] = [];

  constructor(canvas: HTMLCanvasElement, assets: LoadedAssets) {
    this.assets = assets;

    // ── Renderer ─────────────────────────────────────────────────────────
    // alpha:true + premultipliedAlpha:false + setClearAlpha(0) = a fully
    // transparent canvas that composites over the Tauri transparent window.
    this.renderer = new WebGLRenderer({
      canvas,
      alpha: true,
      antialias: true,
      premultipliedAlpha: false,
    });
    this.renderer.setClearAlpha(0);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, MAX_PIXEL_RATIO));
    const initWidth = canvas.clientWidth || 300;
    const initHeight = canvas.clientHeight || 400;
    this.renderer.setSize(initWidth, initHeight, false);

    // ── Scene + lights ────────────────────────────────────────────────────
    this.scene = new Scene();
    this.ambientLight = new AmbientLight(0xffffff, AMBIENT_INTENSITY);
    this.scene.add(this.ambientLight);
    this.directionalLight = new DirectionalLight(
      0xffffff,
      DIRECTIONAL_INTENSITY,
    );
    this.directionalLight.position.set(...DIRECTIONAL_POSITION);
    // No shadows: the canvas is transparent + we have no ground plane to
    // catch a shadow. castShadow off keeps the GPU cost flat.
    this.directionalLight.castShadow = false;
    this.scene.add(this.directionalLight);

    // ── Character + mixer ────────────────────────────────────────────────
    const characterRoot = assets.character.scene;
    this.characterRoot = characterRoot;
    this.scene.add(characterRoot);

    const skinnedMesh = findSkinnedMesh(characterRoot);
    if (!skinnedMesh) {
      throw new Error(
        "MascotRenderer: character GLB has no SkinnedMesh — cannot build AnimationMixer",
      );
    }
    this.mixer = new AnimationMixer(skinnedMesh);

    // ── Camera framing (post-load, after we know character bounds) ───────
    const aspect = initWidth / initHeight;
    this.camera = new PerspectiveCamera(
      CAMERA_FOV_DEG,
      aspect,
      CAMERA_NEAR,
      CAMERA_FAR,
    );
    this.frameCameraForBust(characterRoot);
  }

  /**
   * TEMP 2026-05-12 — render-bug debug snapshot. Returns a one-line
   * summary of the scene state right after construction. Remove once the
   * render bug is fixed.
   */
  getDebugSnapshot(): string {
    const box = new Box3().setFromObject(this.characterRoot);
    const size = new Vector3();
    box.getSize(size);
    const centre = new Vector3();
    box.getCenter(centre);
    const cp = this.camera.position;
    const skinned = findSkinnedMesh(this.characterRoot);
    const mat = skinned
      ? (skinned as unknown as { material?: { name?: string; map?: unknown } }).material
      : undefined;
    const matName = mat?.name ?? "<no-mat>";
    const mapPresent = mat?.map ? "yes" : "no";
    return (
      `box size=(${size.x.toFixed(2)},${size.y.toFixed(2)},${size.z.toFixed(2)})` +
      ` centre=(${centre.x.toFixed(2)},${centre.y.toFixed(2)},${centre.z.toFixed(2)})` +
      ` cam=(${cp.x.toFixed(2)},${cp.y.toFixed(2)},${cp.z.toFixed(2)})` +
      ` near=${this.camera.near} far=${this.camera.far} fov=${this.camera.fov}` +
      ` mat=${matName} map=${mapPresent}`
    );
  }

  /**
   * Compute camera position + look-target from the character's bounding box.
   * CONTEXT Area 2 — bust + upper body framing.
   *
   * 2026-05-12 fixup: Box3.setFromObject on a SkinnedMesh whose mesh node
   * inherits the Armature's scale=0.01 ended up reporting a ~1.7cm-tall
   * box even though the visually-skinned character is ~1.7m. That put the
   * camera ~4cm from origin — inside the rendered mesh — so every canvas
   * pixel painted the inside of the character (full-white window). Until
   * we have a robust skin-aware fitting pass, hardcode the camera for a
   * Mixamo-rigged ~1.7m biped standing at origin, framing the bust.
   */
  private frameCameraForBust(target: Object3D): void {
    const box = new Box3().setFromObject(target);
    const size = new Vector3();
    box.getSize(size);
    const centre = new Vector3();
    box.getCenter(centre);
    // Diagnostic — read with Safari Develop → vibemix → mascot.html.
    // eslint-disable-next-line no-console
    console.log(
      `[mascot] bbox size=${size.x.toFixed(3)},${size.y.toFixed(3)},${size.z.toFixed(3)} ` +
        `centre=${centre.x.toFixed(3)},${centre.y.toFixed(3)},${centre.z.toFixed(3)}`,
    );

    // Fixed bust framing for a 1.7 m Mixamo biped standing at origin.
    const focusY = 1.4;
    this.camera.position.set(0, focusY, 3.0);
    this.camera.lookAt(0, focusY - 0.2, 0);
    void target; // box read above is for the console diagnostic only.
  }

  /**
   * Build (or fetch) the AnimationAction for a given state. Lazy so we
   * only pay clipAction() cost the first time a state is requested.
   */
  private getOrCreateAction(state: MascotState): AnimationAction {
    const cached = this.actions.get(state);
    if (cached) return cached;

    const loaded = this.assets.clips.get(state);
    if (!loaded) {
      // CONTEXT must-have: "No silent fallbacks. Throw on unknown state name."
      throw new Error(
        `MascotRenderer: no AnimationClip registered for MascotState '${state}'`,
      );
    }
    const action = this.mixer.clipAction(loaded.clip);
    action.timeScale = loaded.timeScale;
    this.actions.set(state, action);
    return action;
  }

  /**
   * Drive a visible animation switch. Caller (index.ts) invokes this when
   * the state machine emits a switch_now plan OR when a pendingSwitch
   * timestamp lands inside the rAF loop.
   *
   * @param state - The target MascotState. Must be registered in assets.clips.
   * @param blendMs - Crossfade duration in ms. Use 0 for instant on first frame.
   *
   * Behaviour:
   *   - First call (currentAction null): plays the new action immediately.
   *   - Subsequent calls with a different action: crossFadeTo over blendMs.
   *   - Calls with the same action: no-op (Three.js handles re-entry safely
   *     but we skip the play() reset to keep the loop phase intact).
   */
  crossFadeTo(state: MascotState, blendMs: number): void {
    const next = this.getOrCreateAction(state);
    if (this.currentAction === next) return;

    next.enabled = true;
    next.setEffectiveWeight(1.0);
    next.reset();
    next.play();

    if (this.currentAction && this.currentAction !== next) {
      // Three.js takes seconds, not ms.
      this.currentAction.crossFadeTo(next, blendMs / 1000, false);
    }

    this.currentAction = next;
  }

  /**
   * Called from the rAF loop in index.ts. Advances the AnimationMixer,
   * progresses live particle puffs, and draws the scene. `deltaSeconds`
   * comes from `clock.getDelta()` so the caller controls the wall-clock
   * source.
   */
  tick(deltaSeconds: number): void {
    if (this.disposed) return;
    this.mixer.update(deltaSeconds);

    // ── Plan 13-07 — advance + GC puffs ────────────────────────────────
    if (this.puffs.length > 0) {
      for (const puff of this.puffs) puff.update(deltaSeconds);
      this.puffs = this.puffs.filter((p) => p.alive);
    }

    this.renderer.render(this.scene, this.camera);
  }

  // ── Plan 13-07 — public mood + puff API ──────────────────────────────

  /**
   * Compute (and cache) the head/torso anchor used as the puff origin.
   * Strategy: walk the character skeleton for a bone named `Head` or
   * `mixamorigHead`; if found, return its world-position. Else fall back
   * to the bounding-box top of the character root.
   *
   * Lazy: computed once on first puff, then cached for the renderer's
   * lifetime. The character root doesn't move at runtime — only the
   * skeleton bones do — so a stale head position would only be wrong by
   * the character's animation amplitude (~10cm), which the puff hides
   * anyway. Worth the perf savings.
   */
  private getHeadPosition(): Vector3 {
    if (this.cachedHeadPosition) return this.cachedHeadPosition.clone();

    // Prefer a "Head"-named bone in the skeleton.
    let found: Object3D | null = null;
    this.characterRoot.traverse((node) => {
      if (found) return;
      const name = (node.name ?? "").toLowerCase();
      if (name === "head" || name === "mixamorighead") {
        found = node;
      }
    });

    const out = new Vector3();
    if (found !== null) {
      (found as Object3D).getWorldPosition(out);
    } else {
      // Fallback: bounding-box top, slightly below for torso framing.
      const box = new Box3().setFromObject(this.characterRoot);
      box.getCenter(out);
      const size = new Vector3();
      box.getSize(size);
      out.y = (box.max.y - size.y * 0.3);
    }

    this.cachedHeadPosition = out.clone();
    return out;
  }

  /**
   * Spawn a particle puff at the head/torso anchor with the given colour.
   * Caller (index.ts) passes a THREE.Color derived from the destination
   * mood's accent CSS variable; this method does not know about moods.
   *
   * Each puff is independently controlled — multiple concurrent puffs
   * are allowed (e.g. user hammering the mood selector). T-13-07-02
   * threat is bounded by the 50-particles × 500ms lifetime + per-frame
   * GC in tick().
   */
  playParticlePuff(color: Color): void {
    if (this.disposed) return;
    const origin = this.getHeadPosition();
    const ctrl = spawnParticlePuff(this.scene, origin, color);
    this.puffs.push(ctrl);
  }

  /**
   * Update ambient + directional light intensities to match the given
   * mood profile. Called when a `mood_change` bus event arrives — the
   * lighting shift, combined with the puff and the animation-pool swap,
   * makes the persona feel different on the same rig.
   */
  setMoodLighting(profile: MoodProfile): void {
    if (this.disposed) return;
    this.ambientLight.intensity = profile.ambient_intensity;
    this.directionalLight.intensity = profile.key_intensity;
  }

  /**
   * Re-fit the renderer + camera aspect after a window resize. Bound to
   * the window's resize event in index.ts.
   */
  resize(width: number, height: number): void {
    if (this.disposed) return;
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }

  /**
   * Full Three.js cleanup. Called from module teardown (hot-reload during
   * dev, or future Plan 13-06 "hide mascot" hard-stop path). Releases GPU
   * resources to avoid the classic "WebGL context lost" creep.
   */
  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    // Plan 13-07 — end any live puffs (per-puff geometry/material dispose).
    for (const puff of this.puffs) {
      try {
        puff.end();
      } catch {
        // best-effort cleanup
      }
    }
    this.puffs = [];
    // Stop the mixer's actions.
    this.mixer.stopAllAction();
    // Walk the scene, dispose any geometry/material we own.
    this.scene.traverse((node) => {
      const mesh = node as {
        geometry?: { dispose: () => void };
        material?: unknown;
      };
      if (mesh.geometry && typeof mesh.geometry.dispose === "function") {
        mesh.geometry.dispose();
      }
      const mat = mesh.material;
      if (Array.isArray(mat)) {
        mat.forEach((m) => {
          if (m && typeof (m as { dispose?: () => void }).dispose === "function") {
            (m as { dispose: () => void }).dispose();
          }
        });
      } else if (mat && typeof (mat as { dispose?: () => void }).dispose === "function") {
        (mat as { dispose: () => void }).dispose();
      }
    });
    this.renderer.dispose();
  }
}
