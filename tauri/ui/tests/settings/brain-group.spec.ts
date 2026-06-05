/* DEMOCRATIZATION-1 — Settings drawer BRAIN group spec.
 *
 * The BRAIN group is a dev/support control for the live co-host brain path: a
 * masked Gemini-key input (DIRECT mode) or a one-flip toggle to the hosted
 * Bravoh proxy. Production Settings does not mount it. The secret is written
 * by the BACKEND (Lane B); this group only sends intent over
 * ipc.settings.set_brain and NEVER logs the key.
 *
 * Asserts:
 *   1. Renders the BRAIN group with a DIRECT/PROXY rocker + (direct) masked
 *      key input + Save button + a state line.
 *   2. Optimistic repaint on mode toggle (data-active flips synchronously)
 *      and a single ipc.settings.set_brain { mode: "proxy" } send (no key).
 *   3. Key input is type=password + write-only; cleared after a good ack.
 *   4. Save sends { mode:"direct", gemini_api_key:"AIza-test-fake" } once.
 *   5. NEVER-LOG — no vmxLog call carries the raw key.
 *   6. Failure path: ack ok:false shows the error in the state line and
 *      reverts the optimistic mode.
 *   7. Empty key never sends an empty secret; proxy payload omits the key.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { sendIpcRequestMock } = vi.hoisted(() => ({
  sendIpcRequestMock: vi.fn(
    async (
      _req: string,
      _payload: Record<string, unknown>,
      _res: string,
    ): Promise<unknown> => ({
      type: "ipc.settings.brain_ack",
      ts: "2026-06-04T00:00:00.000Z",
      payload: { ok: true, mode: "direct", key_set: true, restart_required: true, error: null },
    }),
  ),
}));

const { vmxLogMock } = vi.hoisted(() => ({ vmxLogMock: vi.fn() }));

vi.mock("../../src/ipc/client.js", () => ({
  sendIpcRequest: sendIpcRequestMock,
  emitIpc: vi.fn(async () => undefined),
  subscribeIpc: vi.fn(async () => () => {}),
}));

vi.mock("../../src/debug-log.js", () => ({ vmxLog: vmxLogMock }));

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn(async () => undefined) }));
vi.mock("@tauri-apps/api/event", () => ({ listen: vi.fn(async () => () => {}) }));

import {
  BrainGroup,
  _resetBrainGroupForTests,
} from "../../src/settings/components/brain-group.js";

const FAKE_KEY = "AIza-test-fake";

function ack(payload: Record<string, unknown>): unknown {
  return { type: "ipc.settings.brain_ack", ts: "2026-06-04T00:00:00.000Z", payload };
}

function flush(): Promise<void> {
  return new Promise<void>((r) => setTimeout(r, 0));
}

function q<T extends HTMLElement>(root: HTMLElement, sel: string): T {
  const el = root.querySelector<T>(sel);
  expect(el, `expected ${sel}`).toBeTruthy();
  return el as T;
}

beforeEach(() => {
  _resetBrainGroupForTests();
  sendIpcRequestMock.mockClear();
  sendIpcRequestMock.mockResolvedValue(
    ack({ ok: true, mode: "direct", key_set: true, restart_required: true, error: null }),
  );
  vmxLogMock.mockClear();
  document.body.replaceChildren();
});

afterEach(() => {
  document.body.replaceChildren();
});

describe("BrainGroup rendering", () => {
  it("renders the BRAIN group with rocker + masked key + save + state (direct default)", () => {
    const group = BrainGroup();
    document.body.append(group);

    expect(group.querySelector(".vmx-settings-group__header")?.textContent).toContain("BRAIN");
    expect(group.getAttribute("data-component")).toBe("brain-group");

    const mode = q(group, '[data-wire="settings.brain.mode"]');
    const rocker = q(mode, ".vmx-rocker");
    expect(rocker.querySelector('.vmx-rocker__seg[data-id="direct"]')?.getAttribute("data-active"))
      .toBe("true");
    expect(rocker.querySelector('.vmx-rocker__seg[data-id="proxy"]')?.getAttribute("data-active"))
      .toBe("false");

    const key = q<HTMLInputElement>(group, '[data-wire="settings.brain.key"] input');
    expect(key.type).toBe("password");
    q(group, '[data-wire="settings.brain.save"]');
    q(group, '[data-wire="settings.brain.state"]');
  });

  it("hides the key input + save when switched to PROXY", () => {
    const group = BrainGroup();
    document.body.append(group);
    const proxy = q<HTMLButtonElement>(group, '.vmx-rocker__seg[data-id="proxy"]');
    proxy.click();
    expect(group.querySelector('[data-wire="settings.brain.key"]')).toBeNull();
    expect(group.querySelector('[data-wire="settings.brain.save"]')).toBeNull();
  });
});

describe("BrainGroup IPC wiring", () => {
  it("toggling PROXY repaints optimistically and sends { mode:'proxy' } with no key", async () => {
    const group = BrainGroup();
    document.body.append(group);
    const proxy = q<HTMLButtonElement>(group, '.vmx-rocker__seg[data-id="proxy"]');
    proxy.click();
    // Optimistic — the lit segment moves before any awaited ack.
    expect(proxy.dataset.active).toBe("true");

    await flush();
    expect(sendIpcRequestMock).toHaveBeenCalledTimes(1);
    const [reqType, payload, resType] = sendIpcRequestMock.mock.calls[0]!;
    expect(reqType).toBe("ipc.settings.set_brain");
    expect(resType).toBe("ipc.settings.brain_ack");
    expect(payload).toEqual({ mode: "proxy" });
    expect(payload).not.toHaveProperty("gemini_api_key");
  });

  it("Save sends { mode:'direct', gemini_api_key } exactly once and clears the input", async () => {
    const group = BrainGroup();
    document.body.append(group);
    const input = q<HTMLInputElement>(group, '[data-wire="settings.brain.key"] input');
    input.value = FAKE_KEY;
    input.dispatchEvent(new Event("input"));

    const save = q<HTMLButtonElement>(group, '[data-wire="settings.brain.save"]');
    expect(save.disabled).toBe(false);
    save.click();
    await flush();

    expect(sendIpcRequestMock).toHaveBeenCalledTimes(1);
    const [, payload] = sendIpcRequestMock.mock.calls[0]!;
    expect(payload).toEqual({ mode: "direct", gemini_api_key: FAKE_KEY });
    // Write-only: cleared after a good ack, never repopulated.
    expect(input.value).toBe("");
  });

  it("never logs the raw key (NEVER-LOG guard)", async () => {
    const group = BrainGroup();
    document.body.append(group);
    const input = q<HTMLInputElement>(group, '[data-wire="settings.brain.key"] input');
    input.value = FAKE_KEY;
    input.dispatchEvent(new Event("input"));
    q<HTMLButtonElement>(group, '[data-wire="settings.brain.save"]').click();
    await flush();

    for (const call of vmxLogMock.mock.calls) {
      expect(JSON.stringify(call)).not.toContain(FAKE_KEY);
    }
  });

  it("disabled Save with an empty key never sends", async () => {
    const group = BrainGroup();
    document.body.append(group);
    const save = q<HTMLButtonElement>(group, '[data-wire="settings.brain.save"]');
    expect(save.disabled).toBe(true);
    save.click();
    await flush();
    expect(sendIpcRequestMock).not.toHaveBeenCalled();
  });

  it("a saved direct key shows 'Restart' affordance in the state line", async () => {
    const group = BrainGroup();
    document.body.append(group);
    const input = q<HTMLInputElement>(group, '[data-wire="settings.brain.key"] input');
    input.value = FAKE_KEY;
    input.dispatchEvent(new Event("input"));
    q<HTMLButtonElement>(group, '[data-wire="settings.brain.save"]').click();
    await flush();
    const state = q(group, '[data-wire="settings.brain.state"]');
    expect(state.textContent?.toLowerCase()).toContain("restart");
  });
});

describe("BrainGroup failure handling", () => {
  it("ack ok:false reverts the optimistic mode and shows the error", async () => {
    sendIpcRequestMock.mockResolvedValueOnce(
      ack({ ok: false, mode: "direct", key_set: false, restart_required: true, error: "proxy unavailable" }),
    );
    const group = BrainGroup();
    document.body.append(group);
    const proxy = q<HTMLButtonElement>(group, '.vmx-rocker__seg[data-id="proxy"]');
    proxy.click();
    expect(proxy.dataset.active).toBe("true"); // optimistic
    await flush();

    // Reverted: DIRECT is active again.
    const direct = q<HTMLButtonElement>(group, '.vmx-rocker__seg[data-id="direct"]');
    expect(direct.dataset.active).toBe("true");
    const state = q(group, '[data-wire="settings.brain.state"]');
    expect(state.textContent).toContain("proxy unavailable");
  });
});

describe("BrainGroup style guard (no hex literals)", () => {
  it("emitted CSS contains zero hex outside rgba()/var() — frontend-enforcement", () => {
    BrainGroup(); // ensures registerStyle ran
    const styleEl = document.querySelector<HTMLStyleElement>(
      'style[data-scope="vmx-brain-group"]',
    );
    expect(styleEl).toBeTruthy();
    const css = styleEl!.textContent ?? "";
    const hexMatches = css.match(/#[0-9a-fA-F]{3,8}/g) ?? [];
    expect(hexMatches).toEqual([]);
  });
});
