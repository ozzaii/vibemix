/* status-bar.ts — bottom 40px strip with 4 LED dots (UI-SPEC §12 / CDJ Whisper v5).
 *
 * Left-to-right: livekit · gemini · midi · screen.
 *
 * LED states:
 *   - "ok"          → --led-ok green dome
 *   - "connecting"  → --amber + composite --glow-soft, breathing pulse
 *   - "down"        → --led-fault red dome
 *   - null          → --silk-22 unlit (not yet probed)
 *
 * Phase 12 wires real state via ipc.status.tick. The bar always renders
 * — it's part of the v5 "front-panel LED row" feeling. */

import { registerStyle } from "./_style-registry.js";

export type StatusLevel = "ok" | "connecting" | "down" | null;

export interface StatusBarProps {
  livekit: StatusLevel;
  gemini: "ok" | "down" | null;
  midi: number | null;
  screen: "ok" | "denied" | "unavailable" | null;
}

const CSS = `
  .cmp-status-bar {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    width: 100%;
    height: 100%;
  }
  .cmp-status-bar__group {
    display: flex;
    align-items: center;
    gap: var(--sp-4);
  }
  .cmp-status-bar__item {
    display: inline-flex;
    align-items: center;
    gap: var(--sp-1);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 9px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk-40);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .cmp-status-bar__led {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--silk-22);
    box-shadow: inset 0 0 1px rgba(0, 0, 0, 0.5);
  }
  /* ok = lit ink + rose dot (the contract's alive-state); green is not in the
   * room's vocabulary. Fault red survives below as the one functional hue. */
  .cmp-status-bar__item[data-state="ok"] .cmp-status-bar__led {
    background: var(--brand);
    box-shadow: 0 0 6px var(--brand-40);
  }
  .cmp-status-bar__item[data-state="ok"] {
    color: var(--silk);
  }
  .cmp-status-bar__item[data-state="connecting"] .cmp-status-bar__led {
    background: var(--amber);
    box-shadow: var(--glow-soft);
    animation: cmp-status-pulse var(--motion-led-pulse) ease-in-out infinite;
  }
  .cmp-status-bar__item[data-state="connecting"] {
    color: var(--amber);
    text-shadow: 0 0 4px var(--amber-22);
  }
  .cmp-status-bar__item[data-state="down"] .cmp-status-bar__led,
  .cmp-status-bar__item[data-state="denied"] .cmp-status-bar__led {
    background: var(--led-fault);
    box-shadow: 0 0 6px var(--led-fault);
  }
  .cmp-status-bar__item[data-state="down"],
  .cmp-status-bar__item[data-state="denied"] {
    color: var(--led-fault);
  }
  @keyframes cmp-status-pulse {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0.5; }
  }
`;

registerStyle("cmp-status-bar", CSS);

function levelToState(
  level: StatusLevel | "denied" | "unavailable" | "ok" | "down" | null,
): string {
  if (level === "unavailable") return "off";
  return level ?? "off";
}

export function StatusBar(props: StatusBarProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "cmp-status-bar";

  const group = document.createElement("div");
  group.className = "cmp-status-bar__group";

  // Capability words, not vendor names — a DJ doesn't care what the brain
  // runs on, and stack names date the binary. Keys/states stay unchanged.
  const items: Array<{ label: string; state: string; key: string; title?: string }> = [
    { label: "voice link", state: levelToState(props.livekit), key: "livekit" },
    {
      label: "brain",
      state: levelToState(props.gemini),
      key: "gemini",
    },
    {
      label: props.midi == null ? "controller" : `controller ${props.midi}`,
      state: props.midi == null ? "off" : props.midi > 0 ? "ok" : "down",
      key: "midi",
    },
    {
      label: "screen",
      state: levelToState(props.screen),
      key: "screen",
      // Compact key on the badge; the hover names the feature noun so the
      // wizard and session speak the same word ("screen proof").
      title: "Screen proof",
    },
  ];

  for (const item of items) {
    const el = document.createElement("span");
    el.className = "cmp-status-bar__item";
    el.dataset.state = item.state;
    el.dataset.key = item.key;
    if (item.title) el.title = item.title;
    const led = document.createElement("span");
    led.className = "cmp-status-bar__led";
    led.setAttribute("aria-hidden", "true");
    const lbl = document.createElement("span");
    lbl.textContent = item.label;
    el.append(led, lbl);
    group.append(el);
  }

  root.append(group);
  return root;
}

export function setStatusBarState(el: HTMLElement, props: StatusBarProps): void {
  const re = el.querySelector(".cmp-status-bar");
  if (!re) return;
  // Trivial approach: re-render
  const fresh = StatusBar(props);
  el.replaceChildren(...Array.from(fresh.childNodes));
}
