/* Phase 28 Plan 06 — library-panel vitest specs (jsdom).
 *
 * Mocks @tauri-apps/api/webview onDragDropEvent + the library import bridge
 * to drive the panel's drag-drop dedupe + progress flow.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const dragHandlers: Array<(event: { id: number; payload: unknown }) => void> = [];
const emitted: { type: string; payload: Record<string, unknown> }[] = [];
type ProgressFrame = {
  total: number;
  done: number;
  current_track_name: string;
  cache_hits: number;
  cancelled: boolean;
};
const dialogMocks = vi.hoisted(() => ({
  open: vi.fn(),
}));
const libraryApiMocks = vi.hoisted(() => ({
  libraryCancelImport: vi.fn(),
  libraryImport: vi.fn(),
  onLibraryImportProgress: vi.fn(),
  progressHandlers: new Set<(p: ProgressFrame) => void>(),
}));

vi.mock("../../src/ipc/client.js", () => ({
  emitIpc: vi.fn(async (type: string, payload: Record<string, unknown>) => {
    emitted.push({ type, payload });
  }),
  subscribeIpc: vi.fn(),
}));

vi.mock("../../src/library/api.js", () => ({
  libraryCancelImport: libraryApiMocks.libraryCancelImport,
  libraryImport: libraryApiMocks.libraryImport,
  onLibraryImportProgress: libraryApiMocks.onLibraryImportProgress,
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
  libraryApiMocks.libraryCancelImport.mockReset();
  libraryApiMocks.libraryCancelImport.mockResolvedValue(undefined);
  libraryApiMocks.libraryImport.mockReset();
  libraryApiMocks.libraryImport.mockResolvedValue(true);
  libraryApiMocks.onLibraryImportProgress.mockReset();
  libraryApiMocks.onLibraryImportProgress.mockImplementation(async (cb) => {
    libraryApiMocks.progressHandlers.add(cb);
    return () => libraryApiMocks.progressHandlers.delete(cb);
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

describe("library-panel — drag-drop dedupe (Tauri Issue #14134)", () => {
  it("dedupes by event.id — same id starts one library import", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(1, ["/Users/kaan/Music/PSYMIND"]);
    dispatchDrop(1, ["/Users/kaan/Music/PSYMIND"]);
    await _flush();

    expect(libraryApiMocks.libraryImport).toHaveBeenCalledTimes(1);
    expect(libraryApiMocks.libraryImport).toHaveBeenCalledWith(
      "/Users/kaan/Music/PSYMIND",
    );
  });

  it("new event.id starts a new import — dedupe is per-event-id, not per-path", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(10, ["/Users/kaan/Music/PSYMIND"]);
    dispatchDrop(10, ["/Users/kaan/Music/PSYMIND"]);
    dispatchDrop(11, ["/Users/kaan/Music/PSYMIND"]);
    await _flush();

    expect(libraryApiMocks.libraryImport).toHaveBeenCalledTimes(2);
  });
});

describe("library-panel — source drop routing", () => {
  it("accepts a music folder path as an import source", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(19, ["/Users/kaan/Music/PSYMIND"]);
    await _flush();

    expect(libraryApiMocks.libraryImport).toHaveBeenCalledWith(
      "/Users/kaan/Music/PSYMIND",
    );
  });

  it("accepts a DJ catalog file as an import source", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(21, ["/Users/kaan/Music/rekordbox/collection.xml"]);
    await _flush();

    expect(libraryApiMocks.libraryImport).toHaveBeenCalledWith(
      "/Users/kaan/Music/rekordbox/collection.xml",
    );
  });

  it("status tells DJs to drop a folder for single audio-file drops", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(20, ["/path/to/song.mp3"]);
    await _flush();

    const status = handle.element.querySelector(".vmx-library-status");
    expect(status?.textContent).toContain("Drop a music folder or DJ catalog");
  });

  it("copy advertises folder and DJ catalog setup", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    expect(handle.element.querySelector(".vmx-library-panel__title")?.textContent).toBe(
      "Feed Viber real tracks",
    );
    expect(
      Array.from(handle.element.querySelectorAll(".vmx-library-format-chip")).map(
        (chip) => chip.textContent?.trim(),
      ),
    ).toEqual(["folders", "rekordbox", "traktor", "engine"]);
    const drop = handle.element.querySelector(".vmx-library-droptarget");
    expect(drop?.getAttribute("aria-label")).toBe(
      "Drop a music folder or DJ catalog here",
    );
    expect(drop?.textContent).toContain("Drop music folder or DJ catalog");
    expect(drop?.textContent).toContain("Choose catalog");
  });
});

describe("library-panel — native picker", () => {
  it("Choose folder opens the native folder picker and imports the selected path", async () => {
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
    expect(libraryApiMocks.libraryImport).toHaveBeenCalledWith(
      "/Users/kaan/Music/PSYMIND",
    );
  });

  it("Choose catalog opens the native file picker and imports the selected catalog", async () => {
    dialogMocks.open.mockResolvedValue("/Users/kaan/rekordbox/collection.xml");
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    const pickCatalogBtn = handle.element.querySelector(
      ".vmx-library-pick-catalog-btn",
    ) as HTMLButtonElement;
    pickCatalogBtn.click();
    await _flush();
    await _flush();

    expect(dialogMocks.open).toHaveBeenCalledWith({
      title: "Choose DJ library catalog",
      directory: false,
      multiple: false,
      filters: [
        {
          name: "DJ library catalogs",
          extensions: ["xml", "nml", "db"],
        },
      ],
    });
    expect(libraryApiMocks.libraryImport).toHaveBeenCalledWith(
      "/Users/kaan/rekordbox/collection.xml",
    );
  });

  it("cancelling the native picker leaves import untouched and reports no selection", async () => {
    dialogMocks.open.mockResolvedValue(null);
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    const pickFolderBtn = handle.element.querySelector(
      ".vmx-library-pick-folder-btn",
    ) as HTMLButtonElement;
    pickFolderBtn.click();
    await _flush();
    await _flush();

    expect(libraryApiMocks.libraryImport).not.toHaveBeenCalled();
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

    expect(libraryApiMocks.onLibraryImportProgress).toHaveBeenCalled();
    emitProgress({
      total: 100,
      done: 50,
      current_track_name: "X - Y.wav",
      cache_hits: 0,
      cancelled: false,
    });

    const fill = handle.element.querySelector(
      ".vmx-library-progress-fill",
    ) as HTMLElement;
    // jsdom drops trailing zero (50.0% → 50%); accept either form.
    expect(["50%", "50.0%"]).toContain(fill.style.width);
  });

  it("Cancel sends a real library import cancel", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(31, ["/Music/PSYMIND"]);
    await _flush();

    const cancel = handle.element.querySelector(
      ".vmx-library-cancel-btn",
    ) as HTMLButtonElement;
    expect(cancel.hidden).toBe(false);
    cancel.click();

    expect(libraryApiMocks.libraryCancelImport).toHaveBeenCalledTimes(1);
    expect(cancel.disabled).toBe(true);
  });
});

describe("library-panel — programmatic refresh", () => {
  it("beginImport imports folders for stale-source refreshes", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    await handle.beginImport("/path/to/folder");
    await _flush();

    expect(libraryApiMocks.libraryImport).toHaveBeenCalledWith(
      "/path/to/folder",
    );
  });

  it("beginImport routes catalog-file paths through the rich import path", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    await handle.beginImport("/path/to/collection.xml");
    await _flush();

    expect(libraryApiMocks.libraryImport).toHaveBeenCalledWith(
      "/path/to/collection.xml",
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
    expect(libraryApiMocks.onLibraryImportProgress).toHaveBeenCalled();
  });
});

describe("library-panel — completion hides progress", () => {
  it("import-progress terminal frame hides progress and shows the receipt", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(50, ["/Music/PSYMIND"]);
    await _flush();
    emitProgress({
      total: 50,
      done: 50,
      current_track_name: "",
      cache_hits: 12,
      cancelled: false,
    });

    const progress = handle.element.querySelector(".vmx-library-progress");
    expect(progress?.classList.contains("hidden")).toBe(true);
    const status = handle.element.querySelector(".vmx-library-status");
    expect(status?.textContent).toContain("50 processed");
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

    expect(libraryApiMocks.libraryImport).not.toHaveBeenCalled();
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
    libraryApiMocks.onLibraryImportProgress.mockImplementationOnce(async (cb) => {
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
      total: 10,
      done: 10,
      current_track_name: "Late Track.wav",
      cache_hits: 0,
      cancelled: false,
    });
    expect(sawResolveSubscribe).toBe(true);
    resolveSubscribe(() => {
      unlistenCalls += 1;
    });
    await _flush();

    expect(unlistenCalls).toBe(1);
    expect(onImportComplete).not.toHaveBeenCalled();
    expect(handle.element.querySelector(".vmx-library-status")?.textContent).not.toContain(
      "processed",
    );
  });
});
