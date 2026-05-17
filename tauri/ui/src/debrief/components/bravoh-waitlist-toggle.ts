// SPDX-License-Identifier: Apache-2.0
// Plan 44-04 Task 2 — Bravoh waitlist opt-in toggle (LAUNCH-05).
//
// Renders a subtle opt-in toggle in the debrief window. Default OFF.
// When ON, exposes a `<a target="_blank">` link to the canonical Bravoh
// waitlist URL (verbatim from CONTEXT §LAUNCH-05). Not gating, not a form
// intercept — just a link.
//
// Anti-scope-creep (memory `feedback_no_scope_creep_clean_utility`):
//   - No form fields.
//   - No modal.
//   - No analytics fire from the app — the UTM params on the destination
//     URL itself are the entire telemetry surface.
//   - Signed-out telemetry default-off — the component fires NO callback
//     unless the user explicitly clicks the toggle.
//
// Persistence boundary: the mount caller owns the `onToggle` callback and
// wires it to `config_store.bravoh_waitlist_opt_in` (Phase 12 superset
// store, Plan 44-04 Task 1). This component is pure DOM — no IPC inside.
//
// Visual: token-driven CDJ Whisper styling — see `debrief.css`
// `.vmx-bravoh-waitlist-*` rules. Faint amber glow on the active state,
// no shiny gradients (memory `project_visual_direction_cdj_whisper`).

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/**
 * Canonical Bravoh waitlist URL with the LAUNCH-05 UTM tag tuple.
 * VERBATIM from CONTEXT §LAUNCH-05. Do not modify — the launch-day
 * analytics on bravoh.com filter on this exact query string.
 */
export const BRAVOH_WAITLIST_URL =
  "https://bravoh.com/waitlist?utm_source=vibemix&utm_medium=app&utm_campaign=oss-launch";

const TOGGLE_LABEL = "Join Bravoh waitlist (optional)";
const TOGGLE_SUBTITLE =
  "vibemix is built by Bravoh — get notified when the main product opens.";
const LINK_TEXT = "Join the Bravoh waitlist →";

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export interface BravohWaitlistToggleProps {
  /** Initial opt-in state, sourced from `config_store.bravoh_waitlist_opt_in`. */
  initialOptIn: boolean;
  /**
   * Fired on user-driven toggle change. Caller is responsible for
   * persisting the new value (Plan 44-04 Task 1 — config_store).
   *
   * IMPORTANT: NOT fired on mount, NOT fired on imperative `setOptIn`.
   * The callback represents an explicit user intent — that is what
   * LAUNCH-05's "signed-out telemetry default-off" contract pins.
   */
  onToggle: (next: boolean) => void;
}

export interface BravohWaitlistToggleHandle {
  /**
   * Imperative state setter — updates the DOM without firing `onToggle`.
   * Useful for reflecting an externally-persisted value (e.g. after a
   * fresh load from the config store).
   */
  setOptIn(next: boolean): void;
  /** Tear down listeners + remove the mounted DOM. */
  destroy(): void;
}

/**
 * Mount the Bravoh waitlist toggle into `container`. Returns an
 * imperative handle for state updates and teardown.
 *
 * Layout:
 *   <section class="vmx-bravoh-waitlist-row">
 *     <label>
 *       <input type="checkbox" data-vmx-bravoh-toggle />
 *       <span class="vmx-bravoh-waitlist-label">Join Bravoh waitlist (optional)</span>
 *     </label>
 *     <p class="vmx-bravoh-waitlist-subtitle">vibemix is built by Bravoh…</p>
 *     <a class="vmx-bravoh-waitlist-link" href="…" target="_blank"
 *        rel="noopener noreferrer" hidden>Join the Bravoh waitlist →</a>
 *   </section>
 */
export function mountBravohWaitlistToggle(
  container: HTMLElement,
  props: BravohWaitlistToggleProps,
): BravohWaitlistToggleHandle {
  // Clear and stamp the host so re-mounts replace prior content cleanly.
  container.textContent = "";

  const section = document.createElement("section");
  section.className = "vmx-bravoh-waitlist-row";
  section.dataset.optIn = props.initialOptIn ? "true" : "false";

  // Toggle row (label wraps checkbox + text for native a11y).
  const toggleLabel = document.createElement("label");
  toggleLabel.className = "vmx-bravoh-waitlist-toggle-label";

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.className = "vmx-bravoh-waitlist-checkbox";
  checkbox.dataset.vmxBravohToggle = "";
  checkbox.checked = props.initialOptIn;
  checkbox.setAttribute("aria-label", TOGGLE_LABEL);

  const labelText = document.createElement("span");
  labelText.className = "vmx-bravoh-waitlist-label";
  labelText.textContent = TOGGLE_LABEL;

  toggleLabel.append(checkbox, labelText);

  // Subtitle copy — explains the funnel without selling.
  const subtitle = document.createElement("p");
  subtitle.className = "vmx-bravoh-waitlist-subtitle";
  subtitle.textContent = TOGGLE_SUBTITLE;

  // The link — conditionally visible. Kept in the DOM (hidden via the
  // `hidden` attribute) so test queries can introspect href / rel
  // regardless of the current toggle state.
  const link = document.createElement("a");
  link.className = "vmx-bravoh-waitlist-link";
  link.href = BRAVOH_WAITLIST_URL;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = LINK_TEXT;
  link.hidden = !props.initialOptIn;

  section.append(toggleLabel, subtitle, link);
  container.append(section);

  // --- Event wiring ---

  const onChange = (): void => {
    const next = checkbox.checked;
    section.dataset.optIn = next ? "true" : "false";
    link.hidden = !next;
    // Fire the callback EXACTLY ONCE per explicit user toggle, with the
    // post-click state. Setup-time / imperative updates do NOT call this.
    props.onToggle(next);
  };
  checkbox.addEventListener("change", onChange);

  // --- Handle ---

  return {
    setOptIn(next: boolean): void {
      // Update DOM only — do NOT fire onToggle. The caller is the source
      // of truth; firing back would create a write loop.
      if (checkbox.checked !== next) {
        checkbox.checked = next;
      }
      section.dataset.optIn = next ? "true" : "false";
      link.hidden = !next;
    },
    destroy(): void {
      checkbox.removeEventListener("change", onChange);
      section.remove();
    },
  };
}
