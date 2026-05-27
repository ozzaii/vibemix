// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 05 — UnpluggedToast component (UI-SPEC §Component Inventory).
//
// One-off toast surfaced when `ipc.learn.controller_detected` arrives
// with `connected: false`. Renders at the TOP of the Learn window,
// mirrors the `#crash-banner` visual treatment (--led-fault border on
// glass) but auto-dismisses after 4s (this isn't a crash — the
// controller was just unplugged).
//
// Copy: `<display_name> disconnected.` — lowercase verb, period
// terminated, no exclamation. Verbatim from UI-SPEC §Copywriting Contract.
//
// No close button — the toast self-dismisses; adding a close icon would
// imply the user can suppress reconnect notifications, which P91 doesn't
// model.

const AUTO_DISMISS_MS = 4000;

/**
 * Surface the unplugged toast. Idempotent — if one is already mounted
 * we replace its text in place rather than stacking.
 */
export function showUnpluggedToast(displayName: string): void {
  const existing = document.getElementById("learn-unplugged-toast");
  if (existing) {
    existing.textContent = `${displayName} disconnected.`;
    // Restart the auto-dismiss clock.
    const stored = existing.dataset.dismissTimer;
    if (stored) {
      clearTimeout(Number(stored));
    }
    existing.dataset.dismissTimer = String(
      setTimeout(() => existing.remove(), AUTO_DISMISS_MS),
    );
    return;
  }
  const toast = document.createElement("div");
  toast.id = "learn-unplugged-toast";
  toast.className = "learn-unplugged-toast";
  toast.setAttribute("role", "status");
  toast.setAttribute("aria-live", "polite");
  toast.textContent = `${displayName} disconnected.`;
  toast.dataset.dismissTimer = String(
    setTimeout(() => toast.remove(), AUTO_DISMISS_MS),
  );
  document.body.appendChild(toast);
}
