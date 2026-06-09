// SPDX-License-Identifier: Apache-2.0
//
// The cohesive DesktopShell composition. This is the structural lever that
// makes vibemix's scattered surfaces read as ONE app instead of a scatter of
// separate windows: it folds the five interior surfaces (deck/viber/learn/
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
import { OrganismStage } from "./organism-stage.js";
import { createSidebar } from "./Sidebar.js";
import { createGroundingPanel } from "./GroundingPanel.js";
import { createStatusFooter } from "./StatusFooter.js";
import {
  createCommandPalette,
  type PaletteAction,
  type PaletteSummaryCell,
} from "./CommandPalette.js";

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
      // Subliminal energy field behind the stage — the warm rose bed the organism
      // glows over. Its OPACITY ramps by activation (idle still, listening faint,
      // live present); it never breathes, so the tail cursor stays the single
      // rhythmic sign-of-life. Kept under the "name it and it's too strong"
      // threshold per DESIGN.md.
      `<div class="deck-energy" aria-hidden="true"></div>` +
      // The living organism — vibemix's one face, mounted as the deck backdrop
      // (OrganismStage in mountDesktopShell). Real curl drift + rose→gold bloom;
      // presence (sleeping/awake/live) is grounded in real [data-conn]/[data-state]
      // via CSS. When a GL context backs it, [data-organism="live"] hides the
      // static fallback glyph below; without WebGL this canvas stays empty and the
      // energy field + glyph carry the deck. Sits above the energy floor (later in
      // DOM, same z-base) and below the stage text (z-stage).
      `<canvas class="deck-organism" aria-hidden="true"></canvas>` +
      `<div class="deck-stage" data-wire="${def.wire}">` +
      // The flagship surface earns the same composition tier as every other
      // surface's empty state: an engraved glyph + the serif state line + one
      // grounded co-host sub. Without them the home read as the barest screen in
      // the app. The glyph is the deck's own engraved mark (def.glyph).
      `<span class="deck-glyph" aria-hidden="true">${def.glyph}</span>` +
      // The idle hero is CONNECTION-AWARE so it never contradicts the footer.
      // When the audio engine is offline the co-host cannot be "listening" — it
      // says so honestly (and the sub says what to do) instead of claiming to
      // listen while the footer reads "co-host offline". When connected it
      // listens. Toggled by #shell-root[data-conn] in CSS (optimistic repaint).
      `<p class="deck-idle">` +
      `<span class="deck-idle__on">listening for the mix…</span>` +
      `<span class="deck-idle__off">waiting for your audio</span>` +
      `</p>` +
      `<p class="deck-idle-sub">` +
      `<span class="deck-idle__on">Drop a track and play. I'm listening for the first move.</span>` +
      `<span class="deck-idle__off">Route your master output into me, then play. I wake the moment audio flows.</span>` +
      `</p>` +
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

const SURFACE_ALIASES: Readonly<Record<SurfaceId, readonly string[]>> = {
  deck: ["live", "sven", "cohost", "voice", "chatterbox", "moss", "play"],
  viber: ["library", "viber", "set prep", "search", "tracks", "transitions"],
  learn: ["lesson", "practice", "controller", "hands"],
  debrief: ["review", "timeline", "receipts", "proof", "set review"],
  settings: ["setup", "audio", "output", "hotkey", "persona", "recordings"],
};

function sentenceCase(value: string): string {
  if (!value) return value;
  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
}

function buildPaletteActions(store: ShellStore): PaletteAction[] {
  const model = store.getState();
  const goTo: PaletteAction[] = SURFACES.map((surface) => ({
    id: `go.${surface.id}`,
    label: `Go to ${surface.label}`,
    section: "navigate",
    hint: surface.hint,
    // The same bare digit the sidebar nav shows — the palette teaches the
    // surface accelerators it dropped before, in one consistent token.
    accel: surface.kbd,
    glyph: surface.glyph,
    aliases: SURFACE_ALIASES[surface.id],
    status: model.activeSurface === surface.id ? "current" : "surface",
    statusKind: model.activeSurface === surface.id ? "current" : "quiet",
    run: () => store.setActiveSurface(surface.id),
  }));

  const commands: PaletteAction[] = [
    {
      id: "toggle.sidebar",
      label: "Toggle sidebar",
      section: "control",
      hint: "compact navigation rail",
      accel: "Ctrl+\\",
      glyph: "‹",
      aliases: ["collapse", "expand", "chrome", "nav"],
      status: model.collapsed ? "compact" : "full",
      statusKind: "ready",
      run: () => store.toggleCollapsed(),
    },
    {
      id: "toggle.panel",
      label: "Toggle deck notes",
      section: "control",
      hint: "right-side deck notes",
      accel: "Ctrl+]",
      glyph: "▸",
      aliases: ["deck notes", "deck", "next", "panel"],
      status: model.panelOpen ? "open" : "closed",
      statusKind: model.panelOpen ? "current" : "ready",
      run: () => store.togglePanel(),
    },
  ];

  return [...goTo, ...commands];
}

function buildPaletteSummary(store: ShellStore): readonly PaletteSummaryCell[] {
  const model = store.getState();
  const surface = SURFACES.find((entry) => entry.id === model.activeSurface);
  return [
    { label: "Surface", value: surface?.label ?? sentenceCase(model.activeSurface), tone: "ok" },
    {
      label: "State",
      value: sentenceCase(model.activation),
      tone: model.activation === "live" ? "ok" : "muted",
    },
  ];
}

export function mountDesktopShell(host: HTMLElement, store: ShellStore = new ShellStore()): MountedShell {
  host.id = "shell-root";
  host.replaceChildren();

  // The command palette is the documented "permanent cheat-sheet" for every
  // accelerator, but it was advertised nowhere on screen — pure recall. The 28px
  // chrome bar was ~95% dead space (just a clock). One quiet, platform-aware
  // affordance there turns the whole power layer discoverable for the price of
  // the space that was already empty.
  const isMac =
    /Mac|iPhone|iPad|iPod/.test(navigator.platform ?? "") ||
    /Mac OS X/.test(navigator.userAgent);
  const cmdkLabel = isMac ? "⌘K" : "Ctrl K";

  const chrome = document.createElement("header");
  chrome.className = "shell-chrome";
  chrome.setAttribute("data-tauri-drag-region", "");
  chrome.setAttribute("data-wire", "shell.chrome");
  chrome.innerHTML =
    '<div class="traffic-spacer" aria-hidden="true" data-tauri-drag-region></div>' +
    // The mock's centered chrome inscription: the app name lit as the em, the
    // active surface as the honest session descriptor beside it. Decorative
    // (aria-hidden) — the sidebar wordmark stays the accessible brand name.
    '<div class="shell-chrome__title" aria-hidden="true" data-tauri-drag-region>' +
    '<em>vibemix</em><span class="shell-chrome__title-sep"> · </span>' +
    '<span class="shell-chrome__title-surface">deck</span>' +
    "</div>" +
    '<div class="shell-chrome__right" data-tauri-drag-region>' +
    '<button type="button" class="shell-cmdk" data-wire="shell.cmdk" ' +
    'aria-label="Open command palette" title="Command palette">' +
    `<span class="shell-cmdk__hint">search</span>` +
    `<kbd class="shell-cmdk__keys">${cmdkLabel}</kbd>` +
    '</button>' +
    '<div class="shell-clock" id="shell-clock" aria-hidden="true" data-tauri-drag-region>00:00</div>' +
    '</div>';

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
    summaryProvider: () => buildPaletteSummary(store),
  });

  host.append(chrome, body, footer, palette.el);

  // The chrome ⌘K affordance opens the same palette as the keyboard chord, so the
  // power layer has a visible front door, not just a hidden one.
  const cmdkButton = chrome.querySelector<HTMLButtonElement>(".shell-cmdk");
  cmdkButton?.addEventListener("click", () => palette.toggle());

  // ── The living organism deck backdrop ──────────────────────────────────
  // Mount the real ParticleOrganism engine as the deck's face. When a GL context
  // backs it, flag the root so CSS hides the static fallback glyph (the organism
  // IS the face now); without WebGL the stage is a silent no-op and the glyph +
  // energy field carry the deck. The render loop pauses whenever the deck is not
  // the visible surface (perf) — driven from applyState + visibilitychange.
  // The procedural mask form read as a literal emoji (Kaan: 0.1/10, nuked
  // 2026-06-08). The agreed replacement is "abstract living matter" — a real
  // GPGPU divergence-free curl-noise fluid with NO face — which is its own
  // focused rebuild. Until that lands the deck organism stays PARKED: the stage
  // infra is kept, but it is not mounted, so the deck falls back cleanly to the
  // engraved glyph + energy field (no half-baked face ships). Flip to true once
  // the abstract-matter engine replaces the form.
  const ORGANISM_DECK_ENABLED = false;
  const deckRegion = regions.get("deck");
  const organismCanvas = ORGANISM_DECK_ENABLED
    ? deckRegion?.querySelector<HTMLCanvasElement>(".deck-organism") ?? null
    : null;
  const organism = organismCanvas ? new OrganismStage(organismCanvas) : null;
  if (organism?.isLive()) host.dataset.organism = "live";
  // Dev-only handle for live visual verification (advance frames deterministically
  // even when the automation tab is backgrounded and rAF is throttled). Vite
  // strips this branch from production builds.
  if (organism && import.meta.env?.DEV) {
    (globalThis as { __vibemixOrganism?: OrganismStage }).__vibemixOrganism = organism;
  }

  const resizeObserver =
    typeof ResizeObserver !== "undefined" && deckRegion
      ? new ResizeObserver(() => organism?.resize())
      : null;
  if (resizeObserver && deckRegion) resizeObserver.observe(deckRegion);

  const syncOrganismActivity = (): void => {
    organism?.setActive(
      store.getState().activeSurface === "deck" &&
        document.visibilityState !== "hidden",
    );
  };
  document.addEventListener("visibilitychange", syncOrganismActivity);

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
  const chromeTitleSurface = chrome.querySelector<HTMLElement>(
    ".shell-chrome__title-surface",
  );
  const applyState = (): void => {
    const model = store.getState();
    const surfaceLabel =
      SURFACES.find((entry) => entry.id === model.activeSurface)?.label.toLowerCase() ??
      model.activeSurface;
    if (chromeTitleSurface && chromeTitleSurface.textContent !== surfaceLabel) {
      chromeTitleSurface.textContent = surfaceLabel;
    }
    host.dataset.collapsed = String(model.collapsed);
    host.dataset.panel = model.panelOpen ? "open" : "closed";
    host.dataset.settings = model.settingsOpen ? "open" : "closed";
    host.dataset.state = model.activation;
    host.dataset.conn = model.connection;
    host.dataset.surface = model.activeSurface;
    for (const [id, region] of regions) {
      region.classList.toggle("is-active", id === model.activeSurface);
    }
    // Pause the organism's GPU loop unless the deck is the visible surface.
    syncOrganismActivity();
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
    document.removeEventListener("visibilitychange", syncOrganismActivity);
    resizeObserver?.disconnect();
    organism?.dispose();
    globalThis.clearInterval(clockTimer);
    unsubscribe();
    host.replaceChildren();
  };

  return { store, teardown };
}
