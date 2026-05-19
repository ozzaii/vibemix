/* Phase 12 Wave 4 — hotkey capture row (Plan 12-05 §3 HOTKEY group).
 *
 * Two states:
 *   1. Idle  — shows the current combo as a JetBrains Mono 14px chip in
 *              var(--amber), plus a `[ ↻ Rebind ]` secondary button.
 *   2. Capture — chip becomes "PRESS KEYS…" pulsing var(--amber-deep)
 *              with var(--glow-soft); a single keydown captures the new
 *              combo and emits it.
 *
 * Reserved combos (rejected at capture time with inline `--rec` error):
 *   macOS  — cmd+q / cmd+w / cmd+tab / cmd+space / cmd+shift+tab
 *   Windows — alt+f4 / ctrl+alt+del / win+l
 *
 * Capture rules:
 *   - Require at least one modifier (mods.length >= 1).
 *   - Require a non-modifier key (key !== null).
 *   - Swallow all keydown events while in capture mode (preventDefault +
 *     stopPropagation) so the browser doesn't navigate / blur / etc.
 *
 * Emits the combo as a lowercase `+`-separated string matching the Rust
 * side's `validate_combo` grammar (e.g. `cmd+shift+m`). The caller wires
 * `onCapture` to call `sendSettings('push_to_mute_hotkey', combo)` AND
 * invoke the `rebind_hotkey` Tauri command, surfacing any Rust-side error
 * back into this component via `setHotkeyCaptureError`.
 *
 * The display chip rendering uses the platform's pretty form (⌘⇧M on
 * macOS, Ctrl+Shift+M on Windows) — UX clarity, not the wire format.
 */

import { registerStyle } from "../../session/components/_style-registry.js";

export interface HotkeyCaptureProps {
  /** Current hotkey combo in wire form (e.g. `cmd+shift+m`). */
  value: string;
  /** Fires on a valid capture. Reserved combos surface inline error
   *  instead of firing — they never reach the callback. */
  onCapture: (combo: string) => void;
  /** Optional error message — display-only; the caller controls clearing. */
  errorMessage?: string | null;
}

/** Lower-case `+`-joined modifier strings. Must match the Rust
 *  `RESERVED_COMBOS` list. */
const RESERVED_SET = new Set([
  "cmd+q",
  "cmd+w",
  "cmd+tab",
  "cmd+space",
  "cmd+shift+tab",
  "alt+f4",
  "ctrl+alt+del",
  "ctrl+alt+delete",
  "win+l",
  "meta+l",
]);

const CSS = `
  .vmx-hotkey-capture {
    display: flex;
    flex-direction: column;
    gap: var(--sp-3);
  }
  .vmx-hotkey-capture__row {
    display: flex;
    align-items: center;
    gap: var(--sp-3);
  }
  /* Hotkey chip — sealed glass-3 keycap recessed into the surface.
   * Amber readout (the actual combo) sits inside like a Pioneer LCD. */
  .vmx-hotkey-capture__chip {
    flex: 1;
    height: 36px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0 var(--sp-4);
    background: var(--glass-3);
    backdrop-filter: var(--blur-glass-display);
    -webkit-backdrop-filter: var(--blur-glass-display);
    border: 1px solid rgba(0, 0, 0, 0.55);
    border-radius: var(--rad-sm);
    box-shadow:
      inset 0 2px 6px rgba(0, 0, 0, 0.85),
      inset 0 0 0 1px rgba(0, 0, 0, 0.4),
      inset 0 0 14px rgba(255, 138, 61, 0.04),
      0 0 0 1px rgba(255, 255, 255, 0.02);
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-size: 14px;
    letter-spacing: 0.02em;
    color: var(--amber);
    line-height: 1;
    text-shadow: 0 0 6px var(--amber-40), 0 0 14px var(--amber-22);
    user-select: none;
    transition: color var(--motion-snap) ease-out,
                text-shadow var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out;
  }
  /* Capture mode — chip becomes warmer + pulses; signals "listening for
   * keypress". The amber-deep shade reads as "armed" without being alarming. */
  .vmx-hotkey-capture[data-capture="true"] .vmx-hotkey-capture__chip {
    color: var(--amber-deep);
    box-shadow:
      inset 0 2px 6px rgba(0, 0, 0, 0.85),
      inset 0 0 0 1px var(--amber-40),
      inset 0 0 18px var(--amber-22),
      0 0 0 1px rgba(255, 138, 61, 0.18);
    text-shadow: 0 0 7px var(--amber-65), 0 0 16px var(--amber-40);
    animation: vmx-hotkey-capture-pulse 1200ms ease-in-out infinite;
  }
  .vmx-hotkey-capture[data-error="true"] .vmx-hotkey-capture__chip {
    color: var(--led-fault);
    box-shadow:
      inset 0 2px 6px rgba(0, 0, 0, 0.85),
      inset 0 0 0 1px rgba(212, 65, 58, 0.35),
      inset 0 0 12px rgba(212, 65, 58, 0.10);
    text-shadow: 0 0 6px rgba(212, 65, 58, 0.45);
  }
  /* Rebind button — v5 amber-bleed-through-frost active treatment to
   * match the rocker + mood-block + drop-chip vocabulary. */
  .vmx-hotkey-capture__rebind {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    padding: 9px var(--sp-4);
    background: var(--glass-2);
    border: 1px solid var(--glass-edge);
    color: var(--silk-65);
    border-radius: var(--rad-sm);
    cursor: pointer;
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.035),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45);
    transition: color var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out,
                background var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out,
                text-shadow var(--motion-snap) ease-out;
  }
  .vmx-hotkey-capture__rebind:hover {
    color: var(--silk);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45),
      0 0 10px var(--amber-22);
  }
  .vmx-hotkey-capture[data-capture="true"] .vmx-hotkey-capture__rebind {
    color: var(--amber);
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.09) 0%, rgba(255, 138, 61, 0.025) 100%);
    border-color: rgba(255, 138, 61, 0.14);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 var(--amber-40),
      inset 0 0 14px var(--amber-22),
      0 0 0 1px rgba(255, 138, 61, 0.14);
    text-shadow: 0 0 4px var(--amber-65);
  }
  .vmx-hotkey-capture__error {
    font-family: var(--type-mono);
    font-size: 11px;
    line-height: 1.35;
    color: var(--led-fault);
    text-shadow: 0 0 4px rgba(212, 65, 58, 0.18);
  }
  @keyframes vmx-hotkey-capture-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
  }
`;

registerStyle("vmx-hotkey-capture", CSS);

/** Render the combo in OS-pretty form: ⌘⇧M on macOS, Ctrl+Shift+M
 *  elsewhere. Wire form (`cmd+shift+m`) is what we emit; this is the
 *  display surface. */
function prettyCombo(combo: string): string {
  if (!combo) return "·";
  const parts = combo.toLowerCase().split("+");
  const macSymbols: Record<string, string> = {
    cmd: "⌘",
    meta: "⌘",
    super: "⌘",
    shift: "⇧",
    alt: "⌥",
    option: "⌥",
    ctrl: "⌃",
    control: "⌃",
  };
  const isMac =
    typeof navigator !== "undefined" &&
    /Mac|iPhone|iPod|iPad/.test(navigator.platform || "");
  if (isMac) {
    return parts
      .map((p) => macSymbols[p] ?? p.toUpperCase())
      .join("");
  }
  return parts
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join("+");
}

/** Map a KeyboardEvent into a wire-form combo. Returns null if the press
 *  isn't a valid combo (no modifier, or only modifier keys held). */
export function keyEventToCombo(ev: KeyboardEvent): string | null {
  const mods: string[] = [];
  if (ev.metaKey) mods.push("cmd");
  if (ev.ctrlKey) mods.push("ctrl");
  if (ev.altKey) mods.push("alt");
  if (ev.shiftKey) mods.push("shift");
  if (mods.length === 0) return null;

  // The "key" field is null if the user is just holding modifiers.
  const k = ev.key;
  if (!k) return null;
  const MOD_KEYS = new Set([
    "Meta",
    "Control",
    "Alt",
    "Shift",
    "OS",
    "Hyper",
    "Super",
  ]);
  if (MOD_KEYS.has(k)) return null;

  // Normalise the key: single chars lowercase; special keys lowercase.
  let key = k.length === 1 ? k.toLowerCase() : k.toLowerCase();
  // Keep tab/space/escape recognisable; collapse arrow keys etc.
  if (key === " ") key = "space";
  return [...mods, key].join("+");
}

/** Reserved-combo check — used both by the inline error path AND by the
 *  vitest spec (so the wire-form expectations stay in sync). */
export function isReservedCombo(combo: string): boolean {
  return RESERVED_SET.has(combo.toLowerCase());
}

export interface HotkeyCaptureHandle {
  root: HTMLElement;
  /** Programmatically begin capture (test hook). */
  beginCapture: () => void;
  /** Programmatically cancel capture (test hook + Esc handler in drawer). */
  cancelCapture: () => void;
  /** Update the display chip without rebuilding. */
  setValue: (combo: string) => void;
  /** Surface a Rust-side rejection (e.g. unparseable combo). */
  setError: (msg: string | null) => void;
}

export function renderHotkeyCapture(
  props: HotkeyCaptureProps,
): HotkeyCaptureHandle {
  let value = props.value || "";
  let error: string | null = props.errorMessage ?? null;
  let capturing = false;

  const root = document.createElement("div");
  root.className = "vmx-hotkey-capture";
  root.dataset.capture = "false";
  root.dataset.error = error ? "true" : "false";

  const row = document.createElement("div");
  row.className = "vmx-hotkey-capture__row";

  const chip = document.createElement("div");
  chip.className = "vmx-hotkey-capture__chip";
  chip.setAttribute("aria-live", "polite");
  chip.textContent = prettyCombo(value);
  row.append(chip);

  const rebind = document.createElement("button");
  rebind.type = "button";
  rebind.className = "vmx-hotkey-capture__rebind";
  rebind.textContent = "↻ REBIND";
  rebind.setAttribute("aria-label", "rebind push-to-mute hotkey");
  row.append(rebind);

  root.append(row);

  const errorEl = document.createElement("div");
  errorEl.className = "vmx-hotkey-capture__error";
  errorEl.hidden = !error;
  errorEl.textContent = error ?? "";
  root.append(errorEl);

  function setError(msg: string | null): void {
    error = msg;
    root.dataset.error = msg ? "true" : "false";
    errorEl.hidden = !msg;
    errorEl.textContent = msg ?? "";
  }

  function setValue(combo: string): void {
    value = combo;
    chip.textContent = prettyCombo(value);
  }

  function beginCapture(): void {
    if (capturing) return;
    capturing = true;
    setError(null);
    root.dataset.capture = "true";
    chip.textContent = "PRESS KEYS…";
    document.addEventListener("keydown", onKeyDown, true);
  }

  function cancelCapture(): void {
    if (!capturing) return;
    capturing = false;
    root.dataset.capture = "false";
    chip.textContent = prettyCombo(value);
    document.removeEventListener("keydown", onKeyDown, true);
  }

  function onKeyDown(ev: KeyboardEvent): void {
    if (!capturing) return;
    // Allow Escape to cancel capture without recording.
    if (ev.key === "Escape") {
      ev.preventDefault();
      ev.stopPropagation();
      cancelCapture();
      return;
    }
    // Swallow EVERYTHING while in capture so the browser doesn't act.
    ev.preventDefault();
    ev.stopPropagation();

    const combo = keyEventToCombo(ev);
    if (!combo) return; // modifier-only press; wait for real key.

    if (isReservedCombo(combo)) {
      // Inline error; stay in capture mode so user can try again.
      setError(`${prettyCombo(combo)} is reserved by the operating system`);
      return;
    }

    // Valid capture — leave capture mode, update chip, fire callback.
    capturing = false;
    root.dataset.capture = "false";
    setValue(combo);
    document.removeEventListener("keydown", onKeyDown, true);
    props.onCapture(combo);
  }

  rebind.addEventListener("click", (e) => {
    e.preventDefault();
    if (capturing) cancelCapture();
    else beginCapture();
  });

  return {
    root,
    beginCapture,
    cancelCapture,
    setValue,
    setError,
  };
}
