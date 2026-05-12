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
 */

import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const projectRoot = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
  },
  envPrefix: ["VITE_", "TAURI_"],
  build: {
    target: "es2022",
    minify: "esbuild",
    sourcemap: true,
    rollupOptions: {
      input: {
        main: resolve(projectRoot, "index.html"),
        // Phase 13 Plan 02 — second webview entry for the mascot overlay window.
        mascot: resolve(projectRoot, "mascot.html"),
      },
    },
  },
});
