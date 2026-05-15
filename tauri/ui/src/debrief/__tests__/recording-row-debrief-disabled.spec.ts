// SPDX-License-Identifier: Apache-2.0
// Plan 29-06 — Disable gate for the Open Debrief button.

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

describe("recording-row — Open Debrief disable gate (Plan 29-06)", () => {
  it("disables for duration_s < 300 with 'too short' tooltip", () => {
    const { root } = renderRecordingRow({
      summary: { ...baseSummary, duration_s: 120 },
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(root);
    const debrief = root.querySelector<HTMLButtonElement>(
      'button[data-kind="debrief"]',
    );
    expect(debrief?.disabled).toBe(true);
    expect(debrief?.title).toContain("too short");
  });

  it("disables for event_count < 5 with 'no event data' tooltip", () => {
    const { root } = renderRecordingRow({
      summary: { ...baseSummary, event_count: 2 },
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(root);
    const debrief = root.querySelector<HTMLButtonElement>(
      'button[data-kind="debrief"]',
    );
    expect(debrief?.disabled).toBe(true);
    expect(debrief?.title).toContain("No event data");
  });

  it("clicking a disabled button does NOT invoke open_debrief_window", async () => {
    const { root } = renderRecordingRow({
      summary: { ...baseSummary, duration_s: 60 },
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(root);
    const debrief = root.querySelector<HTMLButtonElement>(
      'button[data-kind="debrief"]',
    );
    debrief?.click();
    await Promise.resolve();
    await Promise.resolve();
    expect(invoke).not.toHaveBeenCalled();
  });

  it("enabled state title is 'Open debrief'", () => {
    const { root } = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(root);
    const debrief = root.querySelector<HTMLButtonElement>(
      'button[data-kind="debrief"]',
    );
    expect(debrief?.disabled).toBe(false);
    expect(debrief?.title).toBe("Open debrief");
  });

  it("too-short takes precedence over no-events in title text", () => {
    // Build a session that fails both gates.
    const { root } = renderRecordingRow({
      summary: { ...baseSummary, duration_s: 60, event_count: 2 },
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(root);
    const debrief = root.querySelector<HTMLButtonElement>(
      'button[data-kind="debrief"]',
    );
    expect(debrief?.title).toContain("too short");
  });
});
