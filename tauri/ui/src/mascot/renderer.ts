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
  ACESFilmicToneMapping,
  AmbientLight,
  AnimationAction,
  AnimationMixer,
  Box3,
  Color,
  DirectionalLight,
  Object3D,
  PerspectiveCamera,
  SRGBColorSpace,
  Scene,
  ShaderMaterial,
  Vector3,
  Vector2,
  WebGLRenderer,
} from "three";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { OutputPass } from "three/examples/jsm/postprocessing/OutputPass.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { ShaderPass } from "three/examples/jsm/postprocessing/ShaderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";

import type { LoadedAssets } from "./asset-loader.js";
import type { MoodProfile } from "./mood.js";
import {
  spawnParticlePuff,
  type ParticlePuffController,
} from "./particle-puff.js";
import {
  ParticleOrganism,
  type OrganismSignals,
} from "./particle-organism.js";
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
/** Bloom params for the organism's emissive particle layer. */
const ORGANISM_BLOOM_LAYER = 1;
const BLOOM_THRESHOLD = 0.18;
const BLOOM_STRENGTH = 0.58;
const BLOOM_RADIUS = 0.36;

const BLOOM_MERGE_VERTEX = `
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = vec4(position.xy, 0.0, 1.0);
}
`;

const BLOOM_MERGE_FRAGMENT = `
uniform sampler2D baseTexture;
uniform sampler2D bloomTexture;

varying vec2 vUv;

void main() {
  vec4 base = texture2D(baseTexture, vUv);
  vec4 bloom = texture2D(bloomTexture, vUv);
  vec3 color = base.rgb + bloom.rgb;
  float bloomAlpha = max(bloom.r, max(bloom.g, bloom.b));
  float alpha = max(base.a, bloomAlpha);
  if (alpha <= 0.001) discard;
  gl_FragColor = vec4(color, alpha);
}
`;

// ── Internal helper: Meshy GLB material fixup ─────────────────────────────

/**
 * Meshy AI's GLB exports ship with emissiveFactor=[1,1,1] (full white
 * self-illumination) and metallicFactor=1 (kills diffuse contribution),
 * which makes the character render as a flat-white silhouette regardless
 * of the baseColorTexture. Walk the scene and neutralise both so the
 * diffuse texture takes over and standard lighting produces shading.
 */
function fixMeshyMaterials(root: Object3D): void {
  root.traverse((node) => {
    const mat = (node as unknown as { material?: unknown }).material;
    if (!mat) return;
    const mats = Array.isArray(mat) ? mat : [mat];
    for (const m of mats) {
      const mm = m as {
        emissive?: { setRGB: (r: number, g: number, b: number) => void };
        emissiveIntensity?: number;
        emissiveMap?: unknown;
        metalness?: number;
        roughness?: number;
      };
      if (mm.emissive && typeof mm.emissive.setRGB === "function") {
        mm.emissive.setRGB(0, 0, 0);
      }
      mm.emissiveIntensity = 0;
      mm.emissiveMap = null;
      mm.metalness = 0;
      mm.roughness = 0.7;
    }
  });
}

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

function prefersReducedMotion(): boolean {
  return Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
}

function supportsBloom(renderer: WebGLRenderer): boolean {
  if (prefersReducedMotion()) return false;
  if (!renderer.capabilities.isWebGL2) return false;
  return Boolean(renderer.getContext().getExtension("EXT_color_buffer_float"));
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
  /** The persistent mask organism: one Points cloud in the existing scene. */
  private readonly organism: ParticleOrganism;
  /** Offscreen bloom composer; null when reduced motion or float RT support fails. */
  private readonly bloomComposer: EffectComposer | null = null;
  /** Final transparent merge composer; null falls back to direct renderer.render. */
  private readonly finalComposer: EffectComposer | null = null;

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
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.toneMapping = ACESFilmicToneMapping;
    this.renderer.outputColorSpace = SRGBColorSpace;
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
    fixMeshyMaterials(characterRoot);
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
    this.organism = new ParticleOrganism(this.scene);
    this.organism.enableBloomLayer(ORGANISM_BLOOM_LAYER);
    if (supportsBloom(this.renderer)) {
      const bloomRenderPass = new RenderPass(this.scene, this.camera);
      const bloomPass = new UnrealBloomPass(
        new Vector2(initWidth, initHeight),
        BLOOM_STRENGTH,
        BLOOM_RADIUS,
        BLOOM_THRESHOLD,
      );
      this.bloomComposer = new EffectComposer(this.renderer);
      this.bloomComposer.renderToScreen = false;
      this.bloomComposer.addPass(bloomRenderPass);
      this.bloomComposer.addPass(bloomPass);

      const finalRenderPass = new RenderPass(this.scene, this.camera);
      const mergePass = new ShaderPass(
        new ShaderMaterial({
          uniforms: {
            baseTexture: { value: null },
            bloomTexture: { value: this.bloomComposer.renderTarget2.texture },
          },
          vertexShader: BLOOM_MERGE_VERTEX,
          fragmentShader: BLOOM_MERGE_FRAGMENT,
          transparent: true,
        }),
        "baseTexture",
      );
      this.finalComposer = new EffectComposer(this.renderer);
      this.finalComposer.addPass(finalRenderPass);
      this.finalComposer.addPass(mergePass);
      this.finalComposer.addPass(new OutputPass());
    }
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
    this.organism.tick(deltaSeconds);

    if (this.bloomComposer && this.finalComposer) {
      this.renderer.setClearColor(0x000000, 0);
      this.renderer.setClearAlpha(0);
      this.camera.layers.set(ORGANISM_BLOOM_LAYER);
      this.bloomComposer.render(deltaSeconds);
      this.camera.layers.set(0);
      this.finalComposer.render(deltaSeconds);
      return;
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

  setOrganismSignals(signals: OrganismSignals): void {
    if (this.disposed) return;
    this.organism.setSignals(signals);
  }

  /**
   * Re-fit the renderer + camera aspect after a window resize. Bound to
   * the window's resize event in index.ts.
   */
  resize(width: number, height: number): void {
    if (this.disposed) return;
    this.renderer.setSize(width, height, false);
    this.bloomComposer?.setSize(width, height);
    this.finalComposer?.setSize(width, height);
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
    this.organism.dispose();
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
    this.bloomComposer?.dispose();
    this.finalComposer?.dispose();
    this.renderer.dispose();
  }
}
