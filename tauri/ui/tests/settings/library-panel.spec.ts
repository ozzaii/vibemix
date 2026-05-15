/* Phase 28 Plan 06 — library-panel vitest specs (jsdom).
 *
 * Mocks @tauri-apps/api/webview onDragDropEvent + ipc/client emitIpc /
 * subscribeIpc to drive the panel's drag-drop dedupe + progress flow.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const dragHandlers: Array<(event: { id: number; payload: unknown }) => void> = [];
const subscribers = new Map<string, (msg: unknown) => void>();
const emitted: { type: string; payload: Record<string, unknown> }[] = [];

vi.mock("../../src/ipc/client.js", () => ({
  emitIpc: vi.fn(async (type: string, payload: Record<string, unknown>) => {
    emitted.push({ type, payload });
  }),
  subscribeIpc: vi.fn(
    async (type: string, cb: (msg: unknown) => void) => {
      subscribers.set(type, cb);
      return () => subscribers.delete(type);
    },
  ),
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

import { renderLibraryPanel } from "../../src/settings/components/library-panel.js";

beforeEach(() => {
  dragHandlers.length = 0;
  subscribers.clear();
  emitted.length = 0;
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

describe("library-panel — drag-drop dedupe (Tauri Issue #14134)", () => {
  it("dedupes by event.id — same id fires emitIpc once", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(1, ["/path/to/lib.xml"]);
    dispatchDrop(1, ["/path/to/lib.xml"]);
    await _flush();

    const importCalls = emitted.filter(
      (e) => e.type === "ipc.library.import",
    );
    expect(importCalls).toHaveLength(1);
  });

  it("new event.id fires a new emitIpc — dedupe is per-event-id, not per-path", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(10, ["/path/to/lib.xml"]);
    dispatchDrop(10, ["/path/to/lib.xml"]);
    dispatchDrop(11, ["/path/to/lib.xml"]);
    await _flush();

    const importCalls = emitted.filter(
      (e) => e.type === "ipc.library.import",
    );
    expect(importCalls).toHaveLength(2);
  });
});

describe("library-panel — non-xml drop shows error", () => {
  it("status carries 'Need a .xml file' for .mp3 drops", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(20, ["/path/to/song.mp3"]);
    await _flush();

    const status = handle.element.querySelector(".vmx-library-status");
    expect(status?.textContent).toContain("Need a .xml file");
  });
});

describe("library-panel — progress updates fill width", () => {
  it("sets fill style.width to done/total %", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    // Trigger import to subscribe to progress.
    dispatchDrop(30, ["/lib.xml"]);
    await _flush();

    const cb = subscribers.get("ipc.library.import_progress");
    expect(cb).toBeDefined();
    cb!({
      type: "ipc.library.import_progress",
      ts: "2026-05-15T12:00:00Z",
      payload: {
        total: 100,
        done: 50,
        current_track_name: "X — Y",
        cache_hits: 10,
        cancelled: false,
        schema_version: "1",
      },
    });

    const fill = handle.element.querySelector(
      ".vmx-library-progress-fill",
    ) as HTMLElement;
    // jsdom drops trailing zero (50.0% → 50%); accept either form.
    expect(["50%", "50.0%"]).toContain(fill.style.width);
  });
});

describe("library-panel — cancel emits cancel message", () => {
  it("clicking Cancel emits ipc.library.import_cancel", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(40, ["/lib.xml"]);
    await _flush();

    const cancelBtn = handle.element.querySelector(
      ".vmx-library-cancel-btn",
    ) as HTMLButtonElement;
    cancelBtn.click();
    await _flush();

    const cancels = emitted.filter(
      (e) => e.type === "ipc.library.import_cancel",
    );
    expect(cancels).toHaveLength(1);
  });
});

describe("library-panel — completion hides progress", () => {
  it("done==total hides progress and shows N tracks indexed", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);

    dispatchDrop(50, ["/lib.xml"]);
    await _flush();
    const cb = subscribers.get("ipc.library.import_progress")!;
    cb({
      type: "ipc.library.import_progress",
      ts: "2026-05-15T12:00:00Z",
      payload: {
        total: 50,
        done: 50,
        current_track_name: "Z",
        cache_hits: 12,
        cancelled: false,
        schema_version: "1",
      },
    });

    const progress = handle.element.querySelector(".vmx-library-progress");
    expect(progress?.classList.contains("hidden")).toBe(true);
    const status = handle.element.querySelector(".vmx-library-status");
    expect(status?.textContent).toContain("50 tracks indexed");
    expect(status?.textContent).toContain("12 from cache");
  });
});

describe("library-panel — dispose unsubscribes", () => {
  it("after dispose, drop events do nothing", async () => {
    const handle = await renderLibraryPanel();
    document.body.append(handle.element);
    handle.dispose();

    dispatchDrop(60, ["/lib.xml"]);
    await _flush();

    const importCalls = emitted.filter(
      (e) => e.type === "ipc.library.import",
    );
    expect(importCalls).toHaveLength(0);
  });
});
