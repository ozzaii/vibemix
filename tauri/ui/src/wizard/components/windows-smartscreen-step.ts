/* windows-smartscreen-step.ts — Phase 33 / INSTALL-04.
 *
 * Windows-only wizard step that briefly explains the Defender
 * SmartScreen prompt the user just (likely) clicked through and
 * offers a one-tap "Open install doc" affordance pointing at
 * docs/install/windows-smartscreen.md (or the hosted equivalent).
 *
 * Behaviour:
 *   - On non-Windows platforms: renders nothing (returns an empty
 *     container with data-platform set so the wizard can skip
 *     forward without surfacing the step).
 *   - When the binary is SignPath-signed (Phase 38 secrets land
 *     and the build pipeline produces a trusted MSI), this step
 *     auto-skips at the wizard level — once Defender has reputation
 *     built up, no warning fires and there's nothing to explain.
 *
 * The step is intentionally read-only: no checkbox, no toggle,
 * no setting to persist. Pure information surface. */

export type WindowsSmartScreenPlatform = "win32" | "darwin" | "linux";

export interface WindowsSmartScreenStepProps {
  platform: WindowsSmartScreenPlatform;
  /** True iff the build pipeline signed the binary (Phase 38). When
   *  true and platform === "win32", the step still surfaces a brief
   *  reassurance line but hides the install-doc CTA. */
  signed?: boolean;
  onOpenInstallDoc: () => void;
}

export function renderWindowsSmartScreenStep(
  props: WindowsSmartScreenStepProps,
): HTMLElement {
  const root = document.createElement("div");
  root.className = "wizard-smartscreen-step";
  root.dataset.platform = props.platform;
  root.dataset.signed = props.signed ? "true" : "false";

  if (props.platform !== "win32") {
    // Non-Windows platforms get an empty container — the wizard
    // checks data-platform and advances past the step.
    return root;
  }

  const heading = document.createElement("h2");
  heading.className = "wizard-smartscreen-step__heading";
  heading.textContent = "WINDOWS DEFENDER SMARTSCREEN";

  const body = document.createElement("p");
  body.className = "wizard-smartscreen-step__body";
  body.textContent = props.signed
    ? "Your install was signed. If Defender still flagged it, that's normal until reputation builds up."
    : "If Defender showed a blue \"Windows protected your PC\" dialog, click \"More info\" then \"Run anyway\" to continue. The install doc walks through it.";

  root.append(heading, body);

  if (!props.signed) {
    const cta = document.createElement("button");
    cta.type = "button";
    cta.className = "wizard-smartscreen-step__cta";
    cta.textContent = "Open install doc";
    cta.addEventListener("click", () => props.onOpenInstallDoc());
    root.append(cta);
  }

  return root;
}

/** Public anchor for the install doc. Resolved by the wizard against
 *  the Tauri shell-open allowlist or the in-app docs viewer. */
export const WINDOWS_SMARTSCREEN_DOC_PATH =
  "docs/install/windows-smartscreen.md";
