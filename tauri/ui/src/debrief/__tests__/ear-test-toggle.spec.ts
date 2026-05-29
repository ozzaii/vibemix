// SPDX-License-Identifier: Apache-2.0
// Debrief ear-test sign-off wiring. The desktop path must use the
// bundled Tauri API, not the disabled window.__TAURI__ global.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { invokeMock } = vi.hoisted(() => ({
  invokeMock: vi.fn(async () => undefined),
}));

vi.mock("@tauri-apps/api/core", () => ({
  invoke: invokeMock,
}));

import { mountEarTestToggle } from "../components/ear-test-toggle.js";

let container: HTMLElement;

beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
  clearTauriRuntime();
  invokeMock.mockClear();
});

afterEach(() => {
  clearTauriRuntime();
  document.body.replaceChildren();
  vi.clearAllMocks();
});

describe("ear-test-toggle", () => {
  it("submits through bundled Tauri IPC when __TAURI_INTERNALS__ exists", async () => {
    setTauriInternals();
    const wsSend = vi.fn();

    mountEarTestToggle(
      container,
      {
        session_id: "set-001",
        duration_s: 1860,
        genre: "techno",
      },
      {
        wsSink: { send: wsSend },
      },
    );

    container.querySelector<HTMLButtonElement>(".vmx-debrief-ear-test-toggle-btn")?.click();
    container.querySelector<HTMLInputElement>('input[data-flag="felt_late"]')!.checked =
      true;
    container.querySelector<HTMLTextAreaElement>(".vmx-debrief-ear-test-notes")!.value =
      "Low handoff lagged by one phrase.";
    container.querySelector<HTMLButtonElement>(".vmx-debrief-ear-test-submit")?.click();

    await flushAsync();

    expect(invokeMock).toHaveBeenCalledTimes(1);
    expect(invokeMock).toHaveBeenCalledWith("write_ear_test_log", {
      payload: expect.objectContaining({
        session_id: "set-001",
        duration_s: 1860,
        genre: "techno",
        free_form: "Low handoff lagged by one phrase.",
        signed_by: "kaan",
        slop_flags: {
          felt_slop: false,
          felt_scripted: false,
          felt_late: true,
          felt_generic: false,
        },
      }),
    });
    expect(wsSend).not.toHaveBeenCalled();
  });

  it("falls back to the debrief WS sink outside Tauri", async () => {
    const wsSend = vi.fn();

    mountEarTestToggle(
      container,
      {
        session_id: "browser-dev",
        duration_s: 2400,
        genre: "dnb",
      },
      {
        wsSink: { send: wsSend },
      },
    );

    container.querySelector<HTMLButtonElement>(".vmx-debrief-ear-test-toggle-btn")?.click();
    container.querySelector<HTMLButtonElement>(".vmx-debrief-ear-test-submit")?.click();

    await flushAsync();

    expect(invokeMock).not.toHaveBeenCalled();
    expect(wsSend).toHaveBeenCalledTimes(1);
    expect(wsSend).toHaveBeenCalledWith({
      kind: "ear-test-submit",
      payload: expect.objectContaining({
        session_id: "browser-dev",
        duration_s: 2400,
        genre: "dnb",
        signed_by: "kaan",
      }),
    });
  });
});

function setTauriInternals(): void {
  Object.defineProperty(window, "__TAURI_INTERNALS__", {
    configurable: true,
    value: {},
  });
}

function clearTauriRuntime(): void {
  Reflect.deleteProperty(window, "__TAURI_INTERNALS__");
  Reflect.deleteProperty(window, "__TAURI__");
}

async function flushAsync(): Promise<void> {
  for (let i = 0; i < 5; i += 1) {
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
}
