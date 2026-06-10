/* wizard-handoff.spec.ts — lane A (2026-06-10). Pins the wizard→live handoff:
 * 1. completeWizard persists first_run_state BEFORE emitting ipc.wizard.done.
 * 2. sidecar-state {restarting, reason:"wizard-handoff"} reloads the webview
 *    so main.ts boot() mounts the shell — previously NOTHING consumed it. */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const callOrder: string[] = [];
type SidecarStateCb = (event: { payload: { state?: string; reason?: string } }) => void;
const sidecarStateListeners: SidecarStateCb[] = [];

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async (cmd: string) => {
    callOrder.push(`invoke:${cmd}`);
    return undefined;
  }),
}));
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async () => () => {}),
  emit: vi.fn(async () => undefined),
}));
vi.mock("../../tauri-runtime.js", () => ({
  invokeTauri: vi.fn(async () => undefined),
  listenTauri: vi.fn(async (event: string, cb: SidecarStateCb) => {
    if (event === "sidecar-state") sidecarStateListeners.push(cb);
    return () => {};
  }),
  emitTauri: vi.fn(async () => undefined),
}));
vi.mock("../../ipc/client.js", () => ({
  sendIpcRequest: vi.fn(() => new Promise(() => {})),
  subscribeIpc: vi.fn(async () => () => {}),
  emitIpc: vi.fn(async (type: string) => {
    callOrder.push(`emit:${type}`);
  }),
}));
vi.mock("../../library/api.js", () => ({
  libraryStats: vi.fn(async () => ({
    indexed: 0, backend: "sqlite-vec", library_setup_candidates: [], spent_eur: 0, failed: 0,
  })),
  libraryImportFromAction: vi.fn(async () => {
    callOrder.push("import:library");
    return true;
  }),
  // Router imports this for wipeout detection (lane C 449e5721); the
  // progress callback never fires in these specs, but the closed mock
  // factory must still export the name.
  libraryImportOutcome: vi.fn(() => "succeeded"),
  onLibraryImportProgress: vi.fn(async () => () => {}),
  libraryModels: vi.fn(async () => ({ models: [], required_ready: true, all_ready: true })),
  onModelProgress: vi.fn(async () => () => {}),
}));

import {
  getDevSurface,
  renderCurrentStep,
  _handoffHooks,
  _resetWizardHandoffForTests,
} from "../router.js";

function mountWizardShell(): void {
  document.body.innerHTML = `
    <div id="wizard-step-strip"></div>
    <div id="wizard-primary"></div>
    <div id="status-bar"></div>
  `;
}
function clickOpenVibemix(): void {
  const cta = Array.from(document.querySelectorAll("button")).find((b) =>
    (b.textContent ?? "").toLowerCase().includes("open vibemix"),
  );
  expect(cta).toBeDefined();
  cta!.click();
}
async function flush(n = 10): Promise<void> {
  for (let i = 0; i < n; i++) await Promise.resolve();
}

describe("wizard → live handoff (lane A)", () => {
  beforeEach(() => {
    mountWizardShell();
    callOrder.length = 0;
    sidecarStateListeners.length = 0;
    _resetWizardHandoffForTests();
    getDevSurface().setState({
      currentStep: "library-feed",
      libraryFeed: { status: "empty", candidates: [], indexed: 0 },
    });
    renderCurrentStep();
  });
  afterEach(() => {
    document.body.replaceChildren();
  });

  it("persists first_run_state BEFORE emitting ipc.wizard.done", async () => {
    clickOpenVibemix();
    await flush();
    const writeIdx = callOrder.indexOf("invoke:write_first_run_state");
    const doneIdx = callOrder.indexOf("emit:ipc.wizard.done");
    expect(writeIdx).toBeGreaterThanOrEqual(0);
    expect(doneIdx).toBeGreaterThanOrEqual(0);
    expect(writeIdx).toBeLessThan(doneIdx);
  });

  it("reloads the webview on sidecar-state wizard-handoff, never on plain restarts", async () => {
    const reload = vi.fn();
    _handoffHooks.reload = reload;
    clickOpenVibemix();
    await flush();
    expect(sidecarStateListeners.length).toBeGreaterThan(0);
    for (const cb of sidecarStateListeners) {
      cb({ payload: { state: "restarting" } });
      cb({ payload: { state: "running" } });
    }
    expect(reload).not.toHaveBeenCalled();
    for (const cb of sidecarStateListeners) {
      cb({ payload: { state: "restarting", reason: "wizard-handoff" } });
    }
    expect(reload).toHaveBeenCalledTimes(1);
  });
});
