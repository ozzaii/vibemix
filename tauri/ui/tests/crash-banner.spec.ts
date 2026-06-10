/* v8.0 P74 (UX-04) — crash-banner reason→message coverage.
 *
 * The failure surfaces a user most needs to understand had ZERO unit coverage
 * (deep-audit-adjacent gap). This pins the actionable guidance for every fatal
 * sentinel — especially "api-key-missing" (exit-4), the "co-host never
 * speaks" sentinel: P71 made the Python side fail LOUD with exit 4,
 * sidecar.rs maps exit 4 → reason "api-key-missing", and this is the UI end.
 * A regression that drops the case would silently degrade the message back to
 * the generic fallback — exactly the silent-dead-end this milestone kills. */

import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock the Tauri primitives initCrashBanner subscribes to — there is no Tauri
// runtime under jsdom (same pattern as tests/settings/drawer.spec.ts).
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async () => undefined),
}));
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async () => () => {}),
}));

import { initCrashBanner, reasonMessage, showFatalBanner } from "../src/crash-banner.js";

describe("reasonMessage", () => {
  it("gives customer-safe guidance for a missing co-host brain config (exit-4)", () => {
    const msg = reasonMessage("api-key-missing", "raw stderr");
    expect(msg).toContain("Sven can't reach the co-host brain");
    expect(msg).toContain("Viber library search");
    expect(msg).toContain("set prep");
    expect(msg.toLowerCase()).toContain("restart");
    expect(msg).not.toContain("Gemini");
    expect(msg).not.toContain("GEMINI_API_KEY");
    expect(msg).not.toContain(".env");
    // Must NOT fall through to the raw fallback.
    expect(msg).not.toBe("raw stderr");
  });

  it("gives the BlackHole install path for a missing audio device", () => {
    const msg = reasonMessage("audio-device-missing", "");
    expect(msg).toContain("BlackHole");
    expect(msg).toContain("blackhole-2ch");
  });

  it("explains the port-in-use case", () => {
    expect(reasonMessage("port-in-use", "")).toContain("already running");
  });

  it("explains ws-unreachable with the Restart affordance", () => {
    expect(reasonMessage("ws-unreachable", "")).toContain("Restart");
  });

  it("uses the fallback for session-mount-failed when no detail given", () => {
    expect(reasonMessage("session-mount-failed", "")).toContain("mount");
  });

  it("falls back to the raw error line for an unknown reason", () => {
    expect(reasonMessage("totally-unknown", "raw error here")).toBe("raw error here");
  });

  it("never returns an empty string even with no reason + no fallback", () => {
    expect(reasonMessage(undefined, "")).toBe("Something stopped and we couldn't read why. Restart usually fixes it.");
  });
});

describe("showFatalBanner (DOM)", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="crash-banner" hidden>
        <span id="crash-error-line"></span>
        <button id="crash-restart">[ Restart ]</button>
      </div>`;
    initCrashBanner();
  });

  it("reveals the banner with the api-key-missing guidance", () => {
    showFatalBanner("api-key-missing");
    const banner = document.getElementById("crash-banner") as HTMLElement;
    const line = document.getElementById("crash-error-line") as HTMLElement;
    expect(banner.hidden).toBe(false);
    expect(line.textContent).toContain("Sven can't reach the co-host brain");
    expect(line.textContent).not.toContain("GEMINI_API_KEY");
  });
});
