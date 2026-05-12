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
        track: null,
        status: {
          livekit: "ok",
          gemini: "ok",
          midi: 1,
          screen: "ok",
        },
        settings: {
          voice: "kore",
          mode: "hype",
          genre: "techno",
          output_device_id: null,
          output_profile: "hp",
          retention_days: 30,
          push_to_mute_hotkey: "cmd+shift+m",
          mood: "hype-man",
          click_through: false,
        },
        muted: false,
        cohostStatus: "LISTENING",
        latencyMs: null,
        grounded: true,
        clockText: "12:34:56",
      } as Parameters<typeof _internals.projectToLayoutState>[0]),
    });
    renderSessionFrame(m, layout);

    expect(m.root.style.getPropertyValue("--meter-music-rms")).toBe("0.42");
    expect(m.root.style.getPropertyValue("--meter-voice-rms")).toBe("0.11");
    expect(m.root.style.getPropertyValue("--meter-mic-rms")).toBe("0");
    expect(m.root.style.getPropertyValue("--phase-now-pct")).toBe("0.6");
    expect(m.root.style.getPropertyValue("--bpm-period-ms")).toBe("500ms");
    expect(m.root.style.getPropertyValue("--clock-text")).toContain("12:34:56");
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
      track: null,
      status: { livekit: null, gemini: null, midi: null, screen: null },
      settings: {
        voice: "kore",
        mode: "hype",
        genre: "techno",
        output_device_id: null,
        output_profile: "hp",
        retention_days: 30,
        push_to_mute_hotkey: "cmd+shift+m",
        mood: "hype-man",
        click_through: false,
      },
      muted: false,
      cohostStatus: "IDLE",
      latencyMs: null,
      grounded: false,
      clockText: "00:00:00",
    });
    renderSessionFrame(m, layout);

    expect(m.root.style.getPropertyValue("--meter-music-rms")).toBe("1");
    expect(m.root.style.getPropertyValue("--meter-voice-rms")).toBe("0");
    expect(m.root.style.getPropertyValue("--meter-mic-rms")).toBe("0");
    expect(m.root.style.getPropertyValue("--phase-now-pct")).toBe("1");
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
      track: null,
      status: { livekit: null, gemini: null, midi: null, screen: null },
      settings: {
        voice: "kore",
        mode: "hype",
        genre: "techno",
        output_device_id: null,
        output_profile: "hp",
        retention_days: 30,
        push_to_mute_hotkey: "cmd+shift+m",
        mood: "hype-man",
        click_through: false,
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

describe("sticky-bottom transcript behaviour", () => {
  it("starts in sticky mode (userScrolledUp=false)", () => {
    const root = host();
    const m = mountSessionLayout(root);
    expect(m.userScrolledUp).toBe(false);
    const tr = m.cohost.querySelector<HTMLElement>(
      ".vmx-cohost__transcript",
    );
    expect(tr).toBeTruthy();
    expect(tr?.dataset.sticky).toBe("true");
  });

  it("scroll listener flips userScrolledUp when distance from bottom > 40px", () => {
    const root = host();
    const m = mountSessionLayout(root);
    const tr = m.cohost.querySelector<HTMLElement>(
      ".vmx-cohost__transcript",
    );
    expect(tr).toBeTruthy();

    // jsdom doesn't compute layout; we stub the geometry getters with
    // configured property descriptors so the listener sees "user is
    // scrolled up 60px from bottom".
    Object.defineProperty(tr!, "scrollHeight", {
      configurable: true,
      get: () => 1000,
    });
    Object.defineProperty(tr!, "clientHeight", {
      configurable: true,
      get: () => 400,
    });
    // scrollTop is a normal property in jsdom; set directly.
    tr!.scrollTop = 540; // distFromBottom = 1000 - (540 + 400) = 60 > 40
    tr!.dispatchEvent(new Event("scroll"));

    expect(m.userScrolledUp).toBe(true);
    expect(tr!.dataset.sticky).toBe("false");
  });

  it("scrolling back into the bottom 40px band resets to sticky", () => {
    const root = host();
    const m = mountSessionLayout(root);
    const tr = m.cohost.querySelector<HTMLElement>(
      ".vmx-cohost__transcript",
    );
    Object.defineProperty(tr!, "scrollHeight", {
      configurable: true,
      get: () => 1000,
    });
    Object.defineProperty(tr!, "clientHeight", {
      configurable: true,
      get: () => 400,
    });

    tr!.scrollTop = 540;
    tr!.dispatchEvent(new Event("scroll"));
    expect(m.userScrolledUp).toBe(true);

    tr!.scrollTop = 580; // distFromBottom = 1000 - 980 = 20 <= 40
    tr!.dispatchEvent(new Event("scroll"));
    expect(m.userScrolledUp).toBe(false);
    expect(tr!.dataset.sticky).toBe("true");
  });
});

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
      track: null,
      status: {
        livekit: "ok" as const,
        gemini: "ok" as const,
        midi: 1,
        screen: "ok" as const,
      },
      settings: {
        voice: "kore",
        mode: "hype" as const,
        genre: "techno",
        output_device_id: null,
        output_profile: "hp" as const,
        retention_days: 30,
        push_to_mute_hotkey: "cmd+shift+m",
        mood: "hype-man" as const,
        click_through: false,
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
      track: null,
      status: { livekit: null, gemini: null, midi: null, screen: null },
      settings: {
        voice: "kore",
        mode: "coach",
        genre: "techno",
        output_device_id: null,
        output_profile: "spk",
        retention_days: 30,
        push_to_mute_hotkey: "ctrl+shift+m",
        mood: "hype-man",
        click_through: false,
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
