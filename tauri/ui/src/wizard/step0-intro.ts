/* step0-intro.ts — wizard first-paint brand handshake (post-impeccable Wave 1.2).
 *
 * The mock's character moment ("PIONEER DECK / AT 2 AM / A SIGN OF
 * LIFE" at mocks/vibemix-direction-final.html:1195) had no equivalent
 * in the shipped wizard — the user opened a vibemix install to what
 * read as a generic settings dialog. This step ships the missing moment.
 *
 * Visual anatomy:
 *   - Three-line hero. Saira wdth 82 wght 800 at 76px for the lowercase
 *     wordmark stack; wdth 82 wght 700 for the "DJ FRIEND" line, the slogan
 *     em-rule-bracketed in --silk-65 (mock pattern).
 *   - Single rose accent: the "mix" syllable is lit in --brand (one rose
 *     moment per panel, see DESIGN.md §5) — the same two-tone split, same
 *     lowercase case, as the persistent shell sidebar wordmark.
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
  /* FABLE PASS (2026-06-10): the cool blue-black boxed card is GONE — it was
   * the v5 palette in a glowy frame, the first cheap thing a new install saw.
   * The intro now sits on the same lit warm void as the deck: a single
   * hairline frame seating the moment, a low rose dawn beneath the wordmark.
   * Same room from first paint to live set. */
  .wizard-intro::before {
    content: "";
    position: absolute;
    inset: 14px 8px;
    z-index: 0;
    border: 1px solid var(--border-subtle);
    border-radius: var(--rad-lg);
    pointer-events: none;
  }
  .wizard-intro::after {
    content: "";
    position: absolute;
    inset: 15px 9px;
    z-index: 0;
    pointer-events: none;
    border-radius: var(--rad-lg);
    background:
      radial-gradient(120% 80% at 50% 118%, var(--brand-10), var(--brand-04) 40%, transparent 66%);
    opacity: 0.85;
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
      0 0 32px rgba(255, 165, 223, 0.06);
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
    /* Lowercase, tight — the exact case of the persistent shell wordmark, set
     * with the small negative tracking a large display lockup wants. NO
     * text-transform: the syllables abut (gap 0) so "vibemix" reads as one
     * tight word, the same brand mark scaled up, not an uppercase hero variant. */
    letter-spacing: -0.02em;
    display: inline-flex;
    align-items: baseline;
    gap: 0;
    filter: drop-shadow(0 16px 22px rgba(0, 0, 0, 0.58));
  }
  /* The trademark, hero-scale: "VIBE" in ink, "MIX" lit in rose — the same
   * logic the shell sidebar carries, so the brand reads as one thing from the
   * first paint. The lit syllable keeps a single 12px halo (DESIGN.md §4
   * reserves the larger halo for primary-action hover/press; no second halo). */
  .wizard-intro__wordmark-vibe {
    color: var(--silk);
  }
  .wizard-intro__wordmark-mix {
    color: var(--amber);
    font-variation-settings: "wdth" 82, "wght" 800;
    text-shadow: 0 0 12px var(--amber-40);
  }
  /* The category line speaks in the co-host's serif voice, lowercase — the
   * same warm human face as the deck hero, not a shouting condensed banner.
   * (textContent stays "DJ FRIEND"; the case is a material choice.) */
  .wizard-intro__phrase {
    font-family: var(--type-serif);
    font-weight: 400;
    font-size: 46px;
    line-height: 1.05;
    letter-spacing: -0.01em;
    text-transform: lowercase;
    color: var(--silk);
    text-shadow: var(--text-3d);
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
    margin-top: var(--sp-2);
  }
  /* The CTA in the deck's GO LIVE material: a rose-lit slab key with the
   * machined specular top line — the first physical control the user presses
   * is the same instrument they'll play. */
  .wizard-intro__cta .cmp-btn {
    min-width: 200px;
    padding: 16px 32px 15px;
    letter-spacing: 0.26em;
    color: var(--text-primary);
    text-shadow: var(--text-emboss);
    border-color: var(--brand-35);
    border-radius: var(--rad-md);
    background:
      linear-gradient(180deg, var(--brand-22) 0%, var(--brand-10) 50%, var(--brand-06) 100%),
      linear-gradient(180deg, var(--void-12), var(--void-8));
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.18),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45),
      inset 0 0 24px var(--brand-06),
      0 1px 0 rgba(255, 255, 255, 0.04),
      0 6px 18px rgba(176, 112, 160, 0.18),
      0 14px 32px rgba(0, 0, 0, 0.4);
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
    .wizard-intro__cta {
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
    .wizard-intro__wordmark { font-size: 52px; }
    .wizard-intro__phrase { font-size: 30px; }
    .wizard-intro__slogan { font-size: 11px; }
  }
  @media (max-width: 420px) {
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

  const hero = document.createElement("div");
  hero.className = "wizard-intro__hero";

  const wordmark = document.createElement("span");
  wordmark.className = "wizard-intro__wordmark";
  // The SAME wordmark as the shell sidebar: lowercase, "vibe" in ink + "mix" lit
  // in rose, here at hero scale — so the first impression and the persistent
  // chrome are one trademark, identical in case, not two different wordmarks.
  const wordmarkVibe = document.createElement("span");
  wordmarkVibe.className = "wizard-intro__wordmark-vibe";
  wordmarkVibe.textContent = "vibe";
  const wordmarkMix = document.createElement("span");
  wordmarkMix.className = "wizard-intro__wordmark-mix";
  wordmarkMix.textContent = "mix";
  wordmark.append(wordmarkVibe, wordmarkMix);

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
