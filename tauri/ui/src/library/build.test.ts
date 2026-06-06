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
 *      through the keyless AutoCrate frontdoor when invoke() is unavailable.
 *   3. a jsdom render path that drives the REAL index.ts renderBuildSet (via
 *      mountLibrary → runBuildSet): the numbered set, the rationale, the export
 *      receipt (shown only when export_path is present), the curve-picker
 *      selection, and the honest empty state (no key → max_iters, no rows).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DEV_FALLBACK, libraryBuildSet } from "./api.js";
import type {
  BuildSetResult,
  CueExportFormat,
  LibraryChatResult,
  LibraryCueResult,
  LibraryLiveContext,
  LibraryModelInstallTarget,
  LibraryModelsResult,
  LibraryStats,
} from "./api.js";
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
    expect(runLabel("build")).toBe("Build set");
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
// We mock ./api.js so libraryBuildSet returns a controlled AutoCrate payload; the other
// api fns are stubbed inert so mount/status work stays offline and deterministic.

const buildMock =
  vi.fn<
    (brief: string, curve: string, landDjTags?: boolean) => Promise<BuildSetResult>
  >();
const cueMock =
  vi.fn<
    (
      path: string,
      exportFormat: CueExportFormat,
    ) => Promise<LibraryCueResult>
  >();
const revealMock = vi.fn<(path: string) => Promise<boolean>>();
const modelsMock =
  vi.fn<(install?: LibraryModelInstallTarget) => Promise<LibraryModelsResult>>();
const chatMock =
  vi.fn<
    (
      message: string,
      history: unknown[],
      liveContext?: LibraryLiveContext | null,
    ) => Promise<LibraryChatResult>
  >();
const statsMock = vi.fn<() => Promise<LibraryStats>>();

const STATS_READY: LibraryStats = {
  indexed: 0,
  backend: "sqlite-vec",
  embedding_backend: "clap",
  embedding_dim: 512,
  clap_model_installed: true,
  clap_model_path: "~/.cache/vibemix/clap-onnx",
  clap_model_missing: [],
  agent_backend: "codex",
  agent_ready: true,
  agent_status: "ready",
  agent_hint: "",
  library_setup_candidates: [],
  spent_eur: 0,
  failed: 0,
};

const MODELS_READY: LibraryModelsResult = {
  models: [
    {
      id: "clap",
      label: "CLAP ONNX",
      role: "library embeddings/search/similarity",
      required: true,
      env: "VIBEMIX_CLAP_ONNX_DIR",
      installed: true,
      path: "~/.cache/vibemix/clap-onnx",
      missing: [],
      mismatched: [],
    },
    {
      id: "chatterbox-voice",
      label: "Chatterbox voice",
      role: "local co-host voice",
      required: true,
      env: "VIBEMIX_CHATTERBOX_REF",
      installed: true,
      path: "~/.cache/vibemix/voice/cohost_voice_ref.wav",
      missing: [],
      mismatched: [],
    },
    {
      id: "cue-detr",
      label: "CUE-DETR ONNX",
      role: "cue-anchored ingest and structural cue detection",
      required: false,
      env: "VIBEMIX_CUE_ONNX_PATH",
      installed: true,
      path: "~/.cache/vibemix/cue-detr-onnx/cuedetr.fp32.onnx",
      missing: [],
      mismatched: [],
    },
  ],
  required_ready: true,
  all_ready: true,
};

const MODELS_CUE_MISSING: LibraryModelsResult = {
  ...MODELS_READY,
  models: MODELS_READY.models.map((model) =>
    model.id === "cue-detr"
      ? {
          ...model,
          installed: false,
          installable: true,
          missing: ["cuedetr.fp32.onnx"],
        }
      : model,
  ),
  all_ready: false,
};

const MODELS_FRESH_MISSING: LibraryModelsResult = {
  ...MODELS_CUE_MISSING,
  models: MODELS_CUE_MISSING.models.map((model) =>
    model.id === "clap"
      ? {
          ...model,
          installed: false,
          missing: ["onnx/audio_model.onnx", "onnx/text_model.onnx"],
        }
      : model.id === "chatterbox-voice" || model.id === "moss-tts"
        ? {
            ...model,
            installed: false,
            missing: ["encoder_model.onnx"],
          }
      : model,
  ),
  required_ready: false,
  all_ready: false,
};

const MODELS_REQUIRED_INSTALL_OK: LibraryModelsResult = {
  ...MODELS_FRESH_MISSING,
  models: MODELS_FRESH_MISSING.models.map((model) =>
    model.id === "clap" || model.id === "chatterbox-voice"
      ? {
          ...model,
          installed: true,
          missing: [],
        }
      : model,
  ),
  required_ready: true,
  install: {
    target: "required",
    ok: true,
    results: [
      {
        id: "clap",
        installed: true,
        path: "~/.cache/vibemix/clap-onnx",
        files: [
          {
            rel_path: "onnx/audio_model.onnx",
            path: "~/.cache/vibemix/clap-onnx/onnx/audio_model.onnx",
            status: "downloaded",
            size: 281749092,
            sha256: "sha-audio",
            url: "https://example.test/audio_model.onnx",
          },
          {
            rel_path: "onnx/text_model.onnx",
            path: "~/.cache/vibemix/clap-onnx/onnx/text_model.onnx",
            status: "skipped",
            size: 501513769,
            sha256: "sha-text",
            url: "https://example.test/text_model.onnx",
          },
        ],
        errors: [],
      },
      {
        id: "chatterbox-voice",
        installed: true,
        path: "~/.cache/vibemix/voice/cohost_voice_ref.wav",
        files: [
          {
            rel_path: "cohost_voice_ref.wav",
            path: "~/.cache/vibemix/voice/cohost_voice_ref.wav",
            status: "skipped",
            size: 104857600,
            sha256: "sha-chatterbox",
            url: "https://example.test/chatterbox-ref.wav",
          },
        ],
        errors: [],
      },
    ],
  },
};

const MODELS_CUE_INSTALL_ERROR: LibraryModelsResult = {
  ...MODELS_CUE_MISSING,
  install: {
    target: "cue",
    ok: false,
    results: [
      {
        id: "cue-detr",
        installed: false,
        path: "~/.cache/vibemix/cue-detr-onnx/cuedetr.fp32.onnx",
        files: [],
        errors: ["set VIBEMIX_CUE_ONNX_PATH or place cuedetr.fp32.onnx"],
      },
    ],
  },
};

const CHAT_OK: LibraryChatResult = {
  reply: "ok",
  tool_trace: [],
  playlist: null,
  export_path: null,
  seen_track_ids: [],
  move_grades: [],
  iterations: 1,
  stop_reason: "model_done",
};

const CHAT_CODEX_MISSING: LibraryChatResult = {
  reply:
    "Codex CLI not found. Install it (`npm i -g @openai/codex` or `brew install codex`) and run `codex login`.",
  tool_trace: [],
  playlist: null,
  export_path: null,
  seen_track_ids: [],
  move_grades: [],
  iterations: 0,
  stop_reason: "codex_not_installed",
};

function doMockApi(): void {
  vi.doMock("./api.js", () => ({
    libraryBuildSet: (
      brief: string,
      curve: string,
      landDjTags?: boolean,
    ) => buildMock(brief, curve, landDjTags),
    libraryCueFolder: (path: string, exportFormat: CueExportFormat) =>
      cueMock(path, exportFormat),
    libraryRevealExport: (path: string) => revealMock(path),
    // inert stubs — mountLibrary does a state-dependent boot run + status refresh.
    librarySearch: vi.fn(async () => ({ results: [], centered: true, corpus_size: 0 })),
    librarySimilar: vi.fn(async () => ({ results: [], centered: true, corpus_size: 0 })),
    libraryCurate: vi.fn(async () => ({
      name: "x",
      rationale: "",
      stop_reason: "created",
      tracks: [],
      count: 0,
    })),
    libraryChat: (
      message: string,
      history: unknown[],
      liveContext?: LibraryLiveContext | null,
    ) =>
      liveContext === undefined
        ? chatMock(message, history)
        : chatMock(message, history, liveContext),
    libraryStats: () => statsMock(),
    libraryModels: (install?: LibraryModelInstallTarget) => modelsMock(install),
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
    DEV_FALLBACK: { embedLog: [] },
  }));
}

/** Full library.html DOM skeleton (the ids/attrs index.ts queries for build). */
function mountSkeleton(): void {
  document.body.dataset.mode = "chat";
  document.body.innerHTML = `
    <div class="vmx-lib-app" data-auto-build-on-landing="true">
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
    <button id="vmx-lib-build-tags" role="switch" aria-checked="false"><span class="dot"></span><span>Serato/Mixxx tags</span><b>OFF</b></button>
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
    <h2 id="vmx-lib-rationale-title"></h2>
    <p id="vmx-lib-rationale-body"></p>
    <div id="vmx-lib-rationale-meta"></div>
    <div id="vmx-lib-export" style="display: none">
      <div class="vmx-lib-export-path-row">
        <div id="vmx-lib-export-path"></div>
        <button id="vmx-lib-export-open" type="button" hidden>Reveal</button>
      </div>
      <div id="vmx-lib-export-hint"></div>
    </div>
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

async function flushLandingTimer(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
  await new Promise<void>((resolve) => window.setTimeout(resolve, 0));
  for (let i = 0; i < 6; i++) await Promise.resolve();
}

/** Boot the real window, switch to build mode, optionally click a curve seg,
 *  then trigger a build run. Returns once the render has settled. */
async function runRealBuild(
  payload: BuildSetResult,
  clickCurve?: string,
  clickTags = false,
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
  for (let i = 0; i < 6; i++) await Promise.resolve();
  if (clickCurve) {
    document
      .querySelector<HTMLElement>(`[data-curve="${clickCurve}"]`)
      ?.click();
  }
  if (clickTags) {
    document.getElementById("vmx-lib-build-tags")?.click();
  }
  (document.getElementById("vmx-lib-runbtn") as HTMLButtonElement).click();
  for (let i = 0; i < 6; i++) await Promise.resolve();
}

async function runRealCue(
  payload: LibraryCueResult,
  clickFormat?: CueExportFormat,
): Promise<void> {
  cueMock.mockResolvedValue(payload);
  vi.resetModules();
  doMockApi();
  const { mountLibrary } = await import("./index.js");
  mountSkeleton();
  mountLibrary();
  await Promise.resolve();
  await Promise.resolve();
  document.querySelector<HTMLElement>('button[data-mode="build"]')?.click();
  for (let i = 0; i < 6; i++) await Promise.resolve();
  if (clickFormat) {
    document
      .querySelector<HTMLElement>(`[data-cue-export="${clickFormat}"]`)
      ?.click();
  }
  (document.getElementById("vmx-lib-cue-run") as HTMLButtonElement).click();
  for (let i = 0; i < 6; i++) await Promise.resolve();
}

describe("build — real renderBuildSet path (jsdom, via mountLibrary)", () => {
  beforeEach(() => {
    buildMock.mockReset();
    cueMock.mockReset();
    cueMock.mockResolvedValue(DEV_FALLBACK.cue);
    revealMock.mockReset();
    revealMock.mockResolvedValue(true);
    modelsMock.mockReset();
    modelsMock.mockResolvedValue(MODELS_READY);
    chatMock.mockReset();
    chatMock.mockResolvedValue(CHAT_OK);
    statsMock.mockReset();
    statsMock.mockResolvedValue(STATS_READY);
    vi.resetModules();
    document.body.innerHTML = "";
  });

  afterEach(() => {
    delete (window as Window & { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__;
    document.body.innerHTML = "";
  });

  it("shows staged sequencing rows while AutoCrate is running", async () => {
    let resolveBuild!: (payload: BuildSetResult) => void;
    buildMock.mockImplementation(
      () =>
        new Promise<BuildSetResult>((resolve) => {
          resolveBuild = resolve;
        }),
    );
    vi.resetModules();
    doMockApi();
    const { mountLibrary } = await import("./index.js");
    mountSkeleton();
    mountLibrary();
    await Promise.resolve();
    await Promise.resolve();

    document.querySelector<HTMLElement>('button[data-mode="build"]')?.click();
    for (let i = 0; i < 6; i++) await Promise.resolve();
    (document.getElementById("vmx-lib-runbtn") as HTMLButtonElement).click();
    for (let i = 0; i < 6; i++) await Promise.resolve();

    const runningRows = document.querySelectorAll(".vmx-lib-sequence-step");
    expect(runningRows).toHaveLength(6);
    expect(runningRows[0]?.textContent).toContain("Find candidates");
    expect(runningRows[5]?.textContent).toContain("Write handoff");
    expect(document.getElementById("vmx-lib-rationale-meta")?.textContent).toContain(
      "discovering / ordering / exporting",
    );
    expect(document.getElementById("vmx-lib-rcount")?.textContent).toBe(
      "sequencing…",
    );
    const runBtn = document.getElementById("vmx-lib-runbtn") as HTMLButtonElement;
    expect(runBtn.disabled).toBe(true);
    expect(runBtn.textContent).toBe("Sequencing");

    resolveBuild(DEV_FALLBACK.build);
    for (let i = 0; i < 8; i++) await Promise.resolve();

    expect(document.querySelectorAll(".vmx-lib-sequence-step")).toHaveLength(0);
    expect(document.querySelectorAll(".vmx-lib-row")).toHaveLength(6);
    expect(document.getElementById("vmx-lib-rcount")?.textContent).toBe("6 in set");
    expect(runBtn.disabled).toBe(false);
    expect(runBtn.textContent).toBe("Build set");
  });

  it("renders the numbered set, rationale + export receipt (real renderBuildSet)", async () => {
    await runRealBuild(DEV_FALLBACK.build);
    const rows = document.querySelectorAll(".vmx-lib-row");
    expect(rows).toHaveLength(6);
    expect(rows[0]?.querySelector(".rank")?.textContent).toBe("01");
    expect(rows[0]?.classList.contains("top")).toBe(true);
    // built rows carry NO score number (ordered by the agent's arc).
    expect(rows[0]?.querySelector(".num")).toBeNull();
    expect(rows[0]?.querySelector(".vmx-lib-artwork")?.textContent).toContain(
      "CX",
    );
    expect(rows[0]?.querySelector(".vmx-lib-track-kicker")?.textContent).toContain(
      "Charli XCX",
    );
    expect(rows[0]?.querySelector(".title")?.textContent).toContain("Guess");
    expect(rows[0]?.querySelector(".vmx-lib-track-chips")?.textContent).toContain(
      "BPM 122",
    );
    expect(rows[0]?.querySelector(".vmx-lib-track-chips")?.textContent).toContain(
      "Key 5A",
    );
    expect(rows[0]?.querySelector(".vmx-lib-track-chips")?.textContent).toContain(
      "Energy 64",
    );
    expect(document.getElementById("vmx-lib-scope-state")?.textContent).toBe(
      "sequenced order",
    );
    expect(document.querySelectorAll("#vmx-lib-scope .vmx-lib-dot-near")).toHaveLength(0);
    expect(document.querySelectorAll("#vmx-lib-scope .vmx-lib-dot-far")).toHaveLength(0);
    expect(
      document.querySelectorAll("#vmx-lib-scope .vmx-lib-dot-sequence"),
    ).toHaveLength(6);
    expect(document.getElementById("vmx-lib-scope")?.getAttribute("aria-label")).toContain(
      "No vibe-distance score is available",
    );
    expect(document.getElementById("vmx-lib-scope-note")?.textContent).toContain(
      "No cosine score",
    );
    expect(document.getElementById("vmx-lib-scope-legend-near")?.textContent).toBe(
      "Sequence order",
    );
    expect(document.getElementById("vmx-lib-rationale-body")?.textContent).toContain(
      "peak-time",
    );
    expect(document.getElementById("vmx-lib-rationale-title")?.textContent).toBe(
      "warehouse opener, melodic into rolling, 90 min",
    );
    // export receipt is shown + carries the path.
    const exportEl = document.getElementById("vmx-lib-export") as HTMLElement;
    expect(exportEl.style.display).not.toBe("none");
    expect(document.getElementById("vmx-lib-export-path")?.textContent).toContain(
      "rekordbox:",
    );
    expect(document.getElementById("vmx-lib-export-path")?.textContent).toContain(
      ".xml",
    );
    expect(document.getElementById("vmx-lib-rcount")?.textContent).toBe("6 in set");
  });

  it("does not use demo track details when a real Tauri runtime is present", async () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {},
    });
    const collision: BuildSetResult = {
      ...DEV_FALLBACK.build,
      count: 1,
      tracks: [
        {
          track_id: "23381471",
          title: "23381471",
          meta: "track 23381471",
        },
      ],
    };

    await runRealBuild(collision);

    const row = document.querySelector(".vmx-lib-row");
    expect(row?.querySelector(".vmx-lib-track-kicker")?.textContent).toContain(
      "Local library",
    );
    expect(row?.querySelector(".vmx-lib-track-kicker")?.textContent).not.toContain(
      "Raffertie",
    );
    expect(row?.querySelector(".title")?.textContent).toContain("Track 23381471");
    const chips = row?.querySelector(".vmx-lib-track-chips")?.textContent ?? "";
    expect(chips).toContain("BPM --");
    expect(chips).toContain("Key --");
    expect(chips).toContain("Energy --");
  });

  it("renders all-carrier cue landing receipts from AutoCrate", async () => {
    const payload: BuildSetResult = {
      ...DEV_FALLBACK.build,
      export_path: "/tmp/warehouse.xml",
      export_outputs: {
        rekordbox: "/tmp/warehouse.xml",
        m3u8: "/tmp/warehouse.m3u8",
      },
      export_tag_receipts: [
        {
          carrier: "markers2_tags",
          compatible_apps: ["Serato", "Mixxx"],
          tagged: 2,
          cues_total: 6,
          skipped: 0,
          files: ["/tmp/a.mp3", "/tmp/b.mp3"],
        },
      ],
      export_auto_cues: { enabled: true, tracks_cued: 2, cues_added: 6 },
    };

    await runRealBuild(payload);

    const exportText =
      document.getElementById("vmx-lib-export-path")?.textContent ?? "";
    expect(exportText).toContain("rekordbox: /tmp/warehouse.xml");
    expect(exportText).toContain("m3u8: /tmp/warehouse.m3u8");
    expect(exportText).toContain("Serato/Mixxx tags: 2 files, 6 VM cues");
    expect(document.getElementById("vmx-lib-export-hint")?.textContent).toContain(
      "Serato and Mixxx read the VM tags",
    );
    expect(document.getElementById("vmx-lib-rationale-meta")?.textContent).toContain(
      "6 VM cues",
    );

    const reveal = document.getElementById(
      "vmx-lib-export-open",
    ) as HTMLButtonElement;
    expect(reveal.hidden).toBe(false);
    expect(reveal.dataset.path).toBe("/tmp/warehouse.xml");
    expect(reveal.textContent).toBe("Open set");
    expect(reveal.getAttribute("aria-label")).toBe(
      "Open exported set /tmp/warehouse.xml",
    );
    reveal.click();
    await Promise.resolve();
    expect(revealMock).toHaveBeenCalledWith("/tmp/warehouse.xml");

    revealMock.mockClear();
    const firstRow = document.querySelector<HTMLElement>(".vmx-lib-row");
    expect(firstRow?.dataset.openExport).toBe("/tmp/warehouse.xml");
    expect(firstRow?.getAttribute("role")).toBe("button");
    expect(firstRow?.tabIndex).toBe(0);
    expect(firstRow?.querySelector(".open-hint")?.textContent).toBe("Open");
    firstRow?.click();
    await Promise.resolve();
    expect(revealMock).toHaveBeenCalledWith("/tmp/warehouse.xml");
  });

  it("auto-starts set prep on landing when the indexed library is ready", async () => {
    statsMock.mockResolvedValue({ ...STATS_READY, indexed: 42 });
    buildMock.mockResolvedValue(DEV_FALLBACK.build);
    vi.resetModules();
    doMockApi();
    const { mountLibrary } = await import("./index.js");
    mountSkeleton();
    mountLibrary();

    await flushLandingTimer();

    expect(document.body.dataset.mode).toBe("build");
    expect(buildMock).toHaveBeenCalledTimes(1);
    expect(buildMock).toHaveBeenCalledWith(
      initialLibraryState.brief,
      "peak_time",
      false,
    );
    expect(
      document.querySelector<HTMLElement>('button[data-mode="build"]')?.getAttribute(
        "aria-selected",
      ),
    ).toBe("true");
    expect(document.querySelectorAll(".vmx-lib-row")).toHaveLength(6);
  });

  it("sends per-run tag permission only when the build switch is on", async () => {
    await runRealBuild(DEV_FALLBACK.build, undefined, true);

    const toggle = document.getElementById("vmx-lib-build-tags") as HTMLElement;
    expect(toggle.getAttribute("aria-checked")).toBe("true");
    expect(toggle.textContent).toContain("ON");
    expect(buildMock).toHaveBeenLastCalledWith(
      expect.any(String),
      "peak_time",
      true,
    );
  });

  it("selecting a curve segment updates the picker pressed state", async () => {
    await runRealBuild(DEV_FALLBACK.build, "after_hours");
    const pressed = Array.from(
      document.querySelectorAll<HTMLElement>("[data-curve]"),
    ).filter((s) => s.getAttribute("aria-pressed") === "true");
    expect(pressed).toHaveLength(1);
    expect(pressed[0]?.dataset.curve).toBe("after_hours");
    // and the run after the curve was picked passed the chosen curve.
    expect(buildMock).toHaveBeenLastCalledWith(
      expect.any(String),
      "after_hours",
      false,
    );
  });

  it("does not auto-run AutoCrate just by opening build mode", async () => {
    statsMock.mockResolvedValue({ ...STATS_READY, indexed: 42 });
    buildMock.mockResolvedValue(DEV_FALLBACK.build);
    vi.resetModules();
    doMockApi();
    const { mountLibrary } = await import("./index.js");
    mountSkeleton();
    mountLibrary();

    document.querySelector<HTMLElement>('button[data-mode="build"]')?.click();
    await flushLandingTimer();

    expect(buildMock).not.toHaveBeenCalled();
    expect(document.getElementById("vmx-lib-rationale-body")?.textContent).toBe(
      "No set built yet.",
    );
    expect(document.getElementById("vmx-lib-rcount")?.textContent).toBe("ready");
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
    const reveal = document.getElementById(
      "vmx-lib-export-open",
    ) as HTMLButtonElement;
    expect(reveal.hidden).toBe(true);
    expect(reveal.dataset.path).toBeUndefined();
    expect(document.querySelectorAll(".vmx-lib-row")).toHaveLength(0);
    expect(document.getElementById("vmx-lib-rcount")?.textContent).toBe("0 in set");
  });

  it("renders Viber setup errors as a no-set state with the setup hint", async () => {
    const setupNeeded: BuildSetResult = {
      name: "warehouse",
      stop_reason: "setup_error",
      rationale: "No library cache. Drag a Rekordbox XML onto Settings first.",
      count: 0,
      tracks: [],
      export_path: null,
    };
    await runRealBuild(setupNeeded);
    const results = document.getElementById("vmx-lib-results") as HTMLElement;
    expect(results.querySelector(".vmx-lib-error")).toBeNull();
    expect(results.querySelector(".vmx-lib-empty")?.textContent).toContain(
      "setup_error",
    );
    expect(results.querySelector(".vmx-lib-agent-failure")?.textContent).toContain(
      "Index a music folder first",
    );
    expect(document.getElementById("vmx-lib-rationale-body")?.textContent).toContain(
      "Viber could not open the indexed library cache",
    );
  });

  it("renders Viber clarification choices as an inline set-prep pause", async () => {
    const clarification: BuildSetResult = {
      name: "warehouse",
      stop_reason: "clarification_needed",
      rationale: "Which direction should I take this?",
      question: "Which direction should I take this?",
      choices: ["More hypnotic", "Brighter peak-time pressure"],
      count: 0,
      tracks: [],
      export_path: null,
    };
    await runRealBuild(clarification);
    const results = document.getElementById("vmx-lib-results") as HTMLElement;
    const emptyEl = results.querySelector(".vmx-lib-clarification");
    expect(emptyEl?.textContent).toContain("Viber needs one detail");
    expect(emptyEl?.textContent).toContain("Which direction should I take this?");
    expect(emptyEl?.textContent).toContain("Brighter peak-time pressure");
    expect(emptyEl?.textContent).toContain(
      "Add one choice to the brief and run set prep again.",
    );
    expect(document.querySelectorAll(".vmx-lib-row")).toHaveLength(0);
    expect((document.getElementById("vmx-lib-export") as HTMLElement).style.display).toBe(
      "none",
    );
  });

  it("turns a set-prep timeout into an actionable Viber receipt", async () => {
    const timeout: BuildSetResult = {
      name: "warehouse",
      stop_reason: "timeout",
      rationale: "Codex did not finish within 90s.",
      count: 0,
      tracks: [],
      export_path: null,
    };
    await runRealBuild(timeout);
    const results = document.getElementById("vmx-lib-results") as HTMLElement;
    const receipt = results.querySelector(".vmx-lib-agent-failure");
    expect(receipt).not.toBeNull();
    expect(receipt?.textContent).toContain("Viber kept working too long");
    expect(receipt?.textContent).toContain("Codex did not finish within 90s.");
    expect(receipt?.textContent).toContain("timeout");
    expect(receipt?.textContent).toContain("No Rekordbox XML was written.");
    expect(receipt?.textContent).toContain("venue, BPM lane, energy curve");
    expect(document.querySelectorAll(".vmx-lib-row")).toHaveLength(0);
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

  it("routes a cue-only setup through the cue model target", async () => {
    modelsMock.mockImplementation(async (install) =>
      install === "cue" ? MODELS_CUE_INSTALL_ERROR : MODELS_CUE_MISSING,
    );
    vi.resetModules();
    doMockApi();
    const { mountLibrary } = await import("./index.js");
    mountSkeleton();
    mountLibrary();
    for (let i = 0; i < 6; i++) await Promise.resolve();

    const installBtn = document.getElementById(
      "vmx-lib-install-models",
    ) as HTMLButtonElement;
    expect(installBtn.hidden).toBe(false);
    expect(installBtn.dataset.installTarget).toBe("cue");
    expect(installBtn.textContent).toBe("Check Cue Finder");

    installBtn.click();
    for (let i = 0; i < 6; i++) await Promise.resolve();

    expect(modelsMock).toHaveBeenCalledWith("cue");
    expect(document.getElementById("vmx-lib-model-state")?.textContent).toContain(
      "Cue finder setup unavailable",
    );
    expect(document.getElementById("vmx-lib-model-state")?.textContent).toContain(
      "Cue finder setup path is not configured",
    );
    expect(installBtn.textContent).toBe("Retry Cue Finder");
  });

  it("routes first-run setup through required models, not strict all", async () => {
    modelsMock.mockImplementation(async (install) =>
      install === "required" ? MODELS_REQUIRED_INSTALL_OK : MODELS_FRESH_MISSING,
    );
    vi.resetModules();
    doMockApi();
    const { mountLibrary } = await import("./index.js");
    mountSkeleton();
    mountLibrary();
    for (let i = 0; i < 6; i++) await Promise.resolve();

    const installBtn = document.getElementById(
      "vmx-lib-install-models",
    ) as HTMLButtonElement;
    expect(installBtn.hidden).toBe(false);
    expect(installBtn.dataset.installTarget).toBe("required");
    expect(installBtn.textContent).toBe("Install Sound Match + Voice");

    installBtn.click();
    for (let i = 0; i < 6; i++) await Promise.resolve();

    expect(modelsMock).toHaveBeenCalledWith("required");
    expect(modelsMock).not.toHaveBeenCalledWith("all");
    expect(document.getElementById("vmx-lib-model-state")?.textContent).toContain(
      "Sound match ready",
    );
    expect(document.getElementById("vmx-lib-model-state")?.textContent).toContain(
      "Voice ready",
    );
    expect(document.getElementById("vmx-lib-model-state")?.textContent).toContain(
      "Sound match and voice ready: downloaded 1/3",
    );
  });

  it("surfaces agent setup hints separately from model readiness", async () => {
    statsMock.mockResolvedValue({
      ...STATS_READY,
      agent_ready: false,
      agent_status: "codex_auth_required",
      agent_hint: "Run `codex login` to connect your ChatGPT plan.",
    });
    vi.resetModules();
    doMockApi();
    const { mountLibrary } = await import("./index.js");
    mountSkeleton();
    mountLibrary();
    for (let i = 0; i < 6; i++) await Promise.resolve();

    const setupText = document.getElementById("vmx-lib-model-state")?.textContent ?? "";
    expect(setupText).toContain("Sound match ready");
    expect(setupText).toContain("Voice ready");
    expect(setupText).toContain("Cue finder ready");
    expect(setupText).not.toContain("codex login");

    const agentSetup = document.getElementById("vmx-lib-agent-setup") as HTMLElement;
    const agentText = document.getElementById("vmx-lib-agent-state")?.textContent ?? "";
    expect(agentSetup.hidden).toBe(false);
    expect(agentText).toContain("Viber codex");
    expect(agentText).toContain("codex login");
  });

  it("renders Codex setup failures as setup cards in chat mode", async () => {
    chatMock.mockResolvedValue(CHAT_CODEX_MISSING);
    vi.resetModules();
    doMockApi();
    const { mountLibrary } = await import("./index.js");
    mountSkeleton();
    mountLibrary();
    for (let i = 0; i < 6; i++) await Promise.resolve();

    document.querySelector<HTMLElement>('button[data-mode="chat"]')?.click();
    const chatInput = document.getElementById("vmx-lib-chat") as HTMLTextAreaElement;
    chatInput.value = "are you wired?";
    (document.getElementById("vmx-lib-runbtn") as HTMLButtonElement).click();
    for (let i = 0; i < 6; i++) await Promise.resolve();

    expect(chatMock).toHaveBeenCalledWith("are you wired?", []);
    const threadText = document.getElementById("vmx-lib-chat-thread")?.textContent ?? "";
    expect(threadText).toContain("Codex CLI not found");
    const artifactText =
      document.getElementById("vmx-lib-chat-thread")?.textContent ?? "";
    expect(artifactText).toContain("Codex CLI missing");
    expect(artifactText).toContain("codex login");
    expect(document.getElementById("vmx-lib-scope-state")?.textContent).toBe(
      "setup · codex_not_installed",
    );
  });

  it("renders cue export receipts from the folded Build hot-cue instrument", async () => {
    await runRealCue({
      ok: true,
      mode: "export",
      tracks_cued: 3,
      cues_total: 18,
      skipped: 1,
      outputs: {
        rekordbox: "/tmp/vibemix-cues.xml",
        m3u8: "/tmp/vibemix-cues.m3u8",
      },
    });

    expect(document.querySelector('[data-mode="cue"]')).toBeNull();
    expect(cueMock).toHaveBeenCalledWith("~/Music", "rekordbox");
    expect(document.getElementById("vmx-lib-rationale-body")?.textContent).toContain(
      "Cued 3 tracks with 18 hot cues.",
    );
    expect(document.getElementById("vmx-lib-rationale-meta")?.textContent).toContain(
      "rekordbox + m3u8",
    );
    expect(document.getElementById("vmx-lib-export-path")?.textContent).toBe(
      "/tmp/vibemix-cues.xml",
    );
    const reveal = document.getElementById(
      "vmx-lib-export-open",
    ) as HTMLButtonElement;
    expect(reveal.hidden).toBe(false);
    expect(reveal.dataset.path).toBe("/tmp/vibemix-cues.xml");
    reveal.click();
    await Promise.resolve();
    expect(revealMock).toHaveBeenCalledWith("/tmp/vibemix-cues.xml");
    const text = document.body.textContent ?? "";
    expect(text).not.toMatch(/serato tags/i);
    expect(text).not.toMatch(/written into/i);
  });

  it("passes the selected cue export format to the bridge", async () => {
    await runRealCue(DEV_FALLBACK.cue, "both");

    const pressed = Array.from(
      document.querySelectorAll<HTMLElement>("[data-cue-export]"),
    ).filter((s) => s.getAttribute("aria-pressed") === "true");
    expect(pressed).toHaveLength(1);
    expect(pressed[0]?.dataset.cueExport).toBe("both");
    expect(cueMock).toHaveBeenLastCalledWith("~/Music", "both");
    expect(document.getElementById("vmx-lib-cue-run")?.textContent).toBe(
      "Export hot cues",
    );
  });
});
