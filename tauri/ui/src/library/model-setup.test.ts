// SPDX-License-Identifier: Apache-2.0
/* Vibe Engine — local model setup view spec.
 *
 * Pins the first-run setup contract: CLAP is required for embeddings/search,
 * CUE-DETR is optional unless the user explicitly checks/repairs it.
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
  id: "clap" | "cue-detr",
  overrides: Partial<LibraryModelAsset> = {},
): LibraryModelAsset {
  return {
    id,
    label: id === "clap" ? "CLAP ONNX" : "CUE-DETR ONNX",
    role: id === "clap" ? "library embeddings/search/similarity" : "cue anchors",
    required: id === "clap",
    env: id === "clap" ? "VIBEMIX_CLAP_ONNX_DIR" : "VIBEMIX_CUE_ONNX_PATH",
    installed: true,
    installable: id === "clap",
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
    models: [model("clap"), model("cue-detr")],
    required_ready: true,
    all_ready: true,
    ...overrides,
  };
}

describe("deriveModelSetupView", () => {
  it("hides the install button when CLAP and CUE are ready", () => {
    const view = deriveModelSetupView(payload());

    expect(view.stateText).toBe("CLAP ready · CUE ready");
    expect(view.installTarget).toBeNull();
    expect(view.installButtonHidden).toBe(true);
  });

  it("routes missing CLAP through the required-model install path", () => {
    const view = deriveModelSetupView(
      payload({
        models: [
          model("clap", { installed: false, missing: ["model.onnx"] }),
          model("cue-detr", { installed: false, missing: ["cuedetr.fp32.onnx"] }),
        ],
        required_ready: false,
        all_ready: false,
      }),
    );

    expect(view.stateText).toBe("CLAP missing · CUE optional");
    expect(view.installTarget).toBe("required");
    expect(view.installButtonHidden).toBe(false);
    expect(view.installButtonText).toBe("Install Required Models");
  });

  it("does not show an optional CUE action when no hosted artifact is configured", () => {
    const view = deriveModelSetupView(
      payload({
        models: [
          model("clap"),
          model("cue-detr", { installed: false, missing: ["cuedetr.fp32.onnx"] }),
        ],
        all_ready: false,
      }),
    );

    expect(view.stateText).toBe("CLAP ready · CUE optional");
    expect(view.installTarget).toBeNull();
    expect(view.installButtonHidden).toBe(true);
  });

  it("keeps installable optional CUE as its own check after required CLAP is ready", () => {
    const view = deriveModelSetupView(
      payload({
        models: [
          model("clap"),
          model("cue-detr", {
            installed: false,
            installable: true,
            missing: ["cuedetr.fp32.onnx"],
          }),
        ],
        all_ready: false,
      }),
    );

    expect(view.stateText).toBe("CLAP ready · CUE optional");
    expect(view.installTarget).toBe("cue");
    expect(view.installButtonText).toBe("Check Optional CUE");
  });

  it("surfaces optional CUE repair separately from required CLAP setup", () => {
    const view = deriveModelSetupView(
      payload({
        models: [
          model("clap"),
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

    expect(view.stateText).toBe("CLAP ready · CUE repair");
    expect(view.installTarget).toBe("cue");
    expect(view.installButtonText).toBe("Repair CUE");
  });

  it("labels non-installable CUE mismatch as manual repair without a button", () => {
    const view = deriveModelSetupView(
      payload({
        models: [
          model("clap"),
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

    expect(view.stateText).toBe("CLAP ready · CUE manual repair");
    expect(view.installTarget).toBeNull();
    expect(view.installButtonHidden).toBe(true);
  });

  it("shows retry copy when a required model install returns JSON errors", () => {
    const view = deriveModelSetupView(
      payload({
        models: [
          model("clap", { installed: false, missing: ["model.onnx"] }),
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
});

describe("modelInstallTargetFromDataset", () => {
  it("accepts every backend-supported install target", () => {
    const targets: LibraryModelInstallTarget[] = ["required", "clap", "cue", "all"];

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
    ).toBe("CLAP downloading 2/6 · text_model.onnx · 100 MB/478 MB");
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
    ).toBe("CLAP verified 1/6 · audio_model.onnx");

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
    ).toBe("CUE setup failed 1/1 · cuedetr.fp32.onnx");
  });
});
