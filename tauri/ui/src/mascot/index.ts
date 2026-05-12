/*
 * Phase 13 Plan 02 — mascot overlay placeholder entry.
 *
 * The mascot window (`label = "mascot"`, built by
 * `mascot_window::create_mascot_window`) loads this module via
 * mascot.html. Plan 13-04 will replace this stub with a Three.js
 * AnimationMixer pipeline + GLB character; Plan 13-06 will wire the
 * WebSocket bus that drives state transitions.
 *
 * This file exists in Wave 1 purely so Vite's build succeeds when it
 * crawls mascot.html → /src/mascot/index.ts. Without the file, vite
 * would fail with "Could not resolve" and the second window would
 * white-screen on launch.
 *
 * On boot we:
 *   - log to confirm the second webview booted (visible in DevTools
 *     when devtools is opened against the mascot window),
 *   - paint a single transparent canvas frame so the GPU compositor
 *     surfaces the window at the right size (some platforms skip
 *     compositing a webview that has never rendered).
 */

const TAG = "[mascot]";

function paintStubFrame(): void {
  const canvas = document.getElementById("mascot-canvas") as HTMLCanvasElement | null;
  if (!canvas) {
    console.warn(`${TAG} mascot-canvas not found in DOM`);
    return;
  }
  // Match the canvas pixel buffer to its CSS size so the first GPU
  // commit happens at the right resolution. Plan 13-04 will replace
  // this with a Three.js WebGLRenderer that owns the canvas.
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.floor(rect.width * window.devicePixelRatio);
  canvas.height = Math.floor(rect.height * window.devicePixelRatio);
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
}

window.addEventListener("DOMContentLoaded", () => {
  console.log(`${TAG} stub mounted — Plan 13-04 wires Three.js`);
  paintStubFrame();
});

window.addEventListener("resize", paintStubFrame);

// Export an empty object so this file is treated as a module (and
// `import.meta` would resolve if Plan 13-04 needs it).
export {};
