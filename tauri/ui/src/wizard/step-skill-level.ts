/* step-skill-level.ts — Quick 260529-ifq.
 *
 * New wizard step inserted between "controller" and "profile-consent":
 * SKILL. Asks the user which DJ level they are
 * (beginner / intermediate / pro). On Continue we emit ipc.wizard.set_skill
 * with the current selection so the sidecar persists it to config.json
 * before the wizard exits — the next cold boot seeds VIBEMIX_SKILL_LEVEL
 * and the co-host boots the matching prompt cell.
 *
 * Pre-selected "intermediate" (the runtime default); Continue advances
 * regardless, so the step is non-blocking (mirrors profile/telemetry steps).
 */

import { PrimaryPanel } from "./components/primary-panel.js";
import { Button } from "./components/button.js";
import { renderSkillLevelCard, type SkillLevel } from "./components/skill-level.js";
import { withStepLeadGlyph } from "./step1-permissions.js";
import { registerStyle } from "./components/_style-registry.js";

/* Hover-glow sweep for the skill-level step (mirrors profile-consent):
 * route --glow-faint into the radio rows + Continue/Back CTAs on
 * :hover / :focus-visible so the interactive affordances read cleaner
 * under cursor without a second accent. */
const CSS = `
  .wizard-step--skill-level button:not([disabled]),
  .wizard-step--skill-level [role="button"]:not([aria-disabled="true"]),
  .wizard-step--skill-level [data-interactive] {
    transition: box-shadow var(--motion-snap) ease-out;
  }
  .wizard-step--skill-level button:not([disabled]):hover,
  .wizard-step--skill-level button:not([disabled]):focus-visible,
  .wizard-step--skill-level [role="button"]:not([aria-disabled="true"]):hover,
  .wizard-step--skill-level [role="button"]:not([aria-disabled="true"]):focus-visible,
  .wizard-step--skill-level [data-interactive]:hover,
  .wizard-step--skill-level [data-interactive]:focus-visible {
    box-shadow: var(--glow-faint);
  }
`;

registerStyle("wizard-step--skill-level", CSS);

export interface SkillLevelState {
  skill: SkillLevel;
}

export interface SkillLevelCallbacks {
  onContinue: () => void;
  onSelect: (next: SkillLevel) => void;
  onBack?: () => void;
}

export function renderStepSkillLevel(
  state: SkillLevelState,
  cb: SkillLevelCallbacks,
): HTMLElement {
  const body = document.createElement("div");

  const heading = document.createElement("h1");
  heading.className = "wizard-step__heading";
  heading.textContent = "SKILL";
  withStepLeadGlyph(heading, 4);

  const subtitle = document.createElement("p");
  subtitle.className = "wizard-step__subtitle";
  subtitle.textContent =
    "let vibemix learn your level. coaching matches where you are.";

  body.append(heading, subtitle);

  body.append(
    renderSkillLevelCard({
      selected: state.skill,
      onSelect: cb.onSelect,
    }),
  );

  const panel = PrimaryPanel({ children: body });
  panel.classList.add("wizard-step__panel-rise");

  const ctaRow = document.createElement("div");
  ctaRow.className = "wizard-step__cta-row";
  ctaRow.dataset.back = cb.onBack ? "true" : "false";
  if (cb.onBack) {
    ctaRow.append(
      Button({
        variant: "secondary",
        state: "armed",
        label: "Back",
        leadingGlyph: "←",
        onClick: cb.onBack,
      }),
    );
  }
  ctaRow.append(
    Button({
      variant: "primary",
      state: "armed",
      label: "Continue",
      leadingGlyph: "[",
      trailingGlyph: "]",
      onClick: cb.onContinue,
    }),
  );

  const root = document.createElement("section");
  root.className = "wizard-step wizard-step--skill-level";
  root.append(panel, ctaRow);
  return root;
}
