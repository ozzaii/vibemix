/**
 * @vitest-environment jsdom
 *
 * The shell voice badge is the live-deck signal for the local voice
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
    id: "chatterbox-voice",
    label: "Chatterbox voice",
    role: "local co-host voice",
    required: true,
    env: "VIBEMIX_CHATTERBOX_REF",
    installed: true,
    installable: true,
    path: "~/.cache/vibemix/voice/cohost_voice_ref.wav",
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
  it("maps the installed Chatterbox voice model into a terse ready state", () => {
    expect(voiceReadinessBadgeModel(payload())).toMatchObject({
      state: "ok",
      label: "",
    });
  });

  it("keeps legacy MOSS rows readable for older payloads", () => {
    expect(
      voiceReadinessBadgeModel(
        payload({
          models: [
            model({
              id: "moss-tts",
              label: "MOSS TTS ONNX",
              env: "VIBEMIX_MOSS_TTS_DIR",
              path: "~/.cache/vibemix/moss-tts-onnx/MOSS-TTS-Nano-100M-ONNX",
            }),
          ],
        }),
      ),
    ).toMatchObject({
      state: "ok",
      label: "",
    });
  });

  it("lets the live runtime muted state explain subtitles and setup readiness", () => {
    expect(voiceReadinessBadgeModel(payload(), undefined, "muted")).toMatchObject({
      state: "warn",
      label: "voice muted",
      title:
        "Local voice is muted for this session; voice setup is ready. Subtitles stay visible.",
    });
  });

  it("keeps missing installable voice setup visible without claiming readiness", () => {
    expect(
      voiceReadinessBadgeModel(
        payload({
          models: [
            model({
              installed: false,
              installable: true,
              missing: ["cohost_voice_ref.wav"],
            }),
          ],
          required_ready: false,
          all_ready: false,
        }),
      ),
    ).toMatchObject({
      state: "warn",
      label: "voice setup",
    });
  });

  it("marks non-installable voice setup as manual setup instead of a dead button", () => {
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
      label: "voice down",
    });
  });

  it("keeps runtime muted honest when local voice setup is missing too", () => {
    expect(
      voiceReadinessBadgeModel(
        payload({
          models: [
            model({
              installed: false,
              installable: false,
              missing: ["cohost_voice_ref.wav"],
            }),
          ],
          required_ready: false,
          all_ready: false,
        }),
        undefined,
        "muted",
      ),
    ).toMatchObject({
      state: "warn",
      label: "voice muted",
      title:
        "Local voice is muted for this session; voice setup is missing, missing 1 item. Subtitles stay visible.",
    });
  });

  it("routes first-run users from the shell badge into Viber setup", async () => {
    const footer = document.createElement("footer");
    const onOpenViber = vi.fn();
    const handle = mountVoiceReadinessBadge(footer, {
      autoload: false,
      pollMs: null,
      subscribeStatusTick: false,
      onOpenViber,
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
    // Degraded states carry words now (fable pass): warn/fault label the
    // problem instead of hiding behind a 6px dot.
    expect(handle.element.textContent).toBe("voice setup");
    expect(onOpenViber).toHaveBeenCalledOnce();
    handle.setVoiceStatus("muted");
    expect(handle.element.dataset.state).toBe("warn");
    expect(handle.element.textContent).toBe("voice muted");
    handle.setVoiceStatus("ok");
    expect(handle.element.dataset.state).toBe("warn");
    expect(handle.element.textContent).toBe("voice setup");
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
    expect(handle.element.hidden).toBe(true);
    expect(handle.element.textContent).toBe("");
    expect(handle.element.title).toContain("models offline");
  });
});
