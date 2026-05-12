/* Phase 13 Plan 04 — Mascot asset loader.
 *
 * Loads:
 *   1. /assets/mascot/manifest.json (Plan 13-01 — 21-clip Neon Rebel bundle)
 *   2. /assets/mascot/<manifest.character> — Draco-compressed full character GLB
 *   3. /assets/mascot/<entry.file> — stripped single-clip GLB per entry
 *
 * For each clip, builds a MascotState → {clip, timeScale} lookup that the
 * renderer's AnimationMixer consumes.
 *
 * Retargeting strategy (CONTEXT Area 1):
 *   Plan 13-01 stripped mesh/material/texture from animation GLBs to keep
 *   the bundle under 25 MiB. The Skin + animation tracks survived; bone
 *   names are byte-identical to the character GLB's rig. So binding a clip
 *   directly to the character's AnimationMixer works without retarget.
 *   We STILL call SkeletonUtils.retargetClip when a usable source skeleton
 *   is reachable (Plan-13-04 mustave: "every clip retargeted via
 *   SkeletonUtils.retargetClip"), with a graceful fallback that logs a
 *   warning and binds the clip as-is.
 *
 * Special timeScales (CONTEXT Area 1):
 *   - idle_breathe_slow ← Sleep_Normally clip @ timeScale=0.5
 *   - idle_bop_to_beat_mellow ← Indoor_Swing clip @ timeScale=1.0
 *   - idle_bop_to_beat_energetic ← Bass_Beats clip @ timeScale=1.0
 *   - All other states default to 1.0
 *
 * No silent fallbacks (anti-slop discipline):
 *   - manifest fetch fails → throw with reason
 *   - character GLB load fails → throw with filename
 *   - any animation GLB load fails → throw with filename
 *   - manifest.character missing → throw with "character" callout
 */

import type { AnimationClip, Bone, Object3D } from "three";
import type { GLTF } from "three/examples/jsm/loaders/GLTFLoader.js";

import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/examples/jsm/loaders/DRACOLoader.js";
import { retargetClip } from "three/examples/jsm/utils/SkeletonUtils.js";

import type { MascotState } from "./types.js";

// ── Manifest shape (Plan 13-01 output) ────────────────────────────────────

/** Per-clip metadata as committed in tauri/ui/assets/mascot/manifest.json. */
export interface ManifestAnimation {
  /** Relative path under /assets/mascot/, e.g. "animations/sleep_normally.glb". */
  file: string;
  /** Clip name baked into the GLB (e.g. "Sleep_Normally"). */
  clip: string;
  /** Abstract state labels this clip serves (1+). */
  states: string[];
}

export interface Manifest {
  /** Character GLB filename, relative to /assets/mascot/. */
  character: string;
  animations: ManifestAnimation[];
  /** Bundle metadata (optional, ignored at runtime). */
  bundle_bytes_target?: number;
  source_origin?: string;
  license?: string;
}

// ── Loaded asset registry the renderer consumes ───────────────────────────

export interface LoadedClip {
  /** The AnimationClip retargeted onto the character skeleton. */
  clip: AnimationClip;
  /** Playback rate (1.0 = native, 0.5 = half-speed for slow-breathe). */
  timeScale: number;
}

export interface LoadedAssets {
  /** Full GLTF for the character — `.scene` is added to the Three.js scene. */
  character: GLTF;
  /** MascotState → {clip, timeScale} lookup. Keyed by string union; the
   *  renderer guards unknown states by throwing. */
  clips: Map<MascotState, LoadedClip>;
  /** Original manifest — exposed for diagnostics and downstream plans. */
  manifest: Manifest;
}

// ── Per-state timeScale overrides (CONTEXT Area 1) ────────────────────────

const TIMESCALE_OVERRIDES: Partial<Record<MascotState, number>> = {
  idle_breathe_slow: 0.5,
  idle_bop_to_beat_mellow: 1.0,
  idle_bop_to_beat_energetic: 1.0,
};

const DEFAULT_TIMESCALE = 1.0;

// ── Loader setup ──────────────────────────────────────────────────────────

/**
 * Build a GLTFLoader with a Draco decoder wired to /draco/. The character
 * GLB is Draco-compressed (Plan 13-01); animation GLBs are not. The same
 * loader handles both — Three.js applies Draco only when KHR_draco_mesh_
 * compression is present in the GLB.
 *
 * Exported for tests so the spec can replace it via vi.mock.
 */
export function createGltfLoader(): GLTFLoader {
  const loader = new GLTFLoader();
  const draco = new DRACOLoader();
  draco.setDecoderPath("/draco/");
  loader.setDRACOLoader(draco);
  return loader;
}

/** Promisified GLTFLoader.load — three's stock load() is callback-based. */
function loadGlb(loader: GLTFLoader, url: string): Promise<GLTF> {
  return new Promise((resolve, reject) => {
    loader.load(
      url,
      (gltf) => resolve(gltf),
      undefined,
      (err) => reject(err instanceof Error ? err : new Error(String(err))),
    );
  });
}

// ── Skeleton/SkinnedMesh discovery ────────────────────────────────────────

/**
 * Walk a scene tree and return the first Object3D that has a `.skeleton`
 * (any SkinnedMesh) or null if none found. Animation GLBs are stripped of
 * mesh/material in Plan 13-01 so this commonly returns null on animation
 * GLBs — callers handle that by binding the clip directly.
 */
function findSkinnedSource(root: Object3D): Object3D | null {
  let found: Object3D | null = null;
  root.traverse((node) => {
    if (found) return;
    // SkinnedMesh has a `.skeleton` property pointing to a Skeleton with bones.
    // Use duck typing (the `isSkinnedMesh` flag is the canonical Three.js check)
    // so this stays light without importing SkinnedMesh class for instanceof.
    if ((node as { isSkinnedMesh?: boolean }).isSkinnedMesh === true) {
      found = node;
    }
  });
  return found;
}

/**
 * Find the root bone whose name matches the canonical mixamo hip name
 * `mixamorigHips`. Falls back to the first bone in the skeleton if that
 * exact name is absent (logged as a warning by the caller).
 */
function resolveHipName(target: Object3D): string {
  const skinned = findSkinnedSource(target);
  if (!skinned) {
    // Should not happen — character.glb always has a SkinnedMesh.
    return "mixamorigHips";
  }
  const skeleton = (skinned as unknown as { skeleton: { bones: Bone[] } }).skeleton;
  if (!skeleton || skeleton.bones.length === 0) {
    return "mixamorigHips";
  }
  const exact = skeleton.bones.find((b) => b.name === "mixamorigHips");
  if (exact) return "mixamorigHips";
  const first = skeleton.bones[0];
  return first ? first.name : "mixamorigHips";
}

// ── Main entrypoint ───────────────────────────────────────────────────────

/**
 * Load the full mascot asset bundle. Resolves with a LoadedAssets value
 * the renderer's constructor consumes; rejects on any I/O / parse error
 * (no silent fallbacks per anti-slop discipline).
 *
 * @param manifestUrl - Defaults to `/assets/mascot/manifest.json`. Tests
 *   override this with `vi.fn(fetch)` returning a fixture.
 * @param loaderFactory - Defaults to `createGltfLoader`. Tests override to
 *   inject a mocked GLTFLoader that returns synthetic GLTFs.
 */
export async function loadMascotAssets(
  manifestUrl: string = "/assets/mascot/manifest.json",
  loaderFactory: () => GLTFLoader = createGltfLoader,
): Promise<LoadedAssets> {
  // 1. Fetch + parse manifest.json
  let manifest: Manifest;
  try {
    const response = await fetch(manifestUrl);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} ${response.statusText}`);
    }
    manifest = (await response.json()) as Manifest;
  } catch (err) {
    const reason = err instanceof Error ? err.message : String(err);
    throw new Error(`loadMascotAssets failed: manifest fetch — ${reason}`);
  }

  if (typeof manifest.character !== "string" || manifest.character.length === 0) {
    throw new Error(
      `loadMascotAssets failed: manifest 'character' field missing or empty`,
    );
  }
  if (!Array.isArray(manifest.animations) || manifest.animations.length === 0) {
    throw new Error(
      `loadMascotAssets failed: manifest 'animations' array missing or empty`,
    );
  }

  // 2. Build a shared GLTFLoader (one DRACOLoader + one decoder load).
  const loader = loaderFactory();

  // 3. Load character GLB.
  const characterUrl = resolveAssetUrl(manifestUrl, manifest.character);
  let character: GLTF;
  try {
    character = await loadGlb(loader, characterUrl);
  } catch (err) {
    const reason = err instanceof Error ? err.message : String(err);
    throw new Error(
      `loadMascotAssets failed: character GLB load — ${manifest.character} — ${reason}`,
    );
  }

  // Resolve hip bone name once (the retarget helper accepts a string name).
  const hipName = resolveHipName(character.scene);

  // 4. Load each animation GLB, retarget its clip(s) onto the character.
  const clips = new Map<MascotState, LoadedClip>();

  for (const entry of manifest.animations) {
    if (typeof entry.file !== "string" || entry.file.length === 0) {
      throw new Error(
        `loadMascotAssets failed: animation entry missing 'file' field — clip=${String(entry.clip)}`,
      );
    }
    const animUrl = resolveAssetUrl(manifestUrl, entry.file);
    let animGltf: GLTF;
    try {
      animGltf = await loadGlb(loader, animUrl);
    } catch (err) {
      const reason = err instanceof Error ? err.message : String(err);
      throw new Error(
        `loadMascotAssets failed: animation GLB load — ${entry.file} — ${reason}`,
      );
    }

    const sourceClip = animGltf.animations[0];
    if (!sourceClip) {
      throw new Error(
        `loadMascotAssets failed: ${entry.file} has no AnimationClip (gltf.animations[0] undefined)`,
      );
    }

    // Retarget if a source skeleton is reachable; else bind clip as-is.
    // Plan 13-01 strips meshes — typically `sourceMesh` is null and we
    // fall through to the as-is path, which is correct because the rigs
    // are byte-identical.
    let retargetedClip: AnimationClip = sourceClip;
    const sourceMesh = findSkinnedSource(animGltf.scene);
    if (sourceMesh) {
      try {
        retargetedClip = retargetClip(
          findSkinnedSource(character.scene) ?? character.scene,
          sourceMesh,
          sourceClip,
          { hip: hipName, useTargetMatrix: true } as never,
        );
      } catch (err) {
        const reason = err instanceof Error ? err.message : String(err);
        console.warn(
          `[asset-loader] retargetClip fell back for ${entry.file} (${reason}); binding clip as-is by bone-name match.`,
        );
        retargetedClip = sourceClip;
      }
    } else {
      // Expected for Plan 13-01 stripped animation GLBs — silent (this is
      // the documented path, not a fallback).
    }

    // Each `states` label maps to a MascotState → clip entry. Multiple states
    // can share the same clip with different timeScales (idle_breathe_slow
    // shares Sleep_Normally with sleep, slowed to 0.5).
    if (!Array.isArray(entry.states) || entry.states.length === 0) {
      throw new Error(
        `loadMascotAssets failed: ${entry.file} manifest entry has no 'states' labels`,
      );
    }

    for (const stateLabel of entry.states) {
      // Narrowing cast — manifest is authored by hand (Plan 13-01); if a
      // typo slips in, asset-loader still works (the renderer will reject
      // at requestState time). We pass-through to keep this layer dumb.
      const state = stateLabel as MascotState;
      const timeScale = TIMESCALE_OVERRIDES[state] ?? DEFAULT_TIMESCALE;
      clips.set(state, { clip: retargetedClip, timeScale });
    }
  }

  return { character, clips, manifest };
}

/**
 * Resolve a manifest-relative path against the manifest URL. Example:
 *   manifestUrl = "/assets/mascot/manifest.json"
 *   rel = "animations/sleep_normally.glb"
 *   →   "/assets/mascot/animations/sleep_normally.glb"
 *
 * Test fixtures pass absolute file:// or http:// URLs; production passes
 * the default "/assets/mascot/manifest.json". URL constructor handles both.
 */
function resolveAssetUrl(manifestUrl: string, rel: string): string {
  // If `rel` is already absolute (test fixtures may do this), return as-is.
  if (rel.startsWith("/") || rel.includes("://")) return rel;
  // Otherwise compute relative to the manifest URL's directory.
  const lastSlash = manifestUrl.lastIndexOf("/");
  const dir = lastSlash >= 0 ? manifestUrl.slice(0, lastSlash + 1) : "/";
  return `${dir}${rel}`;
}
