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
  DirectionalLight,
  Object3D,
  PerspectiveCamera,
  Scene,
  Vector3,
  WebGLRenderer,
} from "three";

import type { LoadedAssets } from "./asset-loader.js";
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
    this.scene.add(new AmbientLight(0xffffff, AMBIENT_INTENSITY));
    const dir = new DirectionalLight(0xffffff, DIRECTIONAL_INTENSITY);
    dir.position.set(...DIRECTIONAL_POSITION);
    // No shadows: the canvas is transparent + we have no ground plane to
    // catch a shadow. castShadow off keeps the GPU cost flat.
    dir.castShadow = false;
    this.scene.add(dir);

    // ── Character + mixer ────────────────────────────────────────────────
    const characterRoot = assets.character.scene;
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
   * Compute camera position + look-target from the character's bounding box.
   * CONTEXT Area 2 — bust + upper body framing. We measure the box, place
   * the camera 2.5x box-height back along Z, biased up so the head is at
   * the visual centre rather than the geometric centre.
   *
   * Bounding box is robust against future Meshy character swaps with different
   * scales — no hardcoded positions.
   */
  private frameCameraForBust(target: Object3D): void {
    const box = new Box3().setFromObject(target);
    const size = new Vector3();
    box.getSize(size);
    const centre = new Vector3();
    box.getCenter(centre);

    const height = size.y > 0 ? size.y : 1.6; // fallback ~average human height
    const focusY = centre.y + height * BUST_FOCUS_Y_BIAS;

    this.camera.position.set(
      centre.x,
      focusY,
      centre.z + height * BUST_CAMERA_Z_MULT,
    );
    this.camera.lookAt(centre.x, focusY, centre.z);
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
   * Called from the rAF loop in index.ts. Advances the AnimationMixer and
   * draws the scene. `deltaSeconds` comes from `clock.getDelta()` so the
   * caller controls the wall-clock source.
   */
  tick(deltaSeconds: number): void {
    if (this.disposed) return;
    this.mixer.update(deltaSeconds);
    this.renderer.render(this.scene, this.camera);
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
