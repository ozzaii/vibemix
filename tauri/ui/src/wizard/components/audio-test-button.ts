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
  .cmp-audio-test {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--sp-md);
    padding: var(--sp-lg);
  }
  .cmp-audio-test__visual {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 96px;
    height: 96px;
  }
  .cmp-audio-test__speaker {
    width: 48px;
    height: 48px;
    color: var(--ink-dim);
    z-index: 2;
    position: relative;
  }
  .cmp-audio-test[data-state="playing"] .cmp-audio-test__speaker,
  .cmp-audio-test[data-state="passed"]  .cmp-audio-test__speaker {
    color: var(--phosphor);
  }
  .cmp-audio-test[data-state="failed"] .cmp-audio-test__speaker,
  .cmp-audio-test[data-state="programmatic-failed"] .cmp-audio-test__speaker {
    color: var(--rec);
  }
  .cmp-audio-test__rings {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }
  .cmp-audio-test__ring {
    position: absolute;
    inset: 24px;
    border: 1.5px solid var(--phosphor-soft);
    border-radius: 50%;
    opacity: 0;
  }
  .cmp-audio-test[data-state="playing"] .cmp-audio-test__ring {
    animation: cmp-audio-ring var(--motion-rings-audio) ease-out infinite;
  }
  .cmp-audio-test[data-state="playing"] .cmp-audio-test__ring:nth-child(2) { animation-delay: 0.375s; }
  .cmp-audio-test[data-state="playing"] .cmp-audio-test__ring:nth-child(3) { animation-delay: 0.75s;  }
  .cmp-audio-test[data-state="playing"] .cmp-audio-test__ring:nth-child(4) { animation-delay: 1.125s; }
  @keyframes cmp-audio-ring {
    0%   { opacity: 0.8; transform: scale(0.4); }
    100% { opacity: 0;   transform: scale(2.0); }
  }
  .cmp-audio-test__cta {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    padding: 12px 24px;
    border-radius: 4px;
    background: linear-gradient(180deg, var(--panel-lift), var(--panel));
    border: 1px solid var(--phosphor-dim);
    color: var(--ink-dim);
    min-width: 200px;
    cursor: pointer;
    transition: border-color var(--motion-snap) ease-out, color var(--motion-snap) ease-out, box-shadow var(--motion-snap) ease-out;
  }
  .cmp-audio-test[data-state="idle"] .cmp-audio-test__cta:hover {
    border-color: var(--phosphor);
    color: var(--phosphor);
    box-shadow: var(--phosphor-glow);
  }
  .cmp-audio-test[data-state="playing"] .cmp-audio-test__cta {
    border-color: var(--phosphor);
    color: var(--phosphor);
    text-shadow: var(--phosphor-glow);
    box-shadow: var(--phosphor-glow);
    cursor: progress;
  }
  .cmp-audio-test[data-state="passed"] .cmp-audio-test__cta {
    border-color: var(--ok);
    color: var(--ok);
  }
  .cmp-audio-test[data-state="failed"] .cmp-audio-test__cta,
  .cmp-audio-test[data-state="programmatic-failed"] .cmp-audio-test__cta {
    border-color: var(--rec);
    color: var(--rec);
  }
  .cmp-audio-test__lcd {
    font-family: "DSEG7", "DM Mono", monospace;
    font-size: 22px;
    letter-spacing: 0.06em;
    color: var(--phosphor);
    text-shadow: var(--phosphor-glow);
    line-height: 1;
    min-height: 22px;
  }
  .cmp-audio-test__micro {
    font-family: "DM Mono", monospace;
    font-size: 11px;
    color: var(--ink-dim);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    text-align: center;
    min-height: 14px;
  }
  .cmp-audio-test__micro[data-tone="rec"] {
    color: var(--rec);
  }
  .cmp-audio-test__led {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
  }
  .cmp-audio-test__led[data-tone="ok"]  { background: var(--ok);  box-shadow: 0 0 6px var(--ok); }
  .cmp-audio-test__led[data-tone="rec"] { background: var(--rec); box-shadow: 0 0 6px var(--rec); }
  .cmp-audio-test__confirm-row {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--sp-md);
    margin-top: var(--sp-md);
  }
  .cmp-audio-test__confirm-prompt {
    font-family: "DM Mono", monospace;
    font-size: 14px;
    color: var(--ink);
    text-align: center;
  }
  .cmp-audio-test__confirm-buttons {
    display: flex;
    gap: var(--sp-md);
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
    micro.textContent = `sample rate mismatch — blackhole reporting ${actual}, expected 48000`;
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
    const yesArmed = props.state === "passed" || props.state === "playing";
    buttons.append(
      Button({
        variant: "primary",
        state: yesArmed ? "armed" : "disabled",
        // UI-SPEC §Step 2 "Audio test yes" — VERBATIM
        label: "Yes — sounded clean",
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
