/* install-chain-routing.spec.ts — Audit B-audio-firstrun.
 * Pins the rewired Phase-49 BlackHole install chain:
 *   permissions Continue probes ipc.calibration.list_devices;
 *   present → library-feed; absent → forewarning → driver-fetch →
 *   library-feed; probe error fail-closes into the chain; a failed
 *   companion fetch shows the fallback card AND keeps Continue armed. */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  invoke: vi.fn(async (_cmd: string, _args?: unknown) => undefined as unknown),
  sendIpcRequest: vi.fn(),
  subscribeIpc: vi.fn(async () => () => {}),
  emitIpc: vi.fn(async () => undefined),
}));
vi.mock("@tauri-apps/api/core", () => ({ invoke: mocks.invoke }));
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async () => () => {}),
  emit: vi.fn(async () => undefined),
}));
vi.mock("../../ipc/client.js", () => ({
  sendIpcRequest: mocks.sendIpcRequest,
  subscribeIpc: mocks.subscribeIpc,
  emitIpc: mocks.emitIpc,
}));
vi.mock("../../library/api.js", () => ({
  libraryStats: vi.fn(async () => ({
    indexed: 0, backend: "sqlite-vec", library_setup_candidates: [], spent_eur: 0, failed: 0,
  })),
  libraryImportFromAction: vi.fn(async () => true),
  onLibraryImportProgress: vi.fn(async () => () => {}),
}));

import { currentStep, getDevSurface, renderCurrentStep } from "../router.js";

let deviceReply: (() => Promise<unknown>) | null = null;

function deviceListReply(present: boolean): unknown {
  return {
    type: "ipc.calibration.device_list",
    ts: new Date().toISOString(),
    payload: { devices: [], blackhole_present: present },
  };
}
function primary(): HTMLElement {
  return document.getElementById("wizard-primary")!;
}
function clickContinue(): void {
  const btn = Array.from(primary().querySelectorAll("button")).find((b) =>
    (b.textContent ?? "").toLowerCase().includes("continue"),
  );
  expect(btn).toBeDefined();
  btn!.click();
}
async function flush(n = 6): Promise<void> {
  for (let i = 0; i < n; i++) await Promise.resolve();
}

beforeEach(() => {
  vi.useFakeTimers();
  mocks.invoke.mockReset();
  mocks.invoke.mockResolvedValue(undefined);
  mocks.sendIpcRequest.mockReset();
  mocks.sendIpcRequest.mockImplementation(async (type: string) => {
    if (type === "ipc.calibration.list_devices" && deviceReply) return deviceReply();
    return new Promise(() => {}); // permission polls hang harmlessly
  });
  deviceReply = null;
  document.body.innerHTML = `
    <div id="wizard-step-strip"></div>
    <div id="wizard-primary"></div>
    <div id="status-bar"></div>
  `;
  getDevSurface().setState({
    currentStep: "permissions",
    platform: "darwin",
    step1: { screenRecording: "granted", microphone: "granted", screenSettingsOpened: false },
  });
  renderCurrentStep();
});
afterEach(() => {
  vi.runOnlyPendingTimers();
  vi.useRealTimers();
  document.body.replaceChildren();
});

describe("install chain routing (audit B-audio-firstrun)", () => {
  it("skips the chain when BlackHole is present", async () => {
    deviceReply = async () => deviceListReply(true);
    clickContinue();
    await flush();
    vi.advanceTimersByTime(300);
    expect(currentStep()).toBe("library-feed");
    expect(mocks.sendIpcRequest).toHaveBeenCalledWith(
      "ipc.calibration.list_devices", {}, "ipc.calibration.device_list", 3_000,
    );
  });

  it("routes a fresh Mac into forewarning → driver-fetch and fires the fetch once", async () => {
    deviceReply = async () => deviceListReply(false);
    clickContinue();
    await flush();
    vi.advanceTimersByTime(300);
    expect(currentStep()).toBe("forewarning");
    clickContinue();
    vi.advanceTimersByTime(300);
    expect(currentStep()).toBe("driver-fetch");
    const fetchCalls = mocks.invoke.mock.calls.filter((c) => c[0] === "run_companion_fetch");
    expect(fetchCalls).toHaveLength(1);
    expect(fetchCalls[0]![1]).toEqual({ dryRun: false });
  });

  it("driver-fetch success arms Continue and lands on library-feed", async () => {
    deviceReply = async () => deviceListReply(false);
    clickContinue();
    await flush();
    vi.advanceTimersByTime(300);
    clickContinue();
    vi.advanceTimersByTime(300);
    await flush();                 // run_companion_fetch resolution
    vi.advanceTimersByTime(400);   // midi/tcc/bravoh probe stubs + checkAllDone
    clickContinue();
    vi.advanceTimersByTime(300);
    expect(currentStep()).toBe("library-feed");
  });

  it("probe failure fail-closes into the chain", async () => {
    deviceReply = async () => { throw new Error("bus hiccup"); };
    clickContinue();
    await flush();
    vi.advanceTimersByTime(300);
    expect(currentStep()).toBe("forewarning");
  });

  it("companion-fetch failure shows the fallback card AND keeps Continue armed (no dead-end, no brew)", async () => {
    deviceReply = async () => deviceListReply(false);
    mocks.invoke.mockImplementation(async (cmd: string) => {
      if (cmd === "run_companion_fetch") throw new Error("offline");
      return undefined;
    });
    clickContinue();
    await flush();
    vi.advanceTimersByTime(300);
    clickContinue();
    vi.advanceTimersByTime(300);
    expect(currentStep()).toBe("driver-fetch");
    await flush();
    const fallback = primary().querySelector<HTMLElement>(".step-driver-fetch__fallback");
    expect(fallback).not.toBeNull();
    expect(fallback!.style.display).not.toBe("none");
    expect(fallback!.textContent).not.toContain("brew");
    const continueBtn = Array.from(primary().querySelectorAll("button")).find((b) =>
      (b.textContent ?? "").toLowerCase().includes("continue"),
    );
    expect(continueBtn).toBeDefined();
    expect(continueBtn!.disabled).toBe(false);
    expect(continueBtn!.getAttribute("aria-disabled")).not.toBe("true");
  });
});
