/* Phase 28 Plan 06 — library-panel vitest specs (jsdom).
 *
 * Mocks @tauri-apps/api/webview onDragDropEvent + the library embed bridge
 * to drive the panel's drag-drop dedupe + progress flow.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const dragHandlers: Array<(event: { id: number; payload: unknown }) => void> = [];
const emitted: { type: string; payload: Record<string, unknown> }[] = [];
type ProgressFrame = {
  n: number;
  total: number;
  status: "ok" | "skip" | "err";
  filename: string;
  cost_eur: number;
};
type DoneFrame = {
  embedded: number;
  skipped: number;
  failed: number;
  total: number;
  cost_eur: number;
};
const dialogMocks = vi.hoisted(() => ({
  open: vi.fn(),
}));
const libraryApiMocks = vi.hoisted(() => ({
  libraryEmbedFolder: vi.fn(),
  onEmbedProgress: vi.fn(),
  onEmbedDone: vi.fn(),
  progressHandlers: new Set<(p: ProgressFrame) => void>(),
  doneHandlers: new Set<(d: DoneFrame) => void>(),
}));

vi.mock("../../src/ipc/client.js", () => ({
  emitIpc: vi.fn(async (type: string, payload: Record<string, unknown>) => {
    emitted.push({ type, payload });
  }),
  subscribeIpc: vi.fn(),
}));

vi.mock("../../src/library/api.js", () => ({
  libraryEmbedFolder: libraryApiMocks.libraryEmbedFolder,
  onEmbedProgress: libraryApiMocks.onEmbedProgress,
  onEmbedDone: libraryApiMocks.onEmbedDone,
}));

vi.mock("@tauri-apps/api/webview", () => ({
  getCurrentWebview: () => ({
    onDragDropEvent: async (
      cb: (event: { id: number; payload: unknown }) => void,
    ) => {
      dragHandlers.push(cb);
      return () => {
        const idx = dragHandlers.indexOf(cb);
        if (idx >= 0) dragHandlers.splice(idx, 1);
      };
    },
  }),
}));

vi.mock("@tauri-apps/plugin-dialog", () => ({
  open: dialogMocks.open,
}));

import { renderLibraryPanel } from "../../src/settings/components/library-panel.js";

beforeEach(() => {
  dragHandlers.length = 0;
  emitted.length = 0;
  dialogMocks.open.mockReset();
  dialogMocks.open.mockResolvedValue(null);
  libraryApiMocks.progressHandlers.clear();
  libraryApiMocks.doneHandlers.clear();
  libraryApiMocks.libraryEmbedFolder.mockReset();
  libraryApiMocks.libraryEmbedFolder.mockResolvedValue(true);
  libraryApiMocks.onEmbedProgress.mockReset();
  libraryApiMocks.onEmbedProgress.mockImplementation(async (cb) => {
    libraryApiMocks.progressHandlers.add(cb);
    return () => libraryApiMocks.progressHandlers.delete(cb);
  });
  libraryApiMocks.onEmbedDone.mockReset();
  libraryApiMocks.onEmbedDone.mockImplementation(async (cb) => {
    libraryApiMocks.doneHandlers.add(cb);
    return () => libraryApiMocks.doneHandlers.delete(cb);
  });
  document.body.replaceChildren();
});

afterEach(() => {
  document.body.replaceChildren();
});

async function _flush(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

function dispatchDrop(eventId: number, paths: string[]): void {
  for (const cb of dragHandlers) {
    cb({ id: eventId, payload: { type: "drop", paths } });
  }
}

function emitProgress(frame: ProgressFrame): void {
  for (const cb of libraryApiMocks.progressHandlers) cb(frame);
}

function emitDone(frame: DoneFrame): void {
  for (const cb of libraryApiMocks.doneHandlers) cb(frame);
}

describe("library-panel — drag-drop dedupe (Tauri Issue #14134)", () => {
  it("dedupes by event.id — same id starts one folder embed", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(1, ["/Users/kaan/Music/PSYMIND"]);
    dispatchDrop(1, ["/Users/kaan/Music/PSYMIND"]);
    await _flush();

    expect(libraryApiMocks.libraryEmbedFolder).toHaveBeenCalledTimes(1);
    expect(libraryApiMocks.libraryEmbedFolder).toHaveBeenCalledWith(
      "/Users/kaan/Music/PSYMIND",
      "mean_excerpt",
    );
  });

  it("new event.id starts a new embed — dedupe is per-event-id, not per-path", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(10, ["/Users/kaan/Music/PSYMIND"]);
    dispatchDrop(10, ["/Users/kaan/Music/PSYMIND"]);
    dispatchDrop(11, ["/Users/kaan/Music/PSYMIND"]);
    await _flush();

    expect(libraryApiMocks.libraryEmbedFolder).toHaveBeenCalledTimes(2);
  });
});

describe("library-panel — source drop routing", () => {
  it("accepts a music folder path as a folder embed source", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(19, ["/Users/kaan/Music/PSYMIND"]);
    await _flush();

    expect(libraryApiMocks.libraryEmbedFolder).toHaveBeenCalledWith(
      "/Users/kaan/Music/PSYMIND",
      "mean_excerpt",
    );
  });

  it("status tells DJs to drop a folder for single audio-file drops", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(20, ["/path/to/song.mp3"]);
    await _flush();

    const status = handle.element.querySelector(".vmx-library-status");
    expect(status?.textContent).toContain("Drop a music folder");
  });

  it("copy advertises folder setup only", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    const drop = handle.element.querySelector(".vmx-library-droptarget");
    expect(drop?.getAttribute("aria-label")).toBe("Drop a music folder here");
    expect(drop?.textContent).toContain("Drop a music folder here");
    expect(drop?.textContent).not.toContain("Rekordbox XML");
  });
});

describe("library-panel — native picker", () => {
  it("Choose folder opens the native folder picker and embeds the selected path", async () => {
    dialogMocks.open.mockResolvedValue("/Users/kaan/Music/PSYMIND");
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    const pickFolderBtn = handle.element.querySelector(
      ".vmx-library-pick-folder-btn",
    ) as HTMLButtonElement;
    pickFolderBtn.click();
    await _flush();
    await _flush();

    expect(dialogMocks.open).toHaveBeenCalledWith({
      title: "Choose music folder",
      directory: true,
      multiple: false,
    });
    expect(libraryApiMocks.libraryEmbedFolder).toHaveBeenCalledWith(
      "/Users/kaan/Music/PSYMIND",
      "mean_excerpt",
    );
  });

  it("cancelling the native picker leaves embed untouched and reports no selection", async () => {
    dialogMocks.open.mockResolvedValue(null);
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    const pickFolderBtn = handle.element.querySelector(
      ".vmx-library-pick-folder-btn",
    ) as HTMLButtonElement;
    pickFolderBtn.click();
    await _flush();
    await _flush();

    expect(libraryApiMocks.libraryEmbedFolder).not.toHaveBeenCalled();
    expect(handle.element.querySelector(".vmx-library-status")?.textContent).toBe(
      "No music folder selected.",
    );
  });
});

describe("library-panel — progress updates fill width", () => {
  it("sets fill style.width to done/total %", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    // Trigger import to subscribe to progress.
    dispatchDrop(30, ["/Music/PSYMIND"]);
    await _flush();

    expect(libraryApiMocks.onEmbedProgress).toHaveBeenCalled();
    emitProgress({
      n: 50,
      total: 100,
      status: "ok",
      filename: "X - Y.wav",
      cost_eur: 0.0025,
    });

    const fill = handle.element.querySelector(
      ".vmx-library-progress-fill",
    ) as HTMLElement;
    // jsdom drops trailing zero (50.0% → 50%); accept either form.
    expect(["50%", "50.0%"]).toContain(fill.style.width);
  });
});

describe("library-panel — programmatic refresh", () => {
  it("beginImport embeds folders for stale-source refreshes", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    await handle.beginImport("/path/to/folder");
    await _flush();

    expect(libraryApiMocks.libraryEmbedFolder).toHaveBeenCalledWith(
      "/path/to/folder",
      "mean_excerpt",
    );
  });

  it("beginImport rejects catalog-file paths instead of firing dead IPC", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    await handle.beginImport("/path/to/collection.xml");
    await _flush();

    expect(libraryApiMocks.libraryEmbedFolder).not.toHaveBeenCalled();
    expect(handle.element.querySelector(".vmx-library-status")?.textContent).toBe(
      "Choose a music folder, not a database file.",
    );
  });

  it("beginFolderReindex emits the folder staleness action", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    await handle.beginFolderReindex();
    await _flush();

    expect(emitted).toContainEqual({
      type: "ipc.library.staleness_action",
      payload: { action: "reindex_folder", schema_version: "1" },
    });
    expect(libraryApiMocks.onEmbedProgress).toHaveBeenCalled();
  });
});

describe("library-panel — completion hides progress", () => {
  it("embed-done hides progress and shows the embed receipt", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(50, ["/Music/PSYMIND"]);
    await _flush();
    emitDone({
      embedded: 38,
      skipped: 12,
      failed: 0,
      total: 50,
      cost_eur: 0.02,
    });

    const progress = handle.element.querySelector(".vmx-library-progress");
    expect(progress?.classList.contains("hidden")).toBe(true);
    const status = handle.element.querySelector(".vmx-library-status");
    expect(status?.textContent).toContain("38 embedded");
    expect(status?.textContent).toContain("12 cached");
  });
});

describe("library-panel — dispose unsubscribes", () => {
  it("after dispose, drop events do nothing", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);
    handle.dispose();

    dispatchDrop(60, ["/Music/PSYMIND"]);
    await _flush();

    expect(libraryApiMocks.libraryEmbedFolder).not.toHaveBeenCalled();
  });

  it("immediately unsubs when progress subscribe resolves after dispose", async () => {
    let progressCb: (msg: ProgressFrame) => void = (_msg: ProgressFrame) => {
      throw new Error("expected progress subscription callback");
    };
    let resolveSubscribe: (fn: () => void) => void = (_fn: () => void) => {
      throw new Error("expected delayed subscription resolver");
    };
    let sawProgressCb = false;
    let sawResolveSubscribe = false;
    let unlistenCalls = 0;
    const onImportComplete = vi.fn();
    libraryApiMocks.onEmbedProgress.mockImplementationOnce(async (cb) => {
      progressCb = cb;
      return await new Promise<() => void>((resolve) => {
        resolveSubscribe = resolve;
        sawProgressCb = true;
        sawResolveSubscribe = true;
      });
    });

    const handle = await renderLibraryPanel({ onImportComplete });
    document.body.append(handle.element);
    dispatchDrop(70, ["/Music/PSYMIND"]);
    await _flush();

    handle.dispose();
    expect(sawProgressCb).toBe(true);
    progressCb({
      n: 10,
      total: 10,
      status: "ok",
      filename: "Late Track.wav",
      cost_eur: 0.004,
    });
    expect(sawResolveSubscribe).toBe(true);
    resolveSubscribe(() => {
      unlistenCalls += 1;
    });
    await _flush();

    expect(unlistenCalls).toBe(1);
    expect(onImportComplete).not.toHaveBeenCalled();
    expect(handle.element.querySelector(".vmx-library-status")?.textContent).not.toContain(
      "embedded",
    );
  });
});
