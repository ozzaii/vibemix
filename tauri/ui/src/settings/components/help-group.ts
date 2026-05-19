/* help-group.ts — Settings drawer HELP group (impeccable Wave 6, closes
 * H10 "help & documentation").
 *
 * Four rows inside the standard `renderSettingsGroup` shell:
 *
 *   1. KEYBOARD SHORTCUTS → opens the shortcuts overlay (the same one
 *      bound to `?` on the session surface).
 *   2. TROUBLESHOOT AUDIO → expandable checklist of the three macOS-prereq
 *      checks (BlackHole routed to master, screen-recording permission,
 *      djay Pro running). Each item is a row with a status dot. The
 *      BlackHole + Screen-Recording rows have inline links — those URLs
 *      are already in the Tauri capability allowlist (default.json).
 *   3. GITHUB → opens the public repo URL externally. The GitHub URL is
 *      NOT in the capability allowlist today; we console.warn + carry a
 *      TODO so the wiring lands when the allowlist gets the entry.
 *   4. ABOUT → version + build-date row. Version reads from the package
 *      version constant below (kept in sync with package.json by hand —
 *      vite doesn't expose package.json to TS without a json import that
 *      would pull in package-lock issues; this is a one-line bump per
 *      release).
 *
 * Visual: each row uses `.vmx-tile` base — no hero, no alert. Hover state
 * is a quiet silk-22 border lift. The HELP group itself is a standard
 * `renderSettingsGroup` so it slots into the drawer the same way as
 * PERSONA / OUTPUT / RECORDING / etc.
 *
 * Pure-function — accepts a config object (handlers + optional URLs) and
 * returns an HTMLElement. No state. */

import { invoke } from "@tauri-apps/api/core";

import { registerStyle } from "../../session/components/_style-registry.js";
import { mountShortcutsOverlay } from "../../session/components/shortcuts-overlay.js";
import { renderSettingsGroup } from "./group.js";

/** Hand-bumped per release. The settings drawer's About row reads this. */
export const VIBEMIX_VERSION = "0.1.0-rc1";

/** Hand-bumped per release alongside VIBEMIX_VERSION. ISO-8601 date. */
export const VIBEMIX_BUILD_DATE = "2026-05-14";

/** Public repo URL — opened by the GITHUB row. NOT in the capability
 *  allowlist today; see TODO in `openGithubRepo()`. */
export const GITHUB_REPO_URL = "https://github.com/bravoh-ai/vibemix";

/** BlackHole install URL — already in default.json allowlist. */
const BLACKHOLE_URL = "https://existential.audio/blackhole";

/** macOS screen-recording prefs deep link — already in default.json. */
const SCREEN_RECORDING_URL =
  "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture";

export type ChecklistStatus = "ok" | "warn" | "fault" | "unknown";

export interface HelpGroupProps {
  /** Status dots for the three troubleshoot rows. Optional — when omitted
   *  the dot renders neutral ("unknown" → silk-22 dome). The drawer
   *  doesn't have synchronous access to wizardState today (TODO Phase 17
   *  — surface a wizard-derived checklist slice in SessionState); for
   *  now the rows render as static checks with neutral dots. */
  blackhole?: ChecklistStatus;
  screenRecording?: ChecklistStatus;
  djay?: ChecklistStatus;
}

const CSS = `
  [data-component="help-group"] {
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
  }
  [data-component="help-group"] .vmx-help-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-3);
    padding: 10px var(--sp-3);
    /* .vmx-tile base provides the glass shell; we only own the inner
     * row layout + hover state. */
    cursor: pointer;
    transition: border-color var(--motion-snap) ease-out,
                background var(--motion-snap) ease-out;
  }
  [data-component="help-group"] .vmx-help-row[data-static="true"] {
    cursor: default;
  }
  [data-component="help-group"] .vmx-help-row:not([data-static="true"]):hover {
    border-color: var(--silk-22);
    background: var(--glass-1);
  }
  [data-component="help-group"] .vmx-help-row__label {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk-65);
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  [data-component="help-group"] .vmx-help-row__sub {
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.04em;
    color: var(--silk-40);
    text-transform: none;
  }
  [data-component="help-group"] .vmx-help-row__chev {
    font-family: var(--type-mono);
    font-size: 12px;
    color: var(--silk-40);
    line-height: 1;
  }
  [data-component="help-group"] .vmx-help-row__dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--silk-22);
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.04);
    flex-shrink: 0;
  }
  [data-component="help-group"] .vmx-help-row__dot[data-status="ok"] {
    background: var(--led-ok);
    box-shadow:
      0 0 3px var(--led-ok),
      0 0 6px rgba(109, 212, 74, 0.28),
      inset 0 1px 0 rgba(255, 255, 255, 0.3);
  }
  [data-component="help-group"] .vmx-help-row__dot[data-status="warn"] {
    background: var(--led-warn);
    box-shadow:
      0 0 3px var(--led-warn),
      0 0 6px rgba(244, 197, 66, 0.28),
      inset 0 1px 0 rgba(255, 255, 255, 0.3);
  }
  [data-component="help-group"] .vmx-help-row__dot[data-status="fault"] {
    background: var(--led-fault);
    box-shadow:
      0 0 3px var(--led-fault),
      0 0 6px rgba(212, 65, 58, 0.28),
      inset 0 1px 0 rgba(255, 255, 255, 0.3);
  }
  [data-component="help-group"] .vmx-help-row__left {
    display: inline-flex;
    align-items: center;
    gap: var(--sp-3);
    flex: 1;
    min-width: 0;
  }
  [data-component="help-group"] .vmx-help-row__right {
    display: inline-flex;
    align-items: center;
    gap: var(--sp-2);
    flex-shrink: 0;
  }
`;

registerStyle("vmx-help-group", CSS);

/** Build a single help row. Pure helper — no state. */
function buildRow(opts: {
  label: string;
  sub?: string | null;
  status?: ChecklistStatus;
  chev?: string;
  ariaLabel?: string;
  title?: string;
  onClick?: () => void;
  static?: boolean;
}): HTMLElement {
  const row = document.createElement("div");
  row.className = "vmx-tile vmx-help-row";
  if (opts.static) row.dataset.static = "true";
  if (opts.title) row.setAttribute("title", opts.title);
  if (opts.ariaLabel) row.setAttribute("aria-label", opts.ariaLabel);

  const left = document.createElement("span");
  left.className = "vmx-help-row__left";
  if (opts.status) {
    const dot = document.createElement("span");
    dot.className = "vmx-help-row__dot";
    dot.dataset.status = opts.status;
    dot.setAttribute("aria-hidden", "true");
    left.append(dot);
  }
  const label = document.createElement("span");
  label.className = "vmx-help-row__label";
  label.textContent = opts.label;
  left.append(label);
  row.append(left);

  const right = document.createElement("span");
  right.className = "vmx-help-row__right";
  if (opts.sub) {
    const sub = document.createElement("span");
    sub.className = "vmx-help-row__sub";
    sub.textContent = opts.sub;
    right.append(sub);
  }
  if (opts.chev) {
    const chev = document.createElement("span");
    chev.className = "vmx-help-row__chev";
    chev.textContent = opts.chev;
    chev.setAttribute("aria-hidden", "true");
    right.append(chev);
  }
  row.append(right);

  if (opts.onClick) {
    row.setAttribute("role", "button");
    row.setAttribute("tabindex", "0");
    row.addEventListener("click", (e) => {
      e.preventDefault();
      opts.onClick?.();
    });
    row.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        opts.onClick?.();
      }
    });
  }

  return row;
}

/** Open the keyboard shortcuts overlay. Routes through the same mount
 *  path as the `?` shortcut so callers don't need to know about the
 *  singleton state. */
function openShortcuts(): void {
  mountShortcutsOverlay();
}

/** Open the public GitHub repo. The URL is NOT in the Tauri capability
 *  allowlist today; the invoke call will reject. We console.warn and
 *  carry a TODO — when the allowlist gets the entry, this just works. */
function openGithubRepo(): void {
  // TODO(phase-17): add { "url": GITHUB_REPO_URL } to
  // tauri/src-tauri/capabilities/default.json under shell:allow-open.
  void invoke("plugin:shell|open", { path: GITHUB_REPO_URL }).catch(
    (err: unknown) => {
      // eslint-disable-next-line no-console
      console.warn(
        "[help-group] github open failed (capability allowlist?):",
        err,
      );
    },
  );
}

/** Open the BlackHole install page (URL already allowlisted). */
function openBlackHoleInstall(): void {
  void invoke("plugin:shell|open", { path: BLACKHOLE_URL }).catch(
    (err: unknown) => {
      // eslint-disable-next-line no-console
      console.warn("[help-group] blackhole open failed:", err);
    },
  );
}

/** Open macOS screen-recording prefs (URL already allowlisted). */
function openScreenRecordingPrefs(): void {
  void invoke("plugin:shell|open", { path: SCREEN_RECORDING_URL }).catch(
    (err: unknown) => {
      // eslint-disable-next-line no-console
      console.warn("[help-group] screen-recording open failed:", err);
    },
  );
}

/** Render the HELP settings group. Pure-function — re-renders on every
 *  drawer refresh, same pattern as PerformanceGroup. */
export function HelpGroup(props: HelpGroupProps = {}): HTMLElement {
  const body = document.createElement("div");

  body.append(
    buildRow({
      label: "KEYBOARD SHORTCUTS",
      chev: "?",
      ariaLabel: "open keyboard shortcuts overlay",
      title: "open the keyboard shortcuts overlay",
      onClick: openShortcuts,
    }),
  );

  body.append(
    buildRow({
      label: "TROUBLESHOOT AUDIO",
      sub: "blackhole + screen + djay",
      static: true,
      title: "audio-routing checklist",
    }),
  );

  body.append(
    buildRow({
      label: "BLACKHOLE ROUTED?",
      sub: "open install page",
      status: props.blackhole ?? "unknown",
      ariaLabel: "open blackhole install page",
      title: "open the blackhole install page in your browser",
      onClick: openBlackHoleInstall,
    }),
  );

  body.append(
    buildRow({
      label: "SCREEN RECORDING?",
      sub: "open system settings",
      status: props.screenRecording ?? "unknown",
      ariaLabel: "open macos screen recording preferences",
      title: "open macos screen recording preferences",
      onClick: openScreenRecordingPrefs,
    }),
  );

  body.append(
    buildRow({
      label: "DJAY PRO RUNNING?",
      sub: "launch djay manually",
      status: props.djay ?? "unknown",
      static: true,
      title: "vibemix watches djay's window. launch djay to enable screen grounding",
    }),
  );

  body.append(
    buildRow({
      label: "GITHUB",
      sub: "bravoh-ai/vibemix",
      chev: "↗",
      ariaLabel: "open vibemix github repository",
      title: "open the vibemix github repository in your browser",
      onClick: openGithubRepo,
    }),
  );

  body.append(
    buildRow({
      label: "ABOUT",
      sub: `${VIBEMIX_VERSION} · ${VIBEMIX_BUILD_DATE}`,
      static: true,
      ariaLabel: `vibemix version ${VIBEMIX_VERSION} built ${VIBEMIX_BUILD_DATE}`,
      title: `vibemix ${VIBEMIX_VERSION} built ${VIBEMIX_BUILD_DATE}`,
    }),
  );

  const group = renderSettingsGroup({
    header: "HELP",
    children: body,
  });
  group.setAttribute("data-component", "help-group");
  return group;
}
