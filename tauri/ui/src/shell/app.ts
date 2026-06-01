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
import { wireActivation } from "./activation-bridge.js";
import { mountLibraryFreshnessBadge } from "./LibraryFreshnessBadge.js";
import { routeSession } from "../session/router.js";
import { closeSettings, openSettings } from "../settings/SettingsDrawer.js";
import { getSettingsUIState, subscribeSettingsUI } from "../settings/state.js";

export interface MountedShellApp {
  readonly shell: MountedShell;
  readonly surfaces: MountedSurfaces;
  teardown(): void;
}

/**
 * The live interior deps. The deck IS the live session: routeSession mounts the
 * session layout onto the deck stage AND wires the ws bridge, render loop,
 * settings drawer, and tray/quit listeners. The shell chrome supersedes the
 * session's own titlebar, and shell.css fills the stage with it — both keyed on
 * the mounted .vmx-session, so no post-mount flag is needed.
 */
const appDeps: SurfaceMountDeps = {
  mountDeck: async (stage) => {
    await routeSession(stage);
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
  // Learn folds in two stacked interiors, each in its OWN sub-container so
  // neither clobbers the other (the lesson window owns its host via
  // `root.innerHTML`): the Earned Wall (v11.0 — your six skills at a glance,
  // Mastered only from a cited live set) on top, the lesson runner below. The
  // wall reads `skill_wall` straight off the `ipc.learn.progress_state` window
  // event the lesson runner already requests on mount, so no extra wiring.
  mountLearn: async (mount) => {
    const wallHost = document.createElement("div");
    wallHost.className = "learn-earned-wall";
    const lessonHost = document.createElement("div");
    lessonHost.className = "learn-lesson-host";
    mount.append(wallHost, lessonHost);
    const { mountSkillWall } = await import("../learn/SkillWall.js");
    mountSkillWall(wallHost);
    const { mountLearnWindow } = await import("../learn/learn-window.js");
    mountLearnWindow(lessonHost);
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
export function wireSettingsNav(shell: MountedShell): () => void {
  let prev = shell.store.getState().activeSurface;
  let lastNonSettings = prev === "settings" ? "deck" : prev;

  if (prev === "settings") {
    openSettings();
  }

  const unstore = shell.store.subscribe((model) => {
    if (model.activeSurface !== "settings") {
      lastNonSettings = model.activeSurface;
    }
    if (model.activeSurface === prev) return;
    if (model.activeSurface === "settings") {
      openSettings();
    } else if (prev === "settings" && getSettingsUIState().open) {
      closeSettings();
    }
    prev = model.activeSurface;
  });

  const unsettings = subscribeSettingsUI((ui) => {
    if (!ui.open && shell.store.getState().activeSurface === "settings") {
      shell.store.setActiveSurface(lastNonSettings);
    }
  });

  return () => {
    unstore();
    unsettings();
  };
}

export async function mountShellApp(host: HTMLElement): Promise<MountedShellApp> {
  vmxLog("[vmx:state]", "shell-app → mount");
  const shell = mountDesktopShell(host);
  const surfaces = await mountSurfacesInto(host, appDeps);
  const unwireSettings = wireSettingsNav(shell);
  const footer = host.querySelector<HTMLElement>(".shell-footer");
  const freshnessBadge = footer ? mountLibraryFreshnessBadge(footer) : null;
  // Feed the live session onto the shell's self-arranging activation +
  // connection (energy field, connection dot, the grounding panel auto-open).
  const unwireActivation = wireActivation(shell.store);
  vmxLog("[vmx:state]", "shell-app → mounted");

  return {
    shell,
    surfaces,
    teardown(): void {
      unwireActivation();
      freshnessBadge?.teardown();
      unwireSettings();
      surfaces.teardown();
      shell.teardown();
    },
  };
}
