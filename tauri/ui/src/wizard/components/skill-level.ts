/* skill-level.ts — Quick 260529-ifq.
 *
 * Onboarding skill-level surface. Three equally-prominent radio options
 * (Pitfall P67 — no dark patterns, identical CSS/padding/font per row).
 * Default-selected = "intermediate" (the runtime's existing default), so
 * Continue is always armed and the wizard stays non-blocking.
 *
 * Hard rules (mirror telemetry-consent):
 *   - Three `<input type="radio">` controls of identical CSS class.
 *   - The "intermediate" option carries `data-default="true"`.
 *   - Each row carries `data-value` (the skill id) so the selection is
 *     addressable; selected row carries `data-selected="true"`.
 *   - Single accent: amber on the selected row only.
 */

import { registerStyle } from "./_style-registry.js";

export type SkillLevel = "beginner" | "intermediate" | "pro";

export interface SkillLevelProps {
  selected: SkillLevel;
  onSelect: (next: SkillLevel) => void;
}

const OPTIONS: Array<{
  id: SkillLevel;
  label: string;
  desc: string;
  isDefault: boolean;
}> = [
  {
    id: "beginner",
    label: "beginner",
    desc: "learning beats, phrasing, and your first clean transition.",
    isDefault: false,
  },
  {
    id: "intermediate",
    label: "intermediate",
    desc: "mixing in key, riding the eq, building energy across a set.",
    isDefault: true,
  },
  {
    id: "pro",
    label: "pro",
    desc: "tight already — vibemix stays out of the way unless you ask.",
    isDefault: false,
  },
];

const CSS = `
  .vmx-skill-level {
    display: flex;
    flex-direction: column;
    gap: var(--sp-3);
    padding: var(--sp-4);
    border: 1px solid var(--silk-22);
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.02);
  }
  .vmx-skill-level__choices {
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
  }
  .vmx-skill-level__radio-row {
    /* Equal padding for all options — no asymmetric prominence (P67). */
    display: flex;
    align-items: flex-start;
    gap: var(--sp-3);
    padding: var(--sp-3);
    border: 1px solid var(--silk-22);
    border-radius: 4px;
    cursor: pointer;
    user-select: none;
    background: transparent;
    transition: border-color 150ms ease, background 150ms ease;
  }
  .vmx-skill-level__radio-row:hover {
    border-color: var(--silk-65);
  }
  /* Selected = a RECESS, not a rose slab — brand is spent as a low-alpha ring
   * + glow inside a pressed socket (tokens.css: wash-never-fill). */
  .vmx-skill-level__radio-row[data-selected="true"] {
    border-color: var(--brand-35);
    background: radial-gradient(ellipse at top, var(--void-8), var(--void-12));
    box-shadow:
      inset 0 2px 5px rgba(0, 0, 0, 0.55),
      inset 0 0 0 1px var(--brand-22),
      inset 0 0 14px var(--brand-04);
  }
  .vmx-skill-level__radio {
    appearance: none;
    width: 18px;
    height: 18px;
    border: 1.5px solid var(--silk-65);
    border-radius: 50%;
    background: transparent;
    position: relative;
    flex-shrink: 0;
    margin-top: 2px;
    cursor: pointer;
  }
  .vmx-skill-level__radio:checked {
    border-color: var(--amber);
  }
  .vmx-skill-level__radio:checked::after {
    content: "";
    position: absolute;
    left: 3px;
    top: 3px;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--amber);
  }
  .vmx-skill-level__text {
    display: flex;
    flex-direction: column;
    gap: var(--sp-1);
    flex: 1;
  }
  .vmx-skill-level__label {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 500;
    font-size: 14px;
    letter-spacing: 0.02em;
    color: var(--silk);
    text-transform: uppercase;
  }
  .vmx-skill-level__desc {
    font-family: var(--type-body);
    font-size: 12px;
    line-height: 1.4;
    color: var(--silk-65);
  }
`;

export function renderSkillLevelCard(props: SkillLevelProps): HTMLElement {
  registerStyle("vmx-skill-level", CSS);

  const root = document.createElement("div");
  root.className = "vmx-skill-level";

  const choices = document.createElement("div");
  choices.className = "vmx-skill-level__choices";

  for (const opt of OPTIONS) {
    choices.append(
      makeRadioRow({
        id: `skill-${opt.id}`,
        value: opt.id,
        label: opt.label,
        desc: opt.desc,
        name: "skill_level",
        selected: props.selected === opt.id,
        defaultSelected: opt.isDefault,
        onSelect: () => props.onSelect(opt.id),
      }),
    );
  }

  root.append(choices);
  return root;
}

interface RadioRowProps {
  id: string;
  value: SkillLevel;
  label: string;
  desc: string;
  name: string;
  selected: boolean;
  defaultSelected: boolean;
  onSelect: () => void;
}

function makeRadioRow(props: RadioRowProps): HTMLElement {
  const row = document.createElement("label");
  row.className = "vmx-skill-level__radio-row";
  row.htmlFor = props.id;
  row.dataset.value = props.value;
  row.dataset.selected = props.selected ? "true" : "false";
  if (props.defaultSelected) row.dataset.default = "true";

  const radio = document.createElement("input");
  radio.type = "radio";
  radio.id = props.id;
  radio.name = props.name;
  radio.className = "vmx-skill-level__radio";
  radio.checked = props.selected;
  radio.addEventListener("change", () => {
    if (radio.checked) props.onSelect();
  });

  const text = document.createElement("span");
  text.className = "vmx-skill-level__text";

  const label = document.createElement("span");
  label.className = "vmx-skill-level__label";
  label.textContent = props.label;

  const desc = document.createElement("span");
  desc.className = "vmx-skill-level__desc";
  desc.textContent = props.desc;

  text.append(label, desc);
  row.append(radio, text);
  return row;
}
