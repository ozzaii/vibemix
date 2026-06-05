// SPDX-License-Identifier: Apache-2.0
//
// The surface-mount layer: folds the REAL surface interiors into the cohesive
// shell's keep-alive anchors. The shell skeleton (DesktopShell.ts) renders each
// surface as a designed at-rest placeholder carrying a `data-wire` anchor; this
// layer mounts the live interiors onto those anchors WITHOUT editing the surface
// source modules — it calls their existing exported mount functions
// (routeSession / mountLibrary / mountLearnWindow), which are owned by concurrent
// sessions. The heavy mounts are injected as deps so the protocol below is
// unit-testable without a ws bus or Tauri runtime.
//
// Mount protocol (docs/design/vibemix-translation-layer.md "Mount protocol"):
//   - The deck wires onto its VISIBLE stage (.deck-stage); it owns its own
//     idle/live hero, so there is no hidden mount and no empty state to drop.
//   - The four stub surfaces (Viber/Learn/Debrief/Settings) each mount into a
//     hidden `.surface-mount`; revealing one clears its `hidden` and flags the
//     region `.surface--mounted` so CSS drops the sibling `.surface-empty`
//     (a previous-sibling selector isn't expressible in CSS, so the class is
//     the seam).

import { vmxLog } from "../debug-log.js";
import type { SurfaceId } from "./shell-store.js";

/** The heavy, runtime-bound interior mounts, injected so the orchestration is
 *  testable. In the app these wrap routeSession / mountLibrary / mountLearnWindow. */
export interface SurfaceMountDeps {
  /** Mount the live session onto the deck's visible stage (the hero — always). */
  mountDeck(stage: HTMLElement): void | Promise<void>;
  /** Mount the library / Viber interior into Viber's keep-alive mount. When
   *  absent, Viber keeps its designed at-rest empty state (folds in later). */
  mountViber?(mount: HTMLElement): void | Promise<void>;
  /** Mount the Learn interior into the learn keep-alive mount. When absent, the
   *  learn surface keeps its designed at-rest empty state (folds in later). */
  mountLearn?(mount: HTMLElement): void | Promise<void>;
  /** Mount the Debrief launch dock into the debrief keep-alive mount. */
  mountDebrief?(mount: HTMLElement): void | Promise<void>;
}

export interface MountedSurfaces {
  teardown(): void;
}

/**
 * Resolve a stub surface's hidden mount. The caller reveals it only after the
 * heavy interior mount succeeds, so a failed Viber/Learn boot leaves the
 * designed empty state visible instead of blanking the surface.
 * Returns the `.surface-mount` element where the real interior is injected.
 */
export function getStubMount(region: HTMLElement): HTMLElement {
  const mount = region.querySelector<HTMLElement>(".surface-mount");
  if (!mount) {
    throw new Error(
      `surface-mounts: region [data-surface="${region.dataset.surface ?? "?"}"] has no .surface-mount anchor`,
    );
  }
  return mount;
}

function revealMountedStub(target: HTMLElement): void {
  if (!target.classList.contains("surface-mount")) return;
  target.hidden = false;
  target.closest<HTMLElement>(".surface")?.classList.add("surface--mounted");
}

/**
 * Resolve the mount target for a surface: the visible `.deck-stage` for the deck
 * (no reveal — it has no empty state), or the revealed `.surface-mount` for a
 * stub surface.
 */
export function prepareSurfaceMount(shellRoot: HTMLElement, id: SurfaceId): HTMLElement {
  const region = shellRoot.querySelector<HTMLElement>(`.surface[data-surface="${id}"]`);
  if (!region) {
    throw new Error(`surface-mounts: no surface region for "${id}"`);
  }
  if (id === "deck") {
    const stage = region.querySelector<HTMLElement>(".deck-stage");
    if (!stage) {
      throw new Error('surface-mounts: deck region has no .deck-stage');
    }
    return stage;
  }
  return getStubMount(region);
}

/** Mount one interior, swallowing + logging any failure so a single surface's
 *  mount error never blanks the whole app (mirrors main.ts's per-surface
 *  non-fatal boot discipline). */
async function mountOne(
  label: string,
  target: HTMLElement,
  mount: (el: HTMLElement) => void | Promise<void>,
): Promise<void> {
  try {
    await mount(target);
    revealMountedStub(target);
  } catch (err) {
    const detail =
      err instanceof Error
        ? { message: err.message, stack: err.stack }
        : { message: String(err) };
    vmxLog("[vmx:error]", "shell surface failed to mount", { label, ...detail });
    // eslint-disable-next-line no-console
    console.error("[shell] surface failed to mount:", label, err);
  }
}

/**
 * Fold the real interiors into the shell. Each interior is mounted independently
 * and non-fatally; the deck is the hero (visible stage), Viber + Learn fold into
 * their revealed keep-alive mounts. Settings is wired at the app level because
 * it is the drawer overlay.
 */
export async function mountSurfacesInto(
  shellRoot: HTMLElement,
  deps: SurfaceMountDeps,
): Promise<MountedSurfaces> {
  // Deck is the hero — always mounted onto its visible stage.
  await mountOne("deck", prepareSurfaceMount(shellRoot, "deck"), deps.mountDeck);
  // Stub surfaces fold in only when an interior is provided; otherwise they keep
  // their designed at-rest empty state (so the mount is never revealed blank).
  if (deps.mountViber) {
    await mountOne("viber", prepareSurfaceMount(shellRoot, "viber"), deps.mountViber);
  }
  if (deps.mountLearn) {
    await mountOne("learn", prepareSurfaceMount(shellRoot, "learn"), deps.mountLearn);
  }
  if (deps.mountDebrief) {
    await mountOne("debrief", prepareSurfaceMount(shellRoot, "debrief"), deps.mountDebrief);
  }

  return {
    teardown(): void {
      // Interiors own their own teardown (routeSession's teardownSession, etc.).
      // This layer keeps no extra state to release in the current wiring.
    },
  };
}
