/* Phase 33 / Plan 33-03 — BlackHole step renderer.
 *
 * Pins the absent/present branching:
 *   - probe absent  → install banner surfaces with [Open install page ↗]
 *                     + [↻ Recheck]
 *   - probe present → route status explains master-only vs deck-aware setup
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

  it("surfaces master-only route status when BlackHole 2ch is installed", () => {
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
    const route = root.querySelector<HTMLElement>(".cmp-bh-route");
    expect(route).not.toBeNull();
    expect(route?.dataset.deckCapable).toBe("false");
    expect(route?.textContent).toContain("MASTER ROUTE READY");
    expect(route?.textContent).toContain("BlackHole 2ch lets vibemix hear the master output");
    expect(route?.textContent).toContain("FLX4 plus BlackHole 16ch");
    expect(route?.textContent).toContain("let Sven tell decks apart");
    expect(route?.textContent).not.toContain("proof");
    expect(root.querySelectorAll("button").length).toBe(0);
  });

  it("surfaces deck-aware route status when BlackHole 16ch is installed", () => {
    const root = renderBlackHoleStep(
      { installed: true, device_name: "BlackHole 16ch" },
      {
        onOpenInstall: () => {},
        onRecheck: () => {},
      },
    );
    document.body.append(root);

    const route = root.querySelector<HTMLElement>(".cmp-bh-route");
    expect(route).not.toBeNull();
    expect(route?.dataset.deckCapable).toBe("true");
    expect(route?.textContent).toContain("DECK ROUTE READY");
    expect(route?.textContent).toContain("route deck 1 to channels 1/2");
    expect(route?.textContent).toContain("deck 2 to 3/4");
    expect(route?.textContent).toContain("Sven can tell your decks apart");
    expect(route?.textContent).not.toContain("proof");
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
