/* shortcuts-overlay.ts — `?`-key shortcuts surface (impeccable Wave 5.A).
 *
 * Full-screen dim backdrop + centered glass panel listing the available
 * keyboard shortcuts. Closes the Heuristic 7 (Flexibility & Efficiency)
 * gap from the 2026-05-14 critique — touring DJs now have a discoverable
 * keyboard surface without leaving the session view.
 *
 * Visual contract (CDJ Whisper restraint):
 *   - rgba(0,0,0,0.72) dim backdrop covering the whole window.
 *   - Center-aligned glass panel via `.vmx-tile` utility with data-tile="hero".
 *   - Max-width 480px, single "KEYBOARD" header.
 *   - 2-column rows: left col = kbd chiclets in JetBrains Mono 11px, right
 *     col = action description in Saira 14px --silk-65.
 *   - NO border-anim sweep (moment, not a surface).
 *   - NO modal close-x — Esc / ? dismiss keyboard-only.
 *
 * Mountable via `mountShortcutsOverlay(host?)` which is idempotent — a
 * second call returns the existing handle without re-mounting. Unmount via
 * the returned `unmount()` function or by re-calling mount (no-op if
 * already mounted).
 *
 * NOTE: dismissal via Esc / ? is wired by the parent surface
 * (session-shortcuts.ts) — this component only renders + tears down. */

import { registerStyle } from "./_style-registry.js";

const CSS = `
  .vmx-shortcuts-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.72);
    z-index: 200;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--sp-5);
    animation: vmx-shortcuts-fade 150ms ease-out;
  }
  .vmx-shortcuts-panel {
    width: 100%;
    max-width: 480px;
    padding: var(--sp-5) var(--sp-5) var(--sp-4);
    display: flex;
    flex-direction: column;
    gap: var(--sp-4);
    /* .vmx-tile + data-tile="hero" provides the glass shell + drop shadow;
     * the layout above sits inside that frame. */
  }
  .vmx-shortcuts-panel__header {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 9px;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--silk);
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .vmx-shortcuts-panel__list {
    display: flex;
    flex-direction: column;
    gap: var(--sp-3);
  }
  .vmx-shortcuts-panel__row {
    display: grid;
    grid-template-columns: 140px 1fr;
    align-items: center;
    gap: var(--sp-3);
  }
  .vmx-shortcuts-panel__keys {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    flex-wrap: wrap;
  }
  .vmx-shortcuts-panel__kbd {
    font-family: var(--type-mono);
    font-size: 11px;
    line-height: 1;
    color: var(--silk);
    background: var(--glass-3);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    padding: 4px 7px;
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.04),
      inset 0 -1px 0 rgba(0, 0, 0, 0.5);
    min-width: 18px;
    text-align: center;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    user-select: none;
  }
  .vmx-shortcuts-panel__kbd--sep {
    color: var(--silk-40);
    background: transparent;
    border: none;
    box-shadow: none;
    padding: 0 2px;
    font-family: var(--type-body);
    font-size: 11px;
  }
  .vmx-shortcuts-panel__desc {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 14px;
    color: var(--silk-65);
    line-height: 1.4;
  }
  .vmx-shortcuts-panel__footnote {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 11px;
    color: var(--silk-40);
    text-align: center;
    padding-top: var(--sp-2);
    border-top: 1px solid var(--glass-edge);
    letter-spacing: 0.04em;
  }
  @keyframes vmx-shortcuts-fade {
    from { opacity: 0; }
    to   { opacity: 1; }
  }
`;

registerStyle("vmx-shortcuts-overlay", CSS);

export interface ShortcutsOverlayHandle {
  /** Backdrop root attached to the host. */
  root: HTMLElement;
  /** Tear down the overlay. Idempotent — calling twice is a no-op. */
  unmount: () => void;
}

/** Shortcut entries the overlay renders. The Mac and non-Mac labels are
 *  baked in here so the overlay matches whatever platform the user is on
 *  without leaking platform branching into the parent surface. */
interface ShortcutEntry {
  /** Array of key chiclets to render left-to-right. A literal "+" in the
   *  array renders as a separator (no chiclet frame). */
  keys: string[];
  /** Right-column description, sentence case. */
  desc: string;
}

/** Build the shortcut entries with platform-appropriate modifier labels. */
function getEntries(): ShortcutEntry[] {
  const platform = (globalThis.navigator?.platform ?? "").toLowerCase();
  const ua = (globalThis.navigator?.userAgent ?? "").toLowerCase();
  const mac =
    platform.includes("mac") ||
    platform.includes("iphone") ||
    platform.includes("ipad") ||
    ua.includes("mac");

  const mod = mac ? "⌘" : "Ctrl";
  return [
    { keys: ["?"], desc: "show / hide this panel" },
    { keys: [mod, "+", "M"], desc: "mute the co-host" },
    { keys: ["Esc"], desc: "close any open panel or dialog" },
    { keys: [mod, "+", "["], desc: "back one step (wizard only)" },
  ];
}

// Module-level singleton — a second mount call returns the existing handle.
let mountedHandle: ShortcutsOverlayHandle | null = null;

/** Mount the shortcuts overlay into `host` (defaults to document.body).
 *  Idempotent — returns the existing handle if already mounted. */
export function mountShortcutsOverlay(
  host: HTMLElement = document.body,
): ShortcutsOverlayHandle {
  if (mountedHandle) return mountedHandle;

  const backdrop = document.createElement("div");
  backdrop.className = "vmx-shortcuts-backdrop";
  backdrop.setAttribute("role", "dialog");
  backdrop.setAttribute("aria-modal", "true");
  backdrop.setAttribute("aria-label", "keyboard shortcuts");

  const panel = document.createElement("div");
  panel.className = "vmx-tile vmx-shortcuts-panel";
  panel.setAttribute("data-tile", "hero");

  const header = document.createElement("div");
  header.className = "vmx-shortcuts-panel__header";
  header.textContent = "KEYBOARD";
  panel.append(header);

  const list = document.createElement("div");
  list.className = "vmx-shortcuts-panel__list";
  for (const entry of getEntries()) {
    list.append(renderRow(entry));
  }
  panel.append(list);

  const foot = document.createElement("div");
  foot.className = "vmx-shortcuts-panel__footnote";
  foot.textContent = "press ? again or esc to close";
  panel.append(foot);

  backdrop.append(panel);
  host.append(backdrop);

  const handle: ShortcutsOverlayHandle = {
    root: backdrop,
    unmount: () => {
      if (mountedHandle !== handle) return;
      mountedHandle = null;
      try {
        backdrop.remove();
      } catch {
        /* DOM already gone */
      }
    },
  };
  mountedHandle = handle;
  return handle;
}

/** Test/peek helper — returns the live handle without mounting. */
export function getShortcutsOverlayHandle(): ShortcutsOverlayHandle | null {
  return mountedHandle;
}

/** Is the overlay currently mounted? */
export function isShortcutsOverlayMounted(): boolean {
  return mountedHandle !== null && mountedHandle.root.isConnected;
}

function renderRow(entry: ShortcutEntry): HTMLElement {
  const row = document.createElement("div");
  row.className = "vmx-shortcuts-panel__row";

  const keysCol = document.createElement("div");
  keysCol.className = "vmx-shortcuts-panel__keys";
  for (const k of entry.keys) {
    const cap = document.createElement("span");
    if (k === "+") {
      cap.className = "vmx-shortcuts-panel__kbd vmx-shortcuts-panel__kbd--sep";
      cap.textContent = "+";
    } else {
      cap.className = "vmx-shortcuts-panel__kbd";
      cap.textContent = k;
    }
    keysCol.append(cap);
  }
  row.append(keysCol);

  const desc = document.createElement("div");
  desc.className = "vmx-shortcuts-panel__desc";
  desc.textContent = entry.desc;
  row.append(desc);

  return row;
}
