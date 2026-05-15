/* Phase 33 / Plan 33-03 — BlackHole step renderer.
 *
 * Pins the absent/present branching:
 *   - probe absent  → install banner surfaces with [Open install page ↗]
 *                     + [↻ Recheck]
 *   - probe present → banner hidden (empty container)
 * Plus the install URL is the official existential.audio URL — kept in
 * sync with the Tauri shell-open capability allowlist.
 */

import { afterEach, describe, expect, it } from "vitest";

import {
  BLACKHOLE_INSTALL_URL,
  renderBlackHoleStep,
} from "../components/blackhole-step.js";

afterEach(() => {
  document.body.replaceChildren();
});

describe("BlackHole step renderer", () => {
  it("surfaces install banner when probe reports absent", () => {
    let opened = 0;
    let rechecked = 0;
    const root = renderBlackHoleStep(
      { installed: false, device_name: null },
      {
        onOpenInstall: () => opened++,
        onRecheck: () => rechecked++,
      },
    );
    document.body.append(root);

    expect(root.dataset.installed).toBe("false");
    const banner = root.querySelector(".cmp-bh-banner");
    expect(banner).not.toBeNull();

    const buttons = root.querySelectorAll<HTMLButtonElement>("button");
    // Two buttons: Open install page + Recheck
    expect(buttons.length).toBe(2);
    buttons[0]!.click();
    buttons[1]!.click();
    expect(opened).toBe(1);
    expect(rechecked).toBe(1);
  });

  it("hides install banner when probe reports installed", () => {
    const root = renderBlackHoleStep(
      { installed: true, device_name: "BlackHole 2ch" },
      {
        onOpenInstall: () => {},
        onRecheck: () => {},
      },
    );
    document.body.append(root);

    expect(root.dataset.installed).toBe("true");
    expect(root.querySelector(".cmp-bh-banner")).toBeNull();
    expect(root.querySelectorAll("button").length).toBe(0);
  });

  it("post-click state surfaces the recheck caption", () => {
    const root = renderBlackHoleStep(
      { installed: false, device_name: null },
      {
        onOpenInstall: () => {},
        onRecheck: () => {},
        postClickState: true,
      },
    );
    document.body.append(root);
    const caption = root.querySelector(".cmp-bh-banner__caption");
    expect(caption).not.toBeNull();
    expect(caption?.textContent?.toLowerCase()).toContain("install then click recheck");
  });

  it("install URL is the official existential.audio installer", () => {
    expect(BLACKHOLE_INSTALL_URL).toBe("https://existential.audio/blackhole/");
  });
});
