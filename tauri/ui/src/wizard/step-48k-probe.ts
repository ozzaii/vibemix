/* step-48k-probe.ts — Step §FormatCheck (Phase 49 INSTALL-10).
 *
 * Post-driver-install BlackHole 48 kHz format probe per memory
 * `project_v4_canonical_baseline`.
 *
 * Invokes `audio_config.py --probe-48k` via Tauri command + renders:
 *   - Success: amber pulse + `[ Start your set ]` CTA
 *   - Fail: warn-bordered card with measured kHz + `[ Fix it for me ]` CTA
 *     + manual link to Audio MIDI Setup (Mac) / Sound settings (Win)
 *
 * Strings from `copy.steps.format_check.*` (zero inline literals).
 */

import { invoke } from "@tauri-apps/api/core";
import { Button } from "./components/button.js";
import { registerStyle } from "./components/_style-registry.js";
import { copy, interpolate } from "./copy.js";

export interface FormatCheckCallbacks {
  platform: "darwin" | "win32" | "linux";
  onComplete: () => void;
  onBack?: () => void;
}

interface ProbeResult {
  ok: boolean;
  measured_khz: number;
  expected_khz: number;
  reason?: string;
}

const CSS = `
  .step-48k__heading {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 82, "wght" 600;
    font-size: 22px;
    color: var(--silk);
    margin: 0 0 var(--sp-5);
  }
  .step-48k__card {
    background: var(--glass-1);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-md);
    padding: var(--sp-5);
    margin-bottom: var(--sp-5);
  }
  .step-48k__card[data-state="ok"] {
    border-color: var(--led-ok);
  }
  .step-48k__card[data-state="fail"] {
    border-color: var(--led-fault);
  }
  .step-48k__status {
    font-family: var(--type-body);
    font-size: 16px;
    color: var(--silk);
    margin: 0 0 var(--sp-3);
  }
  .step-48k__card[data-state="ok"] .step-48k__status { color: var(--led-ok); }
  .step-48k__card[data-state="fail"] .step-48k__status { color: var(--led-fault); }
  .step-48k__actions { display: flex; gap: var(--sp-3); }
  .step-48k__manual-link {
    font-size: 13px;
    color: var(--silk-65);
    text-decoration: underline;
    background: none;
    border: 0;
    cursor: pointer;
    padding: 0;
  }
  .step-48k__cta-row {
    display: flex;
    justify-content: flex-end;
  }
`;

registerStyle("step-48k-probe", CSS);

export function createStep48kProbe(
  callbacks: FormatCheckCallbacks,
): HTMLElement {
  const root = document.createElement("div");
  root.className = "wizard-step step-48k-probe";

  const heading = document.createElement("h2");
  heading.className = "step-48k__heading";
  heading.textContent = copy.steps.format_check.heading;
  root.append(heading);

  const card = document.createElement("div");
  card.className = "step-48k__card";
  card.setAttribute("data-state", "probing");
  card.setAttribute("aria-live", "polite");
  card.setAttribute("role", "status");

  const status = document.createElement("p");
  status.className = "step-48k__status";
  status.textContent = "Checking BlackHole format…";
  card.append(status);

  const actions = document.createElement("div");
  actions.className = "step-48k__actions";
  card.append(actions);

  root.append(card);

  const ctaRow = document.createElement("div");
  ctaRow.className = "step-48k__cta-row";
  const finalBtn = Button({
    label: copy.steps.format_check.final_cta,
    variant: "primary",
    disabled: true,
    onClick: callbacks.onComplete,
  });
  ctaRow.append(finalBtn);
  root.append(ctaRow);

  function renderSuccess(): void {
    card.setAttribute("data-state", "ok");
    status.textContent = copy.steps.format_check.success;
    actions.replaceChildren();
    finalBtn.removeAttribute("disabled");
    finalBtn.setAttribute("aria-disabled", "false");
  }

  function renderFail(measuredKhz: number): void {
    card.setAttribute("data-state", "fail");
    status.textContent = interpolate(copy.steps.format_check.fail, { measured_khz: measuredKhz });
    actions.replaceChildren();
    const fixBtn = Button({
      label: copy.steps.format_check.fix_cta,
      variant: "primary",
      onClick: async () => {
        try {
          await invoke("run_audio_config", { action: "configure-routing" });
        } catch {
          /* warn surfaced via probe re-run */
        }
        // Re-probe after fix-it attempt
        await doProbe();
      },
    });
    const manualLabel = callbacks.platform === "darwin"
      ? copy.steps.format_check.mac_manual
      : copy.steps.format_check.win_manual;
    const manualBtn = document.createElement("button");
    manualBtn.type = "button";
    manualBtn.className = "step-48k__manual-link";
    manualBtn.textContent = manualLabel;
    manualBtn.addEventListener("click", () => {
      void invoke("open_audio_settings", { platform: callbacks.platform });
    });
    actions.append(fixBtn, manualBtn);
  }

  async function doProbe(): Promise<void> {
    try {
      const result = await invoke<ProbeResult>("run_audio_config", {
        action: "probe-48k",
      });
      if (result.ok) {
        renderSuccess();
      } else {
        renderFail(result.measured_khz || 0);
      }
    } catch {
      renderFail(0);
    }
  }

  void doProbe();

  return root;
}
