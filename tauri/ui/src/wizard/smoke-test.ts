/* smoke-test.ts — final wizard surface after Step 3 passes (UI-SPEC §11 / CDJ Whisper v5).
 *
 * Heading "READY TO PLAY" in --amber with composite --glow-soft glow.
 * Body "listen for a short voice check through your headphones."
 * Center: 96×96 LED pulse disc (Phase 13 mascot lives as overlay window,
 * not embedded here — this is the deck-LED placeholder).
 * Replay link + Open vibemix CTA (disabled until greetingPlayed).
 * Failure renders its own honest branch (fault disc, retry copy, CTA stays
 * armed as the escape hatch). The old static 3-bar "meter" is gone — a level
 * meter with no signal behind it was a fake instrument.
 *
 * Copy stays short: this is the first audible handoff, not a system receipt. */

import { registerStyle } from "./components/_style-registry.js";
import { PrimaryPanel } from "./components/primary-panel.js";
import { Button } from "./components/button.js";
import { HEADPHONES_SVG } from "./icons/headphones.svg.js";

export interface SmokeTestState {
  greetingPlayed: boolean;
  /** True when the voice check could not play — renders the honest fault
   *  branch instead of the success surface. */
  failed: boolean;
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
    gap: var(--sp-5);
    padding: 48px var(--sp-5); /* mock-verbatim 48 — no v5 sp- token at 48 */
    text-align: center;
  }
  .smoke-test__heading {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 700;
    font-size: 22px;
    letter-spacing: 0.08em;
    color: var(--amber);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7), var(--glow-soft);
    text-transform: uppercase;
    margin: 0;
  }
  .smoke-test__body {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 14px;
    color: var(--silk);
    line-height: 1.5;
    margin: 0;
  }
  .smoke-test__pulse {
    width: 96px;
    height: 96px;
    border-radius: 50%;
    background: linear-gradient(180deg, rgba(255, 165, 223, 0.09) 0%, rgba(255, 165, 223, 0.025) 100%);
    border: 1px solid var(--amber-40);
    box-shadow: var(--glow-soft), inset 0 0 14px var(--amber-22);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--amber);
    animation: smoke-pulse var(--motion-led-pulse) ease-in-out infinite;
  }
  @keyframes smoke-pulse {
    0%, 100% { box-shadow: var(--glow-soft), inset 0 0 14px var(--amber-22); transform: scale(1); }
    50%      { box-shadow: var(--glow-strong), inset 0 0 18px var(--amber-40); transform: scale(1.05); }
  }
  /* Fault branch: the disc stops celebrating — fault tint, no breath. The
   * heading drops the rose glow; the words carry the state. */
  .smoke-test[data-failed="true"] .smoke-test__heading {
    color: var(--text-primary);
    text-shadow: var(--text-emboss);
  }
  .smoke-test[data-failed="true"] .smoke-test__pulse {
    border-color: rgba(212, 65, 58, 0.4);
    color: var(--led-fault);
    box-shadow: inset 0 0 14px rgba(212, 65, 58, 0.16);
    animation: none;
  }
  .smoke-test__replay {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 11px;
    color: var(--silk-65);
  }
  .smoke-test__replay-link {
    background: none;
    border: none;
    color: var(--amber);
    text-decoration: underline dashed;
    text-underline-offset: 2px;
    font-family: inherit;
    font-size: inherit;
    cursor: pointer;
    padding: 0 4px;
    text-shadow: 0 0 4px var(--amber-22);
  }
`;

registerStyle("smoke-test", CSS);

export function renderSmokeTest(state: SmokeTestState, cb: SmokeTestCallbacks): HTMLElement {
  const body = document.createElement("div");
  body.className = "smoke-test";
  body.dataset.failed = String(state.failed);

  // The whole job of this step is to PROVE the voice plays. Failure renders
  // its own surface — never the success celebration (it used to be
  // pixel-identical, reporting success on failure).
  const heading = document.createElement("h1");
  heading.className = "smoke-test__heading";
  heading.textContent = state.failed ? "VOICE CHECK DIDN'T PLAY" : "READY TO PLAY";

  const sub = document.createElement("p");
  sub.className = "smoke-test__body";
  sub.textContent = state.failed
    ? "I couldn't play the voice check. Check your output device, then retry."
    : "listen for a short voice check through your headphones.";

  const pulse = document.createElement("div");
  pulse.className = "smoke-test__pulse";
  pulse.setAttribute("aria-hidden", "true");
  pulse.innerHTML = HEADPHONES_SVG;

  const replay = document.createElement("div");
  replay.className = "smoke-test__replay";
  // UI-SPEC §Smoke Test "Replay link" — VERBATIM (doubles as Retry on fault)
  replay.textContent = state.failed ? "fixed it? " : "didn't hear it? ";
  const replayLink = document.createElement("button");
  replayLink.type = "button";
  replayLink.className = "smoke-test__replay-link";
  replayLink.textContent = state.failed ? "[ ↻ Retry ]" : "[ ↻ Replay ]";
  replayLink.addEventListener("click", () => cb.onReplay());
  replay.append(replayLink);

  body.append(heading, sub, pulse, replay);

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
