import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  emitIpc: vi.fn(async (_type: string, _payload?: unknown) => undefined),
  invoke: vi.fn(async (_cmd: string, _args?: unknown) => undefined),
}));

vi.mock("@tauri-apps/api/core", () => ({
  invoke: mocks.invoke,
}));

vi.mock("../../src/ipc/client.js", () => ({
  emitIpc: mocks.emitIpc,
}));

import { _internals } from "../../src/session/render-loop.js";
import {
  _resetSessionStateForTests,
  getSessionState,
} from "../../src/session/state.js";

beforeEach(() => {
  mocks.emitIpc.mockReset();
  mocks.emitIpc.mockResolvedValue(undefined);
  mocks.invoke.mockReset();
  mocks.invoke.mockResolvedValue(undefined);
  _resetSessionStateForTests();
});

async function flushModeChange(): Promise<void> {
  for (let i = 0; i < 3; i++) await Promise.resolve();
}

function deferred<T = undefined>(): {
  promise: Promise<T>;
  resolve: (value: T | PromiseLike<T>) => void;
} {
  let resolve!: (value: T | PromiseLike<T>) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

describe("render-loop mode picker actions", () => {
  it("build mode opens Vibe Engine and persists mode", async () => {
    _internals.modeChangeHandler("build");
    await flushModeChange();

    expect(getSessionState().mode).toBe("build");
    expect(mocks.invoke).toHaveBeenCalledWith("open_library_window");
    expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.session.set_mode", {
      mode: "build",
    });
  });

  it("debrief mode opens latest Debrief and persists mode", async () => {
    _internals.modeChangeHandler("debrief");
    await flushModeChange();

    expect(getSessionState().mode).toBe("debrief");
    expect(mocks.invoke).toHaveBeenCalledWith("open_debrief_window", {
      sessionDir: "",
    });
    expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.session.set_mode", {
      mode: "debrief",
    });
  });

  it("reverts optimistic mode and skips persistence when the owning window fails", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    mocks.invoke.mockRejectedValueOnce(new Error("window denied"));

    _internals.modeChangeHandler("build");
    await flushModeChange();

    expect(getSessionState().mode).toBe("cohost");
    expect(mocks.invoke).toHaveBeenCalledWith("open_library_window");
    expect(mocks.emitIpc).not.toHaveBeenCalledWith("ipc.session.set_mode", {
      mode: "build",
    });
    expect(warn).toHaveBeenCalledWith(
      "[render-loop] mode surface open failed:",
      expect.any(Error),
    );
  });

  it("does not persist an older mode when its window opens after a newer pick", async () => {
    const buildOpen = deferred();
    mocks.invoke.mockImplementation(async (cmd: string, _args?: unknown) => {
      if (cmd === "open_library_window") return buildOpen.promise;
      return undefined;
    });

    _internals.modeChangeHandler("build");
    _internals.modeChangeHandler("debrief");
    await flushModeChange();

    expect(getSessionState().mode).toBe("debrief");
    expect(mocks.invoke).toHaveBeenCalledWith("open_library_window");
    expect(mocks.invoke).toHaveBeenCalledWith("open_debrief_window", {
      sessionDir: "",
    });
    expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.session.set_mode", {
      mode: "debrief",
    });

    buildOpen.resolve(undefined);
    await flushModeChange();

    expect(getSessionState().mode).toBe("debrief");
    expect(mocks.emitIpc).not.toHaveBeenCalledWith("ipc.session.set_mode", {
      mode: "build",
    });
  });
});
