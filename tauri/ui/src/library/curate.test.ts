// SPDX-License-Identifier: Apache-2.0
/**
 * @vitest-environment jsdom
 */
/* Vibe Engine — CURATE mode vitest spec.
 *
 * Covers the three seams the curate surface adds, all without a Tauri runtime:
 *   1. state-machine: the "curate" mode label / run-label / echo widening (pure).
 *   2. api.ts dev-fallback: libraryCurate resolves the real DEV_CURATE sample
 *      when invoke() is unavailable (vitest / plain vite) — never throws, never
 *      masks a real failure (there is none in the no-Tauri path).
 *   3. a jsdom render path that drives the REAL index.ts renderCurate (via
 *      mountLibrary → runCurate), so the production esc() XSS-escaping and the
 *      empty-tracks `vmx-lib-empty` branch are actually exercised — not a mirror.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DEV_FALLBACK, libraryCurate } from "./api.js";
import type { CurateResult } from "./api.js";
import {
  echoText,
  fieldLabel,
  initialLibraryState,
  runLabel,
  setMode,
  setTheme,
} from "./state-machine.js";

describe("curate — state machine", () => {
  it("seeds an initial theme", () => {
    expect(initialLibraryState.theme).toBe("warm sunset rooftop, dusk to dark");
  });

  it("maps the curate mode to its field + run labels", () => {
    expect(fieldLabel("curate")).toBe("Curate a set");
    expect(runLabel("curate")).toBe("▸ Curate playlist");
  });

  it("echoes the theme in curate mode (not the query/seed)", () => {
    const s = setMode(initialLibraryState, "curate");
    expect(echoText(s)).toBe(s.theme);
  });

  it("setTheme is immutable + touches only theme", () => {
    const s = initialLibraryState;
    const next = setTheme(s, "peak-time rolling");
    expect(next).not.toBe(s);
    expect(next.theme).toBe("peak-time rolling");
    expect(s.theme).toBe("warm sunset rooftop, dusk to dark");
    expect(next.query).toBe(s.query);
  });
});

describe("curate — api dev fallback (no Tauri bridge)", () => {
  it("libraryCurate returns the DEV_CURATE set (6 tracks, created, named)", async () => {
    const r = await libraryCurate("anything");
    expect(r.count).toBe(6);
    expect(r.tracks).toHaveLength(6);
    expect(r.stop_reason).toBe("created");
    expect(r.name).toBe("Dusk to Dark");
    expect(r.rationale.length).toBeGreaterThan(20);
    // honest meta — `track <id>` form when there's no separate artist.
    expect(r.tracks[0]?.meta).toMatch(/^track /);
  });

  it("DEV_FALLBACK exposes the curate sample", () => {
    expect(DEV_FALLBACK.curate.tracks).toHaveLength(6);
  });
});

// ── Real renderCurate path (via mountLibrary) ────────────────────────────────
// renderCurate is module-private in index.ts, so we exercise it through its only
// public entry — mountLibrary → run() → runCurate() → renderCurate(). We mock
// ./api.js so `libraryCurate` returns a controlled payload (including a hostile
// title for the XSS case and a zero-track payload for the empty branch); the
// other api fns are stubbed inert so mount/status work stays offline and deterministic.
// This makes the production esc() escaping + the `vmx-lib-empty` branch real
// coverage instead of an in-test mirror.

const curateMock = vi.fn<(theme: string) => Promise<CurateResult>>();

/** Install a non-hoisted mock of ./api.js for the index.ts-driven tests ONLY
 *  (the state-machine + dev-fallback describes above keep the REAL module). We
 *  pair this with vi.resetModules() so index.js re-resolves against the mock. */
function doMockApi(): void {
  vi.doMock("./api.js", () => ({
    // libraryCurate is overridden per-test via curateMock.
    libraryCurate: (theme: string) => curateMock(theme),
    // build mode is inert in these tests (mountLibrary imports it on boot).
    libraryBuildSet: vi.fn(async () => ({
      name: "x",
      rationale: "",
      stop_reason: "exported",
      tracks: [],
      count: 0,
      export_path: null,
    })),
    libraryChat: vi.fn(async () => ({
      reply: "ok",
      tool_trace: [],
      playlist: null,
      export_path: null,
      seen_track_ids: [],
      iterations: 1,
      stop_reason: "model_done",
    })),
    // inert stubs — mountLibrary does a state-dependent boot run + status refresh.
    librarySearch: vi.fn(async () => ({ results: [], centered: true, corpus_size: 0 })),
    librarySimilar: vi.fn(async () => ({ results: [], centered: true, corpus_size: 0 })),
    libraryStats: vi.fn(async () => ({ indexed: 0, backend: "sqlite-vec", spent_eur: 0, failed: 0 })),
    libraryModels: vi.fn(async () => ({
      models: [],
      required_ready: true,
      all_ready: true,
    })),
    libraryEmbedFolder: vi.fn(async () => false),
    libraryImport: vi.fn(async () => false),
    libraryImportFromAction: vi.fn(async () => false),
    libraryCancelImport: vi.fn(async () => undefined),
    onEmbedProgress: vi.fn(async () => () => {}),
    onEmbedDone: vi.fn(async () => () => {}),
    onLibraryImportProgress: vi.fn(async () => () => {}),
    onModelProgress: vi.fn(async () => () => {}),
    onLiveDeckContext: vi.fn(async () => () => {}),
    onLiveMoveContext: vi.fn(async () => () => {}),
    onViberTool: vi.fn(async () => () => {}),
    // DEV_FALLBACK is consumed by the ingest replay; keep the real embedLog shape.
    DEV_FALLBACK: { embedLog: [] },
  }));
}

/** Full library.html DOM skeleton (the ids/attrs index.ts queries). Building it
 *  here means mountLibrary wires + paints exactly as in the real window. */
function mountSkeleton(): void {
  document.body.dataset.mode = "chat";
  document.body.dataset.allowToolModes = "true";
  document.body.innerHTML = `
    <div class="vmx-lib-modeswitch">
      <button data-mode="search" aria-selected="false">Search</button>
      <button data-mode="similar" aria-selected="false">Similar</button>
      <button data-mode="curate" aria-selected="false">Curate</button>
      <button data-mode="build" aria-selected="false">Build</button>
      <button data-mode="chat" aria-selected="true">Viber</button>
      <button data-mode="ingest" aria-selected="false">Ingest</button>
    </div>
    <span id="vmx-lib-qlabel"></span>
    <input id="vmx-lib-q" />
    <input id="vmx-lib-folder" value="~/Music" />
    <input id="vmx-lib-cue-folder" value="~/Music" />
    <input id="vmx-lib-theme" />
    <textarea id="vmx-lib-brief"></textarea>
    <textarea id="vmx-lib-chat"></textarea>
    <div class="vmx-lib-curve">
      <button class="vmx-lib-curveseg" data-curve="opener" aria-pressed="false">Opener</button>
      <button class="vmx-lib-curveseg" data-curve="peak_time" aria-pressed="true">Peak time</button>
      <button class="vmx-lib-curveseg" data-curve="after_hours" aria-pressed="false">After hours</button>
      <button class="vmx-lib-curveseg" data-curve="festival" aria-pressed="false">Festival</button>
    </div>
    <button data-cue-export="rekordbox" aria-pressed="true">Rekordbox XML</button>
    <button data-cue-export="m3u8" aria-pressed="false">M3U8</button>
    <button data-cue-export="both" aria-pressed="false">Both</button>
    <button id="vmx-lib-cue-run">Export hot cues</button>
    <span id="vmx-lib-seed-name"></span>
    <button id="vmx-lib-runbtn"></button>
    <span id="vmx-lib-center-label"></span>
    <span id="vmx-lib-echo"></span>
    <div id="vmx-lib-stat-indexed"></div>
    <div id="vmx-lib-stat-backend"></div>
    <div id="vmx-lib-stat-spent"></div>
    <div id="vmx-lib-stat-failed"></div>
    <div id="vmx-lib-model-state"></div>
    <button id="vmx-lib-install-models"></button>
    <div id="vmx-lib-agent-setup" hidden><div id="vmx-lib-agent-state"></div></div>
    <p id="vmx-lib-rationale-body"></p>
    <div id="vmx-lib-rationale-meta"></div>
    <div id="vmx-lib-export" style="display: none"><div id="vmx-lib-export-path"></div></div>
    <div id="vmx-lib-results"></div>
    <div id="vmx-lib-chat-thread"></div>
    <span id="vmx-lib-rcount"></span>
    <div id="vmx-lib-prog-n"></div>
    <div id="vmx-lib-prog-cost"></div>
    <i id="vmx-lib-progress-fill"></i>
    <span id="vmx-lib-side-label"></span>
    <div id="vmx-lib-scope-wrap">
    <span id="vmx-lib-scope-state"></span>
    <div id="vmx-lib-chat-tools"></div>
    <div id="vmx-lib-chat-artifact"></div>
    <svg id="vmx-lib-scope"></svg>
    <span id="vmx-lib-scope-legend-origin"></span>
    <span id="vmx-lib-scope-legend-near"></span>
    <span id="vmx-lib-scope-legend-far"></span>
    <div id="vmx-lib-scope-note"></div>
    </div>`;
}

/** Boot the real window, switch to curate mode, and trigger a curate run.
 *  Returns once the curate render has settled (microtasks flushed). */
async function runRealCurate(payload: CurateResult): Promise<void> {
  curateMock.mockResolvedValue(payload);
  vi.resetModules();
  doMockApi();
  // Import BEFORE building the skeleton so index.ts's auto-mount guard
  // (`document.getElementById("vmx-lib-runbtn")`) finds nothing and skips — we
  // then mount exactly once, explicitly, against the freshly-built DOM.
  const { mountLibrary } = await import("./index.js");
  mountSkeleton();
  mountLibrary();
  // mountLibrary kicks its initial state-dependent run; let it settle so it doesn't race us.
  await Promise.resolve();
  await Promise.resolve();
  // switch to curate, then drive the run button (real run → runCurate → renderCurate).
  const curateBtn = document.querySelector<HTMLElement>('button[data-mode="curate"]');
  curateBtn?.click();
  (document.getElementById("vmx-lib-runbtn") as HTMLButtonElement).click();
  // flush the awaited libraryCurate + the renderCurate that follows it.
  for (let i = 0; i < 6; i++) await Promise.resolve();
}

describe("curate — real renderCurate path (jsdom, via mountLibrary)", () => {
  beforeEach(() => {
    curateMock.mockReset();
    vi.resetModules();
    document.body.innerHTML = "";
  });

  afterEach(() => {
    delete (window as Window & { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__;
    document.body.innerHTML = "";
  });

  it("renders the numbered set + rationale (real renderCurate)", async () => {
    await runRealCurate(DEV_FALLBACK.curate);
    const rows = document.querySelectorAll(".vmx-lib-row");
    expect(rows).toHaveLength(6);
    expect(rows[0]?.querySelector(".rank")?.textContent).toBe("01");
    expect(rows[0]?.classList.contains("top")).toBe(true);
    // curated rows carry NO score number (ordered by the agent's arc).
    expect(rows[0]?.querySelector(".num")).toBeNull();
    expect(document.getElementById("vmx-lib-rationale-body")?.textContent).toContain(
      "melodic",
    );
    expect(document.getElementById("vmx-lib-rcount")?.textContent).toBe("6 in set");
  });

  it("does not auto-run Codex curation just by opening curate mode", async () => {
    curateMock.mockResolvedValue(DEV_FALLBACK.curate);
    vi.resetModules();
    doMockApi();
    const { mountLibrary } = await import("./index.js");
    mountSkeleton();
    mountLibrary();
    await Promise.resolve();
    await Promise.resolve();

    document.querySelector<HTMLElement>('button[data-mode="curate"]')?.click();
    for (let i = 0; i < 6; i++) await Promise.resolve();

    expect(curateMock).not.toHaveBeenCalled();
    expect(document.getElementById("vmx-lib-rationale-body")?.textContent).toBe(
      "No playlist curated yet.",
    );
    expect(document.getElementById("vmx-lib-rcount")?.textContent).toBe("ready");
  });

  it("escapes a hostile track title/meta — no raw HTML injection (real esc())", async () => {
    const hostile: CurateResult = {
      name: "xss",
      stop_reason: "created",
      rationale: "<b>note</b> & \"quoted\"",
      count: 1,
      tracks: [
        {
          track_id: "evil",
          title: '<img src=x onerror=alert(1)>',
          meta: 'a & b < c > d "e"',
        },
      ],
    };
    await runRealCurate(hostile);
    const results = document.getElementById("vmx-lib-results") as HTMLElement;
    // No live <img> element was parsed from the title — it was escaped to text.
    expect(results.querySelector("img")).toBeNull();
    // The title cell holds the literal source as text, not as HTML.
    const titleEl = results.querySelector(".vmx-lib-row .title");
    expect(titleEl?.textContent).toBe('<img src=x onerror=alert(1)>');
    expect(titleEl?.querySelector("img")).toBeNull();
    // The escaped entities are present in the raw markup.
    expect(results.innerHTML).toContain("&lt;img");
    expect(results.innerHTML).toContain("&amp;");
    expect(results.innerHTML).not.toContain("<img src=x");
  });

  it("renders the vmx-lib-empty branch when the agent built no set", async () => {
    const empty: CurateResult = {
      name: "nothing",
      stop_reason: "no_create",
      rationale: "",
      count: 0,
      tracks: [],
    };
    await runRealCurate(empty);
    const results = document.getElementById("vmx-lib-results") as HTMLElement;
    const emptyEl = results.querySelector(".vmx-lib-empty");
    expect(emptyEl).not.toBeNull();
    // The stop_reason is surfaced in the empty message (and is escaped).
    expect(emptyEl?.textContent).toContain("no_create");
    expect(document.querySelectorAll(".vmx-lib-row")).toHaveLength(0);
    expect(document.getElementById("vmx-lib-rcount")?.textContent).toBe("0 in set");
  });

  it("renders Viber clarification choices as an inline no-set state", async () => {
    const clarification: CurateResult = {
      name: "warehouse",
      stop_reason: "clarification_needed",
      rationale: "Which direction should I take this?",
      question: "Which direction should I take this?",
      choices: ["More hypnotic", "Brighter peak-time pressure"],
      count: 0,
      tracks: [],
    };
    await runRealCurate(clarification);
    const results = document.getElementById("vmx-lib-results") as HTMLElement;
    const emptyEl = results.querySelector(".vmx-lib-clarification");
    expect(emptyEl?.textContent).toContain("Viber needs one detail");
    expect(emptyEl?.textContent).toContain("Which direction should I take this?");
    expect(emptyEl?.textContent).toContain("More hypnotic");
    expect(emptyEl?.textContent).toContain(
      "Add one choice to the theme and run Viber again.",
    );
    expect(document.querySelectorAll(".vmx-lib-row")).toHaveLength(0);
  });
});
