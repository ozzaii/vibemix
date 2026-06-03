// SPDX-License-Identifier: Apache-2.0
/* Vibe Engine — local model setup view spec.
 *
 * Pins the first-run setup contract: CLAP + MOSS are required, and CUE-DETR
 * is optional unless the user explicitly checks/repairs it.
 */

import { describe, expect, it } from "vitest";

import type {
  LibraryModelAsset,
  LibraryModelInstallTarget,
  LibraryModelsResult,
} from "./api.js";
import {
  deriveModelSetupView,
  modelInstallTargetFromDataset,
  modelProgressStateText,
} from "./index.js";

function model(
  id: "clap" | "moss-tts" | "cue-detr",
  overrides: Partial<LibraryModelAsset> = {},
): LibraryModelAsset {
  const defaults = {
    clap: {
      label: "CLAP ONNX",
      role: "library embeddings/search/similarity",
      required: true,
      env: "VIBEMIX_CLAP_ONNX_DIR",
      installable: true,
    },
    "moss-tts": {
      label: "MOSS TTS ONNX",
      role: "local co-host voice",
      required: true,
      env: "VIBEMIX_MOSS_TTS_DIR",
      installable: false,
    },
    "cue-detr": {
      label: "CUE-DETR ONNX",
      role: "cue anchors",
      required: false,
      env: "VIBEMIX_CUE_ONNX_PATH",
      installable: false,
    },
  }[id];
  return {
    id,
    label: defaults.label,
    role: defaults.role,
    required: defaults.required,
    env: defaults.env,
    installed: true,
    installable: defaults.installable,
    path: `/tmp/vibemix-test/${id}`,
    missing: [],
    mismatched: [],
    ...overrides,
  };
}

function payload(
  overrides: Partial<LibraryModelsResult> = {},
): LibraryModelsResult {
  return {
    models: [model("clap"), model("moss-tts"), model("cue-detr")],
    required_ready: true,
    all_ready: true,
    ...overrides,
  };
}

describe("deriveModelSetupView", () => {
  it("hides the install button when CLAP, MOSS, and CUE are ready", () => {
    const view = deriveModelSetupView(payload());

    expect(view.stateText).toBe("search ready · voice ready · cue export ready");
    expect(view.installTarget).toBeNull();
    expect(view.installButtonHidden).toBe(true);
  });

  it("routes missing CLAP through the required-model install path", () => {
    const view = deriveModelSetupView(
      payload({
        models: [
          model("clap", { installed: false, missing: ["model.onnx"] }),
          model("moss-tts"),
          model("cue-detr", { installed: false, missing: ["cuedetr.fp32.onnx"] }),
        ],
        required_ready: false,
        all_ready: false,
      }),
    );

    expect(view.stateText).toBe("search missing · voice ready · cue export optional");
    expect(view.installTarget).toBe("required");
    expect(view.installButtonHidden).toBe(false);
    expect(view.installButtonText).toBe("Install Required Models");
  });

  it("routes missing MOSS through required setup without pretending it is CLAP", () => {
    const view = deriveModelSetupView(
      payload({
        models: [
          model("clap"),
          model("moss-tts", {
            installed: false,
            installable: false,
            missing: ["encoder_model.onnx"],
          }),
          model("cue-detr"),
        ],
        required_ready: false,
        all_ready: false,
      }),
    );

    expect(view.stateText).toBe("search ready · voice manual setup · cue export ready");
    expect(view.installTarget).toBe("required");
    expect(view.installButtonHidden).toBe(false);
    expect(view.installButtonText).toBe("Install Required Models");
  });

  it("labels an operator-hosted MOSS install as missing when pins are configured", () => {
    const view = deriveModelSetupView(
      payload({
        models: [
          model("clap"),
          model("moss-tts", {
            installed: false,
            installable: true,
            missing: ["encoder_model.onnx"],
          }),
          model("cue-detr"),
        ],
        required_ready: false,
        all_ready: false,
      }),
    );

    expect(view.stateText).toBe("search ready · voice missing · cue export ready");
    expect(view.installTarget).toBe("required");
  });

  it("does not show an optional CUE action when no hosted artifact is configured", () => {
    const view = deriveModelSetupView(
      payload({
        models: [
          model("clap"),
          model("moss-tts"),
          model("cue-detr", { installed: false, missing: ["cuedetr.fp32.onnx"] }),
        ],
        all_ready: false,
      }),
    );

    expect(view.stateText).toBe("search ready · voice ready · cue export optional");
    expect(view.installTarget).toBeNull();
    expect(view.installButtonHidden).toBe(true);
  });

  it("keeps installable optional CUE as its own check after required CLAP is ready", () => {
    const view = deriveModelSetupView(
      payload({
        models: [
          model("clap"),
          model("moss-tts"),
          model("cue-detr", {
            installed: false,
            installable: true,
            missing: ["cuedetr.fp32.onnx"],
          }),
        ],
        all_ready: false,
      }),
    );

    expect(view.stateText).toBe("search ready · voice ready · cue export optional");
    expect(view.installTarget).toBe("cue");
    expect(view.installButtonText).toBe("Check Optional CUE");
  });

  it("surfaces optional cue export repair separately from required CLAP setup", () => {
    const view = deriveModelSetupView(
      payload({
        models: [
          model("clap"),
          model("moss-tts"),
          model("cue-detr", {
            installed: false,
            installable: true,
            missing: [],
            mismatched: ["cuedetr.fp32.onnx"],
          }),
        ],
        all_ready: false,
      }),
    );

    expect(view.stateText).toBe("search ready · voice ready · cue export repair");
    expect(view.installTarget).toBe("cue");
    expect(view.installButtonText).toBe("Repair CUE");
  });

  it("labels non-installable CUE mismatch as manual repair without a button", () => {
    const view = deriveModelSetupView(
      payload({
        models: [
          model("clap"),
          model("moss-tts"),
          model("cue-detr", {
            installed: false,
            installable: false,
            missing: [],
            mismatched: ["cuedetr.fp32.onnx"],
          }),
        ],
        all_ready: false,
      }),
    );

    expect(view.stateText).toBe("search ready · voice ready · cue export manual repair");
    expect(view.installTarget).toBeNull();
    expect(view.installButtonHidden).toBe(true);
  });

  it("shows retry copy when a required model install returns JSON errors", () => {
    const view = deriveModelSetupView(
      payload({
        models: [
          model("clap", { installed: false, missing: ["model.onnx"] }),
          model("moss-tts"),
          model("cue-detr"),
        ],
        required_ready: false,
        all_ready: false,
        install: {
          target: "required",
          ok: false,
          results: [
            {
              id: "clap",
              installed: false,
              path: "/tmp/vibemix-test/clap",
              files: [],
              errors: ["download failed"],
            },
          ],
        },
      }),
    );

    expect(view.stateText).toContain("Model setup failed: download failed");
    expect(view.installTarget).toBe("required");
    expect(view.installButtonText).toBe("Retry Required Models");
  });

  it("shows optional CUE retry copy without blocking required readiness", () => {
    const view = deriveModelSetupView(
      payload({
        models: [
          model("clap"),
          model("moss-tts"),
          model("cue-detr", { installed: false, missing: ["cuedetr.fp32.onnx"] }),
        ],
        all_ready: false,
        install: {
          target: "cue",
          ok: false,
          results: [
            {
              id: "cue-detr",
              installed: false,
              path: "/tmp/vibemix-test/cuedetr.fp32.onnx",
              files: [],
              errors: ["VIBEMIX_CUE_ONNX_URL is not configured"],
            },
          ],
        },
      }),
    );

    expect(view.stateText).toContain("Optional CUE setup unavailable");
    expect(view.installTarget).toBeNull();
    expect(view.installButtonHidden).toBe(true);
  });

  it("uses MOSS-specific install error copy for direct MOSS checks", () => {
    const view = deriveModelSetupView(
      payload({
        models: [
          model("clap"),
          model("moss-tts", {
            installed: false,
            installable: true,
            missing: ["encoder_model.onnx"],
          }),
          model("cue-detr"),
        ],
        required_ready: false,
        all_ready: false,
        install: {
          target: "moss",
          ok: false,
          results: [
            {
              id: "moss-tts",
              installed: false,
              path: "/tmp/vibemix-test/moss-tts",
              files: [],
              errors: ["set VIBEMIX_MOSS_TTS_ARCHIVE_URL"],
            },
          ],
        },
      }),
    );

    expect(view.stateText).toContain("MOSS voice setup unavailable");
    expect(view.installTarget).toBe("required");
  });
});

describe("modelInstallTargetFromDataset", () => {
  it("accepts every backend-supported install target", () => {
    const targets: LibraryModelInstallTarget[] = [
      "required",
      "clap",
      "moss",
      "cue",
      "all",
    ];

    expect(targets.map((target) => modelInstallTargetFromDataset(target))).toEqual(
      targets,
    );
  });

  it("falls back to required for missing or stale markup", () => {
    expect(modelInstallTargetFromDataset(undefined)).toBe("required");
    expect(modelInstallTargetFromDataset("gemini")).toBe("required");
  });
});

describe("modelProgressStateText", () => {
  it("renders first-run CLAP download progress with file count and bytes", () => {
    expect(
      modelProgressStateText({
        target: "required",
        id: "clap",
        n: 2,
        total: 6,
        status: "downloading",
        rel_path: "onnx/text_model.onnx",
        downloaded: 104_857_600,
        size: 501_513_769,
      }),
    ).toBe("Sound match downloading 2/6 · 100 MB/478 MB");
  });

  it("renders verified and error terminal frames without pretending success", () => {
    expect(
      modelProgressStateText({
        target: "required",
        id: "clap",
        n: 1,
        total: 6,
        status: "verified",
        rel_path: "onnx/audio_model.onnx",
        downloaded: 281_749_092,
        size: 281_749_092,
      }),
    ).toBe("Sound match verified 1/6");

    expect(
      modelProgressStateText({
        target: "moss",
        id: "moss-tts",
        n: 1,
        total: 3,
        status: "downloading",
        rel_path: "MOSS-TTS-Nano-100M-ONNX/encoder_model.onnx",
        downloaded: 10_485_760,
        size: 104_857_600,
      }),
    ).toBe("Voice downloading 1/3 · 10 MB/100 MB");

    expect(
      modelProgressStateText({
        target: "cue",
        id: "cue-detr",
        n: 1,
        total: 1,
        status: "error",
        rel_path: "cuedetr.fp32.onnx",
        downloaded: 0,
        size: 0,
      }),
    ).toBe("Cue finder setup failed 1/1");
  });
});
