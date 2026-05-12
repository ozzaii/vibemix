/* status-bar.ts — bottom 40px live status bar (UI-SPEC §12).
 *
 * 4 LED badges (LIVEKIT / GEMINI / MIDI · N / SCREEN) on the left + muted
 * indicator + "made by bravoh" Caveat signature on the right.
 *
 * Click on a badge in `down` state opens a --rec-tinted tooltip with the
 * last error message + `[ ↻ Recheck ]` button. Recheck fires the
 * onRecheck callback supplied by SessionLayout — which in Wave 3 maps to
 * ipc.status.recheck. Pure-function — the callback is the only outgoing
 * channel; the component never knows about IPC. */

import { registerStyle } from "./_style-registry.js";

export type BadgeState = "ok" | "connecting" | "down" | null;

export interface StatusBarProps {
  livekit: BadgeState;
  gemini: "ok" | "down" | null;
  midi: number | null;
  screen: "ok" | "denied" | null;
  muted: boolean;
  hotkey: string;
  /** Called when the user clicks Recheck inside a down-badge tooltip. */
  onRecheck?: (component: "livekit" | "gemini" | "midi" | "screen") => void;
  /** Optional error messages by component for the tooltip body. */
  errors?: Partial<Record<"livekit" | "gemini" | "midi" | "screen", string>>;
}

type BadgeKey = "livekit" | "gemini" | "midi" | "screen";

const CSS = `
  .vmx-statusbar {
    display: flex;
    align-items: center;
    gap: 18px;
    height: var(--statusbar-h);
    padding: 0 var(--sp-lg);
    background: linear-gradient(180deg, var(--panel-lift) 0%, var(--panel-pressed-bottom) 100%);
    border-top: 1px solid var(--bezel-1);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9.5px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-dim);
    position: relative;
  }
  .vmx-statusbar__badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    border: none;
    background: transparent;
    color: var(--ink-dim);
    font-family: inherit;
    font-size: inherit;
    letter-spacing: inherit;
    text-transform: inherit;
    line-height: 1;
    cursor: default;
    padding: 4px 6px;
    border-radius: 3px;
    position: relative;
  }
  .vmx-statusbar__badge[data-clickable="true"] {
    cursor: pointer;
  }
  .vmx-statusbar__led {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--ink-engraved);
    box-shadow: inset 0 0 1px rgba(0, 0, 0, 0.5);
  }
  .vmx-statusbar__badge[data-state="ok"] .vmx-statusbar__led {
    background: var(--ok);
    box-shadow: 0 0 6px var(--ok);
  }
  .vmx-statusbar__badge[data-state="ok"] { color: var(--ink); }
  .vmx-statusbar__badge[data-state="connecting"] .vmx-statusbar__led {
    background: var(--phosphor);
    box-shadow: var(--phosphor-glow);
    animation: vmx-statusbar-pulse var(--motion-led-pulse) ease-in-out infinite;
  }
  .vmx-statusbar__badge[data-state="connecting"] { color: var(--phosphor); }
  .vmx-statusbar__badge[data-state="down"] .vmx-statusbar__led,
  .vmx-statusbar__badge[data-state="denied"] .vmx-statusbar__led {
    background: var(--rec);
    box-shadow: 0 0 6px var(--rec);
  }
  .vmx-statusbar__badge[data-state="down"],
  .vmx-statusbar__badge[data-state="denied"] { color: var(--rec); }
  .vmx-statusbar__muted {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 7px;
    color: var(--rec);
  }
  .vmx-statusbar__muted .vmx-statusbar__led {
    background: var(--rec);
    box-shadow: 0 0 6px var(--rec);
  }
  .vmx-statusbar__muted[hidden] { display: none; }
  .vmx-statusbar__sig {
    font-family: "Caveat", "DM Mono", monospace;
    font-size: 14px;
    color: var(--phosphor);
    letter-spacing: 0;
    text-transform: none;
    text-shadow: 0 0 8px var(--phosphor-soft);
    line-height: 1;
  }
  .vmx-statusbar__sig:not(.has-muted) { margin-left: auto; }
  /* === Tooltip === */
  .vmx-statusbar__tooltip {
    position: absolute;
    bottom: calc(100% + 8px);
    left: 0;
    z-index: 60;
    min-width: 220px;
    background: linear-gradient(180deg, var(--panel-lift), var(--panel));
    border: 1px solid var(--rec);
    border-radius: 5px;
    box-shadow:
      0 8px 16px rgba(0, 0, 0, 0.5),
      inset 0 1px 0 rgba(255, 255, 255, 0.04);
    padding: var(--sp-sm) var(--sp-md);
    display: flex;
    flex-direction: column;
    gap: var(--sp-sm);
    opacity: 0;
    transform: translateY(4px);
    pointer-events: none;
    transition: opacity var(--motion-transition) ease-out,
                transform var(--motion-transition) ease-out;
  }
  .vmx-statusbar__badge[data-tooltip-open="true"] .vmx-statusbar__tooltip {
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
  }
  .vmx-statusbar__tooltip-msg {
    font-family: "DM Mono", monospace;
    font-size: 11px;
    color: var(--ink);
    letter-spacing: 0.01em;
    text-transform: none;
    line-height: 1.4;
  }
  .vmx-statusbar__tooltip-btn {
    align-self: flex-start;
    font-family: "Workbench", "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    padding: 6px 12px;
    border: 1px solid var(--phosphor-dim);
    border-radius: 3px;
    color: var(--phosphor);
    background: linear-gradient(180deg, var(--panel-lift), var(--panel));
    cursor: pointer;
    line-height: 1;
  }
  .vmx-statusbar__tooltip-btn:hover {
    border-color: var(--phosphor);
    box-shadow: var(--phosphor-glow);
  }
  @keyframes vmx-statusbar-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
`;

registerStyle("vmx-statusbar", CSS);

interface BadgeSpec {
  key: BadgeKey;
  state: string;
  label: string;
  clickable: boolean;
}

function buildBadgeSpecs(props: StatusBarProps): BadgeSpec[] {
  return [
    {
      key: "livekit",
      state: props.livekit ?? "off",
      label: badgeLabel("LIVEKIT", props.livekit),
      clickable: props.livekit === "down",
    },
    {
      key: "gemini",
      state: props.gemini ?? "off",
      label: badgeLabel("GEMINI", props.gemini),
      clickable: props.gemini === "down",
    },
    {
      key: "midi",
      state: props.midi == null || props.midi === 0 ? "down" : "ok",
      label: `● MIDI · ${props.midi ?? 0}`,
      clickable: props.midi == null || props.midi === 0,
    },
    {
      key: "screen",
      state: props.screen ?? "off",
      label: badgeLabel(props.screen === "denied" ? "SCREEN · DENIED" : "SCREEN", props.screen),
      clickable: props.screen === "denied",
    },
  ];
}

function badgeLabel(base: string, state: BadgeState | "denied" | null): string {
  if (state === "connecting") return `● ${base} · CONNECTING`;
  if (state === "down") return `● ${base} · DOWN`;
  if (state === "denied") return `● ${base}`;
  return `● ${base}`;
}

export function renderStatusBar(props: StatusBarProps): HTMLElement {
  const root = document.createElement("footer");
  root.className = "vmx-statusbar";
  root.setAttribute("role", "contentinfo");

  const specs = buildBadgeSpecs(props);
  for (const spec of specs) {
    root.append(buildBadge(spec, props));
  }

  const muted = document.createElement("span");
  muted.className = "vmx-statusbar__muted";
  muted.hidden = !props.muted;
  const mled = document.createElement("span");
  mled.className = "vmx-statusbar__led";
  mled.setAttribute("aria-hidden", "true");
  const mlbl = document.createElement("span");
  mlbl.textContent = `MUTED · ${props.hotkey}`;
  muted.append(mled, mlbl);
  root.append(muted);

  const sig = document.createElement("span");
  sig.className = "vmx-statusbar__sig";
  if (props.muted) sig.classList.add("has-muted");
  sig.textContent = "made by bravoh";
  root.append(sig);

  return root;
}

function buildBadge(spec: BadgeSpec, props: StatusBarProps): HTMLElement {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "vmx-statusbar__badge";
  btn.dataset.key = spec.key;
  btn.dataset.state = spec.state;
  btn.dataset.clickable = spec.clickable ? "true" : "false";
  btn.dataset.tooltipOpen = "false";
  if (!spec.clickable) btn.disabled = true;

  const led = document.createElement("span");
  led.className = "vmx-statusbar__led";
  led.setAttribute("aria-hidden", "true");
  // Strip the leading bullet from the label — we render the LED.
  const lbl = document.createElement("span");
  lbl.textContent = spec.label.replace(/^●\s*/, "");
  btn.append(led, lbl);

  if (spec.clickable) {
    const tooltip = buildTooltip(spec.key, props);
    btn.append(tooltip);
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const isOpen = btn.dataset.tooltipOpen === "true";
      // Close all tooltips first
      btn.closest(".vmx-statusbar")?.querySelectorAll<HTMLElement>(
        ".vmx-statusbar__badge[data-tooltip-open='true']",
      ).forEach((b) => (b.dataset.tooltipOpen = "false"));
      btn.dataset.tooltipOpen = isOpen ? "false" : "true";
    });
    // Outside click closes
    document.addEventListener("click", (e) => {
      if (btn.dataset.tooltipOpen !== "true") return;
      if (!(e.target instanceof Node) || !btn.contains(e.target)) {
        btn.dataset.tooltipOpen = "false";
      }
    });
  }

  return btn;
}

function buildTooltip(key: BadgeKey, props: StatusBarProps): HTMLElement {
  const tip = document.createElement("div");
  tip.className = "vmx-statusbar__tooltip";
  tip.dataset.for = key;
  tip.setAttribute("role", "tooltip");

  const msg = document.createElement("div");
  msg.className = "vmx-statusbar__tooltip-msg";
  msg.textContent = props.errors?.[key] ?? defaultErrorMsg(key);
  tip.append(msg);

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "vmx-statusbar__tooltip-btn";
  btn.textContent = "[ ↻ Recheck ]";
  btn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    props.onRecheck?.(key);
  });
  tip.append(btn);

  return tip;
}

function defaultErrorMsg(key: BadgeKey): string {
  switch (key) {
    case "livekit": return "livekit session disconnected — recheck route";
    case "gemini": return "gemini api unreachable — recheck network + key";
    case "midi": return "no midi controllers detected — plug one in";
    case "screen": return "screen-capture permission denied — open system settings";
  }
}
