/* test_waveform_hidden_until_ready.spec.ts
 *
 * The practice waveform strips (deck A + deck B) mount eagerly but have
 * nothing to draw until a deck loads audio (ipc.learn.waveform_ready). Before
 * this fix they rendered as two dead black boxes parked over the tutor line in
 * an idle lesson. The host now carries data-ready, and learn.css hides it until
 * real waveform data flags "partial" (one deck) or "true" (both). This pins the
 * JS half of that contract (the data-ready transitions); the CSS hide rule is
 * the static twin in styles/learn.css.
 */

import { afterEach, describe, expect, it } from "vitest";

import {
  WaveformDisplay,
  type WaveformReadyPayload,
} from "../../src/learn/waveform-display.js";

function host(): HTMLElement {
  const el = document.createElement("div");
  el.id = "learn-waveform-host";
  el.className = "learn-waveform-host";
  document.body.append(el);
  return el;
}

function deck(
  overrides: Partial<NonNullable<WaveformReadyPayload["decks"]["A"]>> = {},
): WaveformReadyPayload["decks"]["A"] {
  return {
    bpm: 128,
    duration_s: 180,
    peaks: [[10, 20, 5]],
    cues: [],
    ...overrides,
  };
}

function ready(
  decks: WaveformReadyPayload["decks"],
): WaveformReadyPayload {
  return { sample_rate: 48000, beat_interval_s: 0.468, decks };
}

afterEach(() => {
  document.body.replaceChildren();
});

describe("learn waveform strips hide until audio is ready", () => {
  it("mounts hidden (data-ready=false) so an idle lesson never shows the empty boxes", () => {
    const h = host();
    WaveformDisplay(h);
    expect(h.dataset.ready).toBe("false");
  });

  it("names the waveform group through a valid image role", () => {
    const h = host();
    WaveformDisplay(h);
    const waveforms = h.querySelector<HTMLElement>(".learn-waveforms");
    expect(waveforms?.getAttribute("role")).toBe("img");
    expect(waveforms?.getAttribute("aria-label")).toBe("practice waveforms");
  });

  it("reveals partial on one deck, true on both", () => {
    const h = host();
    const wf = WaveformDisplay(h);
    wf.updateWaveforms(ready({ A: deck() }));
    expect(h.dataset.ready).toBe("partial");
    wf.updateWaveforms(ready({ A: deck(), B: deck() }));
    expect(h.dataset.ready).toBe("true");
  });

  it("surfaces whether waveform decks are own tracks or bundled practice loops", () => {
    const h = host();
    const wf = WaveformDisplay(h);
    wf.updateWaveforms(ready({
      A: deck({
        source: "library_save_mode",
        title: "Seed Track",
        artist: "Library Artist",
      }),
      B: deck({
        source: "library_save_mode",
        title: "Target Track",
      }),
    }));

    expect(h.querySelector("[data-source-kind]")?.textContent).toBe("own tracks");
    expect(h.querySelector("[data-source-decks]")?.textContent).toContain("A: Seed Track");
    expect(h.querySelector("[data-source-decks]")?.textContent).toContain("Library Artist");
    expect(h.querySelector("[data-source-decks]")?.textContent).toContain("B: Target Track");

    wf.updateWaveforms(ready({ A: deck(), B: deck() }));
    expect(h.querySelector("[data-source-kind]")?.textContent).toBe("practice loops");
  });

  it("keeps the bundled-loop fallback reason visible when own tracks are unavailable", () => {
    const h = host();
    const wf = WaveformDisplay(h);
    wf.updateWaveforms(ready({
      A: deck({
        source: "bundled_demo",
        source_reason: "library vector store is empty",
      }),
      B: deck({
        source: "bundled_demo",
        source_reason: "library vector store is empty",
      }),
    }));

    expect(h.querySelector("[data-source-kind]")?.textContent).toBe("practice loops");
    expect(h.querySelector("[data-source-decks]")?.textContent).toContain(
      "reason: library vector store is empty",
    );
  });

  it("hides again (false) when both decks unload (back to idle)", () => {
    const h = host();
    const wf = WaveformDisplay(h);
    wf.updateWaveforms(ready({ A: deck(), B: deck() }));
    expect(h.dataset.ready).toBe("true");
    wf.updateWaveforms(ready({}));
    expect(h.dataset.ready).toBe("false");
  });

  it("maps live grade phase into gallop direction and save snap state", () => {
    const h = host();
    const wf = WaveformDisplay(h);

    wf.updateGrade({
      verdict: "drifting",
      phase_error_beats: 0.25,
    });
    expect(h.dataset.gallop).toBe("behind");
    expect(h.dataset.gallopVerdict).toBe("drifting");
    expect(h.dataset.gallopSnap).toBe("false");
    expect(h.dataset.gallopPhase).toBe("0.2500");
    expect(h.style.getPropertyValue("--gallop-shift")).toBe("24px");

    wf.updateGrade({
      verdict: "locked",
      phase_error_beats: 0,
      save_landed: true,
    });
    expect(h.dataset.gallop).toBe("save");
    expect(h.dataset.gallopSnap).toBe("true");
    expect(h.style.getPropertyValue("--gallop-shift")).toBe("0px");

    wf.updateGrade({
      verdict: "trainwreck",
      phase_error_beats: -0.42,
    });
    expect(h.dataset.gallop).toBe("off");
    expect(h.dataset.gallopVerdict).toBe("trainwreck");
  });
});
