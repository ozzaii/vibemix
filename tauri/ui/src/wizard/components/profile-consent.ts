/* profile-consent.ts — Phase 32 / PROFILE-05.
 *
 * First-launch consent card: a single checkbox toggle ("Build a profile?")
 * + field-set disclosure (the five allowed fields with one-line each) +
 * the privacy footer ("stored locally only / never uploaded").
 *
 * Default-OFF (PROFILE-05 non-negotiable). The user advances regardless of
 * the toggle state — declining is a first-class choice.
 *
 * CDJ Whisper visual: amber accent on the checkbox when checked; otherwise
 * the section is monochrome --silk on --void. No faux-3D bevels.
 */

import { registerStyle } from "./_style-registry.js";

export interface ProfileConsentProps {
  checked: boolean;
  onToggle: (next: boolean) => void;
}

const CSS = `
  .vmx-profile-consent {
    display: flex;
    flex-direction: column;
    gap: var(--sp-3);
    padding: var(--sp-4);
    border: 1px solid var(--silk-22);
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.02);
  }
  .vmx-profile-consent__row {
    display: flex;
    align-items: center;
    gap: var(--sp-3);
    cursor: pointer;
    user-select: none;
  }
  .vmx-profile-consent__checkbox {
    appearance: none;
    width: 18px;
    height: 18px;
    border: 1.5px solid var(--silk-65);
    border-radius: 3px;
    background: transparent;
    position: relative;
    flex-shrink: 0;
    transition: border-color 150ms ease, background 150ms ease;
    cursor: pointer;
  }
  .vmx-profile-consent__checkbox:hover {
    border-color: var(--silk);
  }
  .vmx-profile-consent__checkbox:checked {
    border-color: var(--amber);
    background: var(--amber-22);
  }
  .vmx-profile-consent__checkbox:checked::after {
    content: "";
    position: absolute;
    left: 4px;
    top: 0px;
    width: 6px;
    height: 11px;
    border: solid var(--amber);
    border-width: 0 2px 2px 0;
    transform: rotate(45deg);
  }
  .vmx-profile-consent__label {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 500;
    font-size: 14px;
    letter-spacing: 0.02em;
    color: var(--silk);
    text-transform: uppercase;
  }
  .vmx-profile-consent__fields {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-top: var(--sp-2);
    padding-left: 30px;
    font-family: var(--type-body);
    font-size: 12px;
    color: var(--silk-65);
    line-height: 1.5;
  }
  .vmx-profile-consent__field-name {
    color: var(--silk);
    font-variation-settings: "wdth" 100, "wght" 500;
  }
  .vmx-profile-consent__footer {
    font-family: var(--type-body);
    font-size: 11px;
    letter-spacing: 0.05em;
    color: var(--silk-40);
    text-transform: uppercase;
    margin-top: var(--sp-2);
    padding-left: 30px;
  }
`;

registerStyle("profile-consent", CSS);

// Field-set disclosure: each entry is the schema key + a one-line description.
// Verbatim — these strings ARE the privacy disclosure.
const FIELDS: Array<{ name: string; desc: string }> = [
  { name: "preferred_genre", desc: "hard_tek, techno, house, or unknown" },
  { name: "avg_session_duration", desc: "session length in minutes" },
  { name: "mix_style_tags", desc: "up to 8 tags (long_blends, quick_cuts, …)" },
  { name: "tempo_preference_bin", desc: "BPM band (128-138, 138-150, …)" },
  { name: "event_response_preferences", desc: "how often to react per event type" },
];

export function renderProfileConsentCard(props: ProfileConsentProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "vmx-profile-consent";
  root.setAttribute("data-testid", "profile-consent-card");

  const label = document.createElement("label");
  label.className = "vmx-profile-consent__row";

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.className = "vmx-profile-consent__checkbox";
  checkbox.checked = props.checked;
  checkbox.setAttribute("data-testid", "profile-consent-checkbox");
  checkbox.addEventListener("change", () => {
    props.onToggle(checkbox.checked);
  });

  const labelText = document.createElement("span");
  labelText.className = "vmx-profile-consent__label";
  labelText.textContent = "Build a profile to personalize coaching";

  label.append(checkbox, labelText);
  root.append(label);

  const fieldList = document.createElement("div");
  fieldList.className = "vmx-profile-consent__fields";
  for (const f of FIELDS) {
    const row = document.createElement("div");
    const name = document.createElement("span");
    name.className = "vmx-profile-consent__field-name";
    name.textContent = f.name;
    row.append(name, document.createTextNode(` · ${f.desc}`));
    fieldList.append(row);
  }
  root.append(fieldList);

  const footer = document.createElement("div");
  footer.className = "vmx-profile-consent__footer";
  footer.textContent = "stored on this machine only · never uploaded";
  root.append(footer);

  return root;
}
