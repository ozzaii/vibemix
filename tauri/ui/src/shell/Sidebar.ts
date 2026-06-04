// SPDX-License-Identifier: Apache-2.0
//
// The fixed sidebar: brand mark with a listening "ear", the five surface nav
// items (one word each, with a Cmd accelerator), a collapse handle, and the
// co-host live pill at the foot. Pure render + store wiring; all styling is in
// shell.css. Collapse width is driven by the root data-collapsed attribute, so
// this component only flips aria-current on the active item.

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
  // Two-tone lockup: "vibe" in ink, "mix" lit in brand rose. The split is
  // cosmetic only — the syllables sit flush so the mark still reads as one
  // lowercase word ("vibemix"), but the second syllable can carry the identity
  // color the way the ear and the active nav glyph do.
  brand.innerHTML =
    '<span class="sb-ear" aria-hidden="true"></span>' +
    '<span class="sb-wordmark"><span class="wm-vibe">vibe</span><span class="wm-mix">mix</span></span>' +
    // Collapsed-rail mark: the wordmark hides at 72px, so a rose "v" monogram
    // keeps the identity (and becomes the lone breathing sign-of-life). It is
    // aria-hidden — the wordmark text stays the accessible brand name.
    '<span class="sb-monogram" aria-hidden="true">v</span>';

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

  const foot = document.createElement("div");
  foot.className = "sb-foot";
  // A static lit rose dot: the sidebar's sign-of-life that the co-host is awake.
  // No caps label — the dot carries the state; the word read as a false control.
  foot.innerHTML =
    '<div class="sb-cohost" data-wire="shell.cohost-pill" aria-label="Co-host">' +
    '<span class="sb-ear" aria-hidden="true"></span>' +
    "</div>";

  sidebar.append(collapse, brand, nav, foot);

  const render = (): void => {
    const state = store.getState();
    const active = state.settingsOpen ? "settings" : state.activeSurface;
    for (const item of items) {
      item.el.setAttribute("aria-current", item.id === active ? "true" : "false");
    }
  };
  store.subscribe(render);
  render();

  return sidebar;
}
