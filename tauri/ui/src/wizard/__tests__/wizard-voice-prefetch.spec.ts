/* wizard-voice-prefetch.spec.ts — lane A (2026-06-10). The launch step kicks
 * the one-shot `library_models --install required` (Tauri-parent child:
 * survives the sidecar handoff) and renders live voice-download progress —
 * the download must never ride the wizard exit path again. */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

type ModelProgressCb = (p: {
  target: string; id: string; n: number; total: number; status: string;
  rel_path: string; downloaded: number; size: number; error?: string;
}) => void;
const progressCbs: ModelProgressCb[] = [];

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn(async () => undefined) }));
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async () => () => {}),
  emit: vi.fn(async () => undefined),
}));
vi.mock("../../tauri-runtime.js", () => ({
  invokeTauri: vi.fn(async () => undefined),
  listenTauri: vi.fn(async () => () => {}),
  emitTauri: vi.fn(async () => undefined),
}));
vi.mock("../../ipc/client.js", () => ({
  sendIpcRequest: vi.fn(() => new Promise(() => {})),
  subscribeIpc: vi.fn(async () => () => {}),
  emitIpc: vi.fn(async () => undefined),
}));

let resolveModels: (v: unknown) => void = () => {};
vi.mock("../../library/api.js", () => ({
  libraryStats: vi.fn(async () => ({
    indexed: 0, backend: "sqlite-vec", library_setup_candidates: [], spent_eur: 0, failed: 0,
  })),
  libraryImportFromAction: vi.fn(async () => true),
  // Router imports this for wipeout detection (lane C 449e5721); never
  // called here, but the closed mock factory must export the name.
  libraryImportOutcome: vi.fn(() => "succeeded"),
  onLibraryImportProgress: vi.fn(async () => () => {}),
  libraryModels: vi.fn(
    () => new Promise((resolve) => { resolveModels = resolve; }),
  ),
  onModelProgress: vi.fn(async (cb: ModelProgressCb) => {
    progressCbs.push(cb);
    return () => {};
  }),
}));

import { getDevSurface, renderCurrentStep } from "../router.js";
import { libraryModels } from "../../library/api.js";

function mountWizardShell(): void {
  document.body.innerHTML = `
    <div id="wizard-step-strip"></div>
    <div id="wizard-primary"></div>
    <div id="status-bar"></div>
  `;
}
async function flush(n = 8): Promise<void> {
  for (let i = 0; i < n; i++) await Promise.resolve();
}

describe("wizard voice-model prefetch (lane A)", () => {
  beforeEach(() => {
    mountWizardShell();
    progressCbs.length = 0;
    getDevSurface().setState({
      currentStep: "library-feed",
      libraryFeed: { status: "empty", candidates: [], indexed: 0 },
      voiceModel: { status: "idle", downloaded: 0, size: 0 },
    });
    renderCurrentStep();
  });
  afterEach(() => {
    document.body.replaceChildren();
  });

  it("kicks the one-shot required-models install once and shows byte progress", async () => {
    await flush();
    expect(libraryModels).toHaveBeenCalledWith("required");
    // Re-render must NOT re-kick (once-guard).
    renderCurrentStep();
    await flush();
    expect(vi.mocked(libraryModels)).toHaveBeenCalledTimes(1);

    const readout = document.getElementById("voice-model-readout");
    expect(readout).not.toBeNull();
    for (const cb of progressCbs) {
      cb({
        target: "required", id: "chatterbox", n: 1, total: 1,
        status: "downloading", rel_path: "model.safetensors",
        downloaded: 331_350_016, size: 706_233_417,
      });
    }
    expect(readout!.textContent).toContain("316 MB");
    expect(readout!.textContent).toContain("674 MB");

    resolveModels({ models: [], required_ready: true, all_ready: true });
    await flush();
    expect(document.getElementById("voice-model-readout")!.dataset.status).toBe("ready");
  });
});
