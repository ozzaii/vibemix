/* Phase 11 Wave 2 — Vite config for the Tauri webview.
 *
 * Minimal config. Wave 3 lifts the UI-SPEC tokens and wires the wizard;
 * Wave 2 just needs `vite build` to emit `dist/index.html` and the crash
 * banner module so Tauri can mount the webview.
 *
 * `clearScreen: false` keeps Tauri's own dev output readable when both
 * `vite` and `cargo tauri dev` run in the same terminal.
 *
 * `envPrefix` lets Vite expose `VITE_*` and `TAURI_*` env vars to the
 * webview (Tauri injects `TAURI_PLATFORM`, `TAURI_ARCH`, etc. at dev time).
 *
 * Phase 13 Plan 02 — Multi-page input:
 * The Tauri app now has TWO windows ("main" → index.html, "mascot" →
 * mascot.html). Rollup needs an explicit entry list with the second
 * HTML page so `vite build` emits both to `dist/`. Without this, vite
 * would only emit `dist/index.html` and the mascot window would 404
 * on `mascot.html` at runtime.
 *
 * Phase 13 Plan 04 — Three.js renderer asset wiring:
 *   - assetsInclude: star-star/star-dot-glb so rollup leaves the asset
 *     bytes alone (we serve them as static files, not as imported modules).
 *   - viteStaticCopy:
 *       1. Mascot bundle (assets/mascot/star-star) → both dev-served and
 *          emitted to dist/assets/mascot/star-star. Plan 13-01 committed
 *          the compressed bundle at tauri/ui/assets/mascot/; the
 *          renderer fetches via /assets/mascot/manifest.json.
 *       2. Three.js Draco WASM decoder (node_modules/three/examples/
 *          jsm/libs/draco/*) -> /draco/. The renderer constructs a
 *          DRACOLoader with setDecoderPath("/draco/"); the character
 *          GLB is Draco-compressed (Plan 13-01), so this MUST resolve
 *          in both dev and prod.
 */

import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import { viteStaticCopy } from "vite-plugin-static-copy";

const projectRoot = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    fs: {
      // Allow Vite's dev server to read from the repo's tauri/ui/assets
      // directory (sits next to the project root, not under public/).
      allow: [projectRoot],
    },
  },
  envPrefix: ["VITE_", "TAURI_"],
  // GLBs are binary assets we fetch ourselves; do not try to inline / parse.
  assetsInclude: ["**/*.glb"],
  plugins: [
    viteStaticCopy({
      targets: [
        // Mascot bundle — manifest.json + character.glb + animations/*.glb.
        // Plan 13-01 committed under tauri/ui/assets/mascot/; vite serves
        // the dev path via the static-copy plugin's dev middleware and
        // emits the same tree into dist/assets/mascot/ on build.
        //
        // Glob trailing slash + dest=assets keeps the "mascot/" folder
        // structure intact (character.glb + manifest.json + animations/
        // subdir preserved). Plain "assets/mascot/star-star" with
        // dest=assets/mascot has a known flatten bug in vite-plugin-static
        // -copy 2.x that double-emits files at the root.
        {
          src: resolve(projectRoot, "assets/mascot") + "/",
          dest: "assets",
        },
        // Three.js DRACO WASM decoder. Plan 13-04 renderer points
        // DRACOLoader at /draco/; the character GLB is Draco-compressed.
        {
          src: resolve(
            projectRoot,
            "node_modules/three/examples/jsm/libs/draco/*",
          ),
          dest: "draco",
        },
      ],
    }),
  ],
  build: {
    target: "es2022",
    minify: "esbuild",
    sourcemap: true,
    rollupOptions: {
      input: {
        main: resolve(projectRoot, "index.html"),
        // Phase 13 Plan 02 — second webview entry for the mascot overlay window.
        mascot: resolve(projectRoot, "mascot.html"),
        // Phase 24 Plan 02 — third webview entry for the per-element
        // overlay-highlight window. Opened on-demand by
        // tauri/src-tauri/src/overlay.rs::show_overlay_highlight; the
        // ring renders for duration_ms then the Rust task closes it.
        overlay: resolve(projectRoot, "overlay.html"),
      },
    },
  },
});
