/* smoke-test.ts — final wizard surface after Step 3 passes (UI-SPEC §11).
 *
 * Heading "WIZARD COMPLETE" in --phosphor with --phosphor-glow.
 * Body "playing one greeting from avery to test your headphones…".
 * Center: 96×96 mascot pulse circle (NOT character art — Phase 13 lifts
 * that. Here it's the LED-pulse placeholder).
 * 3-bar audio meter at static 50% (Wave 3 mock; Wave 4 wires real RMS).
 * Replay link + Open vibemix CTA (disabled until greetingPlayed).
 *
 * Copy strings VERBATIM from UI-SPEC §Smoke Test Strings. */

import { registerStyle } from "./components/_style-registry.js";
import { PrimaryPanel } from "./components/primary-panel.js";
import { Button } from "./components/button.js";
import { HEADPHONES_SVG } from "./icons/headphones.svg.js";

export interface SmokeTestState {
  greetingPlayed: boolean;
  meterLevel: number;
}

export interface SmokeTestCallbacks {
  onReplay: () => void;
  onOpenVibemix: () => void;
}

const CSS = `
  .smoke-test {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--sp-lg);
    padding: var(--sp-2xl) var(--sp-lg);
    text-align: center;
  }
  .smoke-test__heading {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 22px;
    letter-spacing: 0.04em;
    color: var(--phosphor);
    text-shadow: var(--phosphor-glow);
    text-transform: uppercase;
    margin: 0;
  }
  .smoke-test__body {
    font-family: "DM Mono", monospace;
    font-size: 14px;
    color: var(--ink);
    line-height: 1.5;
    margin: 0;
  }
  .smoke-test__pulse {
    width: 96px;
    height: 96px;
    border-radius: 50%;
    background: var(--phosphor-soft);
    box-shadow: var(--phosphor-glow);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--phosphor);
    animation: smoke-pulse var(--motion-led-pulse) ease-in-out infinite;
  }
  @keyframes smoke-pulse {
    0%, 100% { box-shadow: var(--phosphor-glow); transform: scale(1); }
    50%      { box-shadow: var(--phosphor-halo); transform: scale(1.05); }
  }
  .smoke-test__meter {
    display: flex;
    align-items: end;
    gap: var(--sp-xs);
    height: 32px;
  }
  .smoke-test__meter-bar {
    width: 8px;
    background: var(--phosphor);
    box-shadow: 0 0 6px var(--phosphor);
    border-radius: 1px;
  }
  .smoke-test__meter-bar:nth-child(1) { height: 40%; }
  .smoke-test__meter-bar:nth-child(2) { height: 70%; }
  .smoke-test__meter-bar:nth-child(3) { height: 55%; }
  .smoke-test__replay {
    font-family: "DM Mono", monospace;
    font-size: 11px;
    color: var(--ink-dim);
  }
  .smoke-test__replay-link {
    background: none;
    border: none;
    color: var(--phosphor);
    text-decoration: underline dashed;
    text-underline-offset: 2px;
    font-family: inherit;
    font-size: inherit;
    cursor: pointer;
    padding: 0 4px;
  }
`;

registerStyle("smoke-test", CSS);

export function renderSmokeTest(state: SmokeTestState, cb: SmokeTestCallbacks): HTMLElement {
  const body = document.createElement("div");
  body.className = "smoke-test";

  const heading = document.createElement("h1");
  heading.className = "smoke-test__heading";
  // UI-SPEC §Smoke Test "Heading" — VERBATIM
  heading.textContent = "WIZARD COMPLETE";

  const sub = document.createElement("p");
  sub.className = "smoke-test__body";
  // UI-SPEC §Smoke Test "Body" — VERBATIM
  sub.textContent = "playing one greeting from avery to test your headphones…";

  const pulse = document.createElement("div");
  pulse.className = "smoke-test__pulse";
  pulse.setAttribute("aria-hidden", "true");
  pulse.innerHTML = HEADPHONES_SVG;

  const meter = document.createElement("div");
  meter.className = "smoke-test__meter";
  for (let i = 0; i < 3; i++) {
    const bar = document.createElement("div");
    bar.className = "smoke-test__meter-bar";
    meter.append(bar);
  }

  const replay = document.createElement("div");
  replay.className = "smoke-test__replay";
  // UI-SPEC §Smoke Test "Replay link" — VERBATIM
  replay.textContent = "didn't hear avery? ";
  const replayLink = document.createElement("button");
  replayLink.type = "button";
  replayLink.className = "smoke-test__replay-link";
  replayLink.textContent = "[ ↻ Replay ]";
  replayLink.addEventListener("click", () => cb.onReplay());
  replay.append(replayLink);

  body.append(heading, sub, pulse, meter, replay);

  const panel = PrimaryPanel({ children: body });

  const ctaRow = document.createElement("div");
  ctaRow.className = "wizard-step__cta-row";
  ctaRow.append(
    Button({
      variant: "primary",
      state: state.greetingPlayed ? "armed" : "disabled",
      // UI-SPEC §Smoke Test "CTA button" — VERBATIM
      label: "Open vibemix",
      leadingGlyph: "[",
      trailingGlyph: "→ ]",
      onClick: cb.onOpenVibemix,
    })
  );

  const wrap = document.createElement("div");
  wrap.append(panel, ctaRow);
  return wrap;
}
