/* Phase 33 / Plan 33-04 — Windows SmartScreen step renderer.
 *
 * Pins the three behaviors:
 *   - non-Windows → empty body, no CTA
 *   - Windows + unsigned → explainer body + "Open install doc" CTA
 *   - Windows + signed → reassurance body, CTA hidden */

import { afterEach, describe, expect, it } from "vitest";

import {
  renderWindowsSmartScreenStep,
  WINDOWS_SMARTSCREEN_DOC_PATH,
} from "../components/windows-smartscreen-step.js";

afterEach(() => {
  document.body.replaceChildren();
});

describe("renderWindowsSmartScreenStep", () => {
  it("renders nothing on macOS", () => {
    const root = renderWindowsSmartScreenStep({
      platform: "darwin",
      onOpenInstallDoc: () => {},
    });
    document.body.append(root);
    expect(root.dataset.platform).toBe("darwin");
    expect(root.querySelector("button")).toBeNull();
    expect(root.textContent ?? "").toBe("");
  });

  it("renders explainer + CTA on unsigned Windows builds", () => {
    let clicks = 0;
    const root = renderWindowsSmartScreenStep({
      platform: "win32",
      signed: false,
      onOpenInstallDoc: () => clicks++,
    });
    document.body.append(root);
    expect(root.dataset.platform).toBe("win32");
    expect(root.dataset.signed).toBe("false");
    const heading = root.querySelector(".wizard-smartscreen-step__heading");
    expect(heading?.textContent).toContain("SMARTSCREEN");
    const body = root.querySelector(".wizard-smartscreen-step__body");
    expect(body?.textContent?.toLowerCase()).toContain("more info");
    const cta = root.querySelector<HTMLButtonElement>("button");
    expect(cta).not.toBeNull();
    cta!.click();
    expect(clicks).toBe(1);
  });

  it("hides the CTA on signed Windows builds", () => {
    const root = renderWindowsSmartScreenStep({
      platform: "win32",
      signed: true,
      onOpenInstallDoc: () => {},
    });
    document.body.append(root);
    expect(root.dataset.signed).toBe("true");
    expect(root.querySelector("button")).toBeNull();
  });

  it("doc path points at the canonical install doc", () => {
    expect(WINDOWS_SMARTSCREEN_DOC_PATH).toBe(
      "docs/install/windows-smartscreen.md",
    );
  });
});
