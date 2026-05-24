/* debug-log.spec.ts — observability sink contract.
 *
 * Pins:
 *   1. formatLine builds the tagged `<tag> <msg> <data?>` shape.
 *   2. formatData JSON-stringifies + truncates oversized payloads.
 *   3. vmxLog always console.logs the tagged line (DevTools copy).
 *   4. vmxLog forwards the SAME line to invoke("debug_log", { line }) when a
 *      Tauri env is present.
 *   5. Non-Tauri fallback: when @tauri-apps/api/core is unavailable the file
 *      forward is silently skipped — console-only, no throw.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { invokeMock } = vi.hoisted(() => {
  return {
    invokeMock: vi.fn(
      async (_cmd: string, _args?: Record<string, unknown>): Promise<unknown> =>
        undefined,
    ),
  };
});

vi.mock("@tauri-apps/api/core", () => ({
  invoke: invokeMock,
}));

import {
  _resetInvokeCacheForTests,
  formatData,
  formatLine,
  vmxLog,
} from "../src/debug-log.js";

let logSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  invokeMock.mockClear();
  _resetInvokeCacheForTests();
  logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
});

afterEach(() => {
  logSpy.mockRestore();
  vi.clearAllMocks();
});

/** Flush queued work so vmxLog's fire-and-forget chain (dynamic import →
 *  invoke) resolves. The dynamic `import()` settles on a macrotask, so a
 *  setTimeout(0) is needed in addition to microtask drains. */
async function flush(): Promise<void> {
  for (let i = 0; i < 5; i++) {
    await new Promise((r) => setTimeout(r, 0));
  }
}

describe("formatLine", () => {
  it("builds `<tag> <msg>` with no trailing data", () => {
    expect(formatLine("[vmx:click]", "rocker · mood")).toBe(
      "[vmx:click] rocker · mood",
    );
  });

  it("appends JSON-stringified data when provided", () => {
    expect(formatLine("[vmx:ipc>]", "emit mood", { value: "hype-man" })).toBe(
      '[vmx:ipc>] emit mood {"value":"hype-man"}',
    );
  });
});

describe("formatData", () => {
  it("returns empty string for undefined", () => {
    expect(formatData(undefined)).toBe("");
  });

  it("passes a string payload through verbatim", () => {
    expect(formatData("hello")).toBe("hello");
  });

  it("truncates an oversized payload with a +N suffix", () => {
    const big = "x".repeat(5000);
    const out = formatData(big);
    expect(out.length).toBeLessThan(big.length);
    expect(out).toContain("…(+");
    expect(out.endsWith(" chars)")).toBe(true);
  });

  it("does not throw on a circular structure", () => {
    const circular: Record<string, unknown> = {};
    circular.self = circular;
    expect(() => formatData(circular)).not.toThrow();
  });
});

describe("vmxLog — console copy", () => {
  it("always console.logs the tagged line", () => {
    vmxLog("[vmx:state]", "boot: start");
    expect(logSpy).toHaveBeenCalledWith("[vmx:state] boot: start");
  });
});

describe("vmxLog — Tauri file forward", () => {
  it("forwards the same line to invoke('debug_log', { line })", async () => {
    vmxLog("[vmx:error]", "uncaught", { message: "boom" });
    await flush();
    expect(invokeMock).toHaveBeenCalledTimes(1);
    expect(invokeMock).toHaveBeenCalledWith("debug_log", {
      line: '[vmx:error] uncaught {"message":"boom"}',
    });
  });

  it("never throws when the forward rejects (non-fatal)", async () => {
    invokeMock.mockRejectedValueOnce(new Error("command not registered"));
    expect(() => vmxLog("[vmx:ws]", "connection connected")).not.toThrow();
    await flush();
    // Console copy still happened despite the forward failure.
    expect(logSpy).toHaveBeenCalledWith("[vmx:ws] connection connected");
  });
});
