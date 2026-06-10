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

/* VIS-02 (43-02): --glow-faint on hover/focus-visible per CONTEXT.
 * Clickable badges + the recheck tooltip button both gain the faint
 * amber halo on interactive states; non-clickable badges intentionally
 * stay quiet (no action to acknowledge). */

import { registerStyle } from "./_style-registry.js";

export type BadgeState = "ok" | "connecting" | "down" | null;

export interface StatusBarProps {
  livekit: BadgeState;
  gemini: "ok" | "down" | null;
  midi: number | null;
  midiActivity?:
    | "disconnected"
    | "connected_no_midi_traffic"
    | "midi_traffic_unmapped"
    | "midi_events_no_moves"
    | "active"
    | "unknown"
    | null;
  midiDevice?: string | null;
  screen: "ok" | "denied" | "unavailable" | null;
  voice?: "ok" | "muted" | null;
  muted: boolean;
  hotkey: string;
  /** Called when the user clicks Recheck inside a down-badge tooltip. */
  onRecheck?: (component: "livekit" | "gemini" | "midi" | "screen") => void;
  /** Optional error messages by component for the tooltip body. */
  errors?: Partial<Record<"livekit" | "gemini" | "midi" | "screen", string>>;
}

type RecoveryBadgeKey = "livekit" | "gemini" | "midi" | "screen";
type BadgeKey = RecoveryBadgeKey | "voice";
const defaultMidiErrorMsg = "no controller motion is reaching vibemix. plug in the controller, enable MIDI output, then move a fader";

const CSS = `
  /* v5 status strip — translucent dark glass shelf matching the
   * titlebar's treatment so the session window's top and bottom edges
   * read as the same sealed material. Dome LEDs (mock .led) replace the
   * flat coloured dots. */
  .vmx-statusbar {
    display: flex;
    align-items: center;
    gap: var(--sp-5);
    height: var(--statusbar-h);
    padding: 0 var(--sp-5);
    background: rgba(0, 0, 0, 0.55);
    backdrop-filter: var(--blur-glass-light);
    -webkit-backdrop-filter: var(--blur-glass-light);
    border-top: 1px solid var(--glass-edge);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 9px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk-40);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    line-height: 1;
    position: relative;
    z-index: 3;
  }
  .vmx-statusbar__badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border: none;
    background: transparent;
    color: var(--silk-40);
    font: inherit;
    letter-spacing: inherit;
    text-transform: inherit;
    text-shadow: inherit;
    line-height: 1;
    cursor: default;
    padding: 6px 4px;
    border-radius: var(--rad-sm);
    position: relative;
    transition: color var(--motion-snap) ease-out;
  }
  .vmx-statusbar__badge[data-clickable="true"] { cursor: pointer; }
  /* VIS-02 (43-02) — clickable badges (the "down"/"denied" recovery
   * surface) gain --glow-faint on hover/focus-visible so the recovery
   * affordance reads through the silk-40 baseline. Non-clickable
   * badges (disabled) intentionally stay quiet — they have no action
   * to acknowledge. */
  .vmx-statusbar__badge[data-clickable="true"]:hover,
  .vmx-statusbar__badge[data-clickable="true"]:focus-visible {
    color: var(--silk-65);
    box-shadow: var(--glow-faint);
  }
  .vmx-statusbar__led {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: rgba(15, 18, 24, 0.85);
    box-shadow:
      0 0 0 1px rgba(0, 0, 0, 0.7),
      inset 0 1px 0 rgba(255, 255, 255, 0.04);
    flex-shrink: 0;
  }
  /* OK — quiet-by-default (2026-05-26 /impeccable critique P2). The 4
   * status badges and the left-rail persona readout were two competing
   * "is it working?" glances at opposite corners. When everything is OK
   * the bar should recede: a dim green dot (no bloom) + silk-22 label, so
   * the eye only stops here when a badge drops to down/connecting. The
   * cohost foot ("READING THE ROOM") is the canonical alive-signal. */
  .vmx-statusbar__badge[data-state="ok"] .vmx-statusbar__led {
    background: var(--led-ok);
    box-shadow:
      0 0 2px rgba(109, 212, 74, 0.45),
      inset 0 1px 0 rgba(255, 255, 255, 0.18),
      inset 0 -0.5px 0 rgba(0, 0, 0, 0.4);
    opacity: 0.6;
  }
  .vmx-statusbar__badge[data-state="ok"] { color: var(--silk-22); }
  /* CONNECTING — amber dome, solid (no pulse; one-amber-rule per panel) */
  .vmx-statusbar__badge[data-state="connecting"] .vmx-statusbar__led {
    background: var(--amber);
    box-shadow:
      0 0 2px var(--amber-65),
      inset 0 1px 0 rgba(255, 255, 255, 0.18),
      inset 0 -0.5px 0 rgba(0, 0, 0, 0.4);
    opacity: 0.65;
  }
  .vmx-statusbar__badge[data-state="connecting"] { color: var(--amber-pale); }
  /* DOWN / DENIED — red dome */
  .vmx-statusbar__badge[data-state="down"] .vmx-statusbar__led,
  .vmx-statusbar__badge[data-state="denied"] .vmx-statusbar__led {
    background: var(--led-fault);
    box-shadow:
      0 0 3px var(--led-fault),
      0 0 6px rgba(212, 65, 58, 0.28),
      inset 0 1px 0 rgba(255, 255, 255, 0.3),
      inset 0 -0.5px 0 rgba(0, 0, 0, 0.4);
  }
  .vmx-statusbar__badge[data-state="down"],
  .vmx-statusbar__badge[data-state="denied"] {
    color: var(--led-fault);
    text-shadow: 0 0 4px rgba(212, 65, 58, 0.28);
  }
  /* Muted indicator */
  .vmx-statusbar__muted {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: var(--led-fault);
    text-shadow: 0 0 4px rgba(212, 65, 58, 0.28);
  }
  .vmx-statusbar__muted .vmx-statusbar__led {
    background: var(--led-fault);
    box-shadow:
      0 0 3px var(--led-fault),
      0 0 6px rgba(212, 65, 58, 0.28),
      inset 0 1px 0 rgba(255, 255, 255, 0.3),
      inset 0 -0.5px 0 rgba(0, 0, 0, 0.4);
  }
  /* Critique 2026-05-14 pass 2: the statusbar muted strip is a quiet
   * label, not a third alarm. The cohost inline pill carries the live
   * breathing cadence; this LED stays solid so the eye reads one signal,
   * not three. */
  .vmx-statusbar__muted[hidden] { display: none; }
  /* Signature — Saira at very low alpha so brand chrome is present but
   * does not compete with active state indicators. The earlier Caveat
   * treatment fought the Pioneer aesthetic; v5 makes the mark sit quietly
   * in the corner.
   * 2026-05-21 /impeccable pass 57 (HIGH): dropped font-style: italic.
   * DESIGN.md §Typography lists no italic style and RESEARCH Pitfall 5
   * pins "no italic anywhere" (Fraunces italic was the rejected v1 tell).
   * The recessive read is carried by silk-40 + 0.06em tracking + the
   * leading mid-dot, not by a slanted face. */
  .vmx-statusbar__sig {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 11px;
    color: var(--silk-40);
    letter-spacing: 0.06em;
    text-transform: none;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    line-height: 1;
  }
  .vmx-statusbar__sig:not(.has-muted) { margin-left: auto; }
  .vmx-statusbar__sig::before {
    content: '·';
    margin-right: 6px;
    color: var(--silk-22);
  }
  /* === Tooltip — recessed glass popover with fault-tinted hairline ==== */
  .vmx-statusbar__tooltip {
    position: absolute;
    bottom: calc(100% + 8px);
    left: 0;
    z-index: 60;
    min-width: 240px;
    background: var(--glass-1);
    backdrop-filter: var(--blur-glass);
    -webkit-backdrop-filter: var(--blur-glass);
    border: 1px solid rgba(212, 65, 58, 0.35);
    border-radius: var(--rad-sm);
    box-shadow:
      inset 0 1px 0 var(--glass-top),
      0 16px 40px rgba(0, 0, 0, 0.7),
      0 0 0 1px rgba(212, 65, 58, 0.10);
    padding: var(--sp-3) var(--sp-4);
    display: flex;
    flex-direction: column;
    gap: var(--sp-3);
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
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 12px;
    color: var(--silk);
    letter-spacing: 0;
    text-transform: none;
    line-height: 1.5;
    text-shadow: none;
  }
  .vmx-statusbar__tooltip-btn {
    align-self: flex-start;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    padding: 8px 14px;
    border: 1px solid var(--amber-40);
    border-radius: var(--rad-sm);
    color: var(--amber);
    background: linear-gradient(180deg, rgba(255, 165, 223, 0.09) 0%, rgba(255, 165, 223, 0.025) 100%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 var(--amber-40),
      inset 0 0 12px var(--amber-22);
    cursor: pointer;
    line-height: 1;
    text-shadow: 0 0 4px var(--amber-65);
    transition: border-color var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out;
  }
  /* VIS-02 (43-02) — Recheck button keeps its hot amber inset stack
   * AND additively gains --glow-faint as an outer halo so the click
   * affordance reads at-a-glance during error recovery (the moment
   * users most need the cue). :focus-visible mirrors hover for kbd. */
  .vmx-statusbar__tooltip-btn:hover,
  .vmx-statusbar__tooltip-btn:focus-visible {
    border-color: var(--amber);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.08),
      inset 0 -1px 0 var(--amber-65),
      inset 0 0 18px var(--amber-40),
      var(--glow-faint);
  }
`;

registerStyle("vmx-statusbar", CSS);

interface BadgeSpec {
  key: BadgeKey;
  state: string;
  label: string;
  clickable: boolean;
  title?: string;
  tooltip?: string;
}

function buildBadgeSpecs(props: StatusBarProps): BadgeSpec[] {
  // 2026-05-19 /impeccable critique round 3: engineering vocabulary
  // dropped from the user-facing labels. LIVEKIT → LINK, GEMINI → AI,
  // MIDI → CONTROLLER. Internal keys + IPC payloads keep their
  // technical names; only the displayed label shifts to DJ-register.
  const specs: BadgeSpec[] = [
    {
      key: "livekit",
      state: props.livekit ?? "off",
      label: badgeLabel("VOICE LINK", props.livekit),
      clickable: props.livekit === "down",
    },
    {
      key: "gemini",
      state: props.gemini ?? "off",
      label: badgeLabel("BRAIN", props.gemini),
      clickable: props.gemini === "down",
    },
    midiBadgeSpec(props),
    {
      key: "screen",
      state: screenBadgeState(props.screen),
      label: screenBadgeLabel(props.screen),
      clickable: props.screen === "denied",
    },
  ];
  if (props.voice === "muted") {
    specs.push({
      key: "voice",
      state: "down",
      label: "● VOICE MUTED",
      clickable: false,
    });
  }
  return specs;
}

function midiBadgeSpec(props: StatusBarProps): BadgeSpec {
  const device = midiDeviceLabel(props.midiDevice);
  const activity = props.midiActivity ?? null;
  if (props.midi != null && props.midi > 0) {
    return {
      key: "midi",
      state: "ok",
      label: `● ${device} · ACTIVE`,
      clickable: false,
      title: `Controller · ${device} motion proven`,
    };
  }
  if (props.midi == null) {
    return {
      key: "midi",
      state: "down",
      label: "● CONTROLLER · CHECK",
      clickable: true,
      title: "Controller · checking · click for recovery",
      tooltip: "controller status is not available yet. recheck MIDI, then move a fader",
    };
  }
  if (activity === "connected_no_midi_traffic") {
    return {
      key: "midi",
      state: "down",
      label: `● ${device} · WAITING`,
      clickable: true,
      title: `${device} · connected, waiting for motion`,
      tooltip: `${device} is connected, but no MIDI frames have landed. move an EQ knob or fader once`,
    };
  }
  if (activity === "midi_traffic_unmapped") {
    return {
      key: "midi",
      state: "down",
      label: `● ${device} · UNMAPPED`,
      clickable: true,
      title: `${device} · MIDI frames are not mapped`,
      tooltip: `${device} is sending MIDI, but the active profile is not decoding it. run controller mapping`,
    };
  }
  if (activity === "midi_events_no_moves") {
    return {
      key: "midi",
      state: "down",
      label: `● ${device} · NO MOVES`,
      clickable: true,
      title: `${device} · waiting for a deck control move`,
      tooltip: `${device} is visible. move a deck control once so vibemix can cite it`,
    };
  }
  if (activity === "disconnected") {
    return {
      key: "midi",
      state: "down",
      label: "● CONTROLLER · OFF",
      clickable: true,
      title: "Controller · not connected · click for recovery",
      tooltip: "no MIDI input port is visible. connect the controller, enable MIDI output, then recheck",
    };
  }
  return {
    key: "midi",
    state: "down",
    label: `● CONTROLLER · ${props.midi ?? 0}`,
    clickable: true,
    title: "Controller · motion not proven · click for recovery",
    tooltip: defaultMidiErrorMsg,
  };
}

function midiDeviceLabel(device?: string | null): string {
  const text = (device ?? "").trim().replace(/\s+/g, " ");
  return text || "CONTROLLER";
}

function badgeLabel(base: string, state: BadgeState | "denied" | null): string {
  if (state === "connecting") return `● ${base} · CONNECTING`;
  if (state === "down") return `● ${base} · DOWN`;
  if (state === "denied") return `● ${base}`;
  return `● ${base}`;
}

function screenBadgeState(
  screen: StatusBarProps["screen"],
): "ok" | "down" | "off" {
  if (screen === "ok") return "ok";
  if (screen === "denied") return "down";
  return "off";
}

function screenBadgeLabel(screen: StatusBarProps["screen"]): string {
  if (screen === "denied") return "● SCREEN · DENIED";
  if (screen === "unavailable") return "● SCREEN · OFF";
  return "● SCREEN";
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
  // Wave 6 (H6 recognition over recall) — native browser hover tooltip
  // narrates the badge state for users who don't know what each LED means.
  // Click-tooltip (existing) is still the recovery path for "down"; this
  // surfaces "ok" too so the user can read "LiveKit · connected" without
  // having to click into a dead badge.
  const title = spec.title ?? titleForBadge(spec.key, spec.state);
  btn.setAttribute("title", title);
  btn.setAttribute("aria-label", title);
  if (!spec.clickable) btn.disabled = true;

  const led = document.createElement("span");
  led.className = "vmx-statusbar__led";
  led.setAttribute("aria-hidden", "true");
  // Strip the leading bullet from the label — we render the LED.
  const lbl = document.createElement("span");
  lbl.textContent = spec.label.replace(/^●\s*/, "");
  btn.append(led, lbl);

  if (spec.clickable) {
    const tooltip = buildTooltip(spec as BadgeSpec & { key: RecoveryBadgeKey }, props);
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

function buildTooltip(
  spec: BadgeSpec & { key: RecoveryBadgeKey },
  props: StatusBarProps,
): HTMLElement {
  const tip = document.createElement("div");
  tip.className = "vmx-statusbar__tooltip";
  tip.dataset.for = spec.key;
  tip.setAttribute("role", "tooltip");

  const msg = document.createElement("div");
  msg.className = "vmx-statusbar__tooltip-msg";
  msg.textContent = props.errors?.[spec.key] ?? spec.tooltip ?? defaultErrorMsg(spec.key);
  tip.append(msg);

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "vmx-statusbar__tooltip-btn";
  btn.textContent = "[ ↻ Recheck ]";
  btn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    props.onRecheck?.(spec.key);
  });
  tip.append(btn);

  return tip;
}

function defaultErrorMsg(key: RecoveryBadgeKey): string {
  switch (key) {
    case "livekit": return "voice link dropped. click to reconnect";
    case "gemini": return "brain unreachable. check your connection";
    case "midi": return defaultMidiErrorMsg;
    case "screen": return "screen-capture permission denied. open system settings";
  }
}

/** Wave 6 (H6) — native hover-tooltip copy for each badge. Mirrors the
 *  defaultErrorMsg() for the "down" surface but adds an "ok" + neutral
 *  variant so recognition works without clicking. */
function titleForBadge(key: BadgeKey, state: string): string {
  // 2026-05-19 /impeccable critique round 3: tooltip labels match the
  // DJ-register surface vocabulary instead of the internal LiveKit /
  // Gemini / MIDI names. Internal keys (used for IPC + recovery) keep
  // their technical names.
  const label = (() => {
    switch (key) {
      case "livekit": return "Voice link";
      case "gemini": return "Brain";
      case "midi": return "Controller";
      case "screen": return "Screen capture";
      case "voice": return "Local voice";
    }
  })();
  if (key === "voice" && state === "down") return `${label} · muted`;
  if (state === "ok") return `${label} · connected`;
  if (state === "connecting") return `${label} · connecting…`;
  if (state === "denied") return `${label} · permission denied`;
  if (key === "screen" && state === "down") return `${label} · permission denied`;
  if (state === "down") return `${label} · disconnected · click for recovery`;
  return `${label} · off`;
}
