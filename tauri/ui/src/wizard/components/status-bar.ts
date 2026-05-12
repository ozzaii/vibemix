/* status-bar.ts — bottom 40px strip with 4 LED dots (UI-SPEC §12).
 *
 * Left-to-right: livekit · gemini · midi · screen.
 * Right: "made by bravoh" DM Mono 11px --ink-deep.
 *
 * LED states:
 *   - "ok"          → --ok
 *   - "connecting"  → --phosphor pulsing
 *   - "down"        → --rec
 *   - null          → --ink-engraved (not yet probed)
 *
 * UI-SPEC §12 scope: Phase 11 ships the schema + minimal visual; Phase 12
 * wires real state. The bar always renders — it's the cohort of the
 * "wizard hardware front panel" feeling. */

import { registerStyle } from "./_style-registry.js";

export type StatusLevel = "ok" | "connecting" | "down" | null;

export interface StatusBarProps {
  livekit: StatusLevel;
  gemini: "ok" | "down" | null;
  midi: number | null;
  screen: "ok" | "denied" | null;
}

const CSS = `
  .cmp-status-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    height: 100%;
  }
  .cmp-status-bar__group {
    display: flex;
    align-items: center;
    gap: var(--sp-md);
  }
  .cmp-status-bar__item {
    display: inline-flex;
    align-items: center;
    gap: var(--sp-xs);
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-dim);
  }
  .cmp-status-bar__led {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--ink-engraved);
    box-shadow: inset 0 0 1px rgba(0, 0, 0, 0.5);
  }
  .cmp-status-bar__item[data-state="ok"] .cmp-status-bar__led {
    background: var(--ok);
    box-shadow: 0 0 6px var(--ok);
  }
  .cmp-status-bar__item[data-state="ok"] {
    color: var(--ink);
  }
  .cmp-status-bar__item[data-state="connecting"] .cmp-status-bar__led {
    background: var(--phosphor);
    box-shadow: var(--phosphor-glow);
    animation: cmp-status-pulse var(--motion-led-pulse) ease-in-out infinite;
  }
  .cmp-status-bar__item[data-state="connecting"] {
    color: var(--phosphor);
  }
  .cmp-status-bar__item[data-state="down"] .cmp-status-bar__led,
  .cmp-status-bar__item[data-state="denied"] .cmp-status-bar__led {
    background: var(--rec);
    box-shadow: 0 0 6px var(--rec);
  }
  .cmp-status-bar__item[data-state="down"],
  .cmp-status-bar__item[data-state="denied"] {
    color: var(--rec);
  }
  .cmp-status-bar__signature {
    font-family: "DM Mono", monospace;
    font-size: 11px;
    color: var(--ink-deep);
    letter-spacing: 0.06em;
  }
  @keyframes cmp-status-pulse {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0.5; }
  }
`;

registerStyle("cmp-status-bar", CSS);

function levelToState(level: StatusLevel | "denied" | "ok" | "down" | null): string {
  return level ?? "off";
}

export function StatusBar(props: StatusBarProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "cmp-status-bar";

  const group = document.createElement("div");
  group.className = "cmp-status-bar__group";

  const items: Array<{ label: string; state: string; key: string }> = [
    { label: "livekit", state: levelToState(props.livekit), key: "livekit" },
    {
      label: "gemini",
      state: levelToState(props.gemini),
      key: "gemini",
    },
    {
      label: props.midi == null ? "midi" : `midi ${props.midi}`,
      state: props.midi == null ? "off" : props.midi > 0 ? "ok" : "down",
      key: "midi",
    },
    {
      label: "screen",
      state: levelToState(props.screen),
      key: "screen",
    },
  ];

  for (const item of items) {
    const el = document.createElement("span");
    el.className = "cmp-status-bar__item";
    el.dataset.state = item.state;
    el.dataset.key = item.key;
    const led = document.createElement("span");
    led.className = "cmp-status-bar__led";
    led.setAttribute("aria-hidden", "true");
    const lbl = document.createElement("span");
    lbl.textContent = item.label;
    el.append(led, lbl);
    group.append(el);
  }

  const sig = document.createElement("span");
  sig.className = "cmp-status-bar__signature";
  sig.textContent = "made by bravoh";

  root.append(group, sig);
  return root;
}

export function setStatusBarState(el: HTMLElement, props: StatusBarProps): void {
  const re = el.querySelector(".cmp-status-bar");
  if (!re) return;
  // Trivial approach: re-render
  const fresh = StatusBar(props);
  el.replaceChildren(...Array.from(fresh.childNodes));
}
