// SPDX-License-Identifier: Apache-2.0
/**
 * @vitest-environment jsdom
 *
 * Viber's library page also folds into the cohesive shell's Viber surface. This
 * pins the root-scoped mount contract so the standalone page cannot accidentally
 * reach into shell/session DOM when mounted as an interior.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import libraryHtmlRaw from "../../library.html?raw";
import { extractSurfaceMarkup } from "../shell/scaffolds.js";

function mockApi(): void {
  vi.doMock("./api.js", () => ({
    DEV_FALLBACK: { embedLog: [] },
    libraryBuildSet: vi.fn(async () => ({
      count: 0,
      export_path: null,
      rationale: "",
      stop_reason: "created",
      tracks: [],
    })),
    libraryChat: vi.fn(async () => ({
      export_path: null,
      iterations: 0,
      move_grades: [],
      playlist: null,
      reply: "",
      seen_track_ids: [],
      stop_reason: "empty",
      tool_trace: [],
    })),
    libraryCueFolder: vi.fn(async () => ({
      ok: true,
      export_path: null,
      tracks_cued: 0,
    })),
    libraryCurate: vi.fn(async () => ({
      count: 0,
      name: "",
      rationale: "",
      stop_reason: "created",
      tracks: [],
    })),
    libraryEmbedFolder: vi.fn(async () => false),
    libraryImport: vi.fn(async () => false),
    libraryImportFromAction: vi.fn(async () => false),
    libraryCancelImport: vi.fn(async () => undefined),
    libraryModels: vi.fn(async () => ({
      install: null,
      models: [],
      required_ready: true,
    })),
    librarySearch: vi.fn(async () => ({
      centered: true,
      corpus_size: 0,
      results: [],
    })),
    librarySimilar: vi.fn(async () => ({
      centered: true,
      corpus_size: 0,
      results: [],
    })),
    libraryStats: vi.fn(async () => ({
      agent_backend: "codex",
      agent_hint: "",
      agent_ready: true,
      agent_status: "ready",
      backend: "sqlite-vec",
      clap_model_installed: true,
      clap_model_missing: [],
      clap_model_path: "",
      embedding_backend: "clap",
      embedding_dim: 512,
      failed: 0,
      indexed: 0,
      library_setup_candidates: [],
      spent_eur: 0,
    })),
    normalizeLiveContextPayload: vi.fn((payload) => payload),
    onEmbedDone: vi.fn(async () => () => {}),
    onEmbedProgress: vi.fn(async () => () => {}),
    onLibraryImportProgress: vi.fn(async () => () => {}),
    onLiveDeckContext: vi.fn(async () => () => {}),
    onLiveMoveContext: vi.fn(async () => () => {}),
    onModelProgress: vi.fn(async () => () => {}),
    onViberTool: vi.fn(async () => () => {}),
  }));
}

describe("folded library mount", () => {
  beforeEach(() => {
    vi.resetModules();
    mockApi();
    document.body.innerHTML = "";
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("mounts Viber into a provided shell root without touching outside data-for nodes", async () => {
    const shellOnly = document.createElement("div");
    shellOnly.dataset.for = "status-tip";
    shellOnly.textContent = "shell tooltip";
    document.body.append(shellOnly);

    const mount = document.createElement("section");
    mount.innerHTML = extractSurfaceMarkup(libraryHtmlRaw, ".vmx-lib-app");
    document.body.append(mount);

    const { mountLibrary } = await import("./index.js");
    mountLibrary(mount);

    const app = mount.querySelector<HTMLElement>(".vmx-lib-app");
    expect(app?.dataset.mode).toBe("chat");
    expect(mount.querySelector("#vmx-lib-runbtn")?.textContent).toBe("Send");
    expect(shellOnly.style.display).toBe("");
    expect(shellOnly.dataset.for).toBe("status-tip");
  });
});
