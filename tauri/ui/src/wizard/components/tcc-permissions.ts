/* tcc-permissions.ts — Phase 33 / INSTALL-01 / P50.
 *
 * TCC (Transparency, Consent and Control) deep-link helpers for the
 * one-click install wizard. macOS 15 (Sequoia) reorganised the Settings
 * pane URL schemes, so we ship a version-aware ladder + a root-Privacy
 * fallback for unknown majors.
 *
 * Pure functions — no DOM, no Tauri commands. The wizard step component
 * (Plan 33-05) consumes these helpers, calls the Tauri shell to open
 * the URL, and renders the "Why we need this" copy beside each card.
 *
 * 33-RESEARCH §P50 ladder:
 *   macOS 12.3 / 14 : x-apple.systempreferences:com.apple.preference.security
 *                     ?Privacy_<Slot>
 *   macOS 15        : x-apple.systempreferences:com.apple.settings.PrivacySecurity
 *                     .extension?Privacy_<Slot>
 *   fallback        : x-apple.systempreferences:com.apple.preference.security
 *                     (root pane — user navigates manually).
 *
 * Permission names mirror tauri-plugin-macos-permissions surface so the
 * wizard can pass the same enum value through to the plugin's
 * check_permission / request_permission entry points (Plan 33-02). */

export type TccPermission =
  | "microphone"
  | "screen-recording"
  | "accessibility"
  | "automation";

const PRIVACY_SLOT: Record<TccPermission, string> = {
  microphone: "Privacy_Microphone",
  "screen-recording": "Privacy_ScreenCapture",
  accessibility: "Privacy_Accessibility",
  automation: "Privacy_Automation",
};

const FALLBACK_URL =
  "x-apple.systempreferences:com.apple.preference.security";

/**
 * Returns the macOS Settings deep-link URL for the given permission slot.
 *
 * @param macOSMajor — integer macOS major version (12, 13, 14, 15, ...).
 *                     Unknown / pre-12 → fallback root-Privacy URL.
 * @param permission — one of the four TCC slots the wizard manages.
 */
export function tccDeepLinkFor(
  macOSMajor: number,
  permission: TccPermission,
): string {
  const slot = PRIVACY_SLOT[permission];
  if (slot === undefined) {
    return FALLBACK_URL;
  }
  if (!Number.isFinite(macOSMajor) || macOSMajor < 12) {
    return FALLBACK_URL;
  }
  if (macOSMajor >= 15) {
    return `x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?${slot}`;
  }
  // macOS 12.3 / 13 / 14 — pre-Sequoia path.
  return `x-apple.systempreferences:com.apple.preference.security?${slot}`;
}

/**
 * "Why we need this" copy per permission — 2-3 sentences, plain English,
 * no slop ("seamless", "leverage", "delight", "unlock", "magical").
 *
 * Strings are user-facing; UI-SPEC anti-slop bar applies.
 */
const COPY: Record<TccPermission, string> = {
  microphone:
    "vibemix listens to your master output so it can react to the music. Mic stays local — nothing is uploaded unless you talk back.",
  "screen-recording":
    "vibemix watches your DJ software window to ground reactions in what you actually see. Nothing is recorded to disk.",
  accessibility:
    "Used only to read the djay Pro window position so the mascot can sit beside it. No keystrokes are captured.",
  automation:
    "Optional. Lets vibemix read playback metadata directly from supported DJ apps when Now Playing isn't enough.",
};

export function tccCopyFor(permission: TccPermission): string {
  return COPY[permission];
}

export const TCC_PERMISSIONS: ReadonlyArray<TccPermission> = [
  "microphone",
  "screen-recording",
  "accessibility",
  "automation",
];
