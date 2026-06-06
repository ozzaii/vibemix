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
import "../library/library.css"; // the Viber interior's styles (library.html links these separately)

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
import { mountVoiceReadinessBadge } from "./VoiceReadinessBadge.js";
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
  // Viber is the library/set-prep surface. Its module self-boots against fixed
  // ids from library.html, so: import the module first (its auto-boot guard
  // finds no #vmx-lib-runbtn yet and no-ops), then inject the page scaffold and
  // mount explicitly — exactly one mount, zero edits to the (concurrently owned)
  // library module.
  mountViber: async (mount) => {
    const { mountLibrary } = await import("../library/index.js");
    mount.innerHTML = extractSurfaceMarkup(libraryHtmlRaw, ".vmx-lib-app");
    mountLibrary(mount);
  },
  mountLearn: async (mount) => {
    mountLearnTease(mount);
  },
  mountDebrief: async (mount) => {
    const { mountDebriefDock } = await import("./DebriefDock.js");
    mountDebriefDock(mount, { autoRefresh: false });
  },
};

function appendLearnTeaseRow(list: HTMLDListElement, label: string, value: string): void {
  const row = document.createElement("div");
  row.className = "learn-tease__row";
  const dt = document.createElement("dt");
  dt.textContent = label;
  const dd = document.createElement("dd");
  dd.textContent = value;
  row.append(dt, dd);
  list.append(row);
}

function mountLearnTease(mount: HTMLElement): void {
  mount.replaceChildren();

  const root = document.createElement("section");
  root.className = "learn-tease";
  root.setAttribute("aria-labelledby", "learn-tease-title");

  const plate = document.createElement("div");
  plate.className = "learn-tease__plate";

  const led = document.createElement("span");
  led.className = "learn-tease__led";
  led.setAttribute("aria-hidden", "true");

  const kicker = document.createElement("p");
  kicker.className = "learn-tease__kicker";
  kicker.textContent = "Premium v2";

  const title = document.createElement("h2");
  title.id = "learn-tease-title";
  title.className = "learn-tease__title";
  title.textContent = "Teaching that earns its place.";

  const body = document.createElement("p");
  body.className = "learn-tease__body";
  body.textContent =
    "Lessons stay parked for launch until practice audio, controller proof, and feedback all meet the same bar as Sven.";

  const proof = document.createElement("dl");
  proof.className = "learn-tease__proof";
  appendLearnTeaseRow(proof, "Launch", "parked, not hidden");
  appendLearnTeaseRow(proof, "Engine", "preserved in git");
  appendLearnTeaseRow(proof, "Rule", "no fake lessons");

  const note = document.createElement("p");
  note.className = "learn-tease__note";
  note.textContent =
    "Debrief and Viber stay live for launch. Lessons return when they can teach without pretending.";

  plate.append(led, kicker, title, body, proof, note);
  root.append(plate);
  mount.append(root);
}

/**
 * Mount the shell as the app and fold the real surfaces in. Idempotent at the
 * shell level (mountDesktopShell replaces the host's children); the interiors
 * own their own idempotency (routeSession tears down a prior mount first).
 */
/**
 * The Settings surface is the drawer routeSession already mounted (a fixed
 * overlay). Since the shell suppresses the session's own titlebar gear, the
 * shell's Settings nav (click / Cmd+5 / palette) is the opener. Settings is
 * not a real stage surface, though: it is a drawer over the DJ's current task.
 * When navigation lands on Settings, open the drawer and immediately restore
 * the last non-settings surface so the main stage never shows the fake
 * "Settings" empty route behind the drawer.
 */
export function wireSettingsNav(shell: MountedShell): () => void {
  let prev = shell.store.getState().activeSurface;
  let lastNonSettings = prev === "settings" ? "deck" : prev;
  let restoringSettingsSurface = false;

  if (prev === "settings") {
    openSettings();
    shell.store.setSettingsOpen(true);
    restoringSettingsSurface = true;
    shell.store.setActiveSurface(lastNonSettings);
    restoringSettingsSurface = false;
    prev = lastNonSettings;
  }

  const unstore = shell.store.subscribe((model) => {
    if (restoringSettingsSurface) return;
    if (model.activeSurface !== "settings") {
      lastNonSettings = model.activeSurface;
    }
    if (model.activeSurface === prev) return;
    if (model.activeSurface === "settings") {
      restoringSettingsSurface = true;
      openSettings();
      shell.store.setSettingsOpen(true);
      shell.store.setActiveSurface(lastNonSettings);
      restoringSettingsSurface = false;
      prev = lastNonSettings;
      return;
    } else if (getSettingsUIState().open && !restoringSettingsSurface) {
      closeSettings();
    }
    prev = model.activeSurface;
  });

  const unsettings = subscribeSettingsUI((ui) => {
    shell.store.setSettingsOpen(ui.open);
    if (!ui.open && shell.store.getState().activeSurface === "settings") {
      shell.store.setActiveSurface(lastNonSettings);
    }
  });
  shell.store.setSettingsOpen(getSettingsUIState().open);

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
  const freshnessBadge = footer
    ? mountLibraryFreshnessBadge(footer, {
        onOpenViber: () => shell.store.setActiveSurface("viber"),
      })
    : null;
  const voiceBadge = footer
    ? mountVoiceReadinessBadge(footer, {
        onOpenViber: () => shell.store.setActiveSurface("viber"),
      })
    : null;
  // Feed the live session onto the shell's self-arranging activation +
  // connection (energy field, connection dot, the grounding panel auto-open).
  const unwireActivation = wireActivation(shell.store);
  vmxLog("[vmx:state]", "shell-app → mounted");

  return {
    shell,
    surfaces,
    teardown(): void {
      unwireActivation();
      voiceBadge?.teardown();
      freshnessBadge?.teardown();
      unwireSettings();
      surfaces.teardown();
      shell.teardown();
    },
  };
}
