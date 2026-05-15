/* Phase 33 / Plan 33-01 — TCC deep-link wizard helper tests.
 *
 * Pins the macOS Settings URL ladder per P50:
 *   - macOS 12.3 / 14 use the preference.security?Privacy_<Slot> form
 *   - macOS 15 (Sequoia) uses settings.PrivacySecurity.extension?Privacy_<Slot>
 *   - Unknown majors fall back to the root Privacy pane URL
 * Plus the "Why we need this" copy gate — no AI slop words allowed. */

import { describe, expect, it } from "vitest";

import {
  TCC_PERMISSIONS,
  tccCopyFor,
  tccDeepLinkFor,
  type TccPermission,
} from "../components/tcc-permissions.js";

const SLOP_WORDS = [
  "seamless",
  "seamlessly",
  "leverage",
  "leverages",
  "magical",
  "unlock",
  "unlocks",
  "delight",
  "delights",
  "delightful",
  "supercharge",
  "synergy",
  "elevate",
  "elevates",
  "robust",
];

describe("tccDeepLinkFor — macOS settings deep-link ladder (P50)", () => {
  it("test_tcc_deep_link_macos_12_3_microphone — emits 12.3-style URL", () => {
    expect(tccDeepLinkFor(12, "microphone")).toBe(
      "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
    );
  });

  it("test_tcc_deep_link_macos_14_microphone — emits 14-style URL", () => {
    expect(tccDeepLinkFor(14, "microphone")).toBe(
      "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
    );
  });

  it("test_tcc_deep_link_macos_15_microphone — emits 15-style extension URL", () => {
    expect(tccDeepLinkFor(15, "microphone")).toBe(
      "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Microphone",
    );
  });

  it("test_tcc_deep_link_unknown_version_returns_fallback — pre-12 + NaN both fallback", () => {
    expect(tccDeepLinkFor(0, "microphone")).toBe(
      "x-apple.systempreferences:com.apple.preference.security",
    );
    expect(tccDeepLinkFor(Number.NaN, "microphone")).toBe(
      "x-apple.systempreferences:com.apple.preference.security",
    );
    expect(tccDeepLinkFor(11, "microphone")).toBe(
      "x-apple.systempreferences:com.apple.preference.security",
    );
  });

  it("covers all four permissions on macOS 15", () => {
    const slots: Record<TccPermission, string> = {
      microphone: "Privacy_Microphone",
      "screen-recording": "Privacy_ScreenCapture",
      accessibility: "Privacy_Accessibility",
      automation: "Privacy_Automation",
    };
    for (const perm of TCC_PERMISSIONS) {
      const url = tccDeepLinkFor(15, perm);
      expect(url).toBe(
        `x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?${slots[perm]}`,
      );
    }
  });
});

describe("tccCopyFor — Why we need this copy", () => {
  it("test_tcc_copy_present_for_all_four_permissions", () => {
    for (const perm of TCC_PERMISSIONS) {
      const copy = tccCopyFor(perm);
      expect(typeof copy).toBe("string");
      expect(copy.length).toBeGreaterThan(20);
      const lower = copy.toLowerCase();
      for (const slop of SLOP_WORDS) {
        expect(lower).not.toContain(slop);
      }
    }
  });
});
