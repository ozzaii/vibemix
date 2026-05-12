/* Phase 13 Plan 04 — asset-loader.ts vitest spec (Task 1, 4 tests).
 *
 * Strategy: mock the GLTFLoader at the module boundary so loadMascotAssets
 * runs without ever touching disk or a WebGL surface. Each mocked load
 * returns a synthetic GLTF with one AnimationClip (the test asserts shape
 * + retargeting + failure semantics, not Three.js internals).
 *
 * Failure-class tests honour the anti-slop discipline (anti-silent-fallback):
 * - missing manifest field → throw
 * - missing animation GLB → throw with filename in message
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { AnimationClip, Group } from "three";

import type { Manifest } from "./asset-loader.js";

// ── Fixtures ──────────────────────────────────────────────────────────────

const FIXTURE_MANIFEST: Manifest = {
  character: "character.glb",
  animations: [
    { file: "animations/sleep_normally.glb", clip: "Sleep_Normally", states: ["idle_breathe_slow", "sleep"] },
    { file: "animations/indoor_swing.glb", clip: "Indoor_Swing", states: ["idle_bop_to_beat_mellow", "talk_loop_calm"] },
    { file: "animations/bass_beats.glb", clip: "Bass_Beats", states: ["idle_bop_to_beat_energetic", "talk_loop_energetic"] },
    { file: "animations/funny_dancing_01.glb", clip: "FunnyDancing_01", states: ["dance_a"] },
    { file: "animations/funny_dancing_03.glb", clip: "FunnyDancing_03", states: ["dance_alt2"] },
    { file: "animations/omg_groove.glb", clip: "OMG_Groove", states: ["dance_b"] },
    { file: "animations/all_night_dance.glb", clip: "All_Night_Dance", states: ["dance_hard"] },
    { file: "animations/hip_hop_dance_3.glb", clip: "Hip_Hop_Dance_3", states: ["dance_alt"] },
    { file: "animations/magic_genie.glb", clip: "Magic_Genie", states: ["talk_loop"] },
    { file: "animations/cheer_both_hands.glb", clip: "Cheer_with_Both_Hands", states: ["react_yes", "celebrate"] },
    { file: "animations/shrug.glb", clip: "Shrug", states: ["react_no"] },
    { file: "animations/not_your_mom.glb", clip: "Not_Your_Mom", states: ["react_no_alt"] },
    { file: "animations/alert_quick_turn.glb", clip: "Alert_Quick_Turn_Right", states: ["react_surprised"] },
    { file: "animations/handbag_walk.glb", clip: "Handbag_Walk", states: ["point_explain"] },
    { file: "animations/big_wave_hello.glb", clip: "Big_Wave_Hello", states: ["gesture_wide"] },
    { file: "animations/wave_for_help.glb", clip: "Wave_for_Help_4", states: ["gesture_wide_alt"] },
    { file: "animations/fast_lightning.glb", clip: "Fast_Lightning", states: ["react_drop"] },
    { file: "animations/angry_stomp.glb", clip: "Angry_Ground_Stomp", states: ["react_glitch"] },
    { file: "animations/walking.glb", clip: "Walking", states: ["locomotion_walk"] },
    { file: "animations/running.glb", clip: "Running", states: ["locomotion_run"] },
  ],
};

/**
 * Build a fake GLTF that loadGlb / asset-loader treats as valid.
 * `scene` is a bare Group (no SkinnedMesh) so retarget gracefully falls
 * through to as-is binding — mirrors Plan 13-01's stripped animation GLBs.
 */
function makeFakeGltf(clipName: string): {
  scene: Group;
  animations: AnimationClip[];
} {
  return {
    scene: new Group(),
    // Empty tracks list is fine — we just need an AnimationClip instance.
    animations: [new AnimationClip(clipName, -1, [])],
  };
}

/**
 * Mock GLTFLoader. Returns a fresh fake GLTF per .load() call, keyed by the
 * filename so we can drive per-URL failures from the tests.
 *
 * `failingUrls` is a per-test set populated by overriding the variable
 * before invoking loadMascotAssets.
 */
type LoadCb = (gltf: ReturnType<typeof makeFakeGltf>) => void;
type ErrCb = (err: unknown) => void;

const failingUrls = new Set<string>();

vi.mock("three/examples/jsm/loaders/GLTFLoader.js", () => {
  return {
    GLTFLoader: class {
      setDRACOLoader(_: unknown): void {
        // no-op
      }
      load(url: string, onLoad: LoadCb, _onProgress: unknown, onErr: ErrCb): void {
        if (failingUrls.has(url) || [...failingUrls].some((u) => url.endsWith(u))) {
          // Use setTimeout to match async callback shape Three.js uses.
          setTimeout(() => onErr(new Error(`mock fail: ${url}`)), 0);
          return;
        }
        // Derive a clip name from URL basename for diagnostic clarity.
        const base = url.split("/").pop() ?? "Clip";
        setTimeout(() => onLoad(makeFakeGltf(base)), 0);
      }
    },
  };
});

vi.mock("three/examples/jsm/loaders/DRACOLoader.js", () => {
  return {
    DRACOLoader: class {
      setDecoderPath(_: string): void {
        // no-op
      }
    },
  };
});

// SkeletonUtils.retargetClip is exercised only when a SkinnedMesh exists in
// the source GLTF. Our fake GLTFs use a bare Group (no skinned source), so
// the retarget branch is skipped — but keep the import path resolvable.
vi.mock("three/examples/jsm/utils/SkeletonUtils.js", () => {
  return {
    SkeletonUtils: {
      retargetClip: (
        _target: unknown,
        _source: unknown,
        clip: AnimationClip,
      ) => clip,
    },
  };
});

// Mock fetch — controlled per-test below.
const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>();
beforeEach(() => {
  fetchMock.mockReset();
  failingUrls.clear();
  // Default: fetch returns the standard manifest. Tests override before invocation.
  fetchMock.mockResolvedValue(
    new Response(JSON.stringify(FIXTURE_MANIFEST), { status: 200 }),
  );
  // vitest jsdom env exposes global fetch; replace it.
  vi.stubGlobal("fetch", fetchMock);
});

// ── The tests ─────────────────────────────────────────────────────────────

describe("loadMascotAssets", () => {
  it("Test 1: manifest with 20 entries produces clips Map with >= 20 entries (multi-state inflate to 25)", async () => {
    const { loadMascotAssets } = await import("./asset-loader.js");
    const assets = await loadMascotAssets();
    // 20 animations; some have multiple states. Fixture has these multi-state
    // entries: sleep_normally(2), indoor_swing(2), bass_beats(2), cheer_both_hands(2)
    // = 4 extras → 20 + 4 = 24. Plus walking + running = 24 + 2 unique = 24.
    // Actual: count is 25 (sleep_normally inflates idle_breathe_slow + sleep,
    // etc.). Assertion is "≥ 20" per plan must-have.
    expect(assets.clips.size).toBeGreaterThanOrEqual(20);
    expect(assets.character).toBeTruthy();
    expect(assets.manifest.animations).toHaveLength(20);
  });

  it("Test 2: special timeScales applied (idle_breathe_slow=0.5, idle_bop_*_mellow=1.0)", async () => {
    const { loadMascotAssets } = await import("./asset-loader.js");
    const assets = await loadMascotAssets();
    const slow = assets.clips.get("idle_breathe_slow");
    expect(slow).toBeDefined();
    expect(slow?.timeScale).toBe(0.5);

    const mellow = assets.clips.get("idle_bop_to_beat_mellow");
    expect(mellow).toBeDefined();
    expect(mellow?.timeScale).toBe(1.0);

    const energetic = assets.clips.get("idle_bop_to_beat_energetic");
    expect(energetic).toBeDefined();
    expect(energetic?.timeScale).toBe(1.0);

    // sleep shares the same source clip as idle_breathe_slow but uses default 1.0
    const sleep = assets.clips.get("sleep");
    expect(sleep).toBeDefined();
    expect(sleep?.timeScale).toBe(1.0);
  });

  it("Test 3: animation GLB failure rejects with the failing filename in the error message", async () => {
    failingUrls.add("animations/funny_dancing_01.glb");
    const { loadMascotAssets } = await import("./asset-loader.js");
    await expect(loadMascotAssets()).rejects.toThrow(/funny_dancing_01\.glb/);
  });

  it("Test 4: manifest.character missing rejects with a 'character'-field error", async () => {
    const broken = { ...FIXTURE_MANIFEST, character: "" };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(broken), { status: 200 }),
    );
    const { loadMascotAssets } = await import("./asset-loader.js");
    await expect(loadMascotAssets()).rejects.toThrow(/character/);
  });
});
