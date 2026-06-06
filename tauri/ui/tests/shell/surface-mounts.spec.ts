/**
 * @vitest-environment jsdom
 *
 * Contract for the surface-mount layer: how the REAL interiors fold into the
 * cohesive shell's keep-alive anchors. The orchestration takes the heavy mount
 * functions (routeSession / mountLibrary / mountLearnWindow — all ws/Tauri-bound
 * and not unit-testable in jsdom) as injected deps, so this exercises the mount
 * PROTOCOL (hand each interior the hidden anchor, reveal it only after success,
 * keep the at-rest empty state on failure) with real shell DOM and fake
 * interiors.
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { mountDesktopShell, type MountedShell } from "../../src/shell/DesktopShell.js";
import {
  getStubMount,
  mountSurfacesInto,
  prepareSurfaceMount,
  type SurfaceMountDeps,
} from "../../src/shell/surface-mounts.js";

let shell: MountedShell | null = null;
let host: HTMLElement;

beforeEach(() => {
  globalThis.localStorage?.clear();
  host = document.createElement("div");
  document.body.append(host);
  shell = mountDesktopShell(host);
});

afterEach(() => {
  shell?.teardown();
  shell = null;
  host.remove();
});

describe("surface-mount layer", () => {
  it("resolves a stub surface's hidden mount without blanking its empty state", () => {
    const region = host.querySelector<HTMLElement>('.surface[data-surface="viber"]')!;
    const mount = region.querySelector<HTMLElement>(".surface-mount")!;
    expect(mount.hidden).toBe(true);

    const returned = getStubMount(region);

    expect(returned).toBe(mount);
    expect(mount.hidden).toBe(true);
    expect(region.classList.contains("surface--mounted")).toBe(false);
  });

  it("resolves the deck's visible stage as its mount target (no hidden mount)", () => {
    const stage = host.querySelector<HTMLElement>(
      '.surface[data-surface="deck"] .deck-stage',
    )!;
    expect(prepareSurfaceMount(host, "deck")).toBe(stage);
    // The deck has no .surface-mount and keeps no empty-state class.
    expect(
      host.querySelector('.surface[data-surface="deck"] .surface-mount'),
    ).toBeNull();
  });

  it("resolves a stub surface's mount target without revealing it early", () => {
    const mount = prepareSurfaceMount(host, "viber");
    expect(mount.classList.contains("surface-mount")).toBe(true);
    expect(mount.hidden).toBe(true);
    expect(
      host.querySelector('.surface[data-surface="viber"]')!.classList.contains(
        "surface--mounted",
      ),
    ).toBe(false);
  });

  it("hands each interior its correct anchor and reveals the folded stubs", async () => {
    const got: Record<string, HTMLElement> = {};
    const deps: SurfaceMountDeps = {
      mountDeck: (el) => {
        got.deck = el;
      },
      mountViber: (el) => {
        got.viber = el;
      },
      mountLearn: (el) => {
        got.learn = el;
      },
      mountDebrief: (el) => {
        got.debrief = el;
      },
    };

    const mounted = await mountSurfacesInto(host, deps);

    // Deck wires onto the visible stage, never a hidden mount.
    expect(got.deck).toBe(
      host.querySelector('.surface[data-surface="deck"] .deck-stage'),
    );
    // Viber, the parked Learn tease, and Debrief fold into their revealed
    // keep-alive mounts.
    const viberMount = got.viber;
    const learnMount = got.learn;
    const debriefMount = got.debrief;
    expect(viberMount).toBeDefined();
    expect(learnMount).toBeDefined();
    expect(debriefMount).toBeDefined();
    expect(viberMount!.classList.contains("surface-mount")).toBe(true);
    expect(viberMount!.hidden).toBe(false);
    expect(learnMount!.classList.contains("surface-mount")).toBe(true);
    expect(learnMount!.dataset.wire).toBe("shell.surface.learn");
    expect(learnMount!.hidden).toBe(false);
    expect(debriefMount!.classList.contains("surface-mount")).toBe(true);
    expect(debriefMount!.hidden).toBe(false);
    for (const id of ["viber", "learn", "debrief"]) {
      expect(
        host.querySelector(`.surface[data-surface="${id}"]`)!.classList.contains(
          "surface--mounted",
        ),
      ).toBe(true);
    }
    expect(typeof mounted.teardown).toBe("function");
  });

  it("leaves a surface as its designed empty state when no interior dep is given", async () => {
    // Incremental folding: a surface with no interior dep must keep its at-rest
    // empty state (mount stays hidden, no surface--mounted flag) rather than
    // revealing a blank mount. Deck-only is a valid intermediate app state.
    await mountSurfacesInto(host, { mountDeck: () => {} });
    const viber = host.querySelector<HTMLElement>('.surface[data-surface="viber"]')!;
    expect(viber.classList.contains("surface--mounted")).toBe(false);
    expect(viber.querySelector<HTMLElement>(".surface-mount")!.hidden).toBe(true);
    expect(viber.querySelector(".surface-empty")).toBeTruthy();
  });

  it("never throws if one interior's mount fails (a surface failing must not blank the app)", async () => {
    const deps: SurfaceMountDeps = {
      mountDeck: () => {
        throw new Error("deck boom");
      },
      mountViber: () => {},
      mountLearn: () => {},
    };
    // The shell must survive a single surface's mount failure — partial app
    // beats a blank window (mirrors main.ts's per-surface non-fatal discipline).
    await expect(mountSurfacesInto(host, deps)).resolves.toBeTruthy();
  });

  it("keeps a stub surface readable when its heavy mount fails", async () => {
    await mountSurfacesInto(host, {
      mountDeck: () => {},
      mountViber: () => {
        throw new Error("viber boom");
      },
    });

    const viber = host.querySelector<HTMLElement>('.surface[data-surface="viber"]')!;
    expect(viber.classList.contains("surface--mounted")).toBe(false);
    expect(viber.querySelector<HTMLElement>(".surface-mount")!.hidden).toBe(true);
    expect(viber.querySelector(".surface-empty")?.textContent).toContain(
      "Viber is ready for your library.",
    );
  });
});
