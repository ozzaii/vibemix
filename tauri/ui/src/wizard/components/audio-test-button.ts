/* audio-test-button.ts — Step 2 hero element (UI-SPEC §7).
 *
 * 5 states: idle / playing / passed / failed / programmatic-failed.
 * Vertical stack: speaker glyph (48×48) → state label → DSEG7 readout →
 * secondary microcopy.
 *
 * Playing state animates 4 concentric ring pulses around the speaker
 * glyph at 1.5s ease-out infinite (matches sine duration). DSEG7 shows
 * "1000 Hz" during playing, detected sample rate during passed.
 *
 * Below the button: "did you hear a clean tone?" prompt + Yes / Retry
 * buttons (UI-SPEC §7).
 *
 * Copy strings VERBATIM from UI-SPEC §Step 2. */

import { registerStyle } from "./_style-registry.js";
import { SPEAKER_SVG } from "../icons/speaker.svg.js";
import { Button } from "./button.js";

export type AudioTestState =
  | "idle"
  | "playing"
  | "passed"
  | "failed"
  | "programmatic-failed";

export interface AudioTestButtonProps {
  state: AudioTestState;
  actualRate?: number;
  errorMsg?: string;
  onPlay?: () => void;
  onYes?: () => void;
  onRetry?: () => void;
}

const CSS = `
  /* Compact stack — the wizard window is locked at 960×680 (UI-SPEC
   * §Window Dimensions). After chrome (titlebar 56 + statusbar 40 + step
   * strip 64 + cta margin 24 + grid padding 24), the step body has
   * ~472px to render heading + subtitle + dropdown + audio test +
   * (optional) BlackHole banner + window picker + Continue CTA. The
   * audio test is the heaviest block in that budget, so its internal
   * padding/gap/visual size is tuned to keep the default Step 2 render
   * scrollless on the locked window. The .wizard-grid scroll fallback
   * (tokens.css) still catches the BlackHole-banner-present case. */
  .cmp-audio-test {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--sp-3);
    padding: var(--sp-3) var(--sp-5);
  }
  .cmp-audio-test__visual {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 72px;
    height: 72px;
  }
  .cmp-audio-test__speaker {
    width: 36px;
    height: 36px;
    color: var(--silk-65);
    z-index: 2;
    position: relative;
  }
  .cmp-audio-test[data-state="playing"] .cmp-audio-test__speaker,
  .cmp-audio-test[data-state="passed"]  .cmp-audio-test__speaker {
    color: var(--amber);
    filter: drop-shadow(0 0 3px var(--amber-22));
  }
  .cmp-audio-test[data-state="failed"] .cmp-audio-test__speaker,
  .cmp-audio-test[data-state="programmatic-failed"] .cmp-audio-test__speaker {
    color: var(--led-fault);
  }
  .cmp-audio-test__rings {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }
  .cmp-audio-test__ring {
    position: absolute;
    inset: 18px;
    border: 1.5px solid var(--amber-22);
    border-radius: 50%;
    opacity: 0;
  }
  .cmp-audio-test[data-state="playing"] .cmp-audio-test__ring {
    animation: cmp-audio-ring var(--motion-rings-audio) ease-out infinite;
  }
  .cmp-audio-test[data-state="playing"] .cmp-audio-test__ring:nth-child(2) {
    animation-delay: 0.375s;
    border-color: var(--amber-40);
  }
  .cmp-audio-test[data-state="playing"] .cmp-audio-test__ring:nth-child(3) {
    animation-delay: 0.75s;
    border-color: var(--amber-65);
  }
  .cmp-audio-test[data-state="playing"] .cmp-audio-test__ring:nth-child(4) {
    animation-delay: 1.125s;
    border-color: var(--amber-22);
  }
  @keyframes cmp-audio-ring {
    0%   { opacity: 0.8; transform: scale(0.4); }
    100% { opacity: 0;   transform: scale(2.0); }
  }
  .cmp-audio-test__cta {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    padding: 12px 24px;
    border-radius: var(--rad-sm);
    background: var(--glass-2);
    backdrop-filter: var(--blur-glass-display);
    -webkit-backdrop-filter: var(--blur-glass-display);
    border: 1px solid var(--amber-22);
    color: var(--silk-65);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.035),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45);
    min-width: 200px;
    cursor: pointer;
    transition: border-color var(--motion-snap) ease-out, color var(--motion-snap) ease-out, box-shadow var(--motion-snap) ease-out;
  }
  .cmp-audio-test[data-state="idle"] .cmp-audio-test__cta:hover {
    border-color: var(--amber);
    color: var(--amber);
    text-shadow: 0 0 4px var(--amber-65);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 0 14px var(--amber-22),
      var(--glow-soft);
  }
  .cmp-audio-test[data-state="playing"] .cmp-audio-test__cta {
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.09) 0%, rgba(255, 138, 61, 0.025) 100%);
    border-color: var(--amber-40);
    color: var(--amber);
    text-shadow: 0 0 4px var(--amber-65);
    box-shadow:
      inset 0 0 14px var(--amber-22),
      var(--glow-soft);
    cursor: progress;
  }
  .cmp-audio-test[data-state="passed"] .cmp-audio-test__cta {
    border-color: var(--led-ok);
    color: var(--led-ok);
  }
  .cmp-audio-test[data-state="failed"] .cmp-audio-test__cta,
  .cmp-audio-test[data-state="programmatic-failed"] .cmp-audio-test__cta {
    border-color: var(--led-fault);
    color: var(--led-fault);
  }
  .cmp-audio-test__lcd {
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-feature-settings: "tnum";
    font-size: 22px;
    letter-spacing: 0.06em;
    color: var(--amber);
    text-shadow: var(--glow-soft);
    line-height: 1;
    min-height: 22px;
  }
  .cmp-audio-test__micro {
    font-family: var(--type-mono);
    font-size: 11px;
    color: var(--silk-65);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    text-align: center;
    min-height: 14px;
  }
  .cmp-audio-test__micro[data-tone="rec"] {
    color: var(--led-fault);
  }
  .cmp-audio-test__led {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
  }
  .cmp-audio-test__led[data-tone="ok"]  { background: var(--led-ok);    box-shadow: 0 0 6px var(--led-ok); }
  .cmp-audio-test__led[data-tone="rec"] { background: var(--led-fault); box-shadow: 0 0 6px var(--led-fault); }
  .cmp-audio-test__confirm-row {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--sp-3);
    margin-top: var(--sp-3);
  }
  .cmp-audio-test__confirm-prompt {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 14px;
    color: var(--silk);
    text-align: center;
  }
  .cmp-audio-test__confirm-buttons {
    display: flex;
    gap: var(--sp-4);
  }
`;

registerStyle("cmp-audio-test", CSS);

// UI-SPEC §7 — state→label VERBATIM
const LABEL: Record<AudioTestState, string> = {
  idle: "▶ PLAY 1 kHz TEST",
  playing: "■ PLAYING…",
  passed: "✓ HEARD IT — PASSED",
  failed: "✕ DIDN'T HEAR — RETRY",
  "programmatic-failed": "✕ DIDN'T HEAR — RETRY",
};

export function AudioTestButton(props: AudioTestButtonProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "cmp-audio-test";
  root.dataset.state = props.state;

  const visual = document.createElement("div");
  visual.className = "cmp-audio-test__visual";
  const rings = document.createElement("div");
  rings.className = "cmp-audio-test__rings";
  for (let i = 0; i < 4; i++) {
    const r = document.createElement("div");
    r.className = "cmp-audio-test__ring";
    rings.append(r);
  }
  const speaker = document.createElement("div");
  speaker.className = "cmp-audio-test__speaker";
  speaker.innerHTML = SPEAKER_SVG;
  visual.append(rings, speaker);

  const cta = document.createElement("button");
  cta.type = "button";
  cta.className = "cmp-audio-test__cta";
  cta.textContent = LABEL[props.state];
  cta.addEventListener("click", () => {
    if (props.state === "idle" || props.state === "failed" || props.state === "programmatic-failed") {
      props.onPlay?.();
    }
  });

  const lcd = document.createElement("div");
  lcd.className = "cmp-audio-test__lcd";
  if (props.state === "playing") lcd.textContent = "1000 Hz";
  else if (props.state === "passed") lcd.textContent = `${props.actualRate ?? 48000} Hz`;
  else lcd.textContent = "";

  const micro = document.createElement("div");
  micro.className = "cmp-audio-test__micro";
  if (props.state === "passed") {
    const led = document.createElement("span");
    led.className = "cmp-audio-test__led";
    led.dataset.tone = "ok";
    led.setAttribute("aria-hidden", "true");
    micro.append(led, document.createTextNode("OK"));
  } else if (props.state === "failed") {
    micro.dataset.tone = "rec";
    // UI-SPEC §Step 2 — VERBATIM
    micro.textContent = props.errorMsg ?? "no signal heard. check headphone volume + cable";
  } else if (props.state === "programmatic-failed") {
    micro.dataset.tone = "rec";
    const actual = props.actualRate ?? 0;
    // UI-SPEC §Step 2 audio-test-programmatic-fail line — VERBATIM template
    micro.textContent = `sample rate mismatch. blackhole reporting ${actual}, expected 48000.`;
  }

  root.append(visual, cta, lcd, micro);

  // Confirm row — UI-SPEC §7 + Step 2 strings VERBATIM
  if (props.state === "playing" || props.state === "passed" || props.state === "failed" || props.state === "programmatic-failed") {
    const confirm = document.createElement("div");
    confirm.className = "cmp-audio-test__confirm-row";
    const prompt = document.createElement("div");
    prompt.className = "cmp-audio-test__confirm-prompt";
    // UI-SPEC §Step 2 "Audio test prompt" — VERBATIM
    prompt.textContent = "did you hear a clean tone?";
    const buttons = document.createElement("div");
    buttons.className = "cmp-audio-test__confirm-buttons";
    // Yes is armed any time the confirm row is shown — including "failed"
    // and "programmatic-failed". This lets the user override a misfire
    // (e.g., took >30s to click and the probe timed out, or sample rate
    // mismatch but tone was clearly audible). Disabling Yes in failed
    // strands the user: Retry just re-plays the same tone on the same
    // device, so without override there is no path forward. The confirm
    // row itself only renders for the four states this branch handles,
    // so Yes is unconditionally armed here.
    const yesArmed = true;
    buttons.append(
      Button({
        variant: "primary",
        state: yesArmed ? "armed" : "disabled",
        // UI-SPEC §Step 2 "Audio test yes" — VERBATIM
        label: "Yes, sounded clean",
        leadingGlyph: "[",
        trailingGlyph: "]",
        onClick: props.onYes,
      }),
      Button({
        variant: "secondary",
        state: "idle",
        // UI-SPEC §Step 2 "Audio test retry" — VERBATIM
        label: "Retry",
        leadingGlyph: "↻",
        onClick: props.onRetry,
      })
    );
    confirm.append(prompt, buttons);
    root.append(confirm);
  }

  return root;
}
