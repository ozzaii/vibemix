/* tray-mood.spec.ts — bug 3 (2026-05-24) regression guard.
 *
 * The Rust tray (tauri/src-tauri/src/tray.rs) emits a `tray-set-mood` event
 * carrying "hype-man" | "teacher" | "coach". Before the fix nothing in the
 * webview listened for it, so the tray Coach/Hype/Teacher switch was dead.
 *
 * Pins:
 *   1. installTrayMoodListener subscribes to the `tray-set-mood` event.
 *   2. A valid payload forwards ipc.settings.set { field: "mood", value }
 *      down the sidecar bridge (emitIpc → invoke("forward_ipc_to_sidecar")).
 *   3. An unknown payload is dropped (no IPC fired) — defensive narrowing.
 *   4. The returned unsubscribe fn tears the listener down.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { invokeMock, listenMock } = vi.hoisted(() => {
  return {
    invokeMock: vi.fn(
      async (
        _cmd: string,
        _args?: Record<string, unknown>,
      ): Promise<unknown> => undefined,
    ),
    // Capture the registered handler so the test can drive a synthetic
    // tray-set-mood event without a real Tauri runtime.
    listenMock: vi.fn(),
  };
});

vi.mock("@tauri-apps/api/core", () => ({
  invoke: invokeMock,
}));
vi.mock("@tauri-apps/api/event", () => ({
  listen: listenMock,
}));

import { installTrayMoodListener } from "../../src/session/tray-mood.js";

let capturedHandler: ((event: { payload: unknown }) => void) | null = null;
let unlistenSpy: ReturnType<typeof vi.fn>;

beforeEach(() => {
  invokeMock.mockClear();
  capturedHandler = null;
  unlistenSpy = vi.fn();
  listenMock.mockImplementation(
    async (event: string, handler: (e: { payload: unknown }) => void) => {
      expect(event).toBe("tray-set-mood");
      capturedHandler = handler;
      return unlistenSpy;
    },
  );
});

afterEach(() => {
  vi.clearAllMocks();
});

/** Extract the forwarded ipc.settings.set payload from the last
 *  invoke("forward_ipc_to_sidecar", { message }) call, or null. */
function lastSettingsSet(): { field: string; value: unknown } | null {
  for (let i = invokeMock.mock.calls.length - 1; i >= 0; i--) {
    const [cmd, args] = invokeMock.mock.calls[i]!;
    if (cmd !== "forward_ipc_to_sidecar") continue;
    const msg = (args as { message?: { type?: string; payload?: unknown } })
      ?.message;
    if (msg?.type === "ipc.settings.set") {
      return msg.payload as { field: string; value: unknown };
    }
  }
  return null;
}

describe("installTrayMoodListener", () => {
  it("subscribes to the tray-set-mood event", async () => {
    await installTrayMoodListener();
    expect(listenMock).toHaveBeenCalledWith("tray-set-mood", expect.any(Function));
  });

  it("forwards a valid mood to ipc.settings.set", async () => {
    await installTrayMoodListener();
    capturedHandler!({ payload: "coach" });
    // Let the fire-and-forget emitIpc microtask settle.
    await Promise.resolve();
    const set = lastSettingsSet();
    expect(set).toEqual({ field: "mood", value: "coach" });
  });

  it.each(["hype-man", "teacher", "coach"] as const)(
    "forwards %s verbatim as the wire mood value",
    async (mood) => {
      await installTrayMoodListener();
      capturedHandler!({ payload: mood });
      await Promise.resolve();
      expect(lastSettingsSet()).toEqual({ field: "mood", value: mood });
    },
  );

  it("drops an unknown mood payload without firing IPC", async () => {
    await installTrayMoodListener();
    capturedHandler!({ payload: "party-monster" });
    await Promise.resolve();
    expect(lastSettingsSet()).toBeNull();
  });

  it("returns an unsubscribe fn that tears the listener down", async () => {
    const off = await installTrayMoodListener();
    off();
    expect(unlistenSpy).toHaveBeenCalledTimes(1);
  });

  it("returns an inert unsubscribe when listen rejects (non-Tauri env)", async () => {
    listenMock.mockRejectedValueOnce(new Error("no tauri runtime"));
    const off = await installTrayMoodListener();
    expect(typeof off).toBe("function");
    expect(() => off()).not.toThrow();
  });
});
