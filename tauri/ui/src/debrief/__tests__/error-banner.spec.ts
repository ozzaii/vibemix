// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 — ErrorBanner reason→copy map vitest spec.

import { afterEach, describe, expect, it } from "vitest";

import {
  reasonToCopy,
  resolveSkeletonsToTerminal,
  showErrorBanner,
  showWorkingBanner,
  type SkeletonHosts,
} from "../components/error-banner.js";

afterEach(() => {
  document.body.replaceChildren();
});

describe("error-banner reason→copy map", () => {
  it("events_missing → user copy", () => {
    expect(reasonToCopy("events_missing")).toBe(
      "I didn't catch anything in that session to debrief. Try a longer set.",
    );
  });

  it("session_too_short → user copy", () => {
    expect(reasonToCopy("session_too_short")).toBe(
      "That set is too short for a fair debrief. Give me at least five minutes of music.",
    );
  });

  it("sidecar_crashed → user copy", () => {
    expect(reasonToCopy("sidecar_crashed")).toBe(
      "Debrief crashed unexpectedly. Try reopening.",
    );
  });

  it("tldr_generation_failed → user copy", () => {
    expect(reasonToCopy("tldr_generation_failed")).toBe(
      "Couldn't put your recap together. Try reopening.",
    );
  });

  it("drills_generation_failed → user copy", () => {
    expect(reasonToCopy("drills_generation_failed")).toBe(
      "Couldn't build drills I can stand behind this time. Try reopening.",
    );
  });

  it("port_in_use → user copy", () => {
    expect(reasonToCopy("port_in_use")).toContain("already open");
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

  it("unknown reason speaks product copy, never raw sidecar prose", () => {
    const div = document.createElement("div");
    document.body.append(div);
    showErrorBanner(div, "bogus", "Traceback (most recent call last): boom");
    expect(div.textContent).not.toContain("Traceback");
    expect(div.textContent).toContain("Try reopening");
  });

  it("renders the honest working line without a dismiss control", () => {
    const host = document.createElement("div");
    showWorkingBanner(host);
    expect(host.hidden).toBe(false);
    expect(host.dataset.reason).toBe("still_working");
    expect(host.textContent).toContain("still putting your debrief together");
    expect(host.querySelector("button")).toBeNull();
  });
});

describe("resolveSkeletonsToTerminal", () => {
  function skeletonHost(): HTMLElement {
    const host = document.createElement("div");
    const p = document.createElement("p");
    p.className = "vmx-debrief-skeleton";
    p.textContent = "Generating…";
    host.append(p);
    return host;
  }

  function hosts(): SkeletonHosts {
    return { morning: skeletonHost(), tldr: skeletonHost(), drills: skeletonHost() };
  }

  it("a terminal error settles all three skeletons", () => {
    const h = hosts();
    resolveSkeletonsToTerminal(h, "invalid_session_dir");
    for (const host of [h.morning!, h.tldr!, h.drills!]) {
      const line = host.querySelector<HTMLElement>(".vmx-debrief-skeleton");
      expect(line?.dataset.state).toBe("settled");
      expect(line?.textContent).not.toContain("Generating");
    }
  });

  it("a tldr-only failure leaves the other panels' live work alone", () => {
    const h = hosts();
    resolveSkeletonsToTerminal(h, "tldr_generation_failed");
    expect(h.tldr!.textContent).toBe("No recap this time.");
    expect(h.morning!.textContent).toBe("Generating…");
    expect(h.drills!.textContent).toBe("Generating…");
  });

  it("never overwrites a panel a success frame already resolved", () => {
    const h = hosts();
    h.drills!.textContent = "";
    const real = document.createElement("article");
    real.textContent = "real drill content";
    h.drills!.append(real);
    resolveSkeletonsToTerminal(h, "sidecar_crashed");
    expect(h.drills!.textContent).toBe("real drill content");
  });

  it("tolerates null hosts", () => {
    expect(() =>
      resolveSkeletonsToTerminal(
        { morning: null, tldr: null, drills: null },
        "sidecar_crashed",
      ),
    ).not.toThrow();
  });
});
