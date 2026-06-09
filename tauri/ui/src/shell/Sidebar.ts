// SPDX-License-Identifier: Apache-2.0
//
// The fixed sidebar: brand mark with a listening "ear", the five surface nav
// items (one word each, with a Cmd accelerator), a collapse handle, and the
// co-host live pill at the foot. Pure render + store wiring; all styling is in
// shell.css. Collapse width is driven by the root data-collapsed attribute, so
// this component only keeps aria-current on the active item.

import type { ShellStore } from "./shell-store.js";
import { SURFACES } from "./surfaces.js";

export function createSidebar(store: ShellStore): HTMLElement {
  // A plain <div>, not <aside>: the sidebar's content is the primary <nav>
  // below (its own landmark), so an <aside> wrapper would add a second,
  // unlabeled "complementary" landmark competing with the grounding panel.
  const sidebar = document.createElement("div");
  sidebar.className = "shell-sidebar";
  sidebar.setAttribute("data-wire", "shell.sidebar");

  const collapse = document.createElement("button");
  collapse.type = "button";
  collapse.className = "sb-collapse";
  collapse.textContent = "‹";
  collapse.title = "Collapse sidebar (Ctrl+\\)";
  collapse.setAttribute("aria-label", "Collapse sidebar");
  collapse.addEventListener("click", () => store.toggleCollapsed());

  const brand = document.createElement("div");
  brand.className = "sb-brand";
  // The mock's brand-mark: a machined 30px tile holding the rose "v" monogram,
  // with the listening ear as a badge on its corner (a tiny ring whose inner
  // dot pulses with the amp). The two-tone wordmark sits beside it; at the
  // collapsed 72px rail the wordmark hides and the tile alone carries the
  // identity. The monogram is aria-hidden — the wordmark text stays the
  // accessible brand name.
  brand.innerHTML =
    '<span class="sb-mark" aria-hidden="true">' +
    '<span class="sb-monogram" aria-hidden="true">v</span>' +
    '<span class="sb-ear"></span>' +
    "</span>" +
    '<span class="sb-wordmark"><span class="wm-vibe">vibe</span><span class="wm-mix">mix</span></span>';

  // Mono section label above the nav — the mock's quiet engraved index tab.
  const navSection = document.createElement("div");
  navSection.className = "sb-section";
  navSection.textContent = "surfaces";

  const nav = document.createElement("nav");
  nav.className = "sb-nav";
  nav.setAttribute("aria-label", "Surfaces");

  const items = SURFACES.map((surface) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "sb-nav-item";
    item.dataset.surface = surface.id;
    item.title = `${surface.label}: ${surface.hint}`;
    // Explicit accessible name so it survives collapse (when the .sb-label span
    // is display:none, the button would otherwise be an unnamed glyph).
    item.setAttribute("aria-label", surface.label);
    item.innerHTML =
      `<span class="sb-glyph" aria-hidden="true">${surface.glyph}</span>` +
      `<span class="sb-label">${surface.label}</span>` +
      `<span class="sb-kbd">${surface.kbd}</span>`;
    item.addEventListener("click", () => store.setActiveSurface(surface.id));
    nav.append(item);
    return { id: surface.id, el: item };
  });

  // TONIGHT — the mock's session strip, kept honest: the one live item shows
  // only while a session is actually live (CSS gates on #shell-root
  // [data-state]); "all sessions" is a real route into the debrief surface.
  const tonightSection = document.createElement("div");
  tonightSection.className = "sb-section";
  tonightSection.textContent = "tonight";
  const sessions = document.createElement("div");
  sessions.className = "sb-sessions";
  sessions.innerHTML =
    '<div class="sb-session-item sb-session-live">' +
    '<span class="sb-session-title">live session</span>' +
    '<span class="sb-session-meta"><span class="sb-live-dot" aria-hidden="true"></span>on air</span>' +
    "</div>";
  const sessionsAll = document.createElement("button");
  sessionsAll.type = "button";
  sessionsAll.className = "sb-sessions-all";
  sessionsAll.textContent = "all sessions ›";
  sessionsAll.setAttribute("aria-label", "All sessions — open debrief");
  sessionsAll.addEventListener("click", () => store.setActiveSurface("debrief"));

  const foot = document.createElement("div");
  foot.className = "sb-foot";
  // The co-host presence slab (the mock's cohost-pill): names who's with you
  // AND states what it is doing, honestly from activation — ready / listening
  // / live. Warms to the rose slab only when actually live in your ear.
  foot.innerHTML =
    '<div class="sb-cohost" data-wire="shell.cohost-pill" aria-label="Co-host Sven">' +
    '<span class="sb-ear" aria-hidden="true"></span>' +
    '<span class="sb-cohost-name">sven</span>' +
    '<span class="sb-cohost-state">ready</span>' +
    "</div>";

  sidebar.append(
    collapse,
    brand,
    navSection,
    nav,
    tonightSection,
    sessions,
    sessionsAll,
    foot,
  );

  const cohostState = foot.querySelector<HTMLElement>(".sb-cohost-state");
  const render = (): void => {
    const state = store.getState();
    const active = state.settingsOpen ? "settings" : state.activeSurface;
    for (const item of items) {
      if (item.id === active) {
        item.el.setAttribute("aria-current", "true");
      } else {
        item.el.removeAttribute("aria-current");
      }
    }
    // Honest presence wording straight from activation — never claims "live"
    // while idle (cardinal invariant #5: idle is calm, not a fault).
    const presence =
      state.activation === "live"
        ? "live"
        : state.activation === "listening"
          ? "listening"
          : "ready";
    if (cohostState && cohostState.textContent !== presence) {
      cohostState.textContent = presence;
    }
  };
  store.subscribe(render);
  render();

  return sidebar;
}
