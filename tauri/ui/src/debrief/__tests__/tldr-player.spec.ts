// SPDX-License-Identifier: Apache-2.0
// TL;DR audio URL wiring across real Tauri and browser-dev fallback.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { convertFileSrcMock } = vi.hoisted(() => ({
  convertFileSrcMock: vi.fn((path: string) => `asset://converted${path}`),
}));

vi.mock("@tauri-apps/api/core", () => ({
  convertFileSrc: convertFileSrcMock,
}));

import { mountTldrPlayer } from "../components/tldr-player.js";

let container: HTMLElement;

beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
  clearTauriRuntime();
  convertFileSrcMock.mockClear();
});

afterEach(() => {
  clearTauriRuntime();
  document.body.replaceChildren();
  vi.clearAllMocks();
});

describe("tldr-player asset URLs", () => {
  it("uses Tauri convertFileSrc when __TAURI_INTERNALS__ exists", () => {
    setTauriInternals();

    mountTldrPlayer(
      container,
      {
        audio_relative_path: "tldr.mp3",
        duration_s: 74,
        tldr_sha256: "abcdef0123456789",
        mime_type: "audio/mpeg",
      },
      "/recordings/set-001",
    );

    const audio = container.querySelector<HTMLAudioElement>("audio");
    expect(convertFileSrcMock).toHaveBeenCalledWith("/recordings/set-001/tldr.mp3");
    expect(audio?.getAttribute("src")).toBe(
      "asset://converted/recordings/set-001/tldr.mp3",
    );
  });

  it("keeps a browser-dev asset URL fallback outside Tauri", () => {
    mountTldrPlayer(
      container,
      {
        audio_relative_path: "tldr.mp3",
        duration_s: 74,
        tldr_sha256: "abcdef0123456789",
        mime_type: "audio/mpeg",
      },
      "/recordings/set-001",
    );

    const audio = container.querySelector<HTMLAudioElement>("audio");
    expect(convertFileSrcMock).not.toHaveBeenCalled();
    expect(audio?.getAttribute("src")).toBe(
      "asset://localhost//recordings/set-001/tldr.mp3",
    );
  });

  it("keeps file metadata out of the visible review chrome", () => {
    mountTldrPlayer(
      container,
      {
        audio_relative_path: "tldr.mp3",
        duration_s: 74,
        tldr_sha256: "abcdef0123456789",
        mime_type: "audio/mpeg",
      },
      "/recordings/set-001",
    );

    expect(container.textContent).toContain("74s recap");
    expect(container.textContent).not.toContain("audio/mpeg");
    expect(container.textContent).not.toContain("abcdef");
    expect(container.querySelector(".vmx-debrief-tldr-hud")).toBeNull();
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
