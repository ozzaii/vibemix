/* step0-intro.ts — wizard first-paint brand handshake (post-impeccable Wave 1.2).
 *
 * The mock's character moment ("PIONEER DECK / AT 2 AM / — A SIGN OF
 * LIFE —" at mocks/vibemix-direction-final.html:1195) had no equivalent
 * in the shipped wizard — the user opened a vibemix install to what
 * read as a generic settings dialog. This step ships the missing moment.
 *
 * Visual anatomy:
 *   - Three-line hero. Saira wdth 82 wght 800 at 64-72px for the wordmark
 *     stack; wdth 82 wght 600 for the third line, em-rule-bracketed in
 *     --silk-65 (mock pattern).
 *   - Single amber accent: the "V" of "VIBEMIX" gets the lead glyph
 *     treatment (one amber moment per panel, see DESIGN.md §5).
 *   - Single "[ Let's go ]" CTA at the bottom. Secondary visual treatment
 *     (mock-verbatim button armed state from button.ts).
 *
 * No competing chrome: NO border-anim sweep (one-CDJ-one-light rule),
 * NO glass tile shell (the void background carries the moment), NO
 * subtitle clutter. The three-line phrase is the entire surface.
 *
 * Lifecycle: rendered as the FIRST step the user sees post-install
 * (wizardState.currentStep starts as "intro"). One click → advances to
 * permissions. The intro is never visible again — wizard.done is
 * recorded, and the next launch boots straight to the session UI.
 *
 * Step indicator: hidden on this step (router.ts:208-212 pattern, same
 * as smoke-test). The hero owns the full surface. */

import { registerStyle } from "./components/_style-registry.js";
import { Button } from "./components/button.js";

export interface Step0IntroCallbacks {
  onBegin: () => void;
}

const CSS = `
  .wizard-intro {
    position: relative;
    display: grid;
    justify-items: center;
    align-content: center;
    gap: var(--sp-5);
    justify-self: center;
    width: min(720px, calc(100vw - 64px));
    min-height: min(540px, calc(100vh - var(--titlebar-h) - var(--statusbar-h) - 72px));
    padding: clamp(48px, 8vh, 78px) var(--sp-5);
    text-align: center;
    isolation: isolate;
    overflow: hidden;
  }
  .wizard-intro::before {
    content: "";
    position: absolute;
    inset: 14px 8px;
    z-index: 0;
    border: 1px solid rgba(255, 255, 255, 0.055);
    border-radius: var(--rad-lg);
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.035), transparent 18%),
      repeating-linear-gradient(90deg, rgba(214, 207, 199, 0.035) 0 1px, transparent 1px 92px),
      linear-gradient(180deg, rgba(12, 14, 22, 0.58) 0%, rgba(3, 4, 8, 0.78) 58%, rgba(1, 2, 5, 0.92) 100%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.055),
      inset 0 -1px 0 rgba(0, 0, 0, 0.75),
      inset 0 0 0 1px rgba(0, 0, 0, 0.32),
      0 24px 70px rgba(0, 0, 0, 0.35);
  }
  .wizard-intro::after {
    content: "";
    position: absolute;
    inset: 15px 9px;
    z-index: 0;
    pointer-events: none;
    border-radius: var(--rad-lg);
    background:
      linear-gradient(90deg, transparent 0%, rgba(255, 138, 61, 0.12) 50%, transparent 100%),
      repeating-linear-gradient(0deg, transparent 0 8px, rgba(214, 207, 199, 0.025) 8px 9px);
    mix-blend-mode: screen;
    opacity: 0.42;
    mask-image: linear-gradient(180deg, transparent 0%, black 28%, black 72%, transparent 100%);
  }
  .wizard-intro__field {
    position: absolute;
    inset: 22px 14px;
    z-index: 1;
    display: grid;
    place-items: center;
    pointer-events: none;
  }
  .wizard-intro__field::before,
  .wizard-intro__field::after {
    content: "";
    position: absolute;
    inset: 0;
    background:
      radial-gradient(circle at 8px 8px, var(--silk-22) 0 2px, transparent 2.5px),
      radial-gradient(circle at calc(100% - 8px) 8px, var(--silk-12) 0 2px, transparent 2.5px),
      radial-gradient(circle at 8px calc(100% - 8px), rgba(255, 138, 61, 0.18) 0 2px, transparent 2.5px),
      radial-gradient(circle at calc(100% - 8px) calc(100% - 8px), var(--silk-12) 0 2px, transparent 2.5px);
  }
  .wizard-intro__field::after {
    width: min(560px, 78vw);
    height: 1px;
    inset: auto;
    border-radius: 0;
    background: linear-gradient(90deg, transparent, rgba(255, 138, 61, 0.34), transparent);
    box-shadow: none;
    transform: none;
    opacity: 0.48;
  }
  .wizard-intro__orbit {
    position: relative;
    width: min(430px, 70vw);
    aspect-ratio: 1;
    border-radius: 50%;
    border: 1px solid rgba(255, 138, 61, 0.12);
    background:
      radial-gradient(circle, transparent 0 35%, rgba(255, 138, 61, 0.045) 35.5% 36.5%, transparent 37% 57%, rgba(214, 207, 199, 0.055) 57.5% 58.5%, transparent 59%),
      conic-gradient(from 24deg, transparent 0 62deg, rgba(255, 138, 61, 0.24) 72deg, transparent 92deg 360deg);
    box-shadow:
      inset 0 0 42px rgba(0, 0, 0, 0.72),
      0 0 44px rgba(255, 138, 61, 0.055);
    opacity: 0.78;
  }
  .wizard-intro__orbit span {
    position: absolute;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--amber);
    box-shadow: 0 0 10px var(--amber-40);
  }
  .wizard-intro__orbit span:nth-child(1) { top: 13%; left: 49%; }
  .wizard-intro__orbit span:nth-child(2) {
    right: 17%;
    bottom: 27%;
    width: 5px;
    height: 5px;
    background: var(--silk-65);
    box-shadow: 0 0 8px rgba(214, 207, 199, 0.28);
  }
  .wizard-intro__orbit span:nth-child(3) {
    left: 20%;
    bottom: 23%;
    width: 5px;
    height: 5px;
    background: rgba(72, 152, 255, 0.68);
    box-shadow: 0 0 10px rgba(72, 152, 255, 0.24);
  }
  .wizard-intro__rail {
    position: absolute;
    left: 50%;
    bottom: 34px;
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: 5px;
    width: min(300px, 62vw);
    transform: translateX(-50%);
    padding: 7px 8px;
    border: 1px solid rgba(255, 255, 255, 0.055);
    border-radius: var(--rad-md);
    background: rgba(0, 0, 0, 0.34);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.04),
      inset 0 -1px 0 rgba(0, 0, 0, 0.82);
  }
  .wizard-intro__rail i {
    height: 6px;
    border-radius: 999px;
    background: rgba(214, 207, 199, 0.13);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  }
  .wizard-intro__rail i:nth-child(3),
  .wizard-intro__rail i:nth-child(7),
  .wizard-intro__rail i:nth-child(10) {
    background: rgba(255, 138, 61, 0.62);
    box-shadow: 0 0 10px rgba(255, 138, 61, 0.22);
  }
  .wizard-intro__telemetry {
    position: absolute;
    top: 34px;
    left: 50%;
    display: flex;
    gap: 8px;
    transform: translateX(-50%);
    font-family: var(--type-mono);
    font-size: 9px;
    letter-spacing: 0;
    text-transform: uppercase;
    color: var(--silk-40);
  }
  .wizard-intro__telemetry span {
    padding: 5px 7px 4px;
    border: 1px solid rgba(255, 255, 255, 0.055);
    border-radius: var(--rad-sm);
    background: rgba(0, 0, 0, 0.28);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.035),
      inset 0 -1px 0 rgba(0, 0, 0, 0.68);
  }
  .wizard-intro__telemetry span:first-child {
    color: var(--amber);
    border-color: rgba(255, 138, 61, 0.18);
    text-shadow: 0 0 8px rgba(255, 138, 61, 0.24);
  }
  .wizard-intro__hero {
    position: relative;
    z-index: 2;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--sp-3);
    font-family: var(--type-display);
    line-height: 0.95;
    color: var(--silk);
    text-shadow:
      0 2px 8px rgba(0, 0, 0, 0.65),
      0 0 32px rgba(255, 138, 61, 0.06);
  }
  .wizard-intro__hero::before {
    content: "";
    position: absolute;
    left: 50%;
    top: 50%;
    z-index: -1;
    width: 390px;
    height: 170px;
    transform: translate(-50%, -50%);
    border-radius: 50%;
    background: radial-gradient(ellipse, rgba(0, 0, 0, 0.58) 0%, rgba(0, 0, 0, 0.18) 48%, transparent 72%);
    filter: blur(4px);
  }
  .wizard-intro__wordmark {
    font-variation-settings: "wdth" 82, "wght" 800;
    font-size: 76px;
    letter-spacing: 0;
    text-transform: uppercase;
    display: inline-flex;
    align-items: baseline;
    gap: 1px;
    filter: drop-shadow(0 16px 22px rgba(0, 0, 0, 0.58));
  }
  /* The "V" gets the amber lead. Single accent moment per DESIGN.md §5.
   * 2026-05-19 /impeccable critique fix: dropped the second outer
   * glow (0 0 28px var(--amber-22)). Two stacked outer halos on a
   * single 68px character was the closest the wizard came to
   * splash-screen feel — DESIGN.md §4 reserves the larger halo for
   * primary action button hover/press. Single 12px halo is enough. */
  .wizard-intro__wordmark-lead {
    color: var(--amber);
    font-variation-settings: "wdth" 82, "wght" 800;
    text-shadow: 0 0 12px var(--amber-40);
  }
  .wizard-intro__phrase {
    font-variation-settings: "wdth" 82, "wght" 700;
    font-size: 42px;
    letter-spacing: 0;
    text-transform: uppercase;
    color: var(--silk);
  }
  .wizard-intro__slogan {
    font-variation-settings: "wdth" 100, "wght" 500;
    font-size: 12px;
    letter-spacing: 0;
    text-transform: uppercase;
    color: var(--silk-65);
    margin-top: var(--sp-2);
    display: inline-flex;
    align-items: center;
    gap: var(--sp-3);
  }
  .wizard-intro__slogan-rule {
    width: 28px;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--silk-40), transparent);
  }
  .wizard-intro__cta {
    position: relative;
    z-index: 2;
    margin-top: var(--sp-3);
  }
  .wizard-intro__cta .cmp-btn {
    min-width: 184px;
    padding: 15px 28px 14px;
    letter-spacing: 0;
    border-color: rgba(255, 138, 61, 0.2);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.075),
      inset 0 -1px 0 var(--amber-40),
      inset 0 -8px 18px rgba(0, 0, 0, 0.32),
      inset 0 0 18px var(--amber-22),
      0 10px 22px rgba(0, 0, 0, 0.32),
      0 0 0 1px rgba(255, 138, 61, 0.14);
  }
  /* Phase 43 / Plan 43-03 — VIS-02 hover-glow sweep. The intro carries a
   * single CTA ("Let's go"); the broad interactive selector union below
   * applies --glow-faint on :hover + :focus-visible so the first surface
   * the user touches already speaks CDJ Whisper tactility. */
  .wizard-intro__cta button:not([disabled]),
  .wizard-intro__cta [role="button"]:not([aria-disabled="true"]),
  .wizard-intro__cta [data-interactive] {
    transition: box-shadow var(--motion-snap) ease-out;
  }
  .wizard-intro__cta button:not([disabled]):hover,
  .wizard-intro__cta button:not([disabled]):focus-visible,
  .wizard-intro__cta [role="button"]:not([aria-disabled="true"]):hover,
  .wizard-intro__cta [role="button"]:not([aria-disabled="true"]):focus-visible,
  .wizard-intro__cta [data-interactive]:hover,
  .wizard-intro__cta [data-interactive]:focus-visible {
    box-shadow: var(--glow-faint);
  }
  /* 2026-05-19 /impeccable critique fix round 2: at 80ms stagger the
   * CTA appeared almost simultaneously with the hero — the staircase
   * was so compressed it read as a single ease-in instead of a
   * sequence. Dropped the stagger entirely so the hero + CTA boot
   * together. PRODUCT.md anti-references the splash-screen pattern:
   * "It opens, it boots, it works." Two elements arriving on the
   * same beat lands cleaner than three frames apart. */
  @media (prefers-reduced-motion: no-preference) {
    .wizard-intro__hero,
    .wizard-intro__cta,
    .wizard-intro__field {
      animation: vmx-intro-rise var(--motion-step) ease-out both;
    }
  }
  @keyframes vmx-intro-rise {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @media (max-width: 720px) {
    .wizard-intro {
      width: 100%;
      min-height: min(560px, calc(100vh - var(--titlebar-h) - var(--statusbar-h) - 52px));
      padding: 44px var(--sp-4) 58px;
    }
    .wizard-intro::before { inset: 10px 0; }
    .wizard-intro::after { inset: 11px 1px; }
    .wizard-intro__field { inset: 18px 4px; }
    .wizard-intro__telemetry {
      top: 24px;
      width: min(320px, 82vw);
      justify-content: center;
      flex-wrap: wrap;
    }
    .wizard-intro__rail {
      bottom: 24px;
      width: min(270px, 76vw);
    }
    .wizard-intro__wordmark { font-size: 52px; }
    .wizard-intro__phrase { font-size: 30px; }
    .wizard-intro__slogan { font-size: 11px; }
  }
  @media (max-width: 420px) {
    .wizard-intro__telemetry span:nth-child(n + 3) { display: none; }
    .wizard-intro__wordmark { font-size: 42px; }
    .wizard-intro__phrase { font-size: 24px; }
    .wizard-intro__slogan {
      font-size: 10px;
      gap: var(--sp-2);
    }
    .wizard-intro__slogan-rule { width: 20px; }
    .wizard-intro__cta .cmp-btn {
      min-width: 164px;
      padding-inline: 22px;
    }
  }
`;

registerStyle("wizard-intro", CSS);

export function renderStep0Intro(cb: Step0IntroCallbacks): HTMLElement {
  const root = document.createElement("section");
  root.className = "wizard-intro";
  root.setAttribute("aria-label", "vibemix intro");

  const field = document.createElement("div");
  field.className = "wizard-intro__field";
  field.setAttribute("aria-hidden", "true");

  const orbit = document.createElement("div");
  orbit.className = "wizard-intro__orbit";
  orbit.append(
    document.createElement("span"),
    document.createElement("span"),
    document.createElement("span"),
  );

  const rail = document.createElement("div");
  rail.className = "wizard-intro__rail";
  for (let i = 0; i < 12; i++) {
    rail.append(document.createElement("i"));
  }

  const telemetry = document.createElement("div");
  telemetry.className = "wizard-intro__telemetry";
  for (const label of ["local index", "screen", "midi"]) {
    const item = document.createElement("span");
    item.textContent = label;
    telemetry.append(item);
  }

  field.append(orbit, rail, telemetry);
  root.append(field);

  const hero = document.createElement("div");
  hero.className = "wizard-intro__hero";

  const wordmark = document.createElement("span");
  wordmark.className = "wizard-intro__wordmark";
  const wordmarkLead = document.createElement("span");
  wordmarkLead.className = "wizard-intro__wordmark-lead";
  wordmarkLead.textContent = "V";
  const wordmarkRest = document.createElement("span");
  wordmarkRest.textContent = "IBEMIX";
  wordmark.append(wordmarkLead, wordmarkRest);

  const phrase = document.createElement("span");
  phrase.className = "wizard-intro__phrase";
  phrase.textContent = "DJ FRIEND";

  const slogan = document.createElement("span");
  slogan.className = "wizard-intro__slogan";
  const ruleL = document.createElement("span");
  ruleL.className = "wizard-intro__slogan-rule";
  ruleL.setAttribute("aria-hidden", "true");
  const ruleR = document.createElement("span");
  ruleR.className = "wizard-intro__slogan-rule";
  ruleR.setAttribute("aria-hidden", "true");
  const sloganText = document.createElement("span");
  sloganText.textContent = "in your ear";
  slogan.append(ruleL, sloganText, ruleR);

  hero.append(wordmark, phrase, slogan);
  root.append(hero);

  const ctaWrap = document.createElement("div");
  ctaWrap.className = "wizard-intro__cta";
  ctaWrap.append(
    Button({
      variant: "primary",
      state: "armed",
      label: "Let's go",
      leadingGlyph: "[",
      trailingGlyph: "]",
      onClick: cb.onBegin,
    }),
  );
  root.append(ctaWrap);

  return root;
}
