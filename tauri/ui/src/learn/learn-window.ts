// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 01 — Learn window entrypoint PLACEHOLDER.
//
// This is the absolute-minimum Vite module reference target so that
// `npm run build` resolves learn.html's script src and emits
// `dist/learn.html`. The actual renderer (SVG controller mount + MIDI
// position consumer + ARIA + tutor highlight surface) lands in:
//   - Plan 02 (test stubs first under TDD)
//   - Plan 05 (Vite/TS webview entry — the real renderer)
//
// Plan 01's job is to land the IPC contract + shell scaffolding (5
// shared files). This stub is the seventh file added under Rule 3
// (auto-fix blocking issue) because Vite does NOT tolerate a dangling
// script reference in a multi-page input HTML entry — the plan assumed
// otherwise. Without this stub, `npm run build` fails to resolve
// `/src/learn/learn-window.ts` and aborts before emitting dist/learn.html.
//
// Plan 05 will REPLACE this file with the real Learn renderer module.
// Until then, mounting the Learn window will produce a visible
// "Learn module not yet wired (Plan 05)" banner so a curious dev sees
// the seam rather than a silent blank window.

const LEARN_ROOT_ID = "learn-root";
const PLAN_05_NOTICE =
  "Learn module not yet wired (Plan 05 / RENDER-03/05/06 land here).";

function mountPlaceholderNotice(): void {
  const root = document.getElementById(LEARN_ROOT_ID);
  if (!root) {
    // Vite ensures the document is parsed before the module runs, so a
    // missing root means learn.html drifted away from learn-window.ts.
    console.warn(`[learn] missing #${LEARN_ROOT_ID} root`);
    return;
  }
  // Minimal placeholder content. Plan 05 wipes this and mounts the
  // real renderer (controller SVG + 30 Hz MIDI mirror consumer).
  root.textContent = PLAN_05_NOTICE;
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountPlaceholderNotice, {
      once: true,
    });
  } else {
    mountPlaceholderNotice();
  }
}

export {};
