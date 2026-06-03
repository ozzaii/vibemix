/* Phase 12 Wave 3 — render-loop + SessionLayout hot-path tests (Plan 12-04 §Tests).
 *
 * Asserts:
 *   - startRenderLoop / stopRenderLoop are idempotent.
 *   - One rAF queued at any time (single-loop discipline).
 *   - CSS variables on the root mutate to match SessionState every frame.
 *   - Hotkey formatter renders the wire string in DJ-friend shortcut form.
 *   - Sticky-bottom transcript: auto-scrolls when sticky, preserves
 *     position when user has scrolled up.
 *   - Layout projection collapses bridge state onto the layout shape.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  _internals,
  startRenderLoop,
  stopRenderLoop,
} from "../../src/session/render-loop.js";
import {
  _resetSessionStateForTests,
  setSessionState,
} from "../../src/session/state.js";
import {
  defaultState,
  mountSessionLayout,
  renderSessionFrame,
} from "../../src/session/SessionLayout.js";

beforeEach(() => {
  _resetSessionStateForTests();
});

afterEach(() => {
  stopRenderLoop();
  document.body.replaceChildren();
  vi.restoreAllMocks();
});

function host(): HTMLElement {
  const div = document.createElement("div");
  document.body.append(div);
  return div;
}

describe("startRenderLoop / stopRenderLoop", () => {
  it("queues exactly one rAF on start", () => {
    const spy = vi.spyOn(globalThis, "requestAnimationFrame");
    const root = host();
    const m = mountSessionLayout(root);
    startRenderLoop(m);
    expect(spy).toHaveBeenCalledTimes(1);
    stopRenderLoop();
  });

  it("is idempotent — re-start cancels the prior rAF", () => {
    const cancelSpy = vi.spyOn(globalThis, "cancelAnimationFrame");
    const root = host();
    const m = mountSessionLayout(root);
    startRenderLoop(m);
    startRenderLoop(m); // should stop the prior loop first
    expect(cancelSpy).toHaveBeenCalled();
    stopRenderLoop();
  });

  it("stopRenderLoop cancels the pending frame", () => {
    const cancelSpy = vi.spyOn(globalThis, "cancelAnimationFrame");
    const root = host();
    const m = mountSessionLayout(root);
    startRenderLoop(m);
    stopRenderLoop();
    expect(cancelSpy).toHaveBeenCalled();
  });
});

describe("renderSessionFrame — CSS variable hot path", () => {
  it("pokes meter rms variables on the root each frame", () => {
    const root = host();
    const m = mountSessionLayout(root);
    setSessionState({
      meters: {
        music: { rms: 0.42, peak: 0.42 },
        voice: { rms: 0.11, peak: 0.11 },
        mic: { rms: 0.0, peak: 0.0 },
      },
    });
    const layout = _internals.projectToLayoutState({
      ...({
        meters: {
          music: { rms: 0.42, peak: 0.42 },
          voice: { rms: 0.11, peak: 0.11 },
          mic: { rms: 0.0, peak: 0.0 },
        },
        phase: [],
        phaseNowPct: 0.6,
        bpm: 120,
        bpmPeriodMs: 500,
        dropPredBars: 8,
        transcript: [],
        midiEvents: [],
        reactions: [],
        track: null,
        status: {
          livekit: "ok",
          gemini: "ok",
          midi: 1,
          screen: "ok",
        },
        settings: {
          voice: "Adam",
          mode: "hype",
          skill: "intermediate",
          lens: "hype",
          genre: "techno",
          output_device_id: null,
          output_profile: "hp",
          retention_days: 30,
          push_to_mute_hotkey: "cmd+shift+m",
          learn_headphone_device_index: null,
          mood: "hype-man",
          click_through: false,
          lighter_blur: false,
        },
        muted: false,
        cohostStatus: "LISTENING",
        latencyMs: null,
        grounded: true,
        clockText: "12:34:56",
      } as Parameters<typeof _internals.projectToLayoutState>[0]),
    });
    renderSessionFrame(m, layout);

    // "The Deck Speaks": the single master meter is smoothed (0.16 attack
    // from 0) and the foot readouts mirror the snapshot. LISTENING + grounded
    // + all inputs ok → live mode ("").
    expect(m.meterFill.style.width).toBe("6.7%"); // 0.42*100*0.16
    expect(m.bpm.textContent).toBe("120.0");
    expect(m.root.dataset.mode).toBe("");
  });

  it("clamps out-of-range values to [0, 1]", () => {
    const root = host();
    const m = mountSessionLayout(root);
    const layout = _internals.projectToLayoutState({
      meters: {
        music: { rms: 1.5, peak: 1.5 },
        voice: { rms: -0.2, peak: 0 },
        mic: { rms: NaN, peak: 0 },
      },
      phase: [],
      phaseNowPct: 2.0,
      bpm: 0,
      bpmPeriodMs: null,
      dropPredBars: null,
      transcript: [],
      midiEvents: [],
      reactions: [],
      track: null,
      status: { livekit: null, gemini: null, midi: null, screen: null },
      settings: {
        voice: "Adam",
        mode: "hype",
        skill: "intermediate",
        lens: "hype",
        genre: "techno",
        output_device_id: null,
        output_profile: "hp",
        retention_days: 30,
        push_to_mute_hotkey: "cmd+shift+m",
        learn_headphone_device_index: null,
        mood: "hype-man",
        click_through: false,
        lighter_blur: false,
      },
      muted: false,
      cohostStatus: "LISTENING",
      latencyMs: null,
      grounded: true,
      clockText: "00:00:00",
    });
    renderSessionFrame(m, layout);

    // music rms 1.5 clamps to 1 → 100% target; 0.16 attack from 0 = 16.0%.
    // NaN/negative inputs are irrelevant to the single master meter.
    expect(m.meterFill.style.width).toBe("16%"); // CSSOM normalizes "16.0%"
    expect(m.root.dataset.mode).toBe("");
  });

  it("omits --bpm-period-ms when bpmPeriodMs is null", () => {
    const root = host();
    const m = mountSessionLayout(root);
    const layout = _internals.projectToLayoutState({
      meters: {
        music: { rms: 0, peak: 0 },
        voice: { rms: 0, peak: 0 },
        mic: { rms: 0, peak: 0 },
      },
      phase: [],
      phaseNowPct: 0,
      bpm: null,
      bpmPeriodMs: null,
      dropPredBars: null,
      transcript: [],
      midiEvents: [],
      reactions: [],
      track: null,
      status: { livekit: null, gemini: null, midi: null, screen: null },
      settings: {
        voice: "Adam",
        mode: "hype",
        skill: "intermediate",
        lens: "hype",
        genre: "techno",
        output_device_id: null,
        output_profile: "hp",
        retention_days: 30,
        push_to_mute_hotkey: "cmd+shift+m",
        learn_headphone_device_index: null,
        mood: "hype-man",
        click_through: false,
        lighter_blur: false,
      },
      muted: false,
      cohostStatus: "IDLE",
      latencyMs: null,
      grounded: false,
      clockText: "00:00:00",
    });
    renderSessionFrame(m, layout);
    // Property never set → empty string per CSSOM.
    expect(m.root.style.getPropertyValue("--bpm-period-ms")).toBe("");
  });

  it("renders the live claim proof chip from the snapshot policy", () => {
    const root = host();
    const state = defaultState();
    state.claimPolicy = {
      policy: "supported_verdict",
      level: "green",
      reason: "two_deck_audio_window_delta_proof",
      label: "verdict proof",
    };
    const m = mountSessionLayout(root, state);
    const chip = root.querySelector<HTMLElement>(".vmx-claim-policy");
    expect(chip?.hidden).toBe(false);
    expect(chip?.textContent).toBe("verdict proof");
    expect(chip?.dataset.level).toBe("green");
    expect(chip?.getAttribute("title")).toBe(
      "supported_verdict: two_deck_audio_window_delta_proof",
    );
  });

  it("renders the first-move readiness rail without claiming missing screen proof", () => {
    const root = host();
    const state = defaultState();
    state.status.livekit = "ok";
    state.status.gemini = "ok";
    state.status.midi = 1;
    state.status.screen = "unavailable";
    const m = mountSessionLayout(root, state);

    const rail = root.querySelector<HTMLElement>('[data-wire="session.idle-proof"]');
    expect(rail?.hidden).toBe(false);
    expect(rail?.textContent).toContain("audioarmed");
    expect(rail?.textContent).toContain("svenready");
    expect(rail?.textContent).toContain("controllerseen");
    expect(rail?.textContent).toContain("proofunavailable");
    expect(rail?.textContent).toContain("Start playback. Sven waits for proof.");
    expect(
      rail
        ?.querySelector<HTMLElement>('[data-axis="proof"]')
        ?.dataset.state,
    ).toBe("warn");

    state.cohost.status = "LISTENING";
    state.cohost.grounded = true;
    state.cohost.transcript = [{ role: "ai", text: "bar 16 is clean", ts: "00:00:16" }];
    renderSessionFrame(m, state);

    expect(rail?.hidden).toBe(true);
  });
});

describe("hotkey formatter", () => {
  it("renders cmd+shift+m as ⌘⇧M", () => {
    expect(_internals.formatHotkey("cmd+shift+m")).toBe("⌘⇧M");
  });

  it("renders ctrl+shift+m as ⌃⇧M", () => {
    expect(_internals.formatHotkey("ctrl+shift+m")).toBe("⌃⇧M");
  });

  it("renders alt+f4 as ⌥F4", () => {
    expect(_internals.formatHotkey("alt+f4")).toBe("⌥F4");
  });

  it("renders empty string as em-dash", () => {
    expect(_internals.formatHotkey("")).toBe("—");
  });
});

// The sticky-bottom scrolling-transcript behaviour was removed in the
// "The Deck Speaks" rebuild (2026-05-26): there is no scrolling chat log —
// the now-line is the hero and prior lines recede as fixed ghost type, so
// there is nothing to keep stuck to the bottom.

describe("layout projection", () => {
  it("maps muted → REC pill 'off' and unmuted → 'ok'", () => {
    const baseState = {
      meters: {
        music: { rms: 0, peak: 0 },
        voice: { rms: 0, peak: 0 },
        mic: { rms: 0, peak: 0 },
      },
      phase: [],
      phaseNowPct: 0,
      bpm: null,
      bpmPeriodMs: null,
      dropPredBars: null,
      transcript: [],
      midiEvents: [],
      reactions: [],
      track: null,
      status: {
        livekit: "ok" as const,
        gemini: "ok" as const,
        midi: 1,
        screen: "ok" as const,
      },
      settings: {
        voice: "Adam",
        mode: "hype" as const,
        skill: "intermediate" as const,
        lens: "hype" as const,
        genre: "techno",
        output_device_id: null,
        output_profile: "hp" as const,
        retention_days: 30,
        push_to_mute_hotkey: "cmd+shift+m",
        learn_headphone_device_index: null,
        mood: "hype-man" as const,
        click_through: false,
        lighter_blur: false,
      },
      muted: false,
      cohostStatus: "LISTENING" as const,
      latencyMs: null,
      grounded: true,
      clockText: "00:00:00",
    };
    const okLayout = _internals.projectToLayoutState(baseState);
    expect(okLayout.titlebar.rec).toBe("ok");

    const muted = _internals.projectToLayoutState({ ...baseState, muted: true });
    expect(muted.titlebar.rec).toBe("off");
    expect(muted.status.muted).toBe(true);
  });

  it("renders the hotkey on status bar in DJ-friend form", () => {
    const layout = _internals.projectToLayoutState({
      meters: {
        music: { rms: 0, peak: 0 },
        voice: { rms: 0, peak: 0 },
        mic: { rms: 0, peak: 0 },
      },
      phase: [],
      phaseNowPct: 0,
      bpm: null,
      bpmPeriodMs: null,
      dropPredBars: null,
      transcript: [],
      midiEvents: [],
      reactions: [],
      track: null,
      status: { livekit: null, gemini: null, midi: null, screen: null },
      settings: {
        voice: "Adam",
        mode: "coach",
        skill: "intermediate",
        lens: "hype",
        genre: "techno",
        output_device_id: null,
        output_profile: "spk",
        retention_days: 30,
        push_to_mute_hotkey: "ctrl+shift+m",
        learn_headphone_device_index: null,
        mood: "hype-man",
        click_through: false,
        lighter_blur: false,
      },
      muted: true,
      cohostStatus: "IDLE",
      latencyMs: null,
      grounded: false,
      clockText: "00:00:00",
    });
    expect(layout.status.hotkey).toBe("⌃⇧M");
    expect(layout.persona.interaction).toBe("COACH");
    expect(layout.output.profile).toBe("SPK");
  });
});
