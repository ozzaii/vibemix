/**
 * @vitest-environment jsdom
 *
 * Contract for the surface-mount layer: how the REAL interiors fold into the
 * cohesive shell's keep-alive anchors. The orchestration takes the heavy mount
 * functions (routeSession / mountLibrary / mountLearnWindow — all ws/Tauri-bound
 * and not unit-testable in jsdom) as injected deps, so this exercises the mount
 * PROTOCOL (clear the hidden mount, hide the at-rest empty state, hand each
 * interior the right anchor) with real shell DOM and fake interiors.
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { mountDesktopShell, type MountedShell } from "../../src/shell/DesktopShell.js";
import {
  mountSurfacesInto,
  prepareSurfaceMount,
  revealStubMount,
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
  it("reveals a stub surface's hidden mount and hides its empty state", () => {
    const region = host.querySelector<HTMLElement>('.surface[data-surface="crate"]')!;
    const mount = region.querySelector<HTMLElement>(".surface-mount")!;
    expect(mount.hidden).toBe(true);

    const returned = revealStubMount(region);

    expect(returned).toBe(mount);
    expect(mount.hidden).toBe(false);
    // The region is flagged mounted so CSS drops the at-rest empty state
    // (previous-sibling selection isn't expressible in CSS, so a class on the
    // region is the seam).
    expect(region.classList.contains("surface--mounted")).toBe(true);
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

  it("resolves + reveals a stub surface's mount target", () => {
    const mount = prepareSurfaceMount(host, "crate");
    expect(mount.classList.contains("surface-mount")).toBe(true);
    expect(mount.hidden).toBe(false);
    expect(
      host.querySelector('.surface[data-surface="crate"]')!.classList.contains(
        "surface--mounted",
      ),
    ).toBe(true);
  });

  it("hands each interior its correct anchor and reveals the folded stubs", async () => {
    const got: Record<string, HTMLElement> = {};
    const deps: SurfaceMountDeps = {
      mountDeck: (el) => {
        got.deck = el;
      },
      mountCrate: (el) => {
        got.crate = el;
      },
      mountLearn: (el) => {
        got.learn = el;
      },
    };

    const mounted = await mountSurfacesInto(host, deps);

    // Deck wires onto the visible stage, never a hidden mount.
    expect(got.deck).toBe(
      host.querySelector('.surface[data-surface="deck"] .deck-stage'),
    );
    // Crate + Learn fold into their (now-revealed) keep-alive mounts.
    const crateMount = got.crate;
    const learnMount = got.learn;
    expect(crateMount).toBeDefined();
    expect(learnMount).toBeDefined();
    expect(crateMount!.classList.contains("surface-mount")).toBe(true);
    expect(crateMount!.hidden).toBe(false);
    expect(learnMount!.classList.contains("surface-mount")).toBe(true);
    expect(learnMount!.hidden).toBe(false);
    for (const id of ["crate", "learn"]) {
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
    const crate = host.querySelector<HTMLElement>('.surface[data-surface="crate"]')!;
    expect(crate.classList.contains("surface--mounted")).toBe(false);
    expect(crate.querySelector<HTMLElement>(".surface-mount")!.hidden).toBe(true);
    expect(crate.querySelector(".surface-empty")).toBeTruthy();
  });

  it("never throws if one interior's mount fails (a surface failing must not blank the app)", async () => {
    const deps: SurfaceMountDeps = {
      mountDeck: () => {
        throw new Error("deck boom");
      },
      mountCrate: () => {},
      mountLearn: () => {},
    };
    // The shell must survive a single surface's mount failure — partial app
    // beats a blank window (mirrors main.ts's per-surface non-fatal discipline).
    await expect(mountSurfacesInto(host, deps)).resolves.toBeTruthy();
  });
});
