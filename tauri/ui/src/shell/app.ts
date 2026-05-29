// SPDX-License-Identifier: Apache-2.0
//
// The shell application boot. Mounts the cohesive DesktopShell as the live app
// surface and folds the real interiors into its keep-alive anchors. Called by
// main.ts after the first-run wizard check — so the wizard, crash banner, error
// traps, perf observer, and sidecar/tray boot in main.ts are all preserved; this
// only swaps the post-wizard mount target from the bare session to the shell.
//
// Additive by construction: it composes the surfaces' EXISTING exported mount
// functions (routeSession, …) and never edits the surface modules, which are
// owned by concurrent sessions.

import "./shell.css"; // bundle the shell styles when loaded via index.html (shell.html also links them)
import "../library/library.css"; // the crate interior's styles (library.html links these separately)

// The library/Viber page markup, lifted from its own entry `?raw` so the
// injected scaffold never drifts from library.html (they are edited together by
// the surface's owner).
import libraryHtmlRaw from "../../library.html?raw";

import { vmxLog } from "../debug-log.js";
import { mountDesktopShell, type MountedShell } from "./DesktopShell.js";
import {
  mountSurfacesInto,
  type MountedSurfaces,
  type SurfaceMountDeps,
} from "./surface-mounts.js";
import { extractSurfaceMarkup } from "./scaffolds.js";
import { routeSession } from "../session/router.js";
import { closeSettings, openSettings } from "../settings/SettingsDrawer.js";

export interface MountedShellApp {
  readonly shell: MountedShell;
  readonly surfaces: MountedSurfaces;
  teardown(): void;
}

/** Flag the deck region as carrying a mounted interior so shell.css lets the
 *  full session fill the stage (overriding the placeholder's centered 720px). */
function markDeckMounted(stage: HTMLElement): void {
  stage.closest(".surface")?.classList.add("surface--mounted");
}

/**
 * The live interior deps. The deck IS the live session: routeSession mounts the
 * session layout onto the deck stage AND wires the ws bridge, render loop,
 * settings drawer, and tray/quit listeners. The shell chrome supersedes the
 * session's own titlebar (suppressed in shell.css). Crate + Learn fold in via
 * follow-up commits (their deps are added incrementally).
 */
const appDeps: SurfaceMountDeps = {
  mountDeck: async (stage) => {
    await routeSession(stage);
    markDeckMounted(stage);
  },
  // The crate is the library/Viber surface. Its module self-boots against fixed
  // ids from library.html, so: import the module first (its auto-boot guard
  // finds no #vmx-lib-runbtn yet and no-ops), then inject the page scaffold and
  // mount explicitly — exactly one mount, zero edits to the (concurrently owned)
  // library module.
  mountCrate: async (mount) => {
    const { mountLibrary } = await import("../library/index.js");
    mount.innerHTML = extractSurfaceMarkup(libraryHtmlRaw, ".vmx-lib-app");
    mountLibrary();
  },
};

/**
 * Mount the shell as the app and fold the real surfaces in. Idempotent at the
 * shell level (mountDesktopShell replaces the host's children); the interiors
 * own their own idempotency (routeSession tears down a prior mount first).
 */
/**
 * The Settings surface is the drawer routeSession already mounted (a fixed
 * overlay). Since the shell suppresses the session's own titlebar gear, the
 * shell's Settings nav (click / Cmd+5 / palette) is the opener: navigating TO
 * settings slides the drawer in, navigating away slides it out. Returns an
 * unsubscribe.
 */
function wireSettingsNav(shell: MountedShell): () => void {
  let prev = shell.store.getState().activeSurface;
  return shell.store.subscribe((model) => {
    if (model.activeSurface === prev) return;
    if (model.activeSurface === "settings") {
      openSettings();
    } else if (prev === "settings") {
      closeSettings();
    }
    prev = model.activeSurface;
  });
}

export async function mountShellApp(host: HTMLElement): Promise<MountedShellApp> {
  vmxLog("[vmx:state]", "shell-app → mount");
  const shell = mountDesktopShell(host);
  const surfaces = await mountSurfacesInto(host, appDeps);
  const unwireSettings = wireSettingsNav(shell);
  vmxLog("[vmx:state]", "shell-app → mounted");

  return {
    shell,
    surfaces,
    teardown(): void {
      unwireSettings();
      surfaces.teardown();
      shell.teardown();
    },
  };
}
