// SPDX-License-Identifier: Apache-2.0
/**
 * @vitest-environment jsdom
 */
/* Vibe Engine — BUILD (set-prep co-host) mode vitest spec.
 *
 * Covers the seams the build surface adds, all without a Tauri runtime:
 *   1. state-machine: the "build" mode label / run-label / echo widening +
 *      setBrief / setCurve immutability (pure).
 *   2. api.ts dev-fallback: libraryBuildSet resolves the real DEV_BUILD sample
 *      (exported set) when invoke() is unavailable — never throws, never masks.
 *   3. a jsdom render path that drives the REAL index.ts renderBuildSet (via
 *      mountLibrary → runBuildSet): the numbered set, the rationale, the export
 *      receipt (shown only when export_path is present), the curve-picker
 *      selection, and the honest empty state (no key → max_iters, no rows).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DEV_FALLBACK, libraryBuildSet } from "./api.js";
import type { BuildSetResult } from "./api.js";
import {
  echoText,
  fieldLabel,
  initialLibraryState,
  runLabel,
  setBrief,
  setCurve,
  setMode,
} from "./state-machine.js";

describe("build — state machine", () => {
  it("seeds an initial brief + curve", () => {
    expect(initialLibraryState.brief.length).toBeGreaterThan(10);
    expect(initialLibraryState.curve).toBe("peak_time");
  });

  it("maps the build mode to its field + run labels", () => {
    expect(fieldLabel("build")).toBe("Build a Set");
    expect(runLabel("build")).toBe("▸ Build a Set");
  });

  it("echoes the brief in build mode (not the query/seed/theme)", () => {
    const s = setMode(initialLibraryState, "build");
    expect(echoText(s)).toBe(s.brief);
  });

  it("setBrief is immutable + touches only brief", () => {
    const s = initialLibraryState;
    const next = setBrief(s, "festival mainstage, anthemic");
    expect(next).not.toBe(s);
    expect(next.brief).toBe("festival mainstage, anthemic");
    expect(s.brief).toBe(initialLibraryState.brief);
    expect(next.curve).toBe(s.curve);
  });

  it("setCurve is immutable + touches only curve", () => {
    const s = initialLibraryState;
    const next = setCurve(s, "after_hours");
    expect(next).not.toBe(s);
    expect(next.curve).toBe("after_hours");
    expect(s.curve).toBe("peak_time");
    expect(next.brief).toBe(s.brief);
  });
});

describe("build — api dev fallback (no Tauri bridge)", () => {
  it("libraryBuildSet returns the DEV_BUILD exported set (6 tracks, exported)", async () => {
    const r = await libraryBuildSet("anything", "peak_time");
    expect(r.count).toBe(6);
    expect(r.tracks).toHaveLength(6);
    expect(r.stop_reason).toBe("exported");
    expect(r.export_path).toBeTruthy();
    expect(r.export_path).toMatch(/\.xml$/);
    expect(r.rationale.length).toBeGreaterThan(20);
    // honest meta — `track <id>` form (no fabricated human title/artist).
    expect(r.tracks[0]?.meta).toMatch(/^track /);
  });

  it("DEV_FALLBACK exposes the build sample with an export path", () => {
    expect(DEV_FALLBACK.build.tracks).toHaveLength(6);
    expect(DEV_FALLBACK.build.export_path).toMatch(/\.xml$/);
  });
});

// ── Real renderBuildSet path (via mountLibrary) ──────────────────────────────
// renderBuildSet is module-private in index.ts, so we exercise it through its
// only public entry — mountLibrary → run() → runBuildSet() → renderBuildSet().
// We mock ./api.js so libraryBuildSet returns a controlled payload; the other
// api fns are stubbed inert so the search auto-run on mount is a no-op.

const buildMock = vi.fn<(brief: string, curve: string) => Promise<BuildSetResult>>();

function doMockApi(): void {
  vi.doMock("./api.js", () => ({
    libraryBuildSet: (brief: string, curve: string) => buildMock(brief, curve),
    // inert stubs — mountLibrary auto-runs librarySearch + libraryStats on boot.
    librarySearch: vi.fn(async () => ({ results: [], centered: true, corpus_size: 0 })),
    librarySimilar: vi.fn(async () => ({ results: [], centered: true, corpus_size: 0 })),
    libraryCurate: vi.fn(async () => ({
      name: "x",
      rationale: "",
      stop_reason: "created",
      tracks: [],
      count: 0,
    })),
    libraryStats: vi.fn(async () => ({ indexed: 0, backend: "sqlite-vec", spent_eur: 0, failed: 0 })),
    libraryEmbedFolder: vi.fn(async () => false),
    onEmbedProgress: vi.fn(async () => () => {}),
    onEmbedDone: vi.fn(async () => () => {}),
    DEV_FALLBACK: { embedLog: [] },
  }));
}

/** Full library.html DOM skeleton (the ids/attrs index.ts queries for build). */
function mountSkeleton(): void {
  document.body.dataset.mode = "search";
  document.body.innerHTML = `
    <div class="vmx-lib-modeswitch">
      <button data-mode="search" aria-selected="true">Search</button>
      <button data-mode="similar" aria-selected="false">Similar</button>
      <button data-mode="curate" aria-selected="false">Curate</button>
      <button data-mode="build" aria-selected="false">Build</button>
      <button data-mode="ingest" aria-selected="false">Ingest</button>
    </div>
    <span id="vmx-lib-qlabel"></span>
    <input id="vmx-lib-q" />
    <input id="vmx-lib-folder" value="~/Music" />
    <input id="vmx-lib-theme" />
    <textarea id="vmx-lib-brief"></textarea>
    <div class="vmx-lib-curve">
      <button class="vmx-lib-curveseg" data-curve="opener" aria-pressed="false">Opener</button>
      <button class="vmx-lib-curveseg" data-curve="peak_time" aria-pressed="true">Peak time</button>
      <button class="vmx-lib-curveseg" data-curve="after_hours" aria-pressed="false">After hours</button>
      <button class="vmx-lib-curveseg" data-curve="festival" aria-pressed="false">Festival</button>
    </div>
    <span id="vmx-lib-seed-name"></span>
    <button id="vmx-lib-runbtn"></button>
    <span id="vmx-lib-echo"></span>
    <div id="vmx-lib-stat-indexed"></div>
    <div id="vmx-lib-stat-backend"></div>
    <div id="vmx-lib-stat-spent"></div>
    <div id="vmx-lib-stat-failed"></div>
    <p id="vmx-lib-rationale-body"></p>
    <div id="vmx-lib-rationale-meta"></div>
    <div id="vmx-lib-export" style="display: none">
      <div id="vmx-lib-export-path"></div>
    </div>
    <div id="vmx-lib-results"></div>
    <span id="vmx-lib-rcount"></span>
    <div id="vmx-lib-prog-n"></div>
    <div id="vmx-lib-prog-cost"></div>
    <i id="vmx-lib-progress-fill"></i>
    <div id="vmx-lib-loglist"></div>
    <span id="vmx-lib-scope-state"></span>
    <svg id="vmx-lib-scope"></svg>`;
}

/** Boot the real window, switch to build mode, optionally click a curve seg,
 *  then trigger a build run. Returns once the render has settled. */
async function runRealBuild(
  payload: BuildSetResult,
  clickCurve?: string,
): Promise<void> {
  buildMock.mockResolvedValue(payload);
  vi.resetModules();
  doMockApi();
  const { mountLibrary } = await import("./index.js");
  mountSkeleton();
  mountLibrary();
  await Promise.resolve();
  await Promise.resolve();
  const buildBtn = document.querySelector<HTMLElement>('button[data-mode="build"]');
  buildBtn?.click();
  // Switching INTO build auto-runs once; let it settle so `busy` clears before
  // the explicit run below (a click while busy is a no-op by design).
  for (let i = 0; i < 6; i++) await Promise.resolve();
  if (clickCurve) {
    document
      .querySelector<HTMLElement>(`[data-curve="${clickCurve}"]`)
      ?.click();
  }
  (document.getElementById("vmx-lib-runbtn") as HTMLButtonElement).click();
  for (let i = 0; i < 6; i++) await Promise.resolve();
}

describe("build — real renderBuildSet path (jsdom, via mountLibrary)", () => {
  beforeEach(() => {
    buildMock.mockReset();
    vi.resetModules();
    document.body.innerHTML = "";
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("renders the numbered set, rationale + export receipt (real renderBuildSet)", async () => {
    await runRealBuild(DEV_FALLBACK.build);
    const rows = document.querySelectorAll(".vmx-lib-row");
    expect(rows).toHaveLength(6);
    expect(rows[0]?.querySelector(".rank")?.textContent).toBe("01");
    expect(rows[0]?.classList.contains("top")).toBe(true);
    // built rows carry NO score number (ordered by the agent's arc).
    expect(rows[0]?.querySelector(".num")).toBeNull();
    expect(document.getElementById("vmx-lib-rationale-body")?.textContent).toContain(
      "peak-time",
    );
    // export receipt is shown + carries the path.
    const exportEl = document.getElementById("vmx-lib-export") as HTMLElement;
    expect(exportEl.style.display).not.toBe("none");
    expect(document.getElementById("vmx-lib-export-path")?.textContent).toMatch(
      /\.xml$/,
    );
    expect(document.getElementById("vmx-lib-rcount")?.textContent).toBe("6 in set");
  });

  it("selecting a curve segment updates the picker pressed state", async () => {
    await runRealBuild(DEV_FALLBACK.build, "after_hours");
    const pressed = Array.from(
      document.querySelectorAll<HTMLElement>("[data-curve]"),
    ).filter((s) => s.getAttribute("aria-pressed") === "true");
    expect(pressed).toHaveLength(1);
    expect(pressed[0]?.dataset.curve).toBe("after_hours");
    // and the LAST run (after the curve was picked) passed the chosen curve.
    // (Switching INTO build mode auto-runs once with the default curve first;
    // the explicit run-button click after the pick is the call we assert.)
    expect(buildMock).toHaveBeenLastCalledWith(expect.any(String), "after_hours");
  });

  it("hides the export receipt + shows the empty branch on a no-key run (max_iters)", async () => {
    const noKey: BuildSetResult = {
      name: "no key",
      stop_reason: "max_iters",
      rationale: "",
      count: 0,
      tracks: [],
      export_path: null,
    };
    await runRealBuild(noKey);
    const results = document.getElementById("vmx-lib-results") as HTMLElement;
    const emptyEl = results.querySelector(".vmx-lib-empty");
    expect(emptyEl).not.toBeNull();
    expect(emptyEl?.textContent).toContain("max_iters");
    // no export claim when nothing was written (anti-slop).
    const exportEl = document.getElementById("vmx-lib-export") as HTMLElement;
    expect(exportEl.style.display).toBe("none");
    expect(document.querySelectorAll(".vmx-lib-row")).toHaveLength(0);
    expect(document.getElementById("vmx-lib-rcount")?.textContent).toBe("0 in set");
  });

  it("escapes a hostile rationale/title — no raw HTML injection (real esc())", async () => {
    const hostile: BuildSetResult = {
      name: "xss",
      stop_reason: "exported",
      rationale: "<b>x</b>",
      count: 1,
      export_path: "~/x.xml",
      tracks: [
        { track_id: "evil", title: "<img src=x onerror=alert(1)>", meta: "a & b" },
      ],
    };
    await runRealBuild(hostile);
    const results = document.getElementById("vmx-lib-results") as HTMLElement;
    expect(results.querySelector("img")).toBeNull();
    expect(results.innerHTML).toContain("&lt;img");
    expect(results.innerHTML).not.toContain("<img src=x");
  });
});
