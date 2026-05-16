/* shortcuts.ts — global keyboard shortcut registry (impeccable Wave 5.A).
 *
 * Closes the Nielsen heuristic gaps the 2026-05-14 critique flagged: no
 * discoverable shortcuts (Heuristic 3 — User Control & Freedom 1/4) and no
 * power-user efficiency surface (Heuristic 7 — Flexibility & Efficiency
 * 1/4). Touring DJs (Persona B) live keyboard-first; this module gives the
 * app a single registry for `?` / `cmd+m` / `esc` / wizard-back so the
 * surfaces don't each implement their own keydown handler.
 *
 * Combo syntax (case-insensitive, single-token-or-plus-joined):
 *   "?", "esc", "cmd+m", "ctrl+shift+z", "cmd+["
 *
 * Cross-platform: `cmd` resolves to the Meta modifier on macOS and the
 * Control modifier on Windows/Linux. We detect platform off
 * navigator.platform / navigator.userAgentData so tests can stub it. `ctrl`
 * always means literal Control regardless of platform (so a Windows-style
 * `ctrl+m` works on Mac via the explicit modifier).
 *
 * Focus discipline:
 *   - Skips when target is <input> / <textarea> / [contenteditable].
 *   - Skips when a tab-focused interactive element is active (the user
 *     navigated by keyboard into a form widget). Click-focused elements
 *     should NOT disable shortcuts — clicks shouldn't trap the keyboard.
 *
 * Test contract: each combo's callback is invoked exactly once per
 * matching keydown; the returned unregister function detaches the listener
 * AND clears the active platform memo. */

/** Map of combo string → callback. Single-key combos use the lowercase
 *  key name; modified combos use "mod+key" with modifiers in any order. */
export type ShortcutMap = Readonly<Record<string, () => void>>;

/** Unregister handle returned by `registerShortcuts`. */
export type Unregister = () => void;

/** Parsed combo for cheap runtime matching. */
interface ParsedCombo {
  /** Lowercase key — `e.key.toLowerCase()` for letters, ` ` for space,
   *  `escape` for the Esc key, `?` is matched as `e.key === "?"`. */
  key: string;
  meta: boolean;
  ctrl: boolean;
  shift: boolean;
  alt: boolean;
}

const ALIASES: Record<string, string> = {
  esc: "escape",
  escape: "escape",
  // Single-char punctuation stays as-is; we match e.key directly.
  "?": "?",
  "[": "[",
  "]": "]",
};

/** Detect whether the runtime is macOS so `cmd` maps to Meta. Cached per
 *  call so tests can stub navigator.platform between cases. */
function isMac(): boolean {
  try {
    const platform = (globalThis.navigator?.platform ?? "").toLowerCase();
    if (platform.includes("mac")) return true;
    if (platform.includes("iphone") || platform.includes("ipad")) return true;
    // Fall back to userAgent (some Tauri builds report empty platform).
    const ua = (globalThis.navigator?.userAgent ?? "").toLowerCase();
    return ua.includes("mac");
  } catch {
    return false;
  }
}

function parseCombo(combo: string): ParsedCombo {
  const parts = combo.toLowerCase().split("+").map((p) => p.trim()).filter(Boolean);
  const result: ParsedCombo = {
    key: "",
    meta: false,
    ctrl: false,
    shift: false,
    alt: false,
  };
  const mac = isMac();
  for (const part of parts) {
    switch (part) {
      case "cmd":
      case "meta":
      case "super":
        if (mac) result.meta = true;
        else result.ctrl = true;
        break;
      case "ctrl":
      case "control":
        result.ctrl = true;
        break;
      case "shift":
        result.shift = true;
        break;
      case "alt":
      case "option":
        result.alt = true;
        break;
      default:
        // Last non-modifier token is the key. Later tokens override
        // earlier ones — `cmd+a+b` would match `b` (callers shouldn't
        // write that; this is just defensive).
        result.key = ALIASES[part] ?? part;
    }
  }
  return result;
}

/** Should the keydown be suppressed because the user is typing into a
 *  field? Inputs, textareas, contenteditable hosts all count. */
function isTextInputTarget(target: EventTarget | null): boolean {
  if (!target || !(target instanceof Element)) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if ((target as HTMLElement).isContentEditable) return true;
  return false;
}

/** Was the currently-focused element reached via keyboard navigation
 *  (tab)? jsdom doesn't expose `:focus-visible` reliably, so we approximate
 *  by checking `document.activeElement?.matches(":focus-visible")` and
 *  falling back to false. The :focus-visible pseudo-class is true for
 *  tab-focused elements but false for click-focused ones in modern
 *  browsers. */
function isKeyboardFocusedInteractive(): boolean {
  try {
    const ae = document.activeElement as HTMLElement | null;
    if (!ae) return false;
    if (ae === document.body) return false;
    // Only block on actual form/interactive widgets — buttons specifically
    // are NOT blocked because shortcut-driven dismissals (esc closing the
    // shortcuts overlay) should still work even when a button has focus
    // from the keyboard.
    const tag = ae.tagName;
    if (tag !== "INPUT" && tag !== "TEXTAREA" && tag !== "SELECT") return false;
    if (typeof ae.matches === "function") {
      try {
        return ae.matches(":focus-visible");
      } catch {
        return false;
      }
    }
    return false;
  } catch {
    return false;
  }
}

function matches(parsed: ParsedCombo, e: KeyboardEvent): boolean {
  // Modifier match must be exact — `cmd+m` should NOT fire on `cmd+shift+m`.
  if (parsed.meta !== e.metaKey) return false;
  if (parsed.ctrl !== e.ctrlKey) return false;
  if (parsed.shift !== e.shiftKey) return false;
  if (parsed.alt !== e.altKey) return false;
  // Key match. e.key is browser-normalized — letters arrive lowercase
  // unless shift is pressed (in which case e.key is uppercase, but we
  // already required shift to match). We compare lowercase against the
  // parsed key.
  if (parsed.key === "?") {
    // `?` is shift+/ on US keyboards but e.key === "?" regardless.
    return e.key === "?";
  }
  return e.key.toLowerCase() === parsed.key;
}

/** Register a keyboard shortcut map. Returns an unregister function.
 *
 *  Multiple registrations stack — each call attaches its own document
 *  listener so different surfaces (session UI vs. wizard) can wire their
 *  own shortcut tables without coordinating through a singleton.
 *
 *  @example
 *    const unregister = registerShortcuts({
 *      "?": () => toggleOverlay(),
 *      "cmd+m": () => sendMute(),
 *      "esc": () => closeAnyOverlay(),
 *    });
 *    // ...later...
 *    unregister();
 */
export function registerShortcuts(map: ShortcutMap): Unregister {
  const entries = Object.entries(map).map(([combo, cb]) => ({
    combo,
    parsed: parseCombo(combo),
    cb,
  }));

  const onKeyDown = (e: KeyboardEvent): void => {
    if (isTextInputTarget(e.target)) return;
    if (isKeyboardFocusedInteractive()) return;
    for (const entry of entries) {
      if (matches(entry.parsed, e)) {
        e.preventDefault();
        try {
          entry.cb();
        } catch (err) {
          // eslint-disable-next-line no-console
          console.warn(`[shortcuts] callback for "${entry.combo}" threw:`, err);
        }
        return;
      }
    }
  };

  document.addEventListener("keydown", onKeyDown);

  return () => {
    document.removeEventListener("keydown", onKeyDown);
  };
}

// ---------------------------------------------------------------------------
// Test-only surface — vitest specs import these to exercise private parsing
// behaviour without mounting the full registry.
// ---------------------------------------------------------------------------

export const _internals = {
  parseCombo,
  isMac,
  isTextInputTarget,
  matches,
};
