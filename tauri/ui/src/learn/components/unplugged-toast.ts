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

// IN-03 fix (REVIEW.md): `setTimeout` returns `number` in the browser and
// a `Timeout` object in node/jsdom. The prior implementation stored the
// handle via `dataset.dismissTimer = String(handle)` and later
// `clearTimeout(Number(stored))` — works in the browser but yields
// `clearTimeout(NaN)` (a silent no-op) in jsdom where `String(Timeout)`
// is `"[object Object]"`. The auto-dismiss restart on duplicate toasts
// would leak the old timer in test fixtures. Track handles in a
// module-scoped WeakMap keyed on the toast element so we never round-trip
// through dataset strings; tear-down survives jsdom equally well.
const dismissTimers = new WeakMap<HTMLElement, ReturnType<typeof setTimeout>>();

/**
 * Surface the unplugged toast. Idempotent — if one is already mounted
 * we replace its text in place rather than stacking.
 */
export function showUnpluggedToast(displayName: string): void {
  const existing = document.getElementById("learn-unplugged-toast");
  if (existing) {
    existing.textContent = `${displayName} disconnected.`;
    // Restart the auto-dismiss clock.
    const prior = dismissTimers.get(existing);
    if (prior !== undefined) {
      clearTimeout(prior);
    }
    dismissTimers.set(
      existing,
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
  dismissTimers.set(
    toast,
    setTimeout(() => toast.remove(), AUTO_DISMISS_MS),
  );
  document.body.appendChild(toast);
}
