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
// api fns are stubbed inert so mount/status work stays offline and deterministic.

const buildMock = vi.fn<(brief: string, curve: string) => Promise<BuildSetResult>>();
const cueMock =
  vi.fn<
    (
      path: string,
      exportFormat: CueExportFormat,
    ) => Promise<LibraryCueResult>
  >();
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
      id: "moss-tts",
      label: "MOSS TTS ONNX",
      role: "local co-host voice",
      required: true,
      env: "VIBEMIX_MOSS_TTS_DIR",
      installed: true,
      path: "~/.cache/vibemix/moss-tts-onnx/MOSS-TTS-Nano-100M-ONNX",
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
      : model.id === "moss-tts"
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
    model.id === "clap" || model.id === "moss-tts"
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
        id: "moss-tts",
        installed: true,
        path: "~/.cache/vibemix/moss-tts-onnx/MOSS-TTS-Nano-100M-ONNX",
        files: [
          {
            rel_path: "MOSS-TTS-Nano-100M-ONNX/encoder_model.onnx",
            path: "~/.cache/vibemix/moss-tts-onnx/MOSS-TTS-Nano-100M-ONNX/encoder_model.onnx",
            status: "skipped",
            size: 104857600,
            sha256: "sha-moss",
            url: "https://example.test/moss-tts.tar.gz",
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
    libraryBuildSet: (brief: string, curve: string) => buildMock(brief, curve),
    libraryCueFolder: (path: string, exportFormat: CueExportFormat) =>
      cueMock(path, exportFormat),
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
    onEmbedProgress: vi.fn(async () => () => {}),
    onEmbedDone: vi.fn(async () => () => {}),
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
    <div class="vmx-lib-modeswitch">
      <button data-mode="search" aria-selected="false">Search</button>
      <button data-mode="similar" aria-selected="false">Similar</button>
      <button data-mode="curate" aria-selected="false">Curate</button>
      <button data-mode="build" aria-selected="false">Build</button>
      <button data-mode="cue" aria-selected="false">Cue</button>
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
    <div id="vmx-lib-export" style="display: none">
      <div id="vmx-lib-export-path"></div>
    </div>
    <div id="vmx-lib-results"></div>
    <div id="vmx-lib-chat-thread"></div>
    <span id="vmx-lib-rcount"></span>
    <div id="vmx-lib-prog-n"></div>
    <div id="vmx-lib-prog-cost"></div>
    <i id="vmx-lib-progress-fill"></i>
    <div id="vmx-lib-loglist"></div>
    <span id="vmx-lib-side-label"></span>
    <span id="vmx-lib-scope-state"></span>
    <div id="vmx-lib-chat-tools"></div>
    <div id="vmx-lib-chat-artifact"></div>
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
  for (let i = 0; i < 6; i++) await Promise.resolve();
  if (clickCurve) {
    document
      .querySelector<HTMLElement>(`[data-curve="${clickCurve}"]`)
      ?.click();
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
  document.querySelector<HTMLElement>('button[data-mode="cue"]')?.click();
  for (let i = 0; i < 6; i++) await Promise.resolve();
  if (clickFormat) {
    document
      .querySelector<HTMLElement>(`[data-cue-export="${clickFormat}"]`)
      ?.click();
  }
  (document.getElementById("vmx-lib-runbtn") as HTMLButtonElement).click();
  for (let i = 0; i < 6; i++) await Promise.resolve();
}

describe("build — real renderBuildSet path (jsdom, via mountLibrary)", () => {
  beforeEach(() => {
    buildMock.mockReset();
    cueMock.mockReset();
    cueMock.mockResolvedValue(DEV_FALLBACK.cue);
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
    // and the run after the curve was picked passed the chosen curve.
    expect(buildMock).toHaveBeenLastCalledWith(expect.any(String), "after_hours");
  });

  it("does not auto-run Codex set prep just by opening build mode", async () => {
    buildMock.mockResolvedValue(DEV_FALLBACK.build);
    vi.resetModules();
    doMockApi();
    const { mountLibrary } = await import("./index.js");
    mountSkeleton();
    mountLibrary();
    await Promise.resolve();
    await Promise.resolve();

    document.querySelector<HTMLElement>('button[data-mode="build"]')?.click();
    for (let i = 0; i < 6; i++) await Promise.resolve();

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
    expect(document.querySelectorAll(".vmx-lib-row")).toHaveLength(0);
    expect(document.getElementById("vmx-lib-rcount")?.textContent).toBe("0 in set");
  });

  it("renders Codex setup terminals as a no-set state with the setup hint", async () => {
    const setupNeeded: BuildSetResult = {
      name: "warehouse",
      stop_reason: "codex_not_installed",
      rationale: "Codex CLI not found. Install it and run codex login.",
      count: 0,
      tracks: [],
      export_path: null,
    };
    await runRealBuild(setupNeeded);
    const results = document.getElementById("vmx-lib-results") as HTMLElement;
    expect(results.querySelector(".vmx-lib-error")).toBeNull();
    expect(results.querySelector(".vmx-lib-empty")?.textContent).toContain(
      "codex_not_installed",
    );
    expect(document.getElementById("vmx-lib-rationale-body")?.textContent).toContain(
      "codex login",
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
    expect(installBtn.textContent).toBe("Check Optional CUE");

    installBtn.click();
    for (let i = 0; i < 6; i++) await Promise.resolve();

    expect(modelsMock).toHaveBeenCalledWith("cue");
    expect(document.getElementById("vmx-lib-model-state")?.textContent).toContain(
      "Optional CUE setup unavailable",
    );
    expect(document.getElementById("vmx-lib-model-state")?.textContent).toContain(
      "set VIBEMIX_CUE_ONNX_PATH",
    );
    expect(installBtn.textContent).toBe("Retry Optional CUE");
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
    expect(installBtn.textContent).toBe("Install Required Models");

    installBtn.click();
    for (let i = 0; i < 6; i++) await Promise.resolve();

    expect(modelsMock).toHaveBeenCalledWith("required");
    expect(modelsMock).not.toHaveBeenCalledWith("all");
    expect(document.getElementById("vmx-lib-model-state")?.textContent).toContain(
      "CLAP ready",
    );
    expect(document.getElementById("vmx-lib-model-state")?.textContent).toContain(
      "MOSS ready",
    );
    expect(document.getElementById("vmx-lib-model-state")?.textContent).toContain(
      "Required models ready: downloaded 1/3",
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
    expect(setupText).toContain("CLAP ready");
    expect(setupText).toContain("MOSS ready");
    expect(setupText).toContain("CUE ready");
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
      document.getElementById("vmx-lib-chat-artifact")?.textContent ?? "";
    expect(artifactText).toContain("Codex CLI missing");
    expect(artifactText).toContain("codex login");
    expect(document.getElementById("vmx-lib-scope-state")?.textContent).toBe(
      "setup · codex_not_installed",
    );
  });

  it("renders cue export receipts without claiming Serato tag writes", async () => {
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
  });
});
