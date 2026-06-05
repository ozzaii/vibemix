/* Phase 12 Wave 4 — Settings slide-over drawer (Plan 12-05 §2).
 *
 * Right-side, 400px wide, slides in over the live session. The session
 * continues rendering at full fps BEHIND the backdrop — the drawer is
 * pure overlay; it does NOT pause `render-loop.ts`.
 *
 * Mount:  `mountSettingsDrawer(root)` appends two top-level nodes to
 *         `root`:
 *           - `.vmx-settings-backdrop` (full-window dim at 0.55 opacity,
 *             clickable to dismiss)
 *           - `.vmx-settings-drawer`   (slide-over, z-index 50)
 *         Both initially `display: none` / `translateX(100%)`. The shell
 *         calls `openSettings()` to slide in, `closeSettings()` to slide out,
 *         and `unmountSettingsDrawer()` on route/mock teardown.
 *
 * State sources:
 *   - getSessionState().settings — current values for each picker / rocker.
 *   - getSettingsUIState() — drawer-local UX state (open, capture, etc).
 *
 * Outbound writes:
 *   - sendSettings(field, value) — every mutation.
 *   - invoke('rebind_hotkey', { newCombo }) — hotkey rebind (Tauri command).
 *   - emitIpc('ipc.wizard.start', {}) — calibration re-run (sidecar tears
 *     down session and routes to wizard).
 *
 * The drawer re-renders on:
 *   - settings-state diffs (subscribed via subscribeSettingsUI + a polling
 *     check on getSessionState().settings every time the drawer opens —
 *     mid-session edits trigger a sidecar broadcast which the ws-bridge
 *     writes; the drawer re-syncs its picker labels on open).
 *
 * Keyboard:
 *   - Esc closes the drawer (unless inside an in-flight modal or capture).
 */

import { invoke } from "@tauri-apps/api/core";

import { registerStyle } from "../session/components/_style-registry.js";
import { disposePicker, renderPicker } from "../session/components/picker.js";
import { renderRocker } from "../session/components/rocker.js";
import {
  getSessionState,
  setSessionState,
  type MascotMood,
  type SettingsView,
  type SharedLens,
  type SkillLevel,
} from "../session/state.js";
import { sendSettings, type SettingsField } from "../session/ws-bridge.js";
import { emitIpc, sendIpcRequest } from "../ipc/client.js";
import { vmxLog } from "../debug-log.js";
import type {
  RecordingsDeleteAck,
  RecordingsListResult,
} from "../ipc/messages.js";
import { renderSettingsGroup } from "./components/group.js";
import {
  renderHotkeyCapture,
  type HotkeyCaptureHandle,
} from "./components/hotkey-capture.js";
import {
  renderLibraryPanel,
  type LibraryPanelHandle,
} from "./components/library-panel.js";
import {
  renderProfilePanel,
  type ProfilePanelHandle,
} from "./components/profile-panel.js";
import {
  renderStalenessBanner,
  type StalenessBannerHandle,
} from "./components/staleness-banner.js";
import {
  renderRecordingBrowser,
  type RecordingBrowserHandle,
} from "./components/recording-browser.js";
import { mountCitationDiagnostics } from "./components/citation-diagnostics.js";
import {
  renderRetentionSlider,
  type RetentionSliderHandle,
} from "./components/retention-slider.js";
import { renderConfirmDialog } from "./components/confirm-dialog.js";
import { BrainGroup } from "./components/brain-group.js";
import { HelpGroup } from "./components/help-group.js";
import { LearnGroup } from "./components/learn-group.js";
import { MascotGroup } from "./components/mascot-group.js";
import { PerformanceGroup } from "./components/performance-group.js";
import { djLabel } from "../shell/dj-vocab.js";
import {
  closeSettingsState,
  getSettingsUIState,
  openSettingsState,
  setRecordingsSlice,
  setSettingsUIState,
  subscribeSettingsUI,
} from "./state.js";

const CSS = `
  .vmx-settings-backdrop {
    position: fixed;
    inset: 0;
    background:
      linear-gradient(90deg, rgba(0, 0, 0, 0.18), rgba(0, 0, 0, 0.58)),
      rgba(0, 0, 0, 0.52);
    backdrop-filter: blur(1.5px);
    -webkit-backdrop-filter: blur(1.5px);
    z-index: 39;
    opacity: 0;
    pointer-events: none;
    transition: opacity 180ms cubic-bezier(0.22, 1, 0.36, 1);
  }
  .vmx-settings-backdrop[data-open="true"] {
    opacity: 1;
    pointer-events: auto;
  }
  .vmx-settings-drawer {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: clamp(456px, 33vw, 520px);
    max-width: 100vw;
    z-index: 50;
    transform: translateX(100%);
    font-family: var(--type-body);
    /* Forged-Obsidian level-up (2026-05-30): a raised MACHINED slide-over, not
     * a flat dark rectangle. A warm-rose top sheen + a left-edge brand wash over
     * the warm void ladder, so the panel reads as milled obsidian catching the
     * room's one rose key-light as it floats over the live stage. */
    background:
      linear-gradient(115deg, var(--brand-06), transparent 30%),
      linear-gradient(180deg, rgba(255, 222, 242, 0.024), transparent 18%),
      linear-gradient(180deg, var(--void-15) 0%, var(--void-6) 58%, var(--void-0) 100%),
      var(--glass-1);
    backdrop-filter: var(--blur-glass);
    -webkit-backdrop-filter: var(--blur-glass);
    border-left: 1px solid var(--border-strong);
    /* The full lit stack: a machined top lip (--glass-top) + a left-edge milled
     * highlight, a faint rose inner-glow bleeding from the leading edge, a hard
     * floor shadow, and a real ambient drop so it sits ABOVE the stage. */
    box-shadow:
      inset 1px 0 0 var(--glass-top),
      inset 0 1px 0 var(--glass-top),
      inset 10px 0 24px var(--brand-03),
      inset 0 -1px 0 rgba(0, 0, 0, 0.80),
      -2px 0 0 rgba(255, 222, 242, 0.020),
      -20px 0 54px rgba(0, 0, 0, 0.58),
      -1px 0 0 rgba(255, 222, 242, 0.040);
    transition: transform 220ms cubic-bezier(0.22, 1, 0.36, 1);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .vmx-settings-drawer::before,
  .vmx-settings-drawer::after {
    content: "";
    position: absolute;
    inset: 0;
    z-index: 1;
    pointer-events: none;
  }
  .vmx-settings-drawer::before {
    background:
      linear-gradient(90deg, rgba(255, 165, 223, 0.055), transparent 20%),
      linear-gradient(180deg, rgba(214, 207, 199, 0.024), transparent 22%);
    opacity: 0.14;
    mask-image: linear-gradient(180deg, transparent 0%, black 10%, black 88%, transparent 100%);
  }
  .vmx-settings-drawer::after {
    left: 0;
    right: auto;
    width: 1px;
    background: linear-gradient(180deg, transparent, var(--brand) 44%, var(--brand-40) 62%, transparent);
    box-shadow: 0 0 10px var(--brand-12);
    opacity: 0.46;
  }
  /* z-index discipline kept as a defensive baseline even after the
   * .border-anim removal (2026-05-19) so any future glass overlay in
   * the drawer composites below header + body without us re-discovering
   * the stacking issue. */
  .vmx-settings-drawer > * {
    position: relative;
    z-index: 5;
  }
  .vmx-settings-drawer[data-open="true"] {
    transform: translateX(0);
  }
  .vmx-settings-drawer__header {
    position: relative;
    height: 52px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 22px;
    border-bottom: 1px solid var(--border-default);
    /* Lit header — a machined cap on the slide-over: a warm-rose top sheen over
     * a darker base, a top lip catching light, a hard floor, and a real ambient
     * drop so the header reads as a raised crown above the scrolling body. */
    background:
      linear-gradient(180deg, rgba(255, 222, 242, 0.040), transparent 52%),
      linear-gradient(180deg, var(--void-12) 0%, var(--void-5) 100%),
      rgba(0, 0, 0, 0.42);
    box-shadow:
      inset 0 1px 0 var(--glass-top),
      inset 0 -1px 0 rgba(0, 0, 0, 0.74),
      0 10px 24px rgba(0, 0, 0, 0.26);
  }
  /* The lit under-rule — a rose ignition seam beneath the header, brightest at
   * the leading edge, so the header crown reads as actively lit. */
  .vmx-settings-drawer__header::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    bottom: -1px;
    height: 1px;
    pointer-events: none;
    background: linear-gradient(90deg, var(--brand-40) 0%, var(--brand-12) 14%, transparent 56%);
    box-shadow: 0 0 12px var(--brand-08);
  }
  .vmx-settings-drawer__header::before {
    content: "";
    position: absolute;
    left: var(--sp-5);
    right: var(--sp-5);
    top: 50%;
    height: 5px;
    transform: translateY(-50%);
    pointer-events: none;
    background:
      radial-gradient(circle at left center, rgba(214, 207, 199, 0.28) 0 2px, transparent 2.5px),
      radial-gradient(circle at right center, rgba(214, 207, 199, 0.18) 0 2px, transparent 2.5px);
    opacity: 0;
  }
  /* 2026-05-19 /impeccable critique round 3: dropped heading from
   * 14px Saira 700 to 11px Saira 600 + 0.22em tracking — the drawer
   * body label vocabulary is 9-11px throughout (every group header,
   * every row label) and the SETTINGS title was 50% larger than its
   * neighbors. The new size lands as a peer label, not as a
   * separately-styled "page title." */
  .vmx-settings-drawer__title {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 11px;
    padding-left: 13px;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 13px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--text-primary);
    line-height: 1;
    text-shadow: var(--text-emboss);
  }
  /* A lit brand tick anchoring the title — the panel's heartbeat, the single
   * decisive sign-of-life on the header crown (mock §panel-title::before). */
  .vmx-settings-drawer__title::before {
    content: "";
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--brand);
    box-shadow: 0 0 6px var(--brand-50);
  }
  /* 2026-05-19 /impeccable critique fix round 2: drawer title amber
   * dot dropped entirely. When the drawer is open the user already
   * sees the gear button in amber-active state in the titlebar plus
   * every group header in the drawer — adding another amber dot at
   * the drawer title was the third concurrent amber signal in a
   * panel that should carry one. The "SETTINGS" caps + tracking is
   * enough heading affordance. */
  .vmx-settings-drawer__close {
    width: 30px;
    height: 30px;
    border-radius: var(--rad-sm);
    /* Tactile machined key — a milled cap with a top lip + recessed floor. */
    background:
      linear-gradient(180deg, rgba(255, 222, 242, 0.05), transparent 50%),
      linear-gradient(180deg, var(--void-15) 0%, var(--void-5) 100%);
    border: 1px solid var(--border-default);
    color: var(--text-tertiary);
    line-height: 1;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: color var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out,
                background var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out,
                transform var(--motion-snap) ease-out;
    box-shadow:
      inset 0 1px 0 var(--glass-top),
      inset 0 -1px 0 rgba(0, 0, 0, 0.55),
      0 2px 6px rgba(0, 0, 0, 0.30);
  }
  .vmx-settings-drawer__close:active {
    transform: scale(0.94);
    box-shadow:
      inset 0 2px 5px rgba(0, 0, 0, 0.50),
      inset 0 -1px 0 rgba(255, 222, 242, 0.04);
  }
  .vmx-settings-drawer__close svg {
    width: 14px;
    height: 14px;
    stroke: currentColor;
    stroke-width: 1.5;
    stroke-linecap: round;
    fill: none;
  }
  /* Phase 43 / Plan 43-03 — VIS-02 hover-glow sweep. Appended --glow-faint
   * comma-separated onto the existing inset treatment so the close affordance
   * acknowledges cursor without overshouting the SETTINGS title's amber dot
   * (the gear button restraint precedent from session/titlebar critique). */
  .vmx-settings-drawer__close:hover,
  .vmx-settings-drawer__close:focus-visible {
    color: var(--amber);
    border-color: var(--amber-40);
    background: rgba(255, 165, 223, 0.06);
    box-shadow: var(--glow-faint);
  }
  .vmx-settings-drawer__body {
    flex: 1;
    overflow-y: auto;
    padding: 18px 20px 34px;
    display: flex;
    flex-direction: column;
    gap: 0;
    position: relative;
    /* The body floor sits in shadow under the lit header crown — a faint top
     * recess so the scroll region reads as the recessed channel the lit
     * recessed group modules seat into. */
    background:
      linear-gradient(180deg, rgba(0, 0, 0, 0.22) 0%, transparent 5%);
  }
  .vmx-settings-drawer__body::-webkit-scrollbar { width: 6px; }
  .vmx-settings-drawer__body::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.3); }
  .vmx-settings-drawer__body::-webkit-scrollbar-thumb {
    background: var(--silk-22);
    border-radius: 3px;
  }
  .vmx-settings-drawer__body::-webkit-scrollbar-thumb:hover { background: var(--amber-40); }
  .vmx-settings-drawer__btn {
    position: relative;
    overflow: hidden;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    padding: 11px var(--sp-4);
    /* Lit primary (the recipe's signature switch): a rose-washed fill, a brand
     * edge, an inset top-highlight + rose bleed + soft drop, brand ink. The one
     * lit affordance in the CALIBRATION group — the RE-RUN action. */
    background: linear-gradient(180deg, var(--brand-16) 0%, var(--brand-04) 100%);
    border: 1px solid var(--brand-40);
    color: var(--brand);
    border-radius: var(--rad-sm);
    cursor: pointer;
    line-height: 1;
    text-shadow: var(--text-emboss);
    box-shadow:
      inset 0 1px 0 rgba(255, 222, 242, 0.10),
      inset 0 -1px 0 rgba(0, 0, 0, 0.40),
      inset 0 0 16px var(--brand-06),
      0 1px 0 rgba(255, 255, 255, 0.03),
      0 6px 16px rgba(0, 0, 0, 0.30);
    transition: color var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out,
                background var(--motion-snap) ease-out,
                filter var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out;
  }
  /* Top specular line — light skating across the machined cap of the button. */
  .vmx-settings-drawer__btn::before {
    content: "";
    position: absolute;
    top: 0;
    left: 10%;
    right: 10%;
    height: 1px;
    pointer-events: none;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
  }
  /* VIS-02 — Plan 43-03. --glow-faint appended comma-separated; preserves
   * the inset amber bleed (mock §02 .btn.on body) while applying the
   * outer faint glow uniformly across every drawer affordance (Recheck,
   * mascot-group buttons, library-panel actions). */
  .vmx-settings-drawer__btn:hover,
  .vmx-settings-drawer__btn:focus-visible {
    color: var(--brand-glow);
    border-color: var(--brand);
    background: linear-gradient(180deg, var(--brand-22) 0%, var(--brand-06) 100%);
    filter: brightness(1.08);
    box-shadow:
      inset 0 1px 0 rgba(255, 222, 242, 0.12),
      inset 0 -1px 0 rgba(0, 0, 0, 0.40),
      inset 0 0 16px var(--brand-10),
      var(--glow-soft);
  }
  .vmx-settings-drawer__btn:active {
    filter: brightness(0.96);
    box-shadow:
      inset 0 2px 5px rgba(0, 0, 0, 0.50),
      inset 0 -1px 0 rgba(255, 222, 242, 0.04);
  }
  /* Surface-wide VIS-02 contract — broad interactive union; comma-
   * separated --glow-faint so deeper child components that already
   * register their own hover treatments (mascot-group toggle rows,
   * performance-group toggle, library-panel rows, retention slider
   * thumb, hotkey-capture pad) inherit the uniform tactility signal
   * without having to fork their own rules. */
  .vmx-settings-drawer button:not([disabled]),
  .vmx-settings-drawer [role="button"]:not([aria-disabled="true"]),
  .vmx-settings-drawer [data-interactive] {
    transition: box-shadow var(--motion-snap) ease-out;
  }
  .vmx-settings-drawer button:not([disabled]):hover,
  .vmx-settings-drawer button:not([disabled]):focus-visible,
  .vmx-settings-drawer [role="button"]:not([aria-disabled="true"]):hover,
  .vmx-settings-drawer [role="button"]:not([aria-disabled="true"]):focus-visible,
  .vmx-settings-drawer [data-interactive]:hover,
  .vmx-settings-drawer [data-interactive]:focus-visible {
    box-shadow:
      inset 0 1px 0 rgba(255, 251, 244, 0.040),
      var(--glow-faint);
  }
  /* P1-b finding #3 — DEMOTE the blanket glow, reserve a brighter signal for
   * the ACTIVE control. The faint-glow-on-everything-hovered rule above is the
   * OPPOSITE of 20/80: nothing reads as "the selected one." Here the currently-
   * active mode segment and the open/focused picker row carry the ONLY soft
   * outer halo in the drawer, so the eye lands on where the surface actually IS
   * right now (hover stays one rung lower at --glow-faint).
   *
   * Why filter:drop-shadow(currentColor) instead of box-shadow:--glow-soft:
   *   1. COMPOSES — rocker.ts / picker.ts already own a multi-layer INSET
   *      box-shadow on these active states; a box-shadow rule from here would
   *      clobber that whole recess. filter is an independent layer, so the
   *      inset bezel stays intact and we only ADD the outer halo.
   *   2. NO new accent — currentColor inherits the active tile's own ink: amber
   *      for the picker, mood-color (magenta/green/blue) for the interaction
   *      rocker. So we don't paint amber over a mood-colored COACH/HYPE tile
   *      (that would break mood-color ownership + 20/80). Zero hardcoded color.
   * GPU-cheap (static two-stop drop-shadow, no animation), reduced-motion-safe
   * by construction (it's not motion). The "soft" radii mirror --glow-soft. */
  .vmx-settings-drawer .vmx-rocker__seg[data-active="true"],
  .vmx-settings-drawer .vmx-picker[data-open="true"] .vmx-picker__row {
    filter: none;
  }
  .vmx-settings-drawer__modal-slot {
    position: relative;
    z-index: 60;
  }
  .vmx-settings-drawer__label {
    display: inline-flex;
    align-items: center;
    gap: 9px;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--text-muted);
    line-height: 1;
    text-shadow: var(--text-emboss);
  }
  /* Leading hairline tick — the sub-label's quiet rose anchor, one rung below
   * the group header's solid dot (mock §panel-section-label::before). */
  .vmx-settings-drawer__label::before {
    content: "";
    width: 10px;
    height: 1px;
    flex-shrink: 0;
    background: var(--brand-22);
  }
`;

registerStyle("vmx-settings-drawer", CSS);

interface DrawerHandle {
  backdrop: HTMLElement;
  drawer: HTMLElement;
  modalSlot: HTMLElement;
  refresh: () => void;
  unsubscribe: () => void;
}

let mountedHandle: DrawerHandle | null = null;

// Mirrored from src/vibemix/voice_presets.py. These are real MOSS-TTS-Nano
// manifest voices; retired Gemini voice ids must not re-enter this picker.
// Grouped by gender/language: all 11 female voices + the two EN male voices.
const VOICE_OPTIONS = [
  // English male
  "Adam",
  "Nathan",
  // English female
  "Ava",
  "Bella",
  // Chinese female
  "Xiaoyu",
  "Yuewen",
  "Lingyu",
  // Japanese female
  "Soyo",
  "Mei",
  "Arisa",
  "Saki",
  "Mortis",
  "Umiri",
  "Anon",
] as const;

const GENRE_OPTIONS = [
  "house",
  "tech-house",
  "techno",
  "dnb",
  "trance",
  "psytrance",
  "hip-hop",
  "edm-generic",
] as const;

/** Mount the drawer + backdrop into the provided root. Idempotent — a
 *  second call returns the same handle without re-mounting. */
export function mountSettingsDrawer(root: HTMLElement): void {
  if (mountedHandle) return;

  const backdrop = document.createElement("div");
  backdrop.className = "vmx-settings-backdrop";
  backdrop.dataset.open = "false";
  backdrop.dataset.wire = "settings.backdrop";
  backdrop.addEventListener("click", () => {
    closeSettings();
  });

  const drawer = document.createElement("aside");
  drawer.className = "vmx-settings-drawer";
  drawer.dataset.open = "false";
  drawer.dataset.settling = "false";
  drawer.dataset.wire = "settings.drawer";
  drawer.setAttribute("aria-label", "settings");
  drawer.setAttribute("role", "complementary");

  // 2026-05-19 /impeccable critique fix: the drawer no longer mounts a
  // .border-anim sweep. DESIGN.md §5 restricts the 22s amber sweep to
  // the session deck only — opening the drawer over the session view
  // previously put two concurrent sweeps in the same field, violating
  // the One-Amber rule the v5 distill was built around.

  // Header
  const header = document.createElement("div");
  header.className = "vmx-settings-drawer__header";
  header.dataset.wire = "settings.header";
  const title = document.createElement("span");
  title.className = "vmx-settings-drawer__title";
  title.textContent = "SETTINGS";
  header.append(title);
  const close = document.createElement("button");
  close.type = "button";
  close.className = "vmx-settings-drawer__close";
  close.dataset.wire = "settings.close";
  close.setAttribute("aria-label", "close settings");
  close.innerHTML = '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M1 1L13 13M13 1L1 13"/></svg>';
  close.addEventListener("click", (e) => {
    e.preventDefault();
    closeSettings();
  });
  header.append(close);
  drawer.append(header);

  // Body — built inside refresh() so settings/state changes hydrate.
  const body = document.createElement("div");
  body.className = "vmx-settings-drawer__body";
  body.dataset.wire = "settings.body";
  drawer.append(body);

  const modalSlot = document.createElement("div");
  modalSlot.className = "vmx-settings-drawer__modal-slot";
  modalSlot.dataset.wire = "settings.modal-slot";

  root.append(backdrop);
  root.append(drawer);
  root.append(modalSlot);

  // Esc closes the drawer (only when open + no modal in flight).
  // 2026-05-19 /impeccable critique round 3: added cmd+. / ctrl+. as a
  // second close hotkey. cmd+. is the macOS-native "cancel/dismiss"
  // chord (used in TextEdit, Finder, system dialogs); a DJ familiar
  // with the platform reaches for it as a reflex. Esc keeps working.
  const onKey = (e: KeyboardEvent): void => {
    if (!getSettingsUIState().open) return;
    if (getSettingsUIState().confirmDialog) return;
    if (getSettingsUIState().hotkeyCaptureMode) return;
    if (e.key === "Escape") {
      e.preventDefault();
      closeSettings();
      return;
    }
    if (e.key === "." && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      closeSettings();
    }
  };
  document.addEventListener("keydown", onKey);

  const handle: DrawerHandle = {
    backdrop,
    drawer,
    modalSlot,
    refresh: () => {
      renderDrawerBody(body, modalSlot);
      const ui = getSettingsUIState();
      drawer.dataset.open = ui.open ? "true" : "false";
      backdrop.dataset.open = ui.open ? "true" : "false";
    },
    unsubscribe: () => {
      document.removeEventListener("keydown", onKey);
    },
  };

  // Subscribe to UI state changes — the drawer re-renders on every flip.
  const unsubUI = subscribeSettingsUI(() => handle.refresh());
  const origUnsub = handle.unsubscribe;
  handle.unsubscribe = () => {
    unsubUI();
    origUnsub();
  };

  mountedHandle = handle;

  // Initial paint.
  handle.refresh();
}

/** Slide the drawer in. Idempotent. */
export function openSettings(): void {
  if (!mountedHandle) return;
  vmxLog("[vmx:click]", "settings drawer open");
  const wasOpen = getSettingsUIState().open;
  openSettingsState();
  // Arm the titlebar gear (lights amber while the drawer is open — the
  // [data-active] style already exists in titlebar.ts but nothing flipped
  // it). Queried by class to avoid a session→settings import cycle.
  setGearArmed(true);
  // Re-render with fresh settings (sidecar may have broadcast updates
  // while the drawer was closed). The state subscriber already refreshed
  // closed→open; only force this when openSettings() is called idempotently.
  if (wasOpen) mountedHandle.refresh();
  // P1-b finding #2 — STAGE 2 trigger. Stage 1 is the drawer's 250ms
  // translateX (CSS, fires on the data-open flip above). We arm the group
  // micro-settle ONLY on this explicit open path (not on the subscribeSettingsUI
  // refreshes that fire mid-session), so the seat animation plays once per open
  // and never replays on a genre reload / recordings refresh. The flag is
  // cleared after the longest staggered settle has finished. group.ts gates the
  // actual animation behind prefers-reduced-motion: no-preference, so this flag
  // is a no-op visual for reduced-motion users.
  armDrawerSettle();
  // Phase 15 Plan 05 — fire the recordings.list IPC on drawer open,
  // debounced 1s to absorb flickering re-opens (Plan §Task 2 must-haves).
  const now = Date.now();
  if (now - lastLoadAt > LIST_DEBOUNCE_MS) {
    lastLoadAt = now;
    void loadRecordings();
  }
}

// P1-b finding #2 — settle-flag lifecycle. Total budget = stage-1 land (250ms)
// + last stagger delay (~418ms) + settle duration (120ms) ≈ 540ms; clear at
// 560ms with margin. A re-open inside that window resets the timer so the flag
// always clears.
let settleClearTimer: ReturnType<typeof setTimeout> | null = null;
function armDrawerSettle(): void {
  if (!mountedHandle) return;
  const { drawer } = mountedHandle;
  drawer.dataset.settling = "true";
  if (settleClearTimer !== null) clearTimeout(settleClearTimer);
  settleClearTimer = setTimeout(() => {
    drawer.dataset.settling = "false";
    settleClearTimer = null;
  }, 560);
}

/** Slide the drawer out. Idempotent. */
export function closeSettings(): void {
  if (!mountedHandle) return;
  vmxLog("[vmx:click]", "settings drawer close");
  disposeProfilePanelHandle();
  closeSettingsState();
  setGearArmed(false);
}

/** Remove the singleton drawer from the DOM and drop its global listeners.
 *
 * Route/session teardown calls this so the body overlay, document keydown
 * listener, picker resources, and settling timer do not survive a route bounce
 * or dev mock restart. */
export function unmountSettingsDrawer(): void {
  if (settleClearTimer !== null) {
    clearTimeout(settleClearTimer);
    settleClearTimer = null;
  }

  setGearArmed(false);

  const handle = mountedHandle;
  mountedHandle = null;

  if (handle) {
    bodyRenderId += 1;
    disposeDrawerBodyResources();
    disposeProfilePanelHandle();
    disposeStalenessBannerHandle();
    handle.unsubscribe();
    try {
      handle.backdrop.remove();
      handle.drawer.remove();
      handle.modalSlot.remove();
    } catch {
      /* DOM already gone */
    }
  }

  setSettingsUIState({
    open: false,
    hotkeyCaptureMode: false,
    confirmDialog: null,
  });
  lastLoadAt = 0;
}

/** Reflect drawer open/close on the titlebar gear so it lights amber while
 *  the drawer is open. Queried by class (not imported) to keep the
 *  session/settings module boundary clean; no-op if the titlebar isn't
 *  mounted (e.g. a unit test that mounts the drawer in isolation). */
function setGearArmed(armed: boolean): void {
  const gear = document.querySelector<HTMLElement>(".vmx-titlebar__settings");
  if (gear) gear.dataset.active = armed ? "true" : "false";
}

/** Test-only — tear down the singleton so a fresh vitest case can mount. */
export function _resetDrawerForTests(): void {
  unmountSettingsDrawer();
}

// ---------------------------------------------------------------------------
// Body composition — full rebuild on each refresh(). The drawer body is
// small (<~30 DOM nodes); rebuilding sidesteps the diffing complexity that
// the live-session components own. The render-loop is unaffected.
// ---------------------------------------------------------------------------

let hotkeyHandle: HotkeyCaptureHandle | null = null;
let retentionHandle: RetentionSliderHandle | null = null;
let profilePanelHandle: ProfilePanelHandle | null = null;
let profilePanelLoadedThisOpen = false;
let stalenessBannerHandle: StalenessBannerHandle | null = null;
let libraryPanelHandle: LibraryPanelHandle | null = null;
// Phase 15 Plan 05 — Recording browser handle persists across refreshes
// so the loadRecordings() async resolver can push results into the live
// component without rebuilding it on every refresh tick.
let recordingBrowserHandle: RecordingBrowserHandle | null = null;
let bodyRenderId = 0;
let bodyDisposers: Array<() => void> = [];
// Debounce window for drawer-open list refresh (Plan 15-05 §Task 2): a
// flickering re-open within 1s reuses the in-memory slice instead of
// firing a new recordings.list IPC.
let lastLoadAt = 0;
const LIST_DEBOUNCE_MS = 1000;

const SETTINGS_MODES: readonly SettingsView["mode"][] = ["hype", "coach"];
const SETTINGS_SKILLS: readonly SkillLevel[] = ["beginner", "intermediate", "pro"];
const SETTINGS_LENSES: readonly SharedLens[] = ["hype", "critique", "tutor"];
const SETTINGS_OUTPUT_PROFILES: readonly SettingsView["output_profile"][] = ["hp", "spk"];
const SETTINGS_MOODS: readonly MascotMood[] = ["hype-man", "teacher", "coach"];

const LENS_LABELS: Record<SharedLens, string> = {
  hype: "Hype",
  critique: "Coach",
  tutor: "Teach",
};

const SKILL_LABELS: Record<SkillLevel, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  pro: "Pro",
};

const OUTPUT_PROFILE_LABELS: Record<SettingsView["output_profile"], string> = {
  hp: "Headphones",
  spk: "Speakers",
};

function formatOutputDeviceLabel(id: string | null): string {
  if (!id) return "Auto device";
  if (/^\d+$/.test(id)) return `Device ${id}`;
  return id;
}

function oneOf<T extends string>(
  values: readonly T[],
  value: unknown,
): value is T {
  return typeof value === "string" && (values as readonly string[]).includes(value);
}

function applySettingsOptimistic(
  field: SettingsField,
  value: string | number | boolean | null,
): void {
  const state = getSessionState();
  const next: SettingsView = { ...state.settings };
  let changed = false;

  const set = <K extends keyof SettingsView>(key: K, nextValue: SettingsView[K]): void => {
    if (Object.is(next[key], nextValue)) return;
    next[key] = nextValue;
    changed = true;
  };

  switch (field) {
    case "voice":
      if (typeof value === "string") set("voice", value);
      break;
    case "mode":
      if (oneOf(SETTINGS_MODES, value)) set("mode", value);
      break;
    case "genre":
      if (typeof value === "string") set("genre", value);
      break;
    case "output_device_id":
      if (typeof value === "string" || value === null) set("output_device_id", value);
      break;
    case "output_profile":
      if (oneOf(SETTINGS_OUTPUT_PROFILES, value)) set("output_profile", value);
      break;
    case "retention_days":
      if (typeof value === "number" && Number.isFinite(value)) set("retention_days", value);
      break;
    case "push_to_mute_hotkey":
      if (typeof value === "string") set("push_to_mute_hotkey", value);
      break;
    case "mood":
      if (oneOf(SETTINGS_MOODS, value)) set("mood", value);
      break;
    case "click_through":
      if (typeof value === "boolean") set("click_through", value);
      break;
    case "lighter_blur":
      if (typeof value === "boolean") set("lighter_blur", value);
      break;
    case "skill":
      if (oneOf(SETTINGS_SKILLS, value)) set("skill", value);
      break;
    case "lens":
      if (oneOf(SETTINGS_LENSES, value)) set("lens", value);
      break;
    case "learn.headphone_device_index":
      if (
        value === null ||
        (typeof value === "number" && Number.isInteger(value) && value >= 0)
      ) {
        set("learn_headphone_device_index", value);
      }
      break;
  }

  if (changed) setSessionState({ settings: next });
}

function rememberPicker(el: HTMLElement): HTMLElement {
  bodyDisposers.push(() => disposePicker(el));
  return el;
}

function withWire<T extends HTMLElement>(el: T, wire: string): T {
  el.dataset.wire = wire;
  return el;
}

function disposeDrawerBodyResources(): void {
  for (const dispose of bodyDisposers.splice(0)) {
    try {
      dispose();
    } catch {
      /* ignore */
    }
  }
  hotkeyHandle = null;
  retentionHandle = null;
  recordingBrowserHandle = null;
  libraryPanelHandle = null;
}

function disposeProfilePanelHandle(): void {
  if (profilePanelHandle) {
    profilePanelHandle.dispose();
    profilePanelHandle = null;
  }
  profilePanelLoadedThisOpen = false;
}

function disposeStalenessBannerHandle(): void {
  if (stalenessBannerHandle) {
    stalenessBannerHandle.dispose();
    stalenessBannerHandle = null;
  }
  libraryPanelHandle = null;
}

function beginDrawerBodyRender(): number {
  bodyRenderId += 1;
  disposeDrawerBodyResources();
  return bodyRenderId;
}

function renderDrawerBody(body: HTMLElement, modalSlot: HTMLElement): void {
  const renderId = beginDrawerBodyRender();
  body.replaceChildren();

  const settings = getSessionState().settings;
  const ui = getSettingsUIState();

  // --- PERSONA --------------------------------------------------------------
  const personaBody = document.createElement("div");
  personaBody.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-4);";

  // Voice picker
  const voicePicker = rememberPicker(
    renderPicker({
      label: "VOICE",
      value: settings.voice,
      avatar: true,
      options: VOICE_OPTIONS.map((v) => ({ id: v, label: v })),
      onChange: (id) => {
        void sendSettingsField("voice", id);
      },
    }),
  );
  personaBody.append(withWire(voicePicker, "settings.persona.voice"));

  const lensWrap = document.createElement("div");
  lensWrap.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-2);";
  lensWrap.dataset.wire = "settings.persona.lens";
  const lensLabel = document.createElement("div");
  lensLabel.className = "vmx-settings-drawer__label";
  lensLabel.textContent = "MODE";
  lensWrap.append(lensLabel);
  lensWrap.append(
    renderRocker({
      ariaLabel: "persona mode",
      options: [
        { id: "hype", label: LENS_LABELS.hype },
        { id: "critique", label: LENS_LABELS.critique },
        { id: "tutor", label: LENS_LABELS.tutor },
      ],
      active: settings.lens,
      variant: "rocker",
      onChange: (id) => {
        void sendSettingsField("lens", id);
      },
    }),
  );
  personaBody.append(lensWrap);

  // Genre dropdown with reload overlay
  const genreWrap = document.createElement("div");
  genreWrap.className = "vmx-settings-drawer__genre-wrap";
  genreWrap.dataset.wire = "settings.persona.genre";
  genreWrap.append(
    rememberPicker(
      renderPicker({
        label: "GENRE",
        value: settings.genre,
        autoPill: false,
        options: GENRE_OPTIONS.map((g) => ({ id: g, label: g })),
        onChange: (id) => {
          void sendSettingsField("genre", id);
        },
      }),
    ),
  );
  personaBody.append(genreWrap);

  // Skill rocker (2026-05-25) — persona level (beginner/intermediate/pro).
  // Migrated off the live deck: the deck is now a read-only glanceable
  // mirror and the drawer owns every persona write. Sends the wire enum
  // verbatim; the sidecar echoes ipc.settings.state which re-syncs the
  // deck readout.
  const skillRocker = renderRocker({
    ariaLabel: "skill level",
    options: [
      { id: "beginner", label: SKILL_LABELS.beginner },
      { id: "intermediate", label: SKILL_LABELS.intermediate },
      { id: "pro", label: SKILL_LABELS.pro },
    ],
    active: settings.skill,
    variant: "rocker",
    onChange: (id) => {
      void sendSettingsField("skill", id);
    },
  });
  personaBody.append(withWire(skillRocker, "settings.persona.skill"));

  body.append(
    renderSettingsGroup({
      header: "PERSONA",
      badge: "VOICE",
      children: personaBody,
    }),
  );

  // --- BRAIN ----------------------------------------------------------------
  // Direct/proxy brain controls include a BYO Gemini-key field. Keep them for
  // local support builds only; shipped Settings uses the default hosted path
  // and does not ask DJs for a Google key.
  if (import.meta.env.DEV) {
    body.append(BrainGroup());
  }

  // --- OUTPUT ---------------------------------------------------------------
  const outputBody = document.createElement("div");
  outputBody.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-4);";
  outputBody.append(
    rememberPicker(
      renderPicker({
        label: "DEVICE",
        value: formatOutputDeviceLabel(settings.output_device_id),
        autoPill: !settings.output_device_id,
        options: [
          { id: "auto", label: "Auto device", sub: "system default" },
          // Real device list is populated by the sidecar at boot and lives
          // off ipc.settings.state; the picker here lets the user fall
          // back to "auto" or pick a known id. v1 ships with a "auto"
          // default — Phase 15 expands.
          ...(settings.output_device_id
            ? [
                {
                  id: settings.output_device_id,
                  label: formatOutputDeviceLabel(settings.output_device_id),
                  sub: settings.output_device_id,
                },
              ]
            : []),
        ],
        onChange: (id) => {
          void sendSettingsField(
            "output_device_id",
            id === "auto" ? null : id,
          );
        },
      }),
    ),
  );
  outputBody.append(
    renderRocker({
      ariaLabel: "output profile",
      options: [
        { id: "hp", label: OUTPUT_PROFILE_LABELS.hp },
        { id: "spk", label: OUTPUT_PROFILE_LABELS.spk },
      ],
      active: settings.output_profile,
      variant: "rocker",
      onChange: (id) => {
        void sendSettingsField("output_profile", id);
      },
    }),
  );
  body.append(
    renderSettingsGroup({
      header: "OUTPUT",
      children: outputBody,
    }),
  );

  // --- HOTKEY ---------------------------------------------------------------
  const hotkeyBody = document.createElement("div");
  hotkeyBody.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-2);";
  const hotkeyLabel = document.createElement("div");
  hotkeyLabel.className = "vmx-settings-drawer__label";
  hotkeyLabel.textContent = "PUSH-TO-MUTE";
  hotkeyBody.append(hotkeyLabel);

  hotkeyHandle = renderHotkeyCapture({
    value: settings.push_to_mute_hotkey,
    onCapture: (combo) => {
      setSettingsUIState({ hotkeyCaptureMode: false });
      void applyHotkeyCapture(combo);
    },
  });
  hotkeyBody.append(hotkeyHandle.root);
  body.append(
    renderSettingsGroup({
      header: "HOTKEY",
      children: hotkeyBody,
    }),
  );

  // --- RECORDING ------------------------------------------------------------
  const recordingBody = document.createElement("div");
  recordingBody.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-2);";
  const recordingLabel = document.createElement("div");
  recordingLabel.className = "vmx-settings-drawer__label";
  recordingLabel.textContent = "RETENTION";
  recordingBody.append(recordingLabel);

  retentionHandle = renderRetentionSlider({
    value: settings.retention_days,
    onChange: (days) => {
      void sendSettingsField("retention_days", days);
    },
  });
  recordingBody.append(retentionHandle.root);

  // Phase 15 Plan 05 — Recording browser mounts BELOW the retention slider
  // (UI-SPEC §Layout: order is locked retention → disk usage line →
  // browser). The browser component owns the silkscreen disk-usage line +
  // virtualized session rows. The drawer wires:
  //   - On drawer open: fire `ipc.recordings.list` (debounced 1s) and
  //     populate the browser with sessions + usage.
  //   - On `ipc.recordings.usage` push (subscriber in ws-bridge.ts): the
  //     slice mutates → drawer refresh runs → we call setUsage() here.
  //   - On delete confirm: fire `ipc.recordings.delete` and optimistically
  //     remove the row from the slice.
  const recSlice = ui.recordings;
  const initialUsage = recSlice.loading
    ? { sessions: recSlice.usage.sessions, bytes_total: -1 }
    : recSlice.error !== null
    ? { sessions: recSlice.usage.sessions, bytes_total: -2 }
    : recSlice.usage;
  const recBrowser = renderRecordingBrowser({
    initialSessions: recSlice.sessions,
    initialUsage,
    onReplay: () => {
      // Row expansion is owned by the row component (audio + transcript
      // are local — no IPC dispatched here per UI-SPEC §Component
      // Contracts onReplay note).
    },
    onDelete: (session_dir, _timestamp) => {
      void onDeleteRecording(session_dir);
    },
  });
  recordingBrowserHandle = recBrowser;
  bodyDisposers.push(() => recBrowser.dispose());
  recordingBody.append(recBrowser.root);

  body.append(
    renderSettingsGroup({
      header: "RECORDING",
      children: recordingBody,
    }),
  );

  // --- LIBRARY (Phase 28 Plan 06 + 07) -------------------------------------
  // Plan 07: 30-day staleness banner sits at the top.
  // Plan 06: drag-drop XML importer below.
  const libraryBody = document.createElement("div");
  libraryBody.style.cssText =
    "display:flex; flex-direction:column; gap: var(--sp-2);";
  if (!stalenessBannerHandle) {
    stalenessBannerHandle = renderStalenessBanner({
      onRefresh: async (path, sourceKind) => {
        if (sourceKind === "folder") {
          if (libraryPanelHandle) {
            await libraryPanelHandle.beginFolderReindex();
            return;
          }
          await emitIpc("ipc.library.staleness_action", {
            action: "reindex_folder",
            schema_version: "1",
          });
          return;
        }
        if (libraryPanelHandle) await libraryPanelHandle.beginImport(path);
      },
    });
  }
  libraryBody.append(stalenessBannerHandle.element);
  // Library panel is async; mount a placeholder + swap when ready.
  const libraryPanelSlot = document.createElement("div");
  libraryBody.append(libraryPanelSlot);
  void renderLibraryPanel().then((handle) => {
    if (renderId !== bodyRenderId || !libraryPanelSlot.isConnected) {
      handle.dispose();
      return;
    }
    libraryPanelHandle = handle;
    bodyDisposers.push(() => {
      if (libraryPanelHandle === handle) libraryPanelHandle = null;
      handle.dispose();
    });
    libraryPanelSlot.replaceWith(handle.element);
  }).catch((err: unknown) => {
    if (renderId !== bodyRenderId || !libraryPanelSlot.isConnected) return;
    const fallback = document.createElement("div");
    fallback.className = "vmx-library-status";
    fallback.setAttribute("role", "status");
    fallback.textContent = `Library panel unavailable: ${String(err)}`;
    libraryPanelSlot.replaceWith(fallback);
  });
  body.append(
    renderSettingsGroup({
      header: "LIBRARY",
      children: libraryBody,
    }),
  );

  // --- INTERNAL TOOLS -------------------------------------------------------
  // Profile, citation diagnostics, wizard rerun, and learn reset are support
  // and tuning tools. Keep them available in dev while shipped builds strip the
  // whole cluster through Vite's import.meta.env.DEV replacement.
  if (import.meta.env.DEV) {
    // --- PROFILE (Phase 32 / PROFILE-07) -----------------------------------
    if (!profilePanelHandle) {
      profilePanelHandle = renderProfilePanel({ autoload: false });
    }
    if (ui.open && !profilePanelLoadedThisOpen) {
      profilePanelLoadedThisOpen = true;
      void profilePanelHandle.refresh();
    }
    body.append(
      renderSettingsGroup({
        header: "PROFILE",
        children: profilePanelHandle.element,
      }),
    );

    // --- DIAGNOSTICS -------------------------------------------------------
    // Anti-slop citation telemetry (slop ratio / stripped rate / bypass) is a
    // dev instrument, not a paying-user control.
    const citationDiagnostics = mountCitationDiagnostics();
    bodyDisposers.push(() => citationDiagnostics.dispose());
    body.append(
      renderSettingsGroup({
        header: "DIAGNOSTICS",
        badge: "LIVE",
        children: citationDiagnostics.root,
      }),
    );

    // --- CALIBRATION --------------------------------------------------------
    const calibrationBody = document.createElement("div");
    calibrationBody.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-2);";
    const reRunBtn = document.createElement("button");
    reRunBtn.type = "button";
    reRunBtn.className = "vmx-settings-drawer__btn";
    reRunBtn.textContent = "↻ RE-RUN WIZARD";
    reRunBtn.addEventListener("click", (e) => {
      e.preventDefault();
      openConfirmReRun(modalSlot);
    });
    calibrationBody.append(reRunBtn);
    body.append(
      renderSettingsGroup({
        header: "CALIBRATION",
        children: calibrationBody,
      }),
    );

    // --- LEARN (Phase 92 / LESSON-03) --------------------------------------
    // Reset Learn progress is destructive recovery, not a normal Settings row.
    body.append(LearnGroup());
  }

  // --- MASCOT (Phase 13-03) -------------------------------------------------
  // Appended per Plan 13-03 §Task 2; per Plan 14-04 the new PERFORMANCE
  // group sits AFTER MASCOT. Internal dev tools mount just before MASCOT when
  // import.meta.env.DEV is true.
  body.append(MascotGroup());

  // --- PERFORMANCE (Phase 14-04) -------------------------------------------
  // Single-row group: "LIGHTER BLUR" toggle wiring the data-blur-perf
  // attribute on <html>. The toggle persists via settings.set { field:
  // "lighter_blur", value: <bool> } through SettingsApplier; the boot
  // read in main.ts re-applies it on next launch.
  body.append(PerformanceGroup(settings.lighter_blur));

  // --- HELP (impeccable Wave 6 — closes H10 "help & documentation") --------
  // Last group. Shortcuts link + audio-routing checklist + GitHub link +
  // About row. The shortcuts link mounts the same overlay as the `?` key.
  // GitHub URL isn't yet in the Tauri capability allowlist — see the TODO
  // in help-group.ts.
  body.append(HelpGroup());

  // --- Modal slot rebuild ---------------------------------------------------
  renderModalSlot(modalSlot);
}

function renderModalSlot(modalSlot: HTMLElement): void {
  modalSlot.replaceChildren();
  const ui = getSettingsUIState();
  if (ui.confirmDialog === "re-run-calibration") {
    const dialog = renderConfirmDialog({
      heading: "RESTART CALIBRATION?",
      body: "Your live session will pause while the wizard runs.",
      confirmLabel: "RESTART",
      cancelLabel: "CANCEL",
      onCancel: () => {
        setSettingsUIState({ confirmDialog: null });
      },
      onConfirm: () => {
        setSettingsUIState({ confirmDialog: null });
        void emitWizardStart();
      },
    });
    modalSlot.append(dialog);
  }
}

function openConfirmReRun(_modalSlot: HTMLElement): void {
  setSettingsUIState({ confirmDialog: "re-run-calibration" });
}

async function emitWizardStart(): Promise<void> {
  try {
    await emitIpc("ipc.wizard.start", {});
    // Close the drawer; the shell's session router will tear the
    // session down and mount the wizard when the sidecar acks.
    closeSettings();
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("[settings] ipc.wizard.start failed:", err);
  }
}

async function applyHotkeyCapture(combo: string): Promise<void> {
  try {
    // 1) Tell the sidecar to persist via ipc.settings.set.
    await sendSettingsField("push_to_mute_hotkey", combo);
    // 2) Tell Rust to re-register the global shortcut.
    await invoke("rebind_hotkey", { newCombo: combo });
    hotkeyHandle?.setError(null);
  } catch (err) {
    const msg =
      err instanceof Error ? err.message : String(err ?? "rebind failed");
    hotkeyHandle?.setError(msg);
  }
}

async function sendSettingsField(
  field: SettingsField,
  value: string | number | boolean | null,
): Promise<void> {
  // WR-03 in 14-REVIEW.md — value union widened to match ws-bridge's
  // sendSettings (which was widened to include boolean for Plan
  // 14-04's lighter_blur). Without this, any future drawer-side toggle
  // wanting to flow through this try/catch wrapper would need a type
  // assertion to pass a boolean.
  applySettingsOptimistic(field, value);
  try {
    await sendSettings(field, value);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn(`[settings] sendSettings(${field}) failed:`, err);
  }
}

// ---------------------------------------------------------------------------
// Phase 15 Plan 05 — Recording browser IPC wiring.
// ---------------------------------------------------------------------------

/** Fire `ipc.recordings.list` on drawer open. Sentinel-driven loading +
 *  error states: pushes `bytes_total: -1` to the browser usage line to
 *  render `RECORDINGS · LOADING…`; on failure pushes `bytes_total: -2` to
 *  render `RECORDINGS · UNAVAILABLE` (Plan 15-04 sentinel contract).
 *
 *  Exported for vitest coverage; the production caller is `openSettings()`. */
export async function loadRecordings(): Promise<void> {
  // Mark loading + flip the usage line to the LOADING sentinel.
  setRecordingsSlice({ loading: true, error: null });
  if (recordingBrowserHandle) {
    recordingBrowserHandle.setUsage({
      sessions: getSettingsUIState().recordings.usage.sessions,
      bytes_total: -1,
    });
  }
  try {
    const reply = await sendIpcRequest<RecordingsListResult>(
      "ipc.recordings.list",
      {},
      "ipc.recordings.list_result",
    );
    const sessions = reply.payload.sessions.map((s) => ({
      session_dir: s.session_dir,
      started_at_iso: s.started_at_iso,
      duration_s: s.duration_s,
      event_count: s.event_count,
      bytes_total: s.bytes_total,
      crashed: s.crashed,
    }));
    const usage = {
      sessions: sessions.length,
      bytes_total: reply.payload.bytes_total,
    };
    setRecordingsSlice({
      sessions,
      usage,
      loading: false,
      error: null,
    });
    if (recordingBrowserHandle) {
      recordingBrowserHandle.setSessions(sessions);
      recordingBrowserHandle.setUsage(usage);
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    setRecordingsSlice({ loading: false, error: msg });
    if (recordingBrowserHandle) {
      recordingBrowserHandle.setUsage({
        sessions: getSettingsUIState().recordings.usage.sessions,
        bytes_total: -2,
      });
    }
    // eslint-disable-next-line no-console
    console.warn("[settings] ipc.recordings.list failed:", err);
  }
}

/** Dispatch `ipc.recordings.delete` and optimistically remove the row on
 *  ok=true ack. UI-SPEC §State Management: the trailing usage push from
 *  the sidecar (after the sweep fires) updates the disk usage line; we
 *  don't refetch the list here.
 *
 *  Exported for vitest coverage. */
export async function onDeleteRecording(session_dir: string): Promise<void> {
  try {
    const reply = await sendIpcRequest<RecordingsDeleteAck>(
      "ipc.recordings.delete",
      { session_dir },
      "ipc.recordings.delete_ack",
    );
    if (reply.payload.ok) {
      // Optimistic remove — slice update + push to live component.
      const current = getSettingsUIState().recordings;
      const sessions = current.sessions.filter(
        (s) => s.session_dir !== session_dir,
      );
      setRecordingsSlice({ sessions });
      if (recordingBrowserHandle) recordingBrowserHandle.setSessions(sessions);
    } else {
      // ok=false ack — surface error via the slice; the next drawer refresh
      // re-renders with the error sentinel. (UI-SPEC §Copywriting
      // error-toast row lists `Delete failed: {error}` — Plan 15-06 wires
      // the in-dialog retry surface; for v1 we expose via the slice.)
      const errMsg = reply.payload.error ?? "delete failed";
      setRecordingsSlice({ error: `delete failed: ${errMsg}` });
      // eslint-disable-next-line no-console
      console.warn(`[settings] recordings.delete ok=false: ${errMsg}`);
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    setRecordingsSlice({ error: `delete failed: ${msg}` });
    // eslint-disable-next-line no-console
    console.warn("[settings] ipc.recordings.delete failed:", err);
  }
}
