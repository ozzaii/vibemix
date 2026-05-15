// SPDX-License-Identifier: Apache-2.0
// Plan 29-06 — Open Debrief button in the Settings recording row.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@tauri-apps/api/core", () => {
  const invokeMock = vi.fn(async (_cmd: string, _args: unknown) => undefined);
  return {
    convertFileSrc: (path: string): string => `asset://localhost${path}`,
    invoke: invokeMock,
  };
});

vi.mock("../../ipc/client.js", () => ({
  sendIpcRequest: vi.fn(() => new Promise(() => {})),
  revealInOS: vi.fn(async () => undefined),
  openInputWav: vi.fn(async () => undefined),
}));

import { invoke } from "@tauri-apps/api/core";
import { renderRecordingRow } from "../../settings/components/recording-row.js";

const baseSummary = {
  session_dir: "20260513-210410",
  started_at_iso: "2026-05-13T21:04:10+02:00",
  duration_s: 5040,
  event_count: 38,
  bytes_total: 12345678,
  crashed: false,
};

beforeEach(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: () => ({
      matches: false,
      media: "",
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onchange: null,
    }),
  });
});

afterEach(() => {
  document.body.replaceChildren();
  vi.clearAllMocks();
});

describe("recording-row — Open Debrief button (Plan 29-06)", () => {
  it("renders 5 action buttons including the debrief button", () => {
    const { root } = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(root);
    const actions = root.querySelector<HTMLElement>(".vmx-rec-row__actions");
    const buttons = actions?.querySelectorAll("button") ?? [];
    expect(buttons.length).toBe(5);

    const debrief = root.querySelector<HTMLButtonElement>(
      'button[data-kind="debrief"]',
    );
    expect(debrief).not.toBeNull();
    expect(debrief?.disabled).toBe(false);
  });

  it("debrief button is positioned between open-external and delete", () => {
    const { root } = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(root);
    const actions = root.querySelector<HTMLElement>(".vmx-rec-row__actions");
    const kinds = Array.from(actions!.querySelectorAll("button")).map(
      (b) => (b as HTMLButtonElement).dataset.kind,
    );
    expect(kinds).toEqual([
      "replay",
      "reveal",
      "open-external",
      "debrief",
      "delete",
    ]);
  });

  it("click on enabled debrief button calls invoke('open_debrief_window')", async () => {
    const { root } = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(root);
    const debrief = root.querySelector<HTMLButtonElement>(
      'button[data-kind="debrief"]',
    );
    debrief?.click();
    // The handler awaits a dynamic import; let microtasks flush.
    await Promise.resolve();
    await Promise.resolve();
    expect(invoke).toHaveBeenCalledWith("open_debrief_window", {
      sessionDir: "20260513-210410",
    });
  });

  it("aria-label on debrief button references the session timestamp", () => {
    const { root } = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(root);
    const debrief = root.querySelector<HTMLButtonElement>(
      'button[data-kind="debrief"]',
    );
    expect(debrief?.getAttribute("aria-label")).toMatch(/open debrief/);
  });
});
