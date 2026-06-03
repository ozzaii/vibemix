/**
 * @vitest-environment jsdom
 *
 * The shell voice badge is the live-deck receipt for the MOSS-only voice
 * requirement: a clean machine must not look fully ready when Sven cannot speak.
 */

import { describe, expect, it, vi } from "vitest";

import {
  mountVoiceReadinessBadge,
  voiceReadinessBadgeModel,
} from "../../src/shell/VoiceReadinessBadge.js";
import type {
  LibraryModelAsset,
  LibraryModelsResult,
} from "../../src/library/api.js";

function model(
  overrides: Partial<LibraryModelAsset> = {},
): LibraryModelAsset {
  return {
    id: "moss-tts",
    label: "MOSS TTS ONNX",
    role: "local co-host voice",
    required: true,
    env: "VIBEMIX_MOSS_TTS_DIR",
    installed: true,
    installable: true,
    path: "~/.cache/vibemix/moss-tts-onnx/MOSS-TTS-Nano-100M-ONNX",
    missing: [],
    mismatched: [],
    ...overrides,
  };
}

function payload(
  overrides: Partial<LibraryModelsResult> = {},
): LibraryModelsResult {
  return {
    models: [model()],
    required_ready: true,
    all_ready: true,
    ...overrides,
  };
}

describe("voice readiness badge", () => {
  it("maps the installed MOSS model into a terse ready state", () => {
    expect(voiceReadinessBadgeModel(payload())).toMatchObject({
      state: "ok",
      label: "voice ready",
    });
  });

  it("lets the live runtime muted state override installed model readiness", () => {
    expect(voiceReadinessBadgeModel(payload(), undefined, "muted")).toMatchObject({
      state: "warn",
      label: "voice muted",
    });
  });

  it("keeps missing installable MOSS visible without claiming readiness", () => {
    expect(
      voiceReadinessBadgeModel(
        payload({
          models: [
            model({
              installed: false,
              installable: true,
              missing: ["MOSS-TTS-Nano-100M-ONNX/encoder_model.onnx"],
            }),
          ],
          required_ready: false,
          all_ready: false,
        }),
      ),
    ).toMatchObject({
      state: "warn",
      label: "voice missing",
    });
  });

  it("marks non-installable MOSS as manual setup instead of a dead button", () => {
    expect(
      voiceReadinessBadgeModel(
        payload({
          models: [
            model({
              installed: false,
              installable: false,
              missing: ["browser_poc_manifest.json"],
            }),
          ],
          required_ready: false,
          all_ready: false,
        }),
      ),
    ).toMatchObject({
      state: "fault",
      label: "voice manual",
    });
  });

  it("routes first-run users from the shell badge into Crate setup", async () => {
    const footer = document.createElement("footer");
    const onOpenCrate = vi.fn();
    const handle = mountVoiceReadinessBadge(footer, {
      autoload: false,
      pollMs: null,
      subscribeStatusTick: false,
      onOpenCrate,
      getModels: async () =>
        payload({
          models: [
            model({
              installed: false,
              installable: true,
              missing: ["encoder_model.onnx"],
            }),
          ],
          required_ready: false,
          all_ready: false,
        }),
    });

    await handle.refresh();
    handle.element.click();

    expect(footer.querySelector(".footer-separator")).toBeTruthy();
    expect(handle.element.tagName).toBe("BUTTON");
    expect(handle.element.dataset.state).toBe("warn");
    expect(handle.element.textContent).toBe("voice missing");
    expect(onOpenCrate).toHaveBeenCalledOnce();
    handle.setVoiceStatus("muted");
    expect(handle.element.dataset.state).toBe("warn");
    expect(handle.element.textContent).toBe("voice muted");
    handle.setVoiceStatus("ok");
    expect(handle.element.dataset.state).toBe("warn");
    expect(handle.element.textContent).toBe("voice missing");
    handle.teardown();
    expect(footer.querySelector(".voice-readiness-badge")).toBeNull();
  });

  it("keeps backend failures honest as unknown", async () => {
    const footer = document.createElement("footer");
    const handle = mountVoiceReadinessBadge(footer, {
      autoload: false,
      pollMs: null,
      subscribeStatusTick: false,
      getModels: async () => {
        throw new Error("models offline");
      },
    });

    await handle.refresh();

    expect(handle.element.dataset.state).toBe("unknown");
    expect(handle.element.textContent).toBe("voice unknown");
    expect(handle.element.title).toContain("models offline");
  });
});
