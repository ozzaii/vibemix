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

  const render = (): void => {
    const { activation } = store.getState();
    if (activation === "live") {
      // Live, the panel is a RECEIPT, not a promise: two labeled slots the
      // co-host fills as it reacts. Honest placeholders until real citations +
      // the next-track suggestion wire in (trust-the-audio, invariant #3) — so
      // going live materializes a receipt rather than swapping one line.
      body.innerHTML =
        '<div class="panel-section">' +
        '<div class="panel-label">Cited</div>' +
        '<p class="panel-placeholder">Listening for the next move.</p>' +
        "</div>" +
        '<div class="panel-section">' +
        '<div class="panel-label">What\'s next</div>' +
        '<p class="panel-placeholder">—</p>' +
        "</div>";
    } else {
      body.textContent = "Nothing to ground yet. I cite what the deck does, the moment it does it.";
    }
  };
  store.subscribe(render);
  render();

  return aside;
}
