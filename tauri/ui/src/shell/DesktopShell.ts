// SPDX-License-Identifier: Apache-2.0
//
// The cohesive DesktopShell composition. This is the structural lever that
// makes vibemix's scattered surfaces read as ONE app instead of a scatter of
// separate windows: it folds the five interior surfaces (deck/crate/learn/
// debrief/settings) into one frame, while the pill/overlay/mascot stay separate
// transparent windows. Composition:
// fixed sidebar furniture, an offset recessed main with keep-alive surfaces, a
// contextual grounding panel, a Cmd+K palette, and a quiet status footer. The
// shell rearranges itself around the activation state (idle -> listening ->
// live) with no setup screen.
//
// Skeleton scope (this phase): the five surfaces mount as keep-alive
// placeholders carrying their data-wire anchors. The real surfaces
// (session/library/learn/debrief/settings) and the audio pipeline wire in
// during later phases. No backend is touched here.

import { ShellStore, type SurfaceId } from "./shell-store.js";
import { SURFACES, type SurfaceDef } from "./surfaces.js";
import { createSidebar } from "./Sidebar.js";
import { createGroundingPanel } from "./GroundingPanel.js";
import { createStatusFooter } from "./StatusFooter.js";
import { createCommandPalette, type PaletteAction } from "./CommandPalette.js";

export interface MountedShell {
  readonly store: ShellStore;
  teardown(): void;
}

function createSurfaceRegion(def: SurfaceDef): HTMLElement {
  const region = document.createElement("section");
  region.className = `surface surface--${def.id === "deck" ? "deck" : "stub"}`;
  region.dataset.surface = def.id;
  region.setAttribute("role", "region");
  region.setAttribute("aria-label", def.label);

  if (def.id === "deck") {
    region.innerHTML =
      // Subliminal energy field behind the stage. Its OPACITY ramps by
      // activation (idle still, listening faint, live present); it never
      // breathes, so the tail cursor stays the single rhythmic sign-of-life.
      // Kept under the "name it and it's too strong" threshold per DESIGN.md.
      `<div class="deck-energy" aria-hidden="true"></div>` +
      `<div class="deck-stage" data-wire="${def.wire}">` +
      `<p class="deck-idle">listening for the mix…</p>` +
      // The live line is where the co-host's reaction renders once wired. It
      // is an aria-live region so injected reactions are announced to AT. Until
      // wired it speaks in first person (the co-host, not a tagline); the tail
      // cursor is the single sign-of-life that it is speaking.
      `<p class="deck-live-line" aria-live="polite" aria-atomic="true">` +
      `I'm on the mix. The moment something moves, I'll call it.` +
      `<span class="tail-cursor" aria-hidden="true"></span></p>` +
      // Scene chips stay honest dashes until real BPM/key/vibe wire in — no
      // fabricated detected values (trust-the-audio, cardinal invariant #3). The
      // key slot takes gold (.scene-chip--gold) ONLY when a real Camelot value
      // renders (Gold-Is-Quarantined); at rest it is a neutral dash.
      // aria-hidden while it is only dashes; the wiring phase MUST drop this (or
      // move it to the individual placeholders) once real values render, so SR
      // users hear the BPM/key/vibe.
      `<div class="deck-scene" aria-hidden="true">` +
      `<span class="scene-bpm">— BPM</span>` +
      `<span class="scene-chip">—</span>` +
      `<span class="scene-chip">—</span>` +
      `</div></div>`;
  } else {
    const empty = def.empty;
    const proofRows = empty?.proof?.map((row) =>
      `<div class="se-proof-row"><dt>${row.label}</dt><dd>${row.value}</dd></div>`,
    ).join("") ?? "";
    const proof = proofRows ? `<dl class="se-proof">${proofRows}</dl>` : "";
    region.innerHTML =
      `<div class="surface-empty">` +
      `<span class="se-glyph" aria-hidden="true">${def.glyph}</span>` +
      // <h2> (not <p>): gives the surface a real heading so screen-reader users
      // get a document outline to navigate by, not just landmark regions.
      `<h2 class="se-title">${empty?.title ?? def.label}</h2>` +
      `<p class="se-sub">${empty?.sub ?? def.hint}</p>` +
      proof +
      `</div>` +
      `<div class="surface-mount" data-wire="${def.wire}" hidden></div>`;
  }
  return region;
}

function buildPaletteActions(store: ShellStore): PaletteAction[] {
  const goTo: PaletteAction[] = SURFACES.map((surface) => ({
    id: `go.${surface.id}`,
    label: `Go to ${surface.label}`,
    hint: surface.hint,
    // The same bare digit the sidebar nav shows — the palette teaches the
    // surface accelerators it dropped before, in one consistent token.
    accel: surface.kbd,
    glyph: surface.glyph,
    run: () => store.setActiveSurface(surface.id),
  }));

  const commands: PaletteAction[] = [
    { id: "toggle.sidebar", label: "Toggle sidebar", accel: "Ctrl+\\", glyph: "‹", run: () => store.toggleCollapsed() },
    { id: "toggle.panel", label: "Toggle grounding panel", accel: "Ctrl+]", glyph: "▸", run: () => store.togglePanel() },
  ];

  return [...goTo, ...commands];
}

export function mountDesktopShell(host: HTMLElement, store: ShellStore = new ShellStore()): MountedShell {
  host.id = "shell-root";
  host.replaceChildren();

  const chrome = document.createElement("header");
  chrome.className = "shell-chrome";
  chrome.setAttribute("data-tauri-drag-region", "");
  chrome.setAttribute("data-wire", "shell.chrome");
  chrome.innerHTML =
    '<div class="traffic-spacer" aria-hidden="true" data-tauri-drag-region></div>' +
    '<div class="shell-clock" id="shell-clock" aria-hidden="true" data-tauri-drag-region>00:00</div>';

  const body = document.createElement("div");
  body.className = "shell-body";

  const sidebar = createSidebar(store);

  const main = document.createElement("main");
  main.className = "shell-main";
  main.setAttribute("data-wire", "shell.main");
  const surfacesHost = document.createElement("div");
  surfacesHost.className = "shell-surfaces";
  const regions = new Map<SurfaceId, HTMLElement>();
  for (const def of SURFACES) {
    const region = createSurfaceRegion(def);
    regions.set(def.id, region);
    surfacesHost.append(region);
  }
  main.append(surfacesHost);

  const panel = createGroundingPanel(store);
  body.append(sidebar, main, panel);

  const footer = createStatusFooter(store);
  // While the palette is open, inert the rest of the shell so neither Tab nor a
  // screen-reader browse cursor reaches the background (honors aria-modal=true).
  const palette = createCommandPalette(() => buildPaletteActions(store), {
    inertWhileOpen: [chrome, body, footer],
  });

  host.append(chrome, body, footer, palette.el);

  // Mono clock in the drag chrome.
  const clock = chrome.querySelector<HTMLElement>("#shell-clock");
  const tickClock = (): void => {
    if (!clock) return;
    const now = new Date();
    clock.textContent = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  };
  tickClock();
  const clockTimer = globalThis.setInterval(tickClock, 1000);

  // Reflect store state onto the root as data-attributes (optimistic repaint),
  // and toggle keep-alive surface visibility.
  const applyState = (): void => {
    const model = store.getState();
    host.dataset.collapsed = String(model.collapsed);
    host.dataset.panel = model.panelOpen ? "open" : "closed";
    host.dataset.settings = model.settingsOpen ? "open" : "closed";
    host.dataset.state = model.activation;
    host.dataset.conn = model.connection;
    host.dataset.surface = model.activeSurface;
    for (const [id, region] of regions) {
      region.classList.toggle("is-active", id === model.activeSurface);
    }
  };
  const unsubscribe = store.subscribe(applyState);
  applyState();

  // Structural keyboard chords. Every surface has a chord; z-index and bindings
  // are governed, not ad-hoc (mirrors Bravoh's keyboard-first ethos).
  const onKeydown = (event: KeyboardEvent): void => {
    const mod = event.metaKey || event.ctrlKey;
    if (mod && !event.shiftKey && (event.key === "k" || event.key === "K")) {
      event.preventDefault();
      palette.toggle();
      return;
    }
    if (event.ctrlKey && event.key === "\\") {
      event.preventDefault();
      store.toggleCollapsed();
      return;
    }
    if (event.ctrlKey && event.key === "]") {
      event.preventDefault();
      store.togglePanel();
      return;
    }
    // Esc closes the grounding panel (desktop dismissal reflex). Gated on the
    // palette being closed — while open the palette owns Esc and stops it
    // propagating here, so one Esc never closes both.
    if (event.key === "Escape" && !palette.isOpen() && store.getState().panelOpen) {
      event.preventDefault();
      store.setPanelOpen(false);
      return;
    }
    if (mod) {
      const surface = SURFACES.find((entry) => entry.kbd === event.key);
      if (surface) {
        event.preventDefault();
        store.setActiveSurface(surface.id);
      }
    }
  };
  window.addEventListener("keydown", onKeydown);

  const teardown = (): void => {
    window.removeEventListener("keydown", onKeydown);
    globalThis.clearInterval(clockTimer);
    unsubscribe();
    host.replaceChildren();
  };

  return { store, teardown };
}
