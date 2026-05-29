// SPDX-License-Identifier: Apache-2.0
//
// The contextual right panel: where citations, the "what's next" suggestion,
// and grounding receipts live during a live set. It opens on Ctrl+] or whenever
// activation goes "live" (the store auto-opens it). Open/closed is driven by
// the root data-panel attribute (see shell.css + DesktopShell); this component
// only swaps its body copy by activation so the panel is honest at idle.

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
      // Live, the panel is a RECEIPT, not a promise: two labeled slots the
      // co-host fills as it reacts. Honest placeholders until real citations +
      // the next-track suggestion wire in (trust-the-audio, invariant #3) — so
      // going live materializes a receipt rather than swapping one line.
      body.innerHTML =
        '<div class="panel-section">' +
        // The armed dot: a static lit mark (NOT a breath — the deck tail cursor
        // owns the one live breath) that says grounding is live and listening,
        // so the receipt reads alive before the first citation lands.
        '<div class="panel-label"><span class="panel-armed" aria-hidden="true"></span>Cited</div>' +
        '<p class="panel-placeholder">Listening for the next move.</p>' +
        "</div>" +
        '<div class="panel-section">' +
        '<div class="panel-label">What\'s next</div>' +
        // Honest co-host voice, never a dead dash: nothing is cued until the
        // suggestion engine calls it (trust-the-audio, invariant #3).
        '<p class="panel-placeholder">Nothing cued yet.</p>' +
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
