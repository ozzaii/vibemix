#!/usr/bin/env node
/* Phase 13-01 — Mascot Asset Bundle Pipeline.
 *
 * Compresses + strips the 21 Meshy "Neon Rebel" GLBs (1 character + 20 animations)
 * from MESHY_SRC_DIR (default `/Users/ozai/Downloads/Meshy_AI_Neon_Rebel_biped/`)
 * into `tauri/ui/assets/mascot/` under a 25 MiB total cap.
 *
 * Pipeline per asset:
 *   character.glb  → gltf-pipeline Draco compress (keeps mesh + texture)
 *   animation*.glb → programmatic strip via @gltf-transform/core
 *                    (drops Mesh/Material/Texture/Image, detaches mesh refs
 *                     from Nodes, keeps Skin/Skeleton + Animation tracks) →
 *                    NodeIO write
 *
 * The pipeline is idempotent — gltf-pipeline is deterministic; the programmatic
 * strip writes the same byte layout every time. Re-running on already-built
 * output produces byte-identical files.
 *
 * Source files live OUTSIDE the repo (Kaan-local Downloads) and are NOT committed.
 * Maintainers run `npm run build:mascot` manually when refreshing Meshy assets;
 * CI builds use the committed `tauri/ui/assets/mascot/` tree.
 *
 * --------------------------------------------------------------------
 * LOCKED COMPRESSION FLAGS (Phase 13-01 — measured 2026-05-12):
 *   Character:  --draco.compressionLevel 10
 *               --draco.quantizePositionBits 14
 *               --draco.quantizeNormalBits 10
 *               --draco.quantizeTexcoordBits 12
 *   Animations: programmatic strip (Mesh/Material/Texture/Image removed,
 *               mesh attribute cleared from skinned Nodes, Skin + Animation
 *               kept) → written without Draco (animation buffers are small;
 *               Draco on skeleton+anim has marginal gain and adds load-time
 *               cost). Compression headroom comes from mesh+texture removal.
 *
 * Final bundle size: see tauri/ui/assets/mascot/MANIFEST.md
 * --------------------------------------------------------------------
 */

import { NodeIO } from "@gltf-transform/core";
import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const UI_ROOT = resolve(__dirname, "..");
const OUT_DIR = resolve(UI_ROOT, "assets", "mascot");
const OUT_ANIM_DIR = resolve(OUT_DIR, "animations");

const SRC_DIR = process.env.MESHY_SRC_DIR
  || "/Users/ozai/Downloads/Meshy_AI_Neon_Rebel_biped";

const BUNDLE_BYTES_TARGET = 26214400; // 25 MiB hard cap

const CHARACTER_SRC = "Meshy_AI_Neon_Rebel_biped_Character_output.glb";

// Source-file → output-snake_case → clip metadata.
// Mirrors the manifest schema in 13-01-PLAN.md <interfaces>.
const ANIMATIONS = [
  { src: "Animation_Sleep_Normally",        out: "sleep_normally.glb",   clip: "Sleep_Normally",        states: ["idle_breathe_slow", "sleep"] },
  { src: "Animation_Indoor_Swing",          out: "indoor_swing.glb",     clip: "Indoor_Swing",          states: ["idle_bop_to_beat_mellow", "talk_loop_calm"] },
  { src: "Animation_Bass_Beats",            out: "bass_beats.glb",       clip: "Bass_Beats",            states: ["idle_bop_to_beat_energetic", "talk_loop_energetic"] },
  { src: "Animation_FunnyDancing_01",       out: "funny_dancing_01.glb", clip: "FunnyDancing_01",       states: ["dance_a"] },
  { src: "Animation_FunnyDancing_03",       out: "funny_dancing_03.glb", clip: "FunnyDancing_03",       states: ["dance_alt2"] },
  { src: "Animation_OMG_Groove",            out: "omg_groove.glb",       clip: "OMG_Groove",            states: ["dance_b"] },
  { src: "Animation_All_Night_Dance",       out: "all_night_dance.glb",  clip: "All_Night_Dance",       states: ["dance_hard"] },
  { src: "Animation_Hip_Hop_Dance_3",       out: "hip_hop_dance_3.glb",  clip: "Hip_Hop_Dance_3",       states: ["dance_alt"] },
  { src: "Animation_Magic_Genie",           out: "magic_genie.glb",      clip: "Magic_Genie",           states: ["talk_loop"] },
  { src: "Animation_Cheer_with_Both_Hands", out: "cheer_both_hands.glb", clip: "Cheer_with_Both_Hands", states: ["react_yes", "celebrate"] },
  { src: "Animation_Shrug",                 out: "shrug.glb",            clip: "Shrug",                 states: ["react_no"] },
  { src: "Animation_Not_Your_Mom",          out: "not_your_mom.glb",     clip: "Not_Your_Mom",          states: ["react_no_alt"] },
  { src: "Animation_Alert_Quick_Turn_Right",out: "alert_quick_turn.glb", clip: "Alert_Quick_Turn_Right",states: ["react_surprised"] },
  { src: "Animation_Handbag_Walk",          out: "handbag_walk.glb",     clip: "Handbag_Walk",          states: ["point_explain"] },
  { src: "Animation_Big_Wave_Hello",        out: "big_wave_hello.glb",   clip: "Big_Wave_Hello",        states: ["gesture_wide"] },
  { src: "Animation_Wave_for_Help_4",       out: "wave_for_help.glb",    clip: "Wave_for_Help_4",       states: ["gesture_wide_alt"] },
  { src: "Animation_Fast_Lightning",        out: "fast_lightning.glb",   clip: "Fast_Lightning",        states: ["react_drop"] },
  { src: "Animation_Angry_Ground_Stomp",    out: "angry_stomp.glb",      clip: "Angry_Ground_Stomp",    states: ["react_glitch"] },
  { src: "Animation_Walking",               out: "walking.glb",          clip: "Walking",               states: ["locomotion_walk"] },
  { src: "Animation_Running",               out: "running.glb",          clip: "Running",               states: ["locomotion_run"] },
];

const SRC_PREFIX = "Meshy_AI_Neon_Rebel_biped_";
const SRC_SUFFIX = "_withSkin.glb";

// Character compression — Draco knobs locked.
const DRACO_FLAGS = {
  compressionLevel: 10,
  quantizePositionBits: 14,
  quantizeNormalBits: 10,
  quantizeTexcoordBits: 12,
};

function log(line) {
  process.stdout.write(`[build-mascot] ${line}\n`);
}

function ensureSrcDir() {
  if (!existsSync(SRC_DIR)) {
    process.stderr.write(
      `[build-mascot] FATAL: Meshy source dir not found at: ${SRC_DIR}\n` +
      `[build-mascot]   set MESHY_SRC_DIR=/path/to/Meshy_AI_Neon_Rebel_biped before re-running.\n` +
      `[build-mascot]   the directory must contain 1 character GLB + 20 *_withSkin.glb animations.\n`,
    );
    process.exit(1);
  }
  const characterPath = join(SRC_DIR, CHARACTER_SRC);
  if (!existsSync(characterPath)) {
    process.stderr.write(
      `[build-mascot] FATAL: missing character GLB: ${characterPath}\n`,
    );
    process.exit(1);
  }
  for (const a of ANIMATIONS) {
    const srcName = `${SRC_PREFIX}${a.src}${SRC_SUFFIX}`;
    if (!existsSync(join(SRC_DIR, srcName))) {
      process.stderr.write(
        `[build-mascot] FATAL: missing animation GLB: ${srcName}\n`,
      );
      process.exit(1);
    }
  }
}

function resetOutputDirs() {
  // Wipe to keep idempotency guaranteed — same inputs + tools = same outputs.
  if (existsSync(OUT_DIR)) rmSync(OUT_DIR, { recursive: true, force: true });
  mkdirSync(OUT_ANIM_DIR, { recursive: true });
}

function resolveBin(name) {
  // Resolve CLI from this project's node_modules first; fallback to npx.
  const direct = resolve(UI_ROOT, "node_modules", ".bin", name);
  if (existsSync(direct)) return { bin: direct, isNpx: false };
  return { bin: "npx", isNpx: true, args: ["--yes", name] };
}

function runCli(name, args) {
  const r = resolveBin(name);
  const argv = r.isNpx ? [...r.args, ...args] : args;
  const result = spawnSync(r.bin, argv, { stdio: ["ignore", "pipe", "pipe"] });
  if (result.status !== 0) {
    process.stderr.write(`[build-mascot] ${name} failed (exit ${result.status}):\n`);
    process.stderr.write(result.stderr?.toString() ?? "");
    process.stderr.write(result.stdout?.toString() ?? "");
    process.exit(1);
  }
  return result;
}

function compressCharacter() {
  const src = join(SRC_DIR, CHARACTER_SRC);
  const dst = join(OUT_DIR, "character.glb");
  log(`character → ${dst}`);
  runCli("gltf-pipeline", [
    "-i", src,
    "-o", dst,
    "-d",
    `--draco.compressionLevel=${DRACO_FLAGS.compressionLevel}`,
    `--draco.quantizePositionBits=${DRACO_FLAGS.quantizePositionBits}`,
    `--draco.quantizeNormalBits=${DRACO_FLAGS.quantizeNormalBits}`,
    `--draco.quantizeTexcoordBits=${DRACO_FLAGS.quantizeTexcoordBits}`,
  ]);
}

async function stripAnimationGLB(srcPath, dstPath, clipName) {
  // Programmatic strip via @gltf-transform/core:
  //   - clear each Node's mesh reference (so the scene no longer renders meshes)
  //   - delete every Mesh, Material, Texture, TextureInfo
  //   - keep Skin (skeleton inverseBindMatrices, joint list) + Animation channels
  //   - run dispose() chain — accessors/buffers/images orphaned by removal go away
  //
  // Output: a single GLB that carries only the armature node graph + animation
  // tracks. Three.js loads it via GLTFLoader and we attach the AnimationClip
  // to the character mesh's skeleton via SkeletonUtils.retargetClip (Plan 13-04).
  const io = new NodeIO();
  const doc = await io.read(srcPath);
  const root = doc.getRoot();

  // 1. Detach mesh from every node.
  for (const node of root.listNodes()) {
    if (node.getMesh()) node.setMesh(null);
  }

  // 2. Remove all meshes (and their primitives + accessors + indices).
  for (const mesh of root.listMeshes()) {
    for (const prim of mesh.listPrimitives()) prim.dispose();
    mesh.dispose();
  }

  // 3. Remove all materials.
  for (const mat of root.listMaterials()) mat.dispose();

  // 4. Remove all textures.
  for (const tex of root.listTextures()) tex.dispose();

  // 5. Reduce animation list to the single canonical clip.
  //    Meshy animation GLBs usually carry one Animation already, but if multiple
  //    are exported (e.g., an "Idle" + the named clip), keep only the longest.
  const anims = root.listAnimations();
  if (anims.length === 0) {
    throw new Error(`no Animation tracks found in ${srcPath}`);
  }
  if (anims.length > 1) {
    // Find by name first; fall back to longest by sum of input accessor max.
    let chosen = anims.find((a) => a.getName() === clipName);
    if (!chosen) {
      let bestLen = -1;
      for (const a of anims) {
        const len = a.listChannels().reduce((acc, c) => {
          const s = c.getSampler();
          const inp = s ? s.getInput() : null;
          return acc + (inp ? inp.getCount() : 0);
        }, 0);
        if (len > bestLen) { bestLen = len; chosen = a; }
      }
    }
    for (const a of anims) {
      if (a !== chosen) a.dispose();
    }
    chosen.setName(clipName);
  } else {
    anims[0].setName(clipName);
  }

  // 6. Strip any unused accessors / buffer views / images / extensions.
  //    Conservative — only drops what nothing references anymore.
  const orphanCleanup = (list, label) => {
    for (const item of list) {
      const links = item.listParents().filter((p) => p.propertyType !== "Root");
      if (links.length === 0) {
        item.dispose();
      }
    }
    log(`  pruned orphans (${label}): ${list.length}`);
  };
  orphanCleanup(root.listAccessors(), "accessors");

  // 7. Write the stripped GLB.
  await io.write(dstPath, doc);
}

async function processAnimation(anim) {
  const src = join(SRC_DIR, `${SRC_PREFIX}${anim.src}${SRC_SUFFIX}`);
  const dst = join(OUT_ANIM_DIR, anim.out);
  log(`anim ${anim.clip} → ${dst}`);
  await stripAnimationGLB(src, dst, anim.clip);
}

function writeManifest() {
  const manifest = {
    character: "character.glb",
    animations: ANIMATIONS.map((a) => ({
      file: `animations/${a.out}`,
      clip: a.clip,
      states: a.states,
    })),
    bundle_bytes_target: BUNDLE_BYTES_TARGET,
    source_origin: "Meshy AI — Neon Rebel biped",
    license: "see LICENSE-3RD-PARTY.md",
  };
  const path = join(OUT_DIR, "manifest.json");
  writeFileSync(path, JSON.stringify(manifest, null, 2) + "\n");
  log(`manifest → ${path}`);
}

function bundleTotalBytes() {
  let total = 0;
  function walk(dir) {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const p = join(dir, entry.name);
      if (entry.isDirectory()) walk(p);
      else total += statSync(p).size;
    }
  }
  walk(OUT_DIR);
  return total;
}

function perFileSizesDescending() {
  const rows = [];
  function walk(dir) {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const p = join(dir, entry.name);
      if (entry.isDirectory()) walk(p);
      else rows.push({ path: p.replace(OUT_DIR + "/", ""), bytes: statSync(p).size });
    }
  }
  walk(OUT_DIR);
  rows.sort((a, b) => b.bytes - a.bytes);
  return rows;
}

function enforceBundleCap() {
  const total = bundleTotalBytes();
  log(`total bundle bytes: ${total} / ${BUNDLE_BYTES_TARGET} (${(total / BUNDLE_BYTES_TARGET * 100).toFixed(1)}%)`);
  if (total > BUNDLE_BYTES_TARGET) {
    process.stderr.write(`[build-mascot] FATAL: bundle exceeds ${BUNDLE_BYTES_TARGET} bytes\n`);
    for (const r of perFileSizesDescending()) {
      process.stderr.write(`  ${r.bytes.toString().padStart(10)}  ${r.path}\n`);
    }
    process.stderr.write(
      "[build-mascot] hint: consider --draco.quantizePositionBits 12 / --quantizeNormalBits 8, " +
      "or strip more aggressively in the animation pipeline.\n",
    );
    process.exit(1);
  }
}

async function main() {
  log(`source: ${SRC_DIR}`);
  log(`out:    ${OUT_DIR}`);
  ensureSrcDir();
  resetOutputDirs();
  compressCharacter();
  for (const anim of ANIMATIONS) {
    await processAnimation(anim);
  }
  writeManifest();
  enforceBundleCap();
  log("done.");
}

main().catch((err) => {
  process.stderr.write(`[build-mascot] FATAL: ${err.stack || err.message || err}\n`);
  process.exit(1);
});
