/* telemetry-consent.ts — Phase 34 / SEC-08.
 *
 * Telemetry consent surface. Two equally-prominent radio options
 * (Pitfall P67 — no dark patterns). Default-selected = "Don't share".
 *
 * Hard rules:
 *   - Two `<input type="radio">` controls of identical CSS class.
 *   - The "Don't share" option carries `data-default="true"`.
 *   - Both labels render with the same `--sp-*` paddings, same font,
 *     same text-transform. No "skip → off" trick.
 *   - The field-set disclosure below lists EVERY datum collected
 *     on opt-in, plus a visible NOT-COLLECTED list.
 */

import { registerStyle } from "./_style-registry.js";

export interface TelemetryConsentProps {
  consent: boolean;
  onToggle: (next: boolean) => void;
}

const CSS = `
  .vmx-telemetry-consent {
    display: flex;
    flex-direction: column;
    gap: var(--sp-3);
    padding: var(--sp-4);
    border: 1px solid var(--silk-22);
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.02);
  }
  .vmx-telemetry-consent__choices {
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
  }
  .vmx-telemetry-consent__radio-row {
    /* Equal padding for both options — no asymmetric prominence (P67). */
    display: flex;
    align-items: center;
    gap: var(--sp-3);
    padding: var(--sp-3);
    border: 1px solid var(--silk-22);
    border-radius: 4px;
    cursor: pointer;
    user-select: none;
    background: transparent;
    transition: border-color 150ms ease, background 150ms ease;
  }
  .vmx-telemetry-consent__radio-row:hover {
    border-color: var(--silk-65);
  }
  .vmx-telemetry-consent__radio-row[data-selected="true"] {
    border-color: var(--amber);
    background: var(--amber-22);
  }
  .vmx-telemetry-consent__radio {
    appearance: none;
    width: 18px;
    height: 18px;
    border: 1.5px solid var(--silk-65);
    border-radius: 50%;
    background: transparent;
    position: relative;
    flex-shrink: 0;
    cursor: pointer;
  }
  .vmx-telemetry-consent__radio:checked {
    border-color: var(--amber);
  }
  .vmx-telemetry-consent__radio:checked::after {
    content: "";
    position: absolute;
    left: 3px;
    top: 3px;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--amber);
  }
  .vmx-telemetry-consent__label {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 500;
    font-size: 14px;
    letter-spacing: 0.02em;
    color: var(--silk);
    text-transform: uppercase;
    flex: 1;
  }
  .vmx-telemetry-consent__disclosure {
    display: flex;
    flex-direction: column;
    gap: var(--sp-1);
    margin-top: var(--sp-2);
    padding-top: var(--sp-3);
    border-top: 1px solid var(--silk-22);
  }
  .vmx-telemetry-consent__disclosure-title {
    font-family: var(--type-body);
    font-variation-settings: "wght" 500;
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--silk-65);
    margin-bottom: var(--sp-1);
  }
  .vmx-telemetry-consent__field {
    font-family: var(--type-body);
    font-size: 12px;
    color: var(--silk-65);
    padding-left: var(--sp-3);
    position: relative;
  }
  .vmx-telemetry-consent__field::before {
    content: "›";
    position: absolute;
    left: 0;
    color: var(--silk-22);
  }
  .vmx-telemetry-consent__field--not-collected {
    color: var(--silk);
    opacity: 0.85;
  }
  .vmx-telemetry-consent__field--not-collected::before {
    content: "✗";
    color: var(--silk-65);
  }
`;

const COLLECTED_ON_OPT_IN = [
  "anonymized error reports (stack hashes; never paths or values)",
  "feature-usage histogram (button-click counts only)",
  "crash banner timing (seconds-since-launch when banner shown)",
];

const NEVER_COLLECTED = [
  "track titles",
  "audio",
  "library contents",
  "MIDI device names",
  "window titles",
];

export function renderTelemetryConsentCard(
  props: TelemetryConsentProps,
): HTMLElement {
  registerStyle("vmx-telemetry-consent", CSS);

  const root = document.createElement("div");
  root.className = "vmx-telemetry-consent";

  const choices = document.createElement("div");
  choices.className = "vmx-telemetry-consent__choices";

  // Order matters for visual symmetry but NOT for default — the
  // `data-default` flag sets the default-selected option (P67).
  // "Don't share" listed first because it is the default; both rows
  // are identical CSS, identical padding, identical font.
  const dontShareRow = makeRadioRow({
    id: "telemetry-off",
    label: "Don't share",
    name: "telemetry_consent",
    selected: !props.consent,
    defaultSelected: true,
    onSelect: () => props.onToggle(false),
  });

  const shareRow = makeRadioRow({
    id: "telemetry-on",
    label: "Share anonymous diagnostics",
    name: "telemetry_consent",
    selected: props.consent,
    defaultSelected: false,
    onSelect: () => props.onToggle(true),
  });

  choices.append(dontShareRow, shareRow);

  const disclosure = document.createElement("div");
  disclosure.className = "vmx-telemetry-consent__disclosure";

  const collectedTitle = document.createElement("div");
  collectedTitle.className = "vmx-telemetry-consent__disclosure-title";
  collectedTitle.textContent = "On opt-in we collect:";
  disclosure.append(collectedTitle);
  for (const field of COLLECTED_ON_OPT_IN) {
    const el = document.createElement("div");
    el.className = "vmx-telemetry-consent__field";
    el.textContent = field;
    disclosure.append(el);
  }

  const notCollectedTitle = document.createElement("div");
  notCollectedTitle.className = "vmx-telemetry-consent__disclosure-title";
  notCollectedTitle.style.marginTop = "var(--sp-2)";
  notCollectedTitle.textContent = "Never collected, ever:";
  disclosure.append(notCollectedTitle);
  for (const field of NEVER_COLLECTED) {
    const el = document.createElement("div");
    el.className =
      "vmx-telemetry-consent__field vmx-telemetry-consent__field--not-collected";
    el.textContent = field;
    disclosure.append(el);
  }

  root.append(choices, disclosure);
  return root;
}

interface RadioRowProps {
  id: string;
  label: string;
  name: string;
  selected: boolean;
  defaultSelected: boolean;
  onSelect: () => void;
}

function makeRadioRow(props: RadioRowProps): HTMLElement {
  const row = document.createElement("label");
  row.className = "vmx-telemetry-consent__radio-row";
  row.htmlFor = props.id;
  row.dataset.selected = props.selected ? "true" : "false";
  if (props.defaultSelected) row.dataset.default = "true";

  const radio = document.createElement("input");
  radio.type = "radio";
  radio.id = props.id;
  radio.name = props.name;
  radio.className = "vmx-telemetry-consent__radio";
  radio.checked = props.selected;
  radio.addEventListener("change", () => {
    if (radio.checked) props.onSelect();
  });

  const text = document.createElement("span");
  text.className = "vmx-telemetry-consent__label";
  text.textContent = props.label;

  row.append(radio, text);
  return row;
}
