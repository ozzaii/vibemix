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
 *   - Single amber accent: the "A" of "VIBEMIX" gets the lead glyph
 *     treatment (matches cohost AVERY signature).
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
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--sp-6);
    min-height: 360px;
    padding: var(--sp-7) var(--sp-5);
    text-align: center;
  }
  .wizard-intro__hero {
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
  .wizard-intro__wordmark {
    font-variation-settings: "wdth" 82, "wght" 800;
    font-size: 68px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    display: inline-flex;
    align-items: baseline;
    gap: 1px;
  }
  /* The "V" gets the AVERY-style amber lead — single accent moment. */
  .wizard-intro__wordmark-lead {
    color: var(--amber);
    font-variation-settings: "wdth" 82, "wght" 800;
    text-shadow:
      0 0 12px var(--amber-40),
      0 0 28px var(--amber-22);
  }
  .wizard-intro__phrase {
    font-variation-settings: "wdth" 82, "wght" 700;
    font-size: 38px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--silk);
  }
  .wizard-intro__slogan {
    font-variation-settings: "wdth" 100, "wght" 500;
    font-size: 14px;
    letter-spacing: 0.32em;
    text-transform: uppercase;
    color: var(--silk-65);
    margin-top: var(--sp-3);
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
    margin-top: var(--sp-4);
  }
  @media (prefers-reduced-motion: no-preference) {
    .wizard-intro__hero {
      animation: vmx-intro-rise 600ms ease-out both;
    }
    .wizard-intro__cta {
      animation: vmx-intro-rise 600ms ease-out 200ms both;
    }
  }
  @keyframes vmx-intro-rise {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }
`;

registerStyle("wizard-intro", CSS);

export function renderStep0Intro(cb: Step0IntroCallbacks): HTMLElement {
  const root = document.createElement("section");
  root.className = "wizard-intro";
  root.setAttribute("aria-label", "vibemix intro");

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
