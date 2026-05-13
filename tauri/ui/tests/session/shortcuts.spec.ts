/* Impeccable Wave 5.A — global keyboard registry coverage.
 *
 * Asserts:
 *   - registerShortcuts attaches a document keydown listener that fires
 *     the matching callback exactly once per keydown.
 *   - Keydown targeting <input>/<textarea>/[contenteditable] is skipped.
 *   - The returned unregister function detaches the listener (subsequent
 *     keydowns do not fire the callback).
 *   - Cross-platform: stubbing navigator.platform to "MacIntel" makes
 *     `cmd+m` fire on metaKey; stubbing to "Win32" makes the same combo
 *     fire on ctrlKey instead.
 *
 * Vitest env: jsdom (routed via vitest.config.ts `tests/**\/*.spec.ts`). */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { _internals, registerShortcuts } from "../../src/session/shortcuts.js";

function fireKey(opts: KeyboardEventInit & { key: string }): void {
  const ev = new KeyboardEvent("keydown", { bubbles: true, ...opts });
  document.dispatchEvent(ev);
}

function stubPlatform(platform: string): void {
  Object.defineProperty(globalThis.navigator, "platform", {
    value: platform,
    configurable: true,
  });
}

afterEach(() => {
  document.body.replaceChildren();
  // Reset platform to a known default between tests. jsdom's default is
  // empty; we restore that.
  stubPlatform("");
  vi.restoreAllMocks();
});

describe("registerShortcuts — single-key combos", () => {
  it("fires the matched callback on keydown", () => {
    const onQ = vi.fn();
    registerShortcuts({ "?": onQ });
    fireKey({ key: "?" });
    expect(onQ).toHaveBeenCalledTimes(1);
  });

  it("matches `esc` against the Escape key", () => {
    const onEsc = vi.fn();
    registerShortcuts({ esc: onEsc });
    fireKey({ key: "Escape" });
    expect(onEsc).toHaveBeenCalledTimes(1);
  });

  it("does NOT fire a different combo on the same key", () => {
    const onQ = vi.fn();
    const onEsc = vi.fn();
    registerShortcuts({ "?": onQ, esc: onEsc });
    fireKey({ key: "?" });
    expect(onQ).toHaveBeenCalledTimes(1);
    expect(onEsc).not.toHaveBeenCalled();
  });
});

describe("registerShortcuts — modified combos", () => {
  it("matches cmd+m via metaKey on macOS", () => {
    stubPlatform("MacIntel");
    const onMute = vi.fn();
    registerShortcuts({ "cmd+m": onMute });
    fireKey({ key: "m", metaKey: true });
    expect(onMute).toHaveBeenCalledTimes(1);
  });

  it("matches cmd+m via ctrlKey on Windows (cmd maps to ctrl)", () => {
    stubPlatform("Win32");
    const onMute = vi.fn();
    registerShortcuts({ "cmd+m": onMute });
    fireKey({ key: "m", ctrlKey: true });
    expect(onMute).toHaveBeenCalledTimes(1);
  });

  it("does NOT fire cmd+m on bare m keypress", () => {
    stubPlatform("MacIntel");
    const onMute = vi.fn();
    registerShortcuts({ "cmd+m": onMute });
    fireKey({ key: "m" });
    expect(onMute).not.toHaveBeenCalled();
  });

  it("requires exact modifier match — cmd+m does NOT fire on cmd+shift+m", () => {
    stubPlatform("MacIntel");
    const onMute = vi.fn();
    registerShortcuts({ "cmd+m": onMute });
    fireKey({ key: "m", metaKey: true, shiftKey: true });
    expect(onMute).not.toHaveBeenCalled();
  });
});

describe("registerShortcuts — focus discipline", () => {
  it("skips when target is an <input>", () => {
    const onQ = vi.fn();
    registerShortcuts({ "?": onQ });
    const input = document.createElement("input");
    document.body.append(input);
    input.focus();
    const ev = new KeyboardEvent("keydown", { key: "?", bubbles: true });
    input.dispatchEvent(ev);
    expect(onQ).not.toHaveBeenCalled();
  });

  it("skips when target is a <textarea>", () => {
    const onQ = vi.fn();
    registerShortcuts({ "?": onQ });
    const ta = document.createElement("textarea");
    document.body.append(ta);
    const ev = new KeyboardEvent("keydown", { key: "?", bubbles: true });
    ta.dispatchEvent(ev);
    expect(onQ).not.toHaveBeenCalled();
  });

  it("skips when target is contenteditable", () => {
    const onQ = vi.fn();
    registerShortcuts({ "?": onQ });
    const div = document.createElement("div");
    div.setAttribute("contenteditable", "true");
    // jsdom doesn't always reflect contenteditable into isContentEditable;
    // forcibly stub the getter so the registry's check matches a real
    // browser's behavior.
    Object.defineProperty(div, "isContentEditable", {
      value: true,
      configurable: true,
    });
    document.body.append(div);
    const ev = new KeyboardEvent("keydown", { key: "?", bubbles: true });
    div.dispatchEvent(ev);
    expect(onQ).not.toHaveBeenCalled();
  });

  it("still fires when a button is the target (clicks shouldn't trap shortcuts)", () => {
    const onEsc = vi.fn();
    registerShortcuts({ esc: onEsc });
    const btn = document.createElement("button");
    document.body.append(btn);
    const ev = new KeyboardEvent("keydown", { key: "Escape", bubbles: true });
    btn.dispatchEvent(ev);
    expect(onEsc).toHaveBeenCalledTimes(1);
  });
});

describe("registerShortcuts — unregister", () => {
  it("returns a function that detaches the listener", () => {
    const onQ = vi.fn();
    const unregister = registerShortcuts({ "?": onQ });
    fireKey({ key: "?" });
    expect(onQ).toHaveBeenCalledTimes(1);
    unregister();
    fireKey({ key: "?" });
    expect(onQ).toHaveBeenCalledTimes(1); // still 1, no new invocation
  });

  it("unregister is idempotent (does not throw on second call)", () => {
    const unregister = registerShortcuts({ "?": vi.fn() });
    unregister();
    expect(() => unregister()).not.toThrow();
  });
});

describe("registerShortcuts — preventDefault on match", () => {
  it("calls preventDefault on matched keys", () => {
    const onQ = vi.fn();
    registerShortcuts({ "?": onQ });
    const ev = new KeyboardEvent("keydown", { key: "?", bubbles: true, cancelable: true });
    document.dispatchEvent(ev);
    expect(ev.defaultPrevented).toBe(true);
  });

  it("does NOT preventDefault on unmatched keys", () => {
    const onQ = vi.fn();
    registerShortcuts({ "?": onQ });
    const ev = new KeyboardEvent("keydown", { key: "a", bubbles: true, cancelable: true });
    document.dispatchEvent(ev);
    expect(ev.defaultPrevented).toBe(false);
  });
});

describe("registerShortcuts — error containment", () => {
  it("swallows a callback throw and logs a warning", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const onQ = vi.fn(() => {
      throw new Error("boom");
    });
    registerShortcuts({ "?": onQ });
    expect(() => fireKey({ key: "?" })).not.toThrow();
    expect(onQ).toHaveBeenCalledTimes(1);
    expect(warn).toHaveBeenCalled();
  });
});

describe("parseCombo (internal)", () => {
  beforeEach(() => stubPlatform("MacIntel"));

  it("maps cmd → meta on Mac", () => {
    const parsed = _internals.parseCombo("cmd+m");
    expect(parsed.meta).toBe(true);
    expect(parsed.ctrl).toBe(false);
    expect(parsed.key).toBe("m");
  });

  it("maps cmd → ctrl on non-Mac", () => {
    stubPlatform("Win32");
    const parsed = _internals.parseCombo("cmd+m");
    expect(parsed.ctrl).toBe(true);
    expect(parsed.meta).toBe(false);
  });

  it("parses `esc` to escape", () => {
    const parsed = _internals.parseCombo("esc");
    expect(parsed.key).toBe("escape");
  });

  it("handles ctrl+shift+z", () => {
    const parsed = _internals.parseCombo("ctrl+shift+z");
    expect(parsed.ctrl).toBe(true);
    expect(parsed.shift).toBe(true);
    expect(parsed.key).toBe("z");
  });
});
