/* Phase 12 Wave 4 — Settings drawer mount/open/close (Plan 12-05 §7).
 * Phase 15 Plan 05 — adds 4 cases covering the in-drawer recording browser
 * wiring: list IPC dispatch on open, list-result populates rows, delete
 * ok=true optimistically removes, list timeout flips usage to UNAVAILABLE.
 *
 * Asserts:
 *   - mountSettingsDrawer is idempotent (two calls = one DOM tree).
 *   - openSettings + closeSettings flip data-open on drawer + backdrop.
 *   - Esc closes when open; noop when closed.
 *   - Backdrop click closes the drawer.
 *   - ✕ button closes the drawer.
 *   - Esc does NOT close when a modal confirm is in flight.
 *   - Phase 15: recordings.list fires on drawer open.
 *   - Phase 15: list_result populates row count.
 *   - Phase 15: delete ok=true removes row optimistically.
 *   - Phase 15: list error → disk usage line shows UNAVAILABLE.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock @tauri-apps/api/core BEFORE importing the drawer module — the
// drawer imports `invoke` for the rebind_hotkey command. In jsdom we
// don't want a real Tauri context. `convertFileSrc` is pulled in
// transitively via recording-row.ts (Phase 15 Plan 04).
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async (_cmd: string, _args?: Record<string, unknown>) => {}),
  convertFileSrc: (path: string): string => `asset://localhost${path}`,
}));
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async () => () => {}),
}));

// Phase 15 Plan 05 — mock the IPC client so list/delete dispatches are
// observable + controllable in test cases. The drawer's loadRecordings()
// and onDeleteRecording() functions both call sendIpcRequest.
const sendIpcRequestMock = vi.fn();
vi.mock("../../src/ipc/client.js", () => ({
  emitIpc: vi.fn(async () => undefined),
  sendIpcRequest: (
    requestType: string,
    requestPayload: Record<string, unknown>,
    responseType: string,
    timeoutMs?: number,
  ) => sendIpcRequestMock(requestType, requestPayload, responseType, timeoutMs),
  subscribeIpc: vi.fn(async () => () => {}),
}));

import { subscribeIpc } from "../../src/ipc/client.js";
import {
  _resetDrawerForTests,
  closeSettings,
  loadRecordings,
  mountSettingsDrawer,
  onDeleteRecording,
  openSettings,
  unmountSettingsDrawer,
} from "../../src/settings/SettingsDrawer.js";
import {
  getSessionState,
  setSessionState,
} from "../../src/session/state.js";
import {
  _resetSettingsUIStateForTests,
  getSettingsUIState,
  setRecordingsSlice,
  setSettingsUIState,
} from "../../src/settings/state.js";
import {
  SETTINGS_RUNTIME_WIRES,
  wireSelector,
} from "../../src/mock-transfer/contract.js";

const subscribeIpcMock = vi.mocked(subscribeIpc);

beforeEach(() => {
  _resetSettingsUIStateForTests();
  _resetDrawerForTests();
  sendIpcRequestMock.mockReset();
  subscribeIpcMock.mockClear();
  // Default: never-resolves so non-Phase-15 tests don't hit a stub
  // resolution race. Specific cases override below.
  sendIpcRequestMock.mockImplementation(
    () => new Promise(() => undefined),
  );
  document.body.replaceChildren();
});

afterEach(() => {
  _resetDrawerForTests();
  _resetSettingsUIStateForTests();
  document.body.replaceChildren();
});

describe("mountSettingsDrawer", () => {
  it("mounts backdrop + drawer + modal slot into the provided root", () => {
    mountSettingsDrawer(document.body);
    expect(document.querySelectorAll(".vmx-settings-backdrop").length).toBe(1);
    expect(document.querySelectorAll(".vmx-settings-drawer").length).toBe(1);
    expect(
      document.querySelectorAll(".vmx-settings-drawer__modal-slot").length,
    ).toBe(1);
  });

  it("gates internal settings tools to dev builds", () => {
    // Profile view, citation diagnostics, calibration rerun, and Learn reset
    // are support/tuning surfaces. They are present in dev builds and stripped
    // from the shipped drawer a paying user sees. The old BYO brain-key group
    // is deleted in both builds.
    mountSettingsDrawer(document.body);
    expect(document.body.textContent).not.toContain("BRAIN");
    expect(document.body.textContent).not.toContain("Gemini key");
    expect(document.body.textContent).not.toContain("Google");
    if (import.meta.env.DEV) {
      expect(document.querySelector(".vmx-citation-diag")).not.toBeNull();
      expect(document.body.textContent).toContain("PROFILE");
      expect(document.body.textContent).toContain("DIAGNOSTICS");
      expect(document.body.textContent).toContain("CALIBRATION");
      expect(document.body.textContent).toContain("LEARN");
      expect(document.body.textContent).toContain("RE-RUN WIZARD");
      expect(document.body.textContent).toContain("reset learn progress");
    } else {
      expect(document.querySelector(".vmx-citation-diag")).toBeNull();
      expect(document.body.textContent).not.toContain("PROFILE");
      expect(document.body.textContent).not.toContain("DIAGNOSTICS");
      expect(document.body.textContent).not.toContain("CALIBRATION");
      expect(document.body.textContent).not.toContain("LEARN");
      expect(document.body.textContent).not.toContain("RE-RUN WIZARD");
      expect(document.body.textContent).not.toContain("reset learn progress");
    }
  });

  it("exposes transfer anchors for the drawer shell", () => {
    mountSettingsDrawer(document.body);
    for (const wire of SETTINGS_RUNTIME_WIRES) {
      expect(
        document.querySelectorAll(wireSelector(wire)).length,
        `${wire} should mount exactly once`,
      ).toBe(1);
    }
  });

  it("unmountSettingsDrawer removes shell nodes and resets open state", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    expect(getSettingsUIState().open).toBe(true);

    unmountSettingsDrawer();

    expect(getSettingsUIState().open).toBe(false);
    expect(document.querySelector(".vmx-settings-backdrop")).toBeNull();
    expect(document.querySelector(".vmx-settings-drawer")).toBeNull();
    expect(document.querySelector(".vmx-settings-drawer__modal-slot")).toBeNull();

    mountSettingsDrawer(document.body);
    expect(document.querySelectorAll(".vmx-settings-drawer").length).toBe(1);
  });

  it("is idempotent — a second call does not duplicate nodes", () => {
    mountSettingsDrawer(document.body);
    mountSettingsDrawer(document.body);
    expect(document.querySelectorAll(".vmx-settings-drawer").length).toBe(1);
    expect(document.querySelectorAll(".vmx-settings-backdrop").length).toBe(1);
  });

  it("initial state is closed (data-open=false on both)", () => {
    mountSettingsDrawer(document.body);
    const drawer = document.querySelector<HTMLElement>(
      ".vmx-settings-drawer",
    );
    const backdrop = document.querySelector<HTMLElement>(
      ".vmx-settings-backdrop",
    );
    expect(drawer?.dataset.open).toBe("false");
    expect(backdrop?.dataset.open).toBe("false");
  });
});

describe("openSettings / closeSettings", () => {
  it("openSettings flips data-open=true on drawer + backdrop", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    const drawer = document.querySelector<HTMLElement>(
      ".vmx-settings-drawer",
    );
    const backdrop = document.querySelector<HTMLElement>(
      ".vmx-settings-backdrop",
    );
    expect(drawer?.dataset.open).toBe("true");
    expect(backdrop?.dataset.open).toBe("true");
    expect(getSettingsUIState().open).toBe(true);
  });

  it("closeSettings flips data-open=false back", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    closeSettings();
    const drawer = document.querySelector<HTMLElement>(
      ".vmx-settings-drawer",
    );
    expect(drawer?.dataset.open).toBe("false");
    expect(getSettingsUIState().open).toBe(false);
  });

  it("closeSettings clears in-flight capture + confirm state", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    setSettingsUIState({
      hotkeyCaptureMode: true,
      confirmDialog: "re-run-calibration",
    });
    closeSettings();
    const ui = getSettingsUIState();
    expect(ui.hotkeyCaptureMode).toBe(false);
    expect(ui.confirmDialog).toBeNull();
  });

  it("loads profile view only while open and does not duplicate on close", () => {
    mountSettingsDrawer(document.body);
    const profileCalls = () =>
      sendIpcRequestMock.mock.calls.filter((c) => c[0] === "ipc.profile.view");

    expect(profileCalls().length).toBe(0);

    openSettings();
    if (!import.meta.env.DEV) {
      expect(profileCalls().length).toBe(0);
      closeSettings();
      expect(profileCalls().length).toBe(0);
      return;
    }
    expect(profileCalls().length).toBe(1);

    closeSettings();
    expect(profileCalls().length).toBe(1);
  });

  it("keeps one library staleness subscription across open and close refreshes", () => {
    mountSettingsDrawer(document.body);
    const stalenessSubs = () =>
      subscribeIpcMock.mock.calls.filter(
        (c) => c[0] === "ipc.library.staleness_nudge",
      );

    expect(stalenessSubs().length).toBe(1);

    openSettings();
    expect(stalenessSubs().length).toBe(1);

    closeSettings();
    expect(stalenessSubs().length).toBe(1);
  });
});

describe("dismiss paths", () => {
  it("Esc key closes an open drawer", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    expect(getSettingsUIState().open).toBe(true);
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(getSettingsUIState().open).toBe(false);
  });

  it("Esc key is a noop when drawer is closed", () => {
    mountSettingsDrawer(document.body);
    expect(getSettingsUIState().open).toBe(false);
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(getSettingsUIState().open).toBe(false);
  });

  it("Esc does NOT close drawer when confirm dialog is in flight", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    setSettingsUIState({ confirmDialog: "re-run-calibration" });
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(getSettingsUIState().open).toBe(true);
  });

  it("Esc does NOT close drawer when hotkey capture is in flight", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    setSettingsUIState({ hotkeyCaptureMode: true });
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(getSettingsUIState().open).toBe(true);
  });

  it("clicking the backdrop closes the drawer", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    const backdrop = document.querySelector<HTMLElement>(
      ".vmx-settings-backdrop",
    );
    backdrop?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(getSettingsUIState().open).toBe(false);
  });

  it("clicking the ✕ button closes the drawer", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    const closeBtn = document.querySelector<HTMLElement>(
      ".vmx-settings-drawer__close",
    );
    closeBtn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(getSettingsUIState().open).toBe(false);
  });
});

describe("group rendering", () => {
  it("renders always-on groups and dev-only internal groups for the active build", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    const groupHeaders = Array.from(
      document.querySelectorAll<HTMLElement>(".vmx-settings-group__header"),
    ).map((h) => h.textContent ?? "");
    expect(groupHeaders.some((h) => h.includes("PERSONA"))).toBe(true);
    expect(groupHeaders.some((h) => h.includes("OUTPUT"))).toBe(true);
    expect(groupHeaders.some((h) => h.includes("HOTKEY"))).toBe(true);
    expect(groupHeaders.some((h) => h.includes("RECORDING"))).toBe(true);
    expect(groupHeaders.some((h) => h.includes("LIBRARY"))).toBe(true);
    expect(groupHeaders.some((h) => h.includes("MASCOT"))).toBe(true);
    expect(groupHeaders.some((h) => h.includes("PERFORMANCE"))).toBe(true);
    expect(groupHeaders.some((h) => h.includes("HELP"))).toBe(true);
    expect(groupHeaders.some((h) => h.includes("BRAIN"))).toBe(false);
    expect(groupHeaders.some((h) => h.includes("CALIBRATION"))).toBe(import.meta.env.DEV);
  });

  it("HOTKEY group shows the hotkey-capture component", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    expect(document.querySelectorAll(".vmx-hotkey-capture").length).toBe(1);
  });

  it("uses product labels instead of wire abbreviations in the top controls", () => {
    const state = getSessionState();
    setSessionState({
      settings: {
        ...state.settings,
        skill: "intermediate",
        output_device_id: "5",
        output_profile: "spk",
      },
    });

    mountSettingsDrawer(document.body);
    openSettings();

    const drawer = document.querySelector<HTMLElement>(".vmx-settings-drawer");
    expect(drawer?.textContent).toContain("VOICE");
    expect(drawer?.textContent).toContain("Intermediate");
    expect(drawer?.textContent).toContain("Device 5");
    expect(drawer?.textContent).toContain("Speakers");
    expect(drawer?.textContent).not.toContain("CFG");
  });

  it("RECORDING group shows the retention slider with 6 knobs", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    expect(document.querySelectorAll(".vmx-retention__knob").length).toBe(6);
  });
});

// ---------------------------------------------------------------------------
// Phase 15 Plan 05 — Recording browser wiring inside the RECORDING group.
// ---------------------------------------------------------------------------

describe("Phase 15: recording browser wiring", () => {
  it("fires ipc.recordings.list on drawer open with empty payload", async () => {
    // Capture the request without resolving so we can assert the call args.
    sendIpcRequestMock.mockImplementation(
      () => new Promise(() => undefined),
    );
    mountSettingsDrawer(document.body);
    openSettings();

    // Yield a microtask so the void loadRecordings() promise schedules its
    // sendIpcRequest call.
    await Promise.resolve();

    const listCalls = sendIpcRequestMock.mock.calls.filter(
      (c) => c[0] === "ipc.recordings.list",
    );
    expect(listCalls.length).toBe(1);
    expect(listCalls[0]![1]).toEqual({});
    expect(listCalls[0]![2]).toBe("ipc.recordings.list_result");
  });

  it("list_result populates 2 row elements in the recording browser DOM", async () => {
    // Resolve only the recordings.list request. When the drawer is open, the
    // profile panel may also fire sendIpcRequest("ipc.profile.view"), so key on
    // requestType instead of using a one-shot mock.
    sendIpcRequestMock.mockImplementation((requestType: string) => {
      if (requestType === "ipc.recordings.list") {
        return Promise.resolve({
          type: "ipc.recordings.list_result",
          ts: "2026-05-13T21:04:10+02:00",
          payload: {
            sessions: [
              {
                session_dir: "20260513-210410",
                started_at_iso: "2026-05-13T21:04:10+02:00",
                duration_s: 1800,
                event_count: 22,
                bytes_total: 1_500_000,
                crashed: false,
              },
              {
                session_dir: "20260512-182200",
                started_at_iso: "2026-05-12T18:22:00+02:00",
                duration_s: 7380,
                event_count: 71,
                bytes_total: 2_500_000,
                crashed: false,
              },
            ],
            bytes_total: 4_000_000,
          },
        });
      }
      // Everything else (e.g. ipc.profile.view while open) never resolves —
      // matches the beforeEach default and keeps render-time IPC from interfering.
      return new Promise(() => undefined);
    });
    // Mount + set drawer open via state (NOT openSettings, which would
    // auto-fire loadRecordings). We drive loadRecordings explicitly so the
    // assertion runs after the resolver.
    mountSettingsDrawer(document.body);
    setSettingsUIState({ open: true });
    await loadRecordings();

    const rows = document.querySelectorAll(".vmx-rec-row");
    expect(rows.length).toBe(2);
    // Slice state mirrors the wire payload.
    const slice = getSettingsUIState().recordings;
    expect(slice.sessions.length).toBe(2);
    expect(slice.usage.bytes_total).toBe(4_000_000);
    expect(slice.loading).toBe(false);
    expect(slice.error).toBeNull();
  });

  it("delete ok=true ack optimistically removes the row from the slice", async () => {
    // Seed two sessions in the slice directly (skip the list dispatch for
    // this case — we test only the delete path).
    setRecordingsSlice({
      sessions: [
        {
          session_dir: "20260513-210410",
          started_at_iso: "2026-05-13T21:04:10+02:00",
          duration_s: 1800,
          event_count: 22,
          bytes_total: 1_500_000,
          crashed: false,
        },
        {
          session_dir: "20260512-182200",
          started_at_iso: "2026-05-12T18:22:00+02:00",
          duration_s: 7380,
          event_count: 71,
          bytes_total: 2_500_000,
          crashed: false,
        },
      ],
      usage: { sessions: 2, bytes_total: 4_000_000 },
    });
    // Mount + set open via state to avoid auto-firing loadRecordings.
    mountSettingsDrawer(document.body);
    setSettingsUIState({ open: true });

    // Stub the delete reply.
    sendIpcRequestMock.mockResolvedValueOnce({
      type: "ipc.recordings.delete_ack",
      ts: "2026-05-13T21:04:10+02:00",
      payload: {
        session_dir: "20260513-210410",
        ok: true,
        error: null,
      },
    });

    await onDeleteRecording("20260513-210410");

    const deleteCalls = sendIpcRequestMock.mock.calls.filter(
      (c) => c[0] === "ipc.recordings.delete",
    );
    expect(deleteCalls.length).toBe(1);
    expect(deleteCalls[0]![1]).toEqual({ session_dir: "20260513-210410" });
    expect(deleteCalls[0]![2]).toBe("ipc.recordings.delete_ack");

    const slice = getSettingsUIState().recordings;
    expect(slice.sessions.length).toBe(1);
    expect(slice.sessions[0]!.session_dir).toBe("20260512-182200");
  });

  it("list IPC timeout swaps the disk-usage line to UNAVAILABLE copy", async () => {
    // Reject only the recordings.list request (see the row-population test for
    // why one-shot mocks are brittle when other open-drawer IPC exists).
    sendIpcRequestMock.mockImplementation((requestType: string) => {
      if (requestType === "ipc.recordings.list") {
        return Promise.reject(
          new Error(
            "ipc timeout: no ipc.recordings.list_result within 10000ms",
          ),
        );
      }
      return new Promise(() => undefined);
    });
    // Mount + open via state directly so loadRecordings runs against the
    // rejecting mock.
    mountSettingsDrawer(document.body);
    setSettingsUIState({ open: true });
    await loadRecordings();

    const usage = document.querySelector<HTMLElement>(".vmx-rec-browser__usage");
    expect(usage?.textContent).toBe("RECORDINGS · UNAVAILABLE");

    const slice = getSettingsUIState().recordings;
    expect(slice.loading).toBe(false);
    expect(slice.error).not.toBeNull();
    expect(slice.error).toContain("ipc timeout");
  });
});
