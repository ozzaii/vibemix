// SPDX-License-Identifier: Apache-2.0
//
// The contextual right panel. It opens on Ctrl+] or whenever activation goes
// "live" (the store auto-opens it). Until a real citation/suggestion feed is
// wired here, the live state must remain empty-state copy, not a fake receipt.

import type { ShellStore } from "./shell-store.js";

export function createGroundingPanel(store: ShellStore): HTMLElement {
  const aside = document.createElement("aside");
  aside.className = "shell-panel";
  aside.setAttribute("data-wire", "shell.panel");
  aside.setAttribute("aria-label", "Grounding");

  const head = document.createElement("div");
  head.className = "panel-head";
  head.textContent = "Grounding";

  const body = document.createElement("div");
  body.className = "panel-body";
  body.setAttribute("data-wire", "shell.panel.body");

  aside.append(head, body);

  // Tracks the prior activation so the receipt "prints in" ONLY on the
  // idle/listening -> live transition, not on every re-render (the store fires
  // render() on any state change — surface switch, collapse — and a receipt
  // that re-animated on each of those would flicker).
  let prevActivation: string | null = null;

  const render = (): void => {
    const { activation } = store.getState();
    const justWentLive = activation === "live" && prevActivation !== "live";
    if (activation === "live") {
      // Activation is real, but this panel has no citation feed yet. Keep the
      // labels honest: no "Cited" claim and no armed/live dot until real data
      // writes the slot.
      body.innerHTML =
        '<div class="panel-section">' +
        '<div class="panel-label">Evidence</div>' +
        '<p class="panel-placeholder">No cited move yet.</p>' +
        "</div>" +
        '<div class="panel-section">' +
        '<div class="panel-label">What\'s next</div>' +
        '<p class="panel-placeholder">No suggestion yet.</p>' +
        "</div>";
      // One-shot entry: the slots print in as the drawer arrives. Only on the
      // transition — a re-render while already live rebuilds them without it.
      if (justWentLive) {
        Array.from(body.querySelectorAll(".panel-section")).forEach((section) => {
          section.classList.add("panel-section--enter");
        });
      }
    } else {
      body.textContent = "Nothing to ground yet. I cite what the deck does, the moment it does it.";
    }
    prevActivation = activation;
  };
  store.subscribe(render);
  render();

  return aside;
}
