/* step-forewarning.ts — Step §Forewarning (Phase 49 INSTALL-03).
 *
 * Two-card OS forewarning surface that prepares the user for the OS-mandated
 * friction points BEFORE the driver fetch fires:
 *   - macOS: BlackHole system-extension approval in System Settings
 *   - Windows: VB-CABLE driver-install UAC prompt
 *
 * Only the platform-relevant card is visible; the other is `display: none`.
 *
 * Every string reads from `copy.steps.forewarning.*` — zero inline literals
 * (gated by scripts/audit/check_no_slop_install.py).
 *
 * Visual contract: CDJ Whisper (--glass-1 surface, --silk text, --glass-edge
 * border). NO border-anim sweep (one-CDJ-one-light: the wizard's single sweep
 * belongs to step-48k-probe success card).
 *
 * Anti-pattern guard: zero hex literals; every color reads `var(--token)`.
 */

import { Button } from "./components/button.js";
import { registerStyle } from "./components/_style-registry.js";
import { copy } from "./copy.js";

export interface ForewarningCallbacks {
  platform: "darwin" | "win32" | "linux";
  onContinue: () => void;
  onBack?: () => void;
}

const CSS = `
  .step-forewarning__heading {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 82, "wght" 600;
    font-size: 22px;
    line-height: 1.3;
    color: var(--silk);
    margin: 0 0 var(--sp-5);
  }
  .step-forewarning__cards {
    display: flex;
    flex-direction: column;
    gap: var(--sp-4);
    margin-bottom: var(--sp-5);
  }
  .step-forewarning__card {
    background: var(--glass-1);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-md);
    padding: var(--sp-5);
  }
  .step-forewarning__card[data-hidden="true"] { display: none; }
  .step-forewarning__card-title {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 600;
    font-size: 13px;
    color: var(--silk);
    margin: 0 0 var(--sp-2);
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  .step-forewarning__card-body {
    font-family: var(--type-body);
    font-size: 14px;
    line-height: 1.55;
    color: var(--silk-65);
    margin: 0;
  }
  .step-forewarning__cta-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-3);
  }
`;

registerStyle("step-forewarning", CSS);

export function createStepForewarning(
  callbacks: ForewarningCallbacks,
): HTMLElement {
  const root = document.createElement("div");
  root.className = "wizard-step step-forewarning";

  const heading = document.createElement("h2");
  heading.className = "step-forewarning__heading";
  heading.textContent = copy.steps.forewarning.section_heading;
  heading.setAttribute("aria-level", "2");

  const cards = document.createElement("div");
  cards.className = "step-forewarning__cards";
  cards.setAttribute("role", "list");

  // Mac card
  const macCard = document.createElement("article");
  macCard.className = "step-forewarning__card";
  macCard.setAttribute("data-hidden", callbacks.platform === "darwin" ? "false" : "true");
  macCard.setAttribute("aria-label", copy.steps.forewarning.mac_title);
  macCard.setAttribute("role", "listitem");
  const macTitle = document.createElement("h3");
  macTitle.className = "step-forewarning__card-title";
  macTitle.textContent = copy.steps.forewarning.mac_title;
  const macBody = document.createElement("p");
  macBody.className = "step-forewarning__card-body";
  macBody.textContent = copy.steps.forewarning.mac_body;
  macCard.append(macTitle, macBody);

  // Win card
  const winCard = document.createElement("article");
  winCard.className = "step-forewarning__card";
  winCard.setAttribute("data-hidden", callbacks.platform === "win32" ? "false" : "true");
  winCard.setAttribute("aria-label", copy.steps.forewarning.win_title);
  winCard.setAttribute("role", "listitem");
  const winTitle = document.createElement("h3");
  winTitle.className = "step-forewarning__card-title";
  winTitle.textContent = copy.steps.forewarning.win_title;
  const winBody = document.createElement("p");
  winBody.className = "step-forewarning__card-body";
  winBody.textContent = copy.steps.forewarning.win_body;
  winCard.append(winTitle, winBody);

  cards.append(macCard, winCard);

  const ctaRow = document.createElement("div");
  ctaRow.className = "step-forewarning__cta-row";

  if (callbacks.onBack) {
    const back = Button({
      label: copy.steps.forewarning.back_cta,
      variant: "ghost",
      onClick: callbacks.onBack,
    });
    ctaRow.append(back);
  } else {
    ctaRow.append(document.createElement("span")); // spacer
  }

  const continueBtn = Button({
    label: copy.steps.forewarning.continue_cta,
    variant: "primary",
    onClick: callbacks.onContinue,
  });
  ctaRow.append(continueBtn);

  root.append(heading, cards, ctaRow);
  return root;
}
