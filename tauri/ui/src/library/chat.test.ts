// SPDX-License-Identifier: Apache-2.0
/**
 * @vitest-environment jsdom
 */
/* Vibe Engine - chat UI spec.
 *
 * Exercises the real mountLibrary -> runChat path so the conversational Viber
 * surface keeps grounded tools, artifacts, and multi-turn history wired.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  LibraryChatResult,
  LibraryModelInstallTarget,
  LibraryModelsResult,
  LibraryStats,
} from "./api.js";

const chatMock = vi.fn<
  (message: string, history: unknown[]) => Promise<LibraryChatResult>
>();

const STATS_READY: LibraryStats = {
  indexed: 12,
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
      id: "cue-detr",
      label: "CUE-DETR ONNX",
      role: "cue anchors",
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

const CHAT_WITH_PLAYLIST: LibraryChatResult = {
  reply: "Pull SMOKED OUT after the current track and keep the low end clean.",
  tool_trace: [
    { name: "search_vibe", arg: "dark peak techno", ok: true },
    { name: "create_playlist", arg: "Dark Fuse", ok: true },
  ],
  playlist: {
    name: "Dark Fuse",
    track_ids: ["t001", "t002"],
    m3u_path: "/Users/ozai/.cache/vibemix/playlists/dark-fuse.m3u",
    json_path: "/Users/ozai/.cache/vibemix/playlists/dark-fuse.json",
    dropped_ids: [],
  },
  export_path: null,
  seen_track_ids: ["t001", "t002"],
  iterations: 3,
  stop_reason: "created",
};

function doMockApi(): void {
  vi.doMock("./api.js", () => ({
    libraryChat: (message: string, history: unknown[]) =>
      chatMock(message, history),
    libraryBuildSet: vi.fn(async () => ({
      name: "x",
      rationale: "",
      stop_reason: "exported",
      tracks: [],
      count: 0,
      export_path: null,
    })),
    libraryCurate: vi.fn(async () => ({
      name: "x",
      rationale: "",
      stop_reason: "created",
      tracks: [],
      count: 0,
    })),
    librarySearch: vi.fn(async () => ({ results: [], centered: true, corpus_size: 0 })),
    librarySimilar: vi.fn(async () => ({ results: [], centered: true, corpus_size: 0 })),
    libraryStats: vi.fn(async () => STATS_READY),
    libraryModels: vi.fn(async (_install?: LibraryModelInstallTarget) => MODELS_READY),
    libraryEmbedFolder: vi.fn(async () => false),
    onEmbedProgress: vi.fn(async () => () => {}),
    onEmbedDone: vi.fn(async () => () => {}),
    onModelProgress: vi.fn(async () => () => {}),
    DEV_FALLBACK: { embedLog: [] },
  }));
}

function mountSkeleton(): void {
  document.body.dataset.mode = "chat";
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
    <input id="vmx-lib-theme" />
    <textarea id="vmx-lib-brief"></textarea>
    <textarea id="vmx-lib-chat"></textarea>
    <div class="vmx-lib-curve">
      <button data-curve="opener" aria-pressed="false">Opener</button>
      <button data-curve="peak_time" aria-pressed="true">Peak time</button>
      <button data-curve="after_hours" aria-pressed="false">After hours</button>
      <button data-curve="festival" aria-pressed="false">Festival</button>
    </div>
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
    <div id="vmx-lib-loglist"></div>
    <span id="vmx-lib-side-label"></span>
    <span id="vmx-lib-scope-state"></span>
    <div id="vmx-lib-chat-tools"></div>
    <div id="vmx-lib-chat-artifact"></div>
    <svg id="vmx-lib-scope"></svg>`;
}

async function mountChat(): Promise<void> {
  vi.resetModules();
  doMockApi();
  const { mountLibrary } = await import("./index.js");
  mountSkeleton();
  mountLibrary();
  for (let i = 0; i < 6; i++) await Promise.resolve();
}

async function sendChat(message: string): Promise<void> {
  const input = document.getElementById("vmx-lib-chat") as HTMLTextAreaElement;
  input.value = message;
  (document.getElementById("vmx-lib-runbtn") as HTMLButtonElement).click();
  for (let i = 0; i < 8; i++) await Promise.resolve();
}

describe("chat - real runChat path", () => {
  beforeEach(() => {
    chatMock.mockReset();
    chatMock.mockResolvedValue(CHAT_WITH_PLAYLIST);
    vi.resetModules();
    document.body.innerHTML = "";
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("renders a grounded tool trace and playlist artifact from one Viber turn", async () => {
    await mountChat();
    await sendChat("find two dark peak techno tracks");

    expect(chatMock).toHaveBeenCalledWith("find two dark peak techno tracks", []);

    const threadText = document.getElementById("vmx-lib-chat-thread")?.textContent ?? "";
    expect(threadText).toContain("find two dark peak techno tracks");
    expect(threadText).toContain("Pull SMOKED OUT");
    expect((document.getElementById("vmx-lib-chat") as HTMLTextAreaElement).value).toBe("");

    const toolText = document.getElementById("vmx-lib-chat-tools")?.textContent ?? "";
    expect(toolText).toContain("search_vibe");
    expect(toolText).toContain("dark peak techno");
    expect(toolText).toContain("create_playlist");

    const artifactText =
      document.getElementById("vmx-lib-chat-artifact")?.textContent ?? "";
    expect(artifactText).toContain("playlist");
    expect(artifactText).toContain("Dark Fuse");
    expect(artifactText).toContain("2 tracks");
    expect(artifactText).toContain("dark-fuse.m3u");
    expect(document.getElementById("vmx-lib-scope-state")?.textContent).toBe(
      "3 iter · created",
    );
  });

  it("renders live indexed count without the stale mock denominator", async () => {
    await mountChat();

    const indexed = document.getElementById("vmx-lib-stat-indexed")?.textContent ?? "";
    expect(indexed).toBe("12");
    expect(indexed).not.toContain("1547");
  });

  it("passes only completed prior turns as history on the next message", async () => {
    chatMock
      .mockResolvedValueOnce({ ...CHAT_WITH_PLAYLIST, reply: "First answer" })
      .mockResolvedValueOnce({ ...CHAT_WITH_PLAYLIST, reply: "Second answer" });

    await mountChat();
    await sendChat("first");
    await sendChat("second");

    expect(chatMock).toHaveBeenNthCalledWith(1, "first", []);
    expect(chatMock).toHaveBeenNthCalledWith(2, "second", [
      { role: "you", text: "first" },
      { role: "viber", text: "First answer" },
    ]);
  });

  it("does not keep a thrown backend turn in API history", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    chatMock
      .mockRejectedValueOnce(new Error("sidecar down"))
      .mockResolvedValueOnce({ ...CHAT_WITH_PLAYLIST, reply: "Recovered" });

    await mountChat();
    await sendChat("first");
    await sendChat("second");

    expect(chatMock).toHaveBeenNthCalledWith(1, "first", []);
    expect(chatMock).toHaveBeenNthCalledWith(2, "second", []);
    expect(errorSpy).toHaveBeenCalled();
    const threadText = document.getElementById("vmx-lib-chat-thread")?.textContent ?? "";
    expect(threadText).toContain("engine error: sidecar down");
    expect(threadText).toContain("Recovered");
  });
});
