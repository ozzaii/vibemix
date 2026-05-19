// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 — ErrorBanner reason→copy map vitest spec.

import { afterEach, describe, expect, it } from "vitest";

import { reasonToCopy, showErrorBanner } from "../components/error-banner.js";

afterEach(() => {
  document.body.replaceChildren();
});

describe("error-banner reason→copy map", () => {
  it("events_missing → user copy", () => {
    expect(reasonToCopy("events_missing")).toBe(
      "This session has no event data. Try a longer recording.",
    );
  });

  it("session_too_short → user copy", () => {
    expect(reasonToCopy("session_too_short")).toBe(
      "Session is too short for a meaningful debrief (need ≥ 5 minutes).",
    );
  });

  it("sidecar_crashed → user copy", () => {
    expect(reasonToCopy("sidecar_crashed")).toBe(
      "Debrief crashed unexpectedly. Try reopening.",
    );
  });

  it("tldr_generation_failed → user copy", () => {
    expect(reasonToCopy("tldr_generation_failed")).toBe(
      "Couldn't generate the voiced summary. Try refreshing.",
    );
  });

  it("drills_generation_failed → user copy", () => {
    expect(reasonToCopy("drills_generation_failed")).toBe(
      "Couldn't generate drills with valid citations. Try refreshing.",
    );
  });

  it("port_in_use → user copy", () => {
    expect(reasonToCopy("port_in_use")).toContain("8766");
  });

  it("unknown reason returns empty string", () => {
    expect(reasonToCopy("bogus")).toBe("");
  });
});

describe("showErrorBanner mounts dom", () => {
  it("renders banner with reason data attr + dismiss button", () => {
    const div = document.createElement("div");
    document.body.append(div);
    showErrorBanner(div, "session_too_short");
    expect(div.hidden).toBe(false);
    expect(div.dataset.reason).toBe("session_too_short");
    expect(div.querySelector(".vmx-debrief-error-dismiss")).not.toBeNull();
  });

  it("dismiss button hides the banner", () => {
    const div = document.createElement("div");
    document.body.append(div);
    showErrorBanner(div, "sidecar_crashed");
    (div.querySelector(".vmx-debrief-error-dismiss") as HTMLButtonElement).click();
    expect(div.hidden).toBe(true);
  });

  it("unknown reason renders fallback message", () => {
    const div = document.createElement("div");
    document.body.append(div);
    showErrorBanner(div, "bogus", "fallback msg");
    expect(div.textContent).toContain("fallback msg");
  });
});
