/* step2-output-device.ts — Step 2 surface (UI-SPEC §Step 2).
 *
 * Header → conditional BlackHole banner (macOS + missing) → DeviceDropdown
 * → AudioTestButton → WindowPicker → Continue CTA (armed only when
 * audio passed + window selected).
 *
 * Copy strings VERBATIM from UI-SPEC §Step 2. */

import { PrimaryPanel } from "./components/primary-panel.js";
import { BlackHoleBanner } from "./components/blackhole-banner.js";
import { DropdownDevice, type DropdownDevice as DropdownDeviceItem } from "./components/dropdown-device.js";
import { AudioTestButton, type AudioTestState } from "./components/audio-test-button.js";
import { WindowPicker, type WindowPickerMode } from "./components/window-picker.js";
import { Button } from "./components/button.js";
import { withStepLeadGlyph } from "./step1-permissions.js";
import { registerStyle } from "./components/_style-registry.js";

/* Phase 43 / Plan 43-03 — VIS-02 hover-glow sweep for the output-device
 * step. Step 2 owns the device dropdown + 1kHz test tone + window picker
 * — every one of those is interactive. The scoped block here lifts the
 * existing .wizard-step__cta-row glow rule (registered by
 * step1-permissions.ts) onto the deeper device-picker / test-tone /
 * window-picker subtrees so the entire calibration surface is uniform
 * under cursor. */
const CSS = `
  .wizard-step--output-device button:not([disabled]),
  .wizard-step--output-device [role="button"]:not([aria-disabled="true"]),
  .wizard-step--output-device [data-interactive] {
    transition: box-shadow var(--motion-snap) ease-out;
  }
  .wizard-step--output-device button:not([disabled]):hover,
  .wizard-step--output-device button:not([disabled]):focus-visible,
  .wizard-step--output-device [role="button"]:not([aria-disabled="true"]):hover,
  .wizard-step--output-device [role="button"]:not([aria-disabled="true"]):focus-visible,
  .wizard-step--output-device [data-interactive]:hover,
  .wizard-step--output-device [data-interactive]:focus-visible {
    box-shadow: var(--glow-faint);
  }
`;

registerStyle("wizard-step--output-device", CSS);

export interface Step2State {
  blackHolePresent: boolean;
  blackHoleBannerPostClick: boolean;
  devices: DropdownDeviceItem[];
  selectedDeviceId: string;
  audioTestState: AudioTestState;
  audioPassed: boolean;
  actualRate: number;
  detectedDjApp?: { appName: string; windowTitle: string };
  windowPickerMode: WindowPickerMode;
  windowSelected: boolean;
  /** Phase 97 / ONBOARD-04 — headphone device pick for tutor exemplar
   *  playback. `null` means system default (the user has not chosen);
   *  otherwise the integer index from the `devices` array maps to a
   *  sounddevice device id via the existing list_devices roundtrip.
   *  Persisted via `ipc.settings.set { field: 'learn.headphone_device_index' }`. */
  selectedHeadphoneDeviceIndex: number | null;
}

export interface Step2Callbacks {
  platform: "darwin" | "win32" | "linux";
  onContinue: () => void;
  onSelectDevice: (id: string) => void;
  onPlayTest: () => void;
  onAudioYes: () => void;
  onAudioRetry: () => void;
  onOpenInstall: () => void;
  onRecheckBlackHole: () => void;
  onSelectWindow: () => void;
  onPickDifferent: () => void;
  /** Impeccable Wave 5.A — walks the wizard one step backward. Optional
   *  for back-compat with existing tests; the router always wires it. */
  onBack?: () => void;
  /** Phase 97 / ONBOARD-04 — fires when the user picks a headphone device
   *  (or "[ system default ]"). The parent (router.ts) emits
   *  `ipc.settings.set { field: 'learn.headphone_device_index', value }`.
   *  Optional for back-compat with existing tests; the router always wires it. */
  onSelectHeadphoneDevice?: (deviceIndex: number | null) => void;
}

export function renderStep2(state: Step2State, cb: Step2Callbacks): HTMLElement {
  const body = document.createElement("div");
  // Scoping class so the VIS-02 hover-glow rule above latches onto this
  // step's interactive subtree (Plan 43-03).
  body.classList.add("wizard-step--output-device");

  const heading = document.createElement("h1");
  heading.className = "wizard-step__heading";
  // UI-SPEC §Step 2 H1 — VERBATIM
  heading.textContent = "STEP 2 / 5 · OUTPUT DEVICE";
  withStepLeadGlyph(heading, 2);

  const subtitle = document.createElement("p");
  subtitle.className = "wizard-step__subtitle";
  // UI-SPEC §Step 2 Subtitle — VERBATIM
  subtitle.textContent = "picking your headphones and proving the audio chain works.";

  body.append(heading, subtitle);

  // Conditional BlackHole banner (macOS only + missing)
  if (cb.platform === "darwin" && !state.blackHolePresent) {
    body.append(
      BlackHoleBanner({
        onOpenInstall: cb.onOpenInstall,
        onRecheck: cb.onRecheckBlackHole,
        postClickState: state.blackHoleBannerPostClick,
      })
    );
  }

  // Device dropdown — with AUTO pill driven by state's `isAuto` flag
  const devices = state.devices.map((d) =>
    d.id === state.selectedDeviceId && state.selectedDeviceId === "airpods"
      ? { ...d, isAuto: true }
      : { ...d, isAuto: false }
  );
  body.append(
    DropdownDevice({
      devices,
      selectedId: state.selectedDeviceId,
      onSelect: cb.onSelectDevice,
    })
  );

  // Audio test
  body.append(
    AudioTestButton({
      state: state.audioTestState,
      actualRate: state.actualRate,
      onPlay: cb.onPlayTest,
      onYes: cb.onAudioYes,
      onRetry: cb.onAudioRetry,
    })
  );

  // Phase 97 / ONBOARD-04 — headphone device picker row. Beginner lessons
  // play short tutor exemplars; the user picks where they should come out
  // (default = system output). The picker is OPTIONAL — the wizard's
  // continue gate (audioPassed + windowSelected) does NOT depend on it,
  // so a user who skips this step still reaches the smoke-test.
  // Advanced BlackHole + Multi-Output Device routing recipes are documented
  // in docs/audio-routing.md (§LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE).
  if (cb.onSelectHeadphoneDevice) {
    body.append(renderHeadphonePickerSection(state, cb));
  }

  // Window picker
  if (state.detectedDjApp || state.windowPickerMode === "enum") {
    body.append(
      WindowPicker({
        mode: state.windowPickerMode,
        detectedHint: state.detectedDjApp ? {
          appName: state.detectedDjApp.appName,
          windowTitle: state.detectedDjApp.windowTitle,
        } : undefined,
        allWindows: state.windowPickerMode === "enum" ? [
          { id: "djay", name: "djay Pro AI" },
          { id: "rekordbox", name: "Rekordbox" },
          { id: "chrome", name: "Chrome · gmail" },
        ] : undefined,
        onSelect: () => cb.onSelectWindow(),
        onPickDifferent: cb.onPickDifferent,
      })
    );
  }

  const panel = PrimaryPanel({ children: body });
  panel.classList.add("wizard-step__panel-rise");

  const ctaRow = document.createElement("div");
  ctaRow.className = "wizard-step__cta-row";
  ctaRow.dataset.back = cb.onBack ? "true" : "false";
  if (cb.onBack) {
    ctaRow.append(
      Button({
        variant: "secondary",
        state: "idle",
        label: "Back",
        leadingGlyph: "←",
        onClick: cb.onBack,
      }),
    );
  }
  // Continue is armed once the window has been picked. We previously
  // required state.audioPassed too, but the 1kHz tone test can fail in
  // ways that don't reflect the user's actual rig (sample rate
  // mismatch flagged as failure even though the user heard it; user
  // clicked Retry once and is now on a stale failed state with the
  // Yes button stranded behind the disabled-on-failed branch). The
  // tone test stays informational — user judgment over a fragile
  // probe heuristic.
  const armed = state.windowSelected;
  ctaRow.append(
    Button({
      variant: "primary",
      state: armed ? "armed" : "disabled",
      // UI-SPEC §Step 2 Continue button — VERBATIM
      label: "Continue",
      leadingGlyph: "[",
      trailingGlyph: "→ ]",
      onClick: cb.onContinue,
    })
  );

  const wrap = document.createElement("div");
  wrap.append(panel, ctaRow);
  return wrap;
}

/* ---------------------------------------------------------------------------
 * Phase 97 / ONBOARD-04 — Headphone device picker section.
 *
 * Renders a labelled DropdownDevice below the audio-test block:
 *
 *   ╭ Tutor exemplar playback (headphones) ──────────────────────╮
 *   │ Beginner lessons play short audio examples — pick where    │
 *   │ they should come out.                                      │
 *   │ ┌──────────────────────────────────────────────────────┐   │
 *   │ │  🎧  [ system default ]                          ▾  │   │
 *   │ └──────────────────────────────────────────────────────┘   │
 *   ╰────────────────────────────────────────────────────────────╯
 *
 * The "[ system default ]" pseudo-option maps to deviceIndex=null on the
 * wire. Real device indices are 0..N-1 from the same `devices` array the
 * master output picker uses (the wizard already roundtripped
 * ipc.calibration.list_devices). Persists via the parent's
 * onSelectHeadphoneDevice callback → ipc.settings.set.
 *
 * Tone discipline: lowercase subheading + helper text; consistent with
 * the rest of the wizard's copy register.
 * ------------------------------------------------------------------------- */
const HEADPHONE_PICKER_CSS = `
  .wizard-step__headphone-picker {
    margin-top: var(--sp-4);
    padding-top: var(--sp-4);
    border-top: 1px solid var(--silk-22);
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
  }
  .wizard-step__headphone-picker__heading {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 90, "wght" 600;
    font-size: 11px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--silk-65);
    line-height: 1;
    margin: 0;
  }
  .wizard-step__headphone-picker__helper {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 13px;
    color: var(--silk-65);
    line-height: 1.4;
    margin: 0;
  }
`;

registerStyle("wizard-step__headphone-picker", HEADPHONE_PICKER_CSS);

/** ID used to represent the "[ system default ]" pseudo-option on the
 *  DropdownDevice items array. Distinct from any real sounddevice id
 *  string ("0", "1", ...) so the onSelect path can disambiguate cleanly. */
const HEADPHONE_SYSTEM_DEFAULT_ID = "__system_default__";

function renderHeadphonePickerSection(
  state: Step2State,
  cb: Step2Callbacks,
): HTMLElement {
  const section = document.createElement("div");
  section.className = "wizard-step__headphone-picker";

  const heading = document.createElement("h2");
  heading.className = "wizard-step__headphone-picker__heading";
  heading.textContent = "tutor exemplar playback (headphones)";
  section.append(heading);

  const helper = document.createElement("p");
  helper.className = "wizard-step__headphone-picker__helper";
  helper.textContent =
    "beginner lessons play short audio examples — pick where they should come out.";
  section.append(helper);

  // Prepend the "[ system default ]" pseudo-option. The DropdownDevice
  // component renders id strings; "__system_default__" stays distinct
  // from any real device id which is a numeric stringified index.
  const headphoneOptions = [
    {
      id: HEADPHONE_SYSTEM_DEFAULT_ID,
      name: "[ system default ]",
      isAuto: true,
    },
    ...state.devices.map((d) => ({
      id: d.id,
      name: d.name,
      isHeadphones: d.isHeadphones,
      isSpeaker: d.isSpeaker,
      isAuto: false,
    })),
  ];

  const currentIdx = state.selectedHeadphoneDeviceIndex;
  const currentSelectedId =
    currentIdx === null ? HEADPHONE_SYSTEM_DEFAULT_ID : String(currentIdx);

  section.append(
    DropdownDevice({
      devices: headphoneOptions,
      selectedId: currentSelectedId,
      onSelect: (id) => {
        if (id === HEADPHONE_SYSTEM_DEFAULT_ID) {
          cb.onSelectHeadphoneDevice?.(null);
        } else {
          // The DropdownDevice id strings are numeric stringified indices
          // — parse them back to integers for the ipc.settings.set wire
          // value. Negative or NaN guards: fall back to null (system
          // default) rather than crashing the callback.
          const idx = Number.parseInt(id, 10);
          if (Number.isFinite(idx) && idx >= 0) {
            cb.onSelectHeadphoneDevice?.(idx);
          } else {
            cb.onSelectHeadphoneDevice?.(null);
          }
        }
      },
    }),
  );

  return section;
}
