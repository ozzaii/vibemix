/* Phase 54 Plan 04 / LIVE-01 (SC4) — hype-mode-indicator vitest spec.
 *
 * Covers the PURE deriveIndicatorState core (no DOM, no animation flake —
 * mirrors mascot/mood.test.ts): the indicator states, the cadence-pulse
 * window, the active-vs-listening recency band, the offline fault state, and
 * the prefers-reduced-motion degrade.
 *
 * The pulse density on screen = the felt cadence (SC4); these tests pin the
 * logic that drives that heartbeat.
 */

import { describe, expect, it } from "vitest";

import type { CohostReaction } from "./state.js";
import {
  ACTIVE_WINDOW_MS,
  PULSE_WINDOW_MS,
  deriveIndicatorState,
  lastReactionArrivalMs,
} from "./hype-mode-indicator.js";

const NOW = 1_700_000_000_000; // fixed epoch ms — deterministic

describe("deriveIndicatorState — indicator states", () => {
  it("Case 1: mode 'coach' → hidden (no amber on screen)", () => {
    const s = deriveIndicatorState({
      mode: "coach",
      live: true,
      lastReactionAtMs: NOW - 100,
      nowMs: NOW,
    });
    expect(s.visible).toBe(false);
    expect(s.label).toBe("");
    expect(s.pulse).toBe(false);
  });

  it("Case 2: hype + live + reaction within PULSE_WINDOW_MS → LIVE / glow-strong / pulse", () => {
    const s = deriveIndicatorState({
      mode: "hype",
      live: true,
      lastReactionAtMs: NOW - 100, // 100ms ago, well inside the 600ms window
      nowMs: NOW,
    });
    expect(s.visible).toBe(true);
    expect(s.label).toBe("HYPE · LIVE");
    expect(s.ledTier).toBe("glow-strong");
    expect(s.pulse).toBe(true);
  });

  it("Case 3: hype + live + reaction past pulse but within ACTIVE_WINDOW_MS → LIVE / glow-soft / no pulse", () => {
    const s = deriveIndicatorState({
      mode: "hype",
      live: true,
      lastReactionAtMs: NOW - 3000, // 3s ago — past pulse, within active window
      nowMs: NOW,
    });
    expect(s.label).toBe("HYPE · LIVE");
    expect(s.ledTier).toBe("glow-soft");
    expect(s.pulse).toBe(false);
  });

  it("Case 4: hype + live + reaction older than ACTIVE_WINDOW_MS → LISTENING / glow-faint", () => {
    const s = deriveIndicatorState({
      mode: "hype",
      live: true,
      lastReactionAtMs: NOW - (ACTIVE_WINDOW_MS + 5000),
      nowMs: NOW,
    });
    expect(s.label).toBe("HYPE · LISTENING");
    expect(s.ledTier).toBe("glow-faint");
    expect(s.pulse).toBe(false);
  });

  it("Case 4b: hype + live + NO reaction yet (null) → LISTENING / glow-faint", () => {
    const s = deriveIndicatorState({
      mode: "hype",
      live: true,
      lastReactionAtMs: null,
      nowMs: NOW,
    });
    expect(s.label).toBe("HYPE · LISTENING");
    expect(s.ledTier).toBe("glow-faint");
    expect(s.pulse).toBe(false);
  });

  it("Case 5: hype + NOT live → OFFLINE / fault / no pulse", () => {
    const s = deriveIndicatorState({
      mode: "hype",
      live: false,
      lastReactionAtMs: NOW - 100,
      nowMs: NOW,
    });
    expect(s.visible).toBe(true);
    expect(s.label).toBe("HYPE · OFFLINE");
    expect(s.ledTier).toBe("fault");
    expect(s.pulse).toBe(false);
  });

  it("Case 6: reducedMotion + within-window reaction → pulse:false, glow-soft (degrade)", () => {
    const s = deriveIndicatorState({
      mode: "hype",
      live: true,
      lastReactionAtMs: NOW - 100, // would normally pulse
      nowMs: NOW,
      reducedMotion: true,
    });
    expect(s.label).toBe("HYPE · LIVE");
    expect(s.ledTier).toBe("glow-soft");
    expect(s.pulse).toBe(false); // no ramp under reduced motion
  });
});

describe("deriveIndicatorState — window boundary behaviour", () => {
  it("a reaction exactly at PULSE_WINDOW_MS still pulses (inclusive boundary)", () => {
    const s = deriveIndicatorState({
      mode: "hype",
      live: true,
      lastReactionAtMs: NOW - PULSE_WINDOW_MS,
      nowMs: NOW,
    });
    expect(s.ledTier).toBe("glow-strong");
    expect(s.pulse).toBe(true);
  });

  it("a future-skewed reaction (negative since) does not falsely pulse", () => {
    // Clock skew: lastReactionAtMs slightly ahead of now. sinceReaction < 0 →
    // not within [0, PULSE_WINDOW_MS]; falls through to LISTENING rather than
    // a phantom pulse.
    const s = deriveIndicatorState({
      mode: "hype",
      live: true,
      lastReactionAtMs: NOW + 5000,
      nowMs: NOW,
    });
    expect(s.pulse).toBe(false);
    expect(s.label).toBe("HYPE · LISTENING");
  });
});

describe("lastReactionArrivalMs — ring → epoch ms", () => {
  function reaction(ts: string): CohostReaction {
    return { ts, text: "x", event_id: "PHASE", citation_strip: [] };
  }

  it("empty ring → null", () => {
    expect(lastReactionArrivalMs([])).toBeNull();
  });

  it("returns the LAST reaction's arrival in epoch ms", () => {
    const ring = [
      reaction("2026-05-21T10:00:00.000Z"),
      reaction("2026-05-21T10:00:05.000Z"),
    ];
    expect(lastReactionArrivalMs(ring)).toBe(
      Date.parse("2026-05-21T10:00:05.000Z"),
    );
  });

  it("malformed ts → null (no NaN leak into the derive math)", () => {
    expect(lastReactionArrivalMs([reaction("not-a-date")])).toBeNull();
  });
});
