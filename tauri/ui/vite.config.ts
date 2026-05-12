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
 */

import { defineConfig } from "vite";

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
  },
});
