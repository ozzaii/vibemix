/* Phase 12 Wave 2 — vitest spec for the live-session presentation
 * components. Runs under jsdom (configured in vitest.config.ts).
 *
 * Covers the must-have asserts from 12-03-PLAN.md §Tests:
 *   - Meter: rms=0.5 → 8 segments lit; rms=1.0 → all 16 + peak lit
 *   - PhaseTape: chunks order + flex weights + nowPct marker positioning
 *   - DropChip: bars=null → null; bars=8 → renders; bars=0 → renders w/ rec-flash
 *   - EventRibbon: 15 events → 12 rendered (oldest 3 trimmed)
 *   - Cohost: 200 lines → last 200 rendered; last has .now; lines 6-10 .faded
 *   - StatusBar: livekit=down → click opens tooltip with Recheck button
 *
 * Plus the cross-cutting grep guard the plan demands: assert each
 * component's emitted CSS contains 0 `#[0-9a-fA-F]{3,6}` matches except
 * where the value sits inside a `--paper-*` local var declaration. */

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { renderMeter, setMeterLevels } from "../../src/session/components/meter.js";
import { renderPhaseTape } from "../../src/session/components/phase-tape.js";
import { renderDropChip } from "../../src/session/components/drop-chip.js";
import { renderEventRibbon, type MidiEvent } from "../../src/session/components/event-ribbon.js";
import { renderCohostPanel, type TranscriptLine } from "../../src/session/components/cohost.js";
import { renderStatusBar } from "../../src/session/components/status-bar.js";
import { renderTitlebar } from "../../src/session/components/titlebar.js";
import { renderRocker } from "../../src/session/components/rocker.js";
import { renderPicker } from "../../src/session/components/picker.js";
import { renderPanel } from "../../src/session/components/panel.js";
import { renderMutedBanner } from "../../src/session/components/muted-banner.js";
import { renderTimecode } from "../../src/session/components/timecode.js";
import {
  defaultState,
  mountSessionLayout,
  renderSessionFrame,
} from "../../src/session/SessionLayout.js";

function host(): HTMLElement {
  const div = document.createElement("div");
  document.body.append(div);
  return div;
}

afterEach(() => {
  document.body.replaceChildren();
});

// === Meter ===================================================================

describe("renderMeter / setMeterLevels", () => {
  it("renders 16 segments + a peak needle on mount", () => {
    const m = renderMeter({ label: "music" });
    host().append(m);
    expect(m.querySelectorAll(".vmx-meter__seg")).toHaveLength(16);
    expect(m.querySelector(".vmx-meter__peak")).toBeTruthy();
  });

  it("lights 8 segments when rms=0.5", () => {
    const m = renderMeter({ label: "music" });
    host().append(m);
    const lit = setMeterLevels(m, { rms: 0.5, peak: 0.5 });
    expect(lit).toBe(8);
    const litCount = m.querySelectorAll(".vmx-meter__seg[data-lit='true']").length;
    expect(litCount).toBe(8);
  });

  it("fills from peak too so near-red capture does not look tiny", () => {
    const m = renderMeter({ label: "music" });
    host().append(m);
    const lit = setMeterLevels(m, { rms: 0.12, peak: 0.95 });
    expect(lit).toBe(14);
    expect(m.dataset.litCount).toBe("14");
    const peak = m.querySelector<HTMLElement>(".vmx-meter__peak");
    expect(peak?.style.getPropertyValue("--meter-peak-shown")).toBe("1");
    expect(peak?.style.getPropertyValue("--meter-peak-pct")).toBe("0.95");
  });

  it("lights all 16 segments + shows peak needle at rms=1.0", () => {
    const m = renderMeter({ label: "music" });
    host().append(m);
    setMeterLevels(m, { rms: 1.0, peak: 1.0 });
    expect(
      m.querySelectorAll(".vmx-meter__seg[data-lit='true']").length,
    ).toBe(16);
    const peak = m.querySelector<HTMLElement>(".vmx-meter__peak");
    expect(peak?.style.getPropertyValue("--meter-peak-shown")).toBe("1");
    expect(peak?.style.getPropertyValue("--meter-peak-pct")).toBe("1");
  });

  it("clamps rms input to [0, 1]", () => {
    const m = renderMeter({ label: "voice" });
    host().append(m);
    expect(setMeterLevels(m, { rms: -0.5, peak: null })).toBe(0);
    expect(setMeterLevels(m, { rms: 2.5, peak: null })).toBe(16);
  });

  it("zone mapping: bottom 5 safe, middle 8 warm, top 3 clip", () => {
    const m = renderMeter({ label: "mic" });
    host().append(m);
    const zones = Array.from(m.querySelectorAll<HTMLElement>(".vmx-meter__seg")).map(
      (s) => s.dataset.zone,
    );
    const safeCount = zones.filter((z) => z === "safe").length;
    const warmCount = zones.filter((z) => z === "warm").length;
    const clipCount = zones.filter((z) => z === "clip").length;
    expect(safeCount).toBe(5);
    expect(warmCount).toBe(8);
    expect(clipCount).toBe(3);
  });
});

// === PhaseTape ===============================================================

describe("renderPhaseTape", () => {
  it("renders chunks in order with correct flex weights", () => {
    const tape = renderPhaseTape({
      chunks: [
        { kind: "silent", weight: 0.5, label: "silent" },
        { kind: "groove", weight: 1.8, label: "groove" },
        { kind: "build", weight: 1.2, label: "build" },
      ],
      nowPct: 50,
    });
    host().append(tape);
    const chunks = Array.from(tape.querySelectorAll<HTMLElement>(".vmx-phase-chunk"));
    expect(chunks).toHaveLength(3);
    expect(chunks[0]?.dataset.kind).toBe("silent");
    expect(chunks[1]?.dataset.kind).toBe("groove");
    expect(chunks[2]?.dataset.kind).toBe("build");
    expect(chunks[0]?.style.flexGrow).toBe("0.5");
    expect(chunks[1]?.style.flexGrow).toBe("1.8");
    expect(chunks[2]?.style.flexGrow).toBe("1.2");
  });

  it("positions NOW marker via --phase-now-pct custom property", () => {
    const tape = renderPhaseTape({
      chunks: [{ kind: "groove", weight: 1, label: "groove" }],
      nowPct: 62,
    });
    host().append(tape);
    const marker = tape.querySelector<HTMLElement>(".vmx-phase-tape__marker");
    expect(marker?.style.getPropertyValue("--phase-now-pct")).toBe("62%");
  });

  it("clamps nowPct to [0, 100]", () => {
    const tape = renderPhaseTape({
      chunks: [{ kind: "silent", weight: 1, label: "x" }],
      nowPct: 150,
    });
    host().append(tape);
    const marker = tape.querySelector<HTMLElement>(".vmx-phase-tape__marker");
    expect(marker?.style.getPropertyValue("--phase-now-pct")).toBe("100%");
  });
});

// === DropChip ================================================================

describe("renderDropChip", () => {
  it("returns null when bars=null", () => {
    const chip = renderDropChip({ bars: null });
    expect(chip).toBeNull();
  });

  it("renders chip when bars=8", () => {
    const chip = renderDropChip({ bars: 8, bpmPeriodMs: 500 });
    expect(chip).toBeTruthy();
    expect(chip!.dataset.bars).toBe("8");
    expect(chip!.querySelector(".vmx-drop-chip__count")?.textContent).toBe("08:00");
  });

  it("renders with rec-flash class when bars=0", () => {
    const chip = renderDropChip({ bars: 0 });
    expect(chip).toBeTruthy();
    expect(chip!.classList.contains("rec-flash")).toBe(true);
    expect(chip!.dataset.bars).toBe("0");
  });

  it("propagates bpmPeriodMs to inline CSS variable", () => {
    const chip = renderDropChip({ bars: 4, bpmPeriodMs: 480 });
    expect(chip!.style.getPropertyValue("--bpm-period-ms")).toBe("480ms");
  });
});

// === EventRibbon =============================================================

describe("renderEventRibbon", () => {
  it("trims to last 6 events when 15 provided", () => {
    // 2026-05-26 /impeccable critique P3: cap dropped 12 → 6 (a dozen
    // mono chips was the one un-glanceable region mid-mix).
    const events: MidiEvent[] = Array.from({ length: 15 }, (_, i) => ({
      id: `evt-${i}`,
      label: `EVT ${i}`,
      ageMs: 100 + i * 10,
    }));
    const ribbon = renderEventRibbon({ events });
    host().append(ribbon);
    const chips = ribbon.querySelectorAll(".vmx-event-chip");
    expect(chips).toHaveLength(6);
    // Oldest 9 (ids 0-8) trimmed — first visible should be evt-9.
    expect((chips[0] as HTMLElement).dataset.id).toBe("evt-9");
    expect((chips[5] as HTMLElement).dataset.id).toBe("evt-14");
  });

  it("buckets ages into now / warm / cool", () => {
    const events: MidiEvent[] = [
      { id: "a", label: "A", ageMs: 100 },   // now
      { id: "b", label: "B", ageMs: 2000 },  // warm
      { id: "c", label: "C", ageMs: 8000 },  // cool
    ];
    const ribbon = renderEventRibbon({ events });
    host().append(ribbon);
    const chips = Array.from(ribbon.querySelectorAll<HTMLElement>(".vmx-event-chip"));
    expect(chips[0]?.dataset.age).toBe("now");
    expect(chips[1]?.dataset.age).toBe("warm");
    expect(chips[2]?.dataset.age).toBe("cool");
  });

  it("renders empty when given no events", () => {
    const ribbon = renderEventRibbon({ events: [] });
    host().append(ribbon);
    expect(ribbon.querySelectorAll(".vmx-event-chip")).toHaveLength(0);
  });
});

// === Cohost transcript =======================================================

describe("renderCohostPanel", () => {
  it("caps live transcript to MAX_LIVE_TRANSCRIPT_LINES (3); last has .now tier, prior 2 are .faded", () => {
    // 2026-05-19 /impeccable critique round 4 (Kaan: "OVERHAUL"): live
    // transcript is now a glance surface, capped at 3 lines. Full
    // 200-line history lives in the debrief window only — the cohost
    // panel renders the latest reaction + 2 faded peers + a "see all"
    // footer link. State ring still holds every line so the debrief
    // receives everything.
    const lines: TranscriptLine[] = Array.from({ length: 200 }, (_, i) => ({
      role: "ai",
      text: `line-${i}`,
      ts: "00:00:00",
    }));
    const panel = renderCohostPanel({
      status: "TALKING",
      transcript: lines,
      latencyMs: 820,
      grounded: true,
    });
    host().append(panel);
    const msgs = panel.querySelectorAll<HTMLElement>(".vmx-cohost__msg");
    expect(msgs).toHaveLength(3);
    const last = msgs[msgs.length - 1];
    expect(last?.dataset.tier).toBe("now");
    expect(msgs[0]?.dataset.tier).toBe("faded");
    expect(msgs[1]?.dataset.tier).toBe("faded");
    expect(last?.textContent).toContain("line-199");
  });

  it("caps live transcript to 3 lines regardless of input length", () => {
    const lines: TranscriptLine[] = Array.from({ length: 250 }, (_, i) => ({
      role: "ai",
      text: `line-${i}`,
      ts: "",
    }));
    const panel = renderCohostPanel({
      status: "TALKING",
      transcript: lines,
      latencyMs: null,
      grounded: false,
    });
    host().append(panel);
    expect(
      panel.querySelectorAll<HTMLElement>(".vmx-cohost__msg").length,
    ).toBe(3);
  });

  it("renders the see-all footer link when transcript has reactions + handler is wired", () => {
    const lines: TranscriptLine[] = Array.from({ length: 12 }, (_, i) => ({
      role: "ai",
      text: `line-${i}`,
      ts: "00:00:00",
    }));
    let opened = 0;
    const panel = renderCohostPanel({
      status: "LISTENING",
      transcript: lines,
      latencyMs: null,
      grounded: true,
      onOpenAllReactions: () => {
        opened++;
      },
    });
    host().append(panel);
    const seeAll = panel.querySelector<HTMLElement>(".vmx-cohost__see-all");
    expect(seeAll).toBeTruthy();
    expect(seeAll?.dataset.state).toBe("linked");
    const link = panel.querySelector<HTMLButtonElement>(
      ".vmx-cohost__see-all-link",
    );
    expect(link?.textContent).toContain("12 reactions");
    link?.click();
    expect(opened).toBe(1);
  });

  it("see-all footer renders the empty-state placeholder when N=0", () => {
    // 2026-05-19 critique round 5 (Kaan: "unique fun young"): the
    // affordance teaches itself during the quiet opening of a session.
    // The footer line stays visible at silk-25 with placeholder copy
    // so the user knows the debrief path exists before the first
    // reaction lands.
    const panel = renderCohostPanel({
      status: "LISTENING",
      transcript: [],
      latencyMs: null,
      grounded: true,
      onOpenAllReactions: () => {},
    });
    host().append(panel);
    const seeAll = panel.querySelector<HTMLElement>(".vmx-cohost__see-all");
    expect(seeAll?.dataset.state).toBe("empty");
    const placeholder = panel.querySelector<HTMLElement>(
      ".vmx-cohost__see-all-empty",
    );
    expect(placeholder?.textContent).toContain("no reactions yet");
    expect(placeholder?.textContent).toContain("debrief opens after the first one");
    // No clickable link in empty state.
    expect(
      panel.querySelector<HTMLButtonElement>(".vmx-cohost__see-all-link"),
    ).toBeNull();
  });

  it("see-all footer renders a link even when N is below the live cap (rail height stays stable)", () => {
    // 2026-05-19 critique round 5 (Kaan: "unique fun young"): the
    // link is always-on at N>=1 so the affordance is observable from
    // the first reaction. Two reactions visible in the glance still
    // get the debrief link because debrief carries audio quote +
    // citation context the live surface drops.
    const lines: TranscriptLine[] = Array.from({ length: 2 }, (_, i) => ({
      role: "ai",
      text: `line-${i}`,
      ts: "",
    }));
    const panel = renderCohostPanel({
      status: "LISTENING",
      transcript: lines,
      latencyMs: null,
      grounded: true,
      onOpenAllReactions: () => {},
    });
    host().append(panel);
    const seeAll = panel.querySelector<HTMLElement>(".vmx-cohost__see-all");
    expect(seeAll?.dataset.state).toBe("linked");
    const link = panel.querySelector<HTMLButtonElement>(
      ".vmx-cohost__see-all-link",
    );
    expect(link?.textContent).toContain("2 reactions");
  });

  it("see-all footer is hidden when no click handler is wired", () => {
    const lines: TranscriptLine[] = Array.from({ length: 5 }, (_, i) => ({
      role: "ai",
      text: `line-${i}`,
      ts: "",
    }));
    const panel = renderCohostPanel({
      status: "LISTENING",
      transcript: lines,
      latencyMs: null,
      grounded: true,
      // onOpenAllReactions intentionally omitted.
    });
    host().append(panel);
    const seeAll = panel.querySelector<HTMLElement>(".vmx-cohost__see-all");
    expect(seeAll?.dataset.empty).toBe("true");
    expect(seeAll?.style.visibility).toBe("hidden");
  });

  // Critique 2026-05-14: the foot now renders LED + label only — the
  // amber tabular-mono latency readout was retired (anti-slop, real DJs
  // don't read latency). Latency stays on the prop interface for a
  // future Settings → Debug pane.
  it("foot shows READING THE ROOM (LED + label only, no latency readout) when grounded=true", () => {
    // 2026-05-19 /impeccable critique fix round 2: "GROUNDED ON AUDIO
    // + SCREEN" was Bravoh-internal anti-hallucination jargon visible
    // 99% of the live session. Renamed to a DJ-vocabulary phrase that
    // signals "the cohost is paying attention" without the engineer
    // language. The grounded boolean prop is unchanged.
    const panel = renderCohostPanel({
      status: "LISTENING",
      transcript: [],
      latencyMs: 820,
      grounded: true,
    });
    host().append(panel);
    const foot = panel.querySelector<HTMLElement>(".vmx-cohost__foot");
    expect(foot?.dataset.grounded).toBe("true");
    expect(foot?.querySelector(".vmx-cohost__foot-lbl")?.textContent).toBe(
      "READING THE ROOM",
    );
    expect(foot?.querySelector(".vmx-cohost__foot-latency")).toBeNull();
  });

  it("foot shows TUNING IN when grounded=false", () => {
    const panel = renderCohostPanel({
      status: "IDLE",
      transcript: [],
      latencyMs: null,
      grounded: false,
    });
    host().append(panel);
    const foot = panel.querySelector<HTMLElement>(".vmx-cohost__foot");
    expect(foot?.dataset.grounded).toBe("false");
    expect(foot?.querySelector(".vmx-cohost__foot-lbl")?.textContent).toBe(
      "TUNING IN",
    );
  });

  // Phase 13-03 — the 42×42 mascot placeholder bubble was dropped from the
  // transcript header (CONTEXT.md Open Q 2). This assertion pins the
  // deletion so a future revert can't silently reintroduce the corner.
  it("header has NO mascot placeholder bubble (Phase 13 drop)", () => {
    const panel = renderCohostPanel({
      status: "LISTENING",
      transcript: [],
      latencyMs: null,
      grounded: true,
    });
    host().append(panel);
    expect(panel.querySelector(".vmx-cohost__mascot")).toBeNull();
    // The header still mounts and carries the status row (no name span;
    // AVERY moniker dropped — cohost is name-less, vibemix-as-instrument).
    const header = panel.querySelector<HTMLElement>(".vmx-cohost__header");
    expect(header).toBeTruthy();
    expect(panel.querySelector(".vmx-cohost__name")).toBeNull();
    expect(
      panel.querySelector<HTMLElement>(".vmx-cohost__status")?.dataset.state,
    ).toBe("LISTENING");
  });
});

// === StatusBar tooltip =======================================================

describe("renderStatusBar", () => {
  it("renders 4 badges with no brand signature on the live screen", () => {
    const sb = renderStatusBar({
      livekit: "ok",
      gemini: "ok",
      midi: 1,
      screen: "ok",
      muted: false,
      hotkey: "⌘⇧M",
    });
    host().append(sb);
    expect(sb.querySelectorAll(".vmx-statusbar__badge")).toHaveLength(4);
    // "made by bravoh" brand vanity stripped from the live performance screen.
    expect(sb.querySelector(".vmx-statusbar__sig")).toBeNull();
  });

  it("adds a voice-muted badge only when the voice engine is muted", () => {
    const ok = renderStatusBar({
      livekit: "ok",
      gemini: "ok",
      midi: 1,
      screen: "ok",
      voice: "ok",
      muted: false,
      hotkey: "⌘⇧M",
    });
    expect(ok.querySelector('.vmx-statusbar__badge[data-key="voice"]')).toBeNull();

    const muted = renderStatusBar({
      livekit: "ok",
      gemini: "ok",
      midi: 1,
      screen: "ok",
      voice: "muted",
      muted: false,
      hotkey: "⌘⇧M",
    });
    const voice = muted.querySelector<HTMLElement>('.vmx-statusbar__badge[data-key="voice"]');
    expect(voice?.textContent).toContain("VOICE MUTED");
    expect(voice?.dataset.clickable).toBe("false");
    expect(voice?.getAttribute("title")).toBe("Local voice · muted");
  });

  it("muted indicator shows when muted=true", () => {
    const sb = renderStatusBar({
      livekit: "ok",
      gemini: "ok",
      midi: 1,
      screen: "ok",
      muted: true,
      hotkey: "⌘⇧M",
    });
    host().append(sb);
    const muted = sb.querySelector<HTMLElement>(".vmx-statusbar__muted");
    expect(muted?.hidden).toBe(false);
    expect(muted?.textContent).toContain("MUTED");
    expect(muted?.textContent).toContain("⌘⇧M");
  });

  it("livekit=down badge is clickable and opens tooltip with Recheck button", () => {
    const fired: string[] = [];
    const sb = renderStatusBar({
      livekit: "down",
      gemini: "ok",
      midi: 1,
      screen: "ok",
      muted: false,
      hotkey: "⌘⇧M",
      errors: { livekit: "test-error" },
      onRecheck: (key) => fired.push(key),
    });
    host().append(sb);
    const livekitBadge = sb.querySelector<HTMLButtonElement>(
      '.vmx-statusbar__badge[data-key="livekit"]',
    );
    expect(livekitBadge).toBeTruthy();
    expect(livekitBadge!.dataset.clickable).toBe("true");
    // Initially closed
    expect(livekitBadge!.dataset.tooltipOpen).toBe("false");
    // Click opens
    livekitBadge!.click();
    expect(livekitBadge!.dataset.tooltipOpen).toBe("true");
    // Tooltip contains Recheck button
    const recheckBtn = livekitBadge!.querySelector<HTMLButtonElement>(
      ".vmx-statusbar__tooltip-btn",
    );
    expect(recheckBtn).toBeTruthy();
    expect(recheckBtn!.textContent).toContain("Recheck");
    // Tooltip message present
    expect(
      livekitBadge!.querySelector(".vmx-statusbar__tooltip-msg")?.textContent,
    ).toBe("test-error");
    // Clicking Recheck fires onRecheck("livekit")
    recheckBtn!.click();
    expect(fired).toEqual(["livekit"]);
  });

  it("midi=0 badge is clickable (treated as down)", () => {
    const sb = renderStatusBar({
      livekit: "ok",
      gemini: "ok",
      midi: 0,
      screen: "ok",
      muted: false,
      hotkey: "⌘⇧M",
    });
    host().append(sb);
    const midiBadge = sb.querySelector<HTMLButtonElement>(
      '.vmx-statusbar__badge[data-key="midi"]',
    );
    expect(midiBadge?.dataset.clickable).toBe("true");
    expect(midiBadge?.dataset.state).toBe("down");
    expect(
      midiBadge?.querySelector(".vmx-statusbar__tooltip-msg")?.textContent,
    ).toContain("no controller motion is reaching vibemix");
    expect(
      midiBadge?.querySelector(".vmx-statusbar__tooltip-msg")?.textContent,
    ).toContain("enable MIDI output");
  });

  it("names a connected controller that has not sent motion yet", () => {
    const sb = renderStatusBar({
      livekit: "ok",
      gemini: "ok",
      midi: 0,
      midiActivity: "connected_no_midi_traffic",
      midiDevice: "DDJ-FLX4",
      screen: "ok",
      muted: false,
      hotkey: "⌘⇧M",
    });
    host().append(sb);

    const midiBadge = sb.querySelector<HTMLButtonElement>(
      '.vmx-statusbar__badge[data-key="midi"]',
    );
    expect(midiBadge?.dataset.state).toBe("down");
    expect(midiBadge?.textContent).toContain("DDJ-FLX4 · WAITING");
    expect(midiBadge?.getAttribute("title")).toBe("DDJ-FLX4 · connected, waiting for motion");
    expect(
      midiBadge?.querySelector(".vmx-statusbar__tooltip-msg")?.textContent,
    ).toContain("DDJ-FLX4 is connected, but no MIDI frames have landed");
  });
});

// === Titlebar / rocker / picker smoke =======================================

describe("renderTitlebar", () => {
  // Critique 2026-05-14: trimmed the triple LIVE/REC/SYS pill row to
  // a single LIVE indicator (Pioneer hardware labels the one that
  // matters). REC + SYS state still flows through SessionLayout's
  // diff loop — setTitlebarPill no-ops when the DOM node is absent.
  it("renders wordmark + 1 pill (LIVE) + clock + settings gear", () => {
    const tb = renderTitlebar({
      live: "ok",
      rec: "ok",
      sys: "ok",
      clock: "02:44:31",
    });
    host().append(tb);
    expect(tb.querySelector(".vmx-titlebar__wordmark")?.textContent).toBe("vibemix");
    const pills = tb.querySelectorAll<HTMLElement>(".vmx-titlebar__pill");
    expect(pills).toHaveLength(1);
    expect(pills[0]?.dataset.key).toBe("live");
    expect(tb.querySelector(".vmx-titlebar__clock")?.textContent).toBe("02:44:31");
    expect(tb.querySelector(".vmx-titlebar__settings")).toBeTruthy();
  });

  it("settings click invokes callback", () => {
    let clicked = 0;
    const tb = renderTitlebar({
      live: "ok",
      rec: "ok",
      sys: "ok",
      clock: "00:00:00",
      onSettingsClick: () => clicked++,
    });
    host().append(tb);
    tb.querySelector<HTMLButtonElement>(".vmx-titlebar__settings")!.click();
    expect(clicked).toBe(1);
  });
});

describe("renderRocker", () => {
  it("marks active option and fires onChange on non-active click", () => {
    let changed: string | null = null;
    const r = renderRocker({
      options: [
        { id: "BEG", label: "BEG" },
        { id: "INT", label: "INT" },
        { id: "PRO", label: "PRO" },
      ],
      active: "PRO",
      onChange: (id) => (changed = id),
    });
    host().append(r);
    const active = r.querySelector<HTMLElement>('.vmx-rocker__seg[data-active="true"]');
    expect(active?.dataset.id).toBe("PRO");
    r.querySelector<HTMLButtonElement>('.vmx-rocker__seg[data-id="INT"]')!.click();
    expect(changed).toBe("INT");
    // Optimistic repaint (2026-05-26 "no buttons work" fix): the lit segment
    // moves to the clicked id immediately, before the ipc.settings.set round-
    // trip — the drawer has no settings.state refresh path, so without this
    // the active segment never moved and the control looked dead.
    expect(
      r.querySelector<HTMLElement>('.vmx-rocker__seg[data-active="true"]')?.dataset.id,
    ).toBe("INT");
    expect(
      r.querySelector<HTMLElement>('.vmx-rocker__seg[data-id="PRO"]')?.dataset.active,
    ).toBe("false");
  });

  it("optimistic flip is a no-op when re-clicking the already-active segment", () => {
    let calls = 0;
    const r = renderRocker({
      options: [
        { id: "hp", label: "HP" },
        { id: "spk", label: "SPK" },
      ],
      active: "hp",
      onChange: () => calls++,
    });
    host().append(r);
    r.querySelector<HTMLButtonElement>('.vmx-rocker__seg[data-id="hp"]')!.click();
    expect(calls).toBe(0); // already active → guard returns before onChange
    expect(
      r.querySelector<HTMLElement>('.vmx-rocker__seg[data-active="true"]')?.dataset.id,
    ).toBe("hp");
  });
});

describe("renderPicker", () => {
  it("opens dropdown on click", () => {
    const p = renderPicker({
      label: "VOICE",
      value: "Adam",
      options: [
        { id: "Adam", label: "Adam" },
        { id: "Bella", label: "Bella" },
      ],
    });
    host().append(p);
    expect(p.dataset.open).toBe("false");
    p.querySelector<HTMLButtonElement>(".vmx-picker__row")!.click();
    expect(p.dataset.open).toBe("true");
  });

  it("renders auto pill when autoPill=true", () => {
    const p = renderPicker({
      label: "GENRE",
      value: "techno",
      autoPill: true,
      options: [],
    });
    host().append(p);
    expect(p.querySelector(".vmx-picker__auto")?.textContent).toBe("AUTO");
  });
});

describe("renderMutedBanner", () => {
  it("renders MUTED label + hotkey caption", () => {
    const b = renderMutedBanner({ hotkey: "⌘⇧M" });
    host().append(b);
    expect(b.textContent).toContain("MUTED");
    expect(b.textContent).toContain("⌘⇧M");
  });
});

describe("renderPanel", () => {
  it("renders header + badge + body children", () => {
    const child = document.createElement("p");
    child.textContent = "child";
    const p = renderPanel({ header: "PERSONA", badge: "CFG", children: child });
    host().append(p);
    expect(p.querySelector(".vmx-panel__header")?.textContent).toContain("PERSONA");
    expect(p.querySelector(".vmx-panel__badge")?.textContent).toBe("CFG");
    expect(p.querySelector(".vmx-panel__body p")?.textContent).toBe("child");
  });
});

describe("renderTimecode", () => {
  it("renders hero clock + track title + meta cells", () => {
    const t = renderTimecode({
      clock: "02:44:31",
      bpm: 140,
      key: "Am",
      deck: "A",
      track: { title: "Strobe", artist: "Deadmau5" },
      genre: "techno",
    });
    host().append(t);
    expect(t.querySelector(".vmx-timecode__hero-clock")?.textContent).toBe("02:44:31");
    expect(t.querySelector<HTMLElement>(".vmx-timecode__title")?.dataset.empty).toBe("false");
    expect(t.querySelector(".vmx-timecode__title")?.textContent).toContain("Strobe");
    expect(t.querySelector(".vmx-timecode__title .sub")?.textContent).toBe("Deadmau5");
    const cells = t.querySelectorAll<HTMLElement>(".vmx-timecode__meta-cell");
    expect(cells).toHaveLength(3);
    expect(cells[0]?.querySelector("b")?.textContent).toBe("140");
    expect(cells[1]?.querySelector("b")?.textContent).toBe("Am");
    expect(cells[2]?.querySelector("b")?.textContent).toBe("A");
  });

  it("hides every null meta cell (no dash placeholders) + shows empty state", () => {
    const t = renderTimecode({
      clock: "00:00:00",
      bpm: null,
      key: null,
      deck: null,
      track: null,
      genre: null,
    });
    host().append(t);
    // 2026-05-20 contract: a null field hides its cell rather than printing
    // a dash, so the row only ever carries grounded facts.
    const cells = t.querySelectorAll<HTMLElement>(".vmx-timecode__meta-cell");
    expect(cells).toHaveLength(3);
    cells.forEach((c) => expect(c.style.display).toBe("none"));
    // Whole row collapses when nothing is grounded.
    expect(t.querySelector<HTMLElement>('[data-role="meta"]')?.style.display).toBe("none");
    expect(t.querySelector<HTMLElement>(".vmx-timecode__title")?.dataset.empty).toBe("true");
  });

  it("hides only the null cell, keeps grounded ones (KEY absent)", () => {
    const t = renderTimecode({
      clock: "00:41:12",
      bpm: 128,
      key: null,
      deck: "A",
      track: { title: "Strobe", artist: "Deadmau5" },
      genre: "techno",
    });
    host().append(t);
    const bpmCell = t.querySelector<HTMLElement>('[data-role="bpm"]');
    const keyCell = t.querySelector<HTMLElement>('[data-role="key"]');
    const deckCell = t.querySelector<HTMLElement>('[data-role="deck"]');
    expect(bpmCell?.style.display).toBe("");
    expect(bpmCell?.querySelector("b")?.textContent).toBe("128");
    expect(keyCell?.style.display).toBe("none");
    expect(deckCell?.style.display).toBe("");
    expect(deckCell?.querySelector("b")?.textContent).toBe("A");
  });
});

// === SessionLayout — composer smoke ===========================================

describe("SessionLayout", () => {
  it("mounts the deck: titlebar + rail/speak/foot + quiet fault row (no card, no screws)", () => {
    const root = host();
    mountSessionLayout(root);
    const session = root.querySelector<HTMLElement>(".vmx-session");
    expect(session).toBeTruthy();
    expect(session?.dataset.statusrow).toBe("quiet");
    expect(root.querySelector(".vmx-titlebar")).toBeTruthy();
    expect(root.querySelector(".vmx-deck__rail")).toBeTruthy();
    expect(root.querySelector(".vmx-deck__speak")).toBeTruthy();
    expect(root.querySelector(".vmx-deck__foot")).toBeTruthy();
    expect(root.querySelector<HTMLElement>(".vmx-statusrow")?.hidden).toBe(true);
    // "The Deck Speaks" rebuild: open void — no glass card, no corner screws,
    // no 3-column grid.
    expect(root.querySelectorAll(".vmx-session__screw")).toHaveLength(0);
    expect(root.querySelectorAll(".vmx-session__col")).toHaveLength(0);
  });

  it("gives BPM and key stable readout slots in the footer", () => {
    const root = host();
    const state = defaultState();
    state.timecode.bpm = 128.4;
    state.timecode.key = "12A";
    mountSessionLayout(root, state);

    const bpmWrap = root.querySelector<HTMLElement>('.vmx-read[data-readout="bpm"]');
    const keyWrap = root.querySelector<HTMLElement>('.vmx-read[data-readout="key"]');
    expect(bpmWrap?.querySelector(".vmx-read__num")?.textContent).toBe("128.4");
    expect(keyWrap?.querySelector(".vmx-read__key")?.textContent).toBe("12A");
    expect(document.head.textContent).toContain('.vmx-read[data-readout="bpm"]');
    expect(document.head.textContent).toContain('.vmx-read[data-readout="key"]');
  });

  it("mounts a visible Vibe Engine rail control", () => {
    const root = host();
    mountSessionLayout(root);
    const btn = root.querySelector<HTMLElement>('[data-action="vibe-engine"]');
    expect(btn).toBeTruthy();
    expect(btn?.dataset.primary).toBe("true");
    expect(btn?.textContent).toBe("crate");
    expect(btn?.getAttribute("aria-label")).toBe("open Viber crate");
    expect(btn?.getAttribute("title")).toContain("Viber library");
  });

  it("renders the idle Deck as an actionable readiness state, not vague listening copy", () => {
    const root = host();
    const mounted = mountSessionLayout(root, defaultState());
    renderSessionFrame(mounted, {
      ...defaultState(),
      status: {
        ...defaultState().status,
        livekit: "ok",
        gemini: "ok",
        midi: 1,
        screen: "unavailable",
      },
    });

    expect(root.querySelector(".vmx-now")?.textContent).toBe("Ready for the first move.");
    expect(root.textContent).toContain("audio waiting · co-host ready · controller seen");
    expect(root.textContent).toContain(
      "capture silent · Route DJ output into capture.",
    );
    expect(root.textContent).not.toContain(
      "screen proof unavailable · Start playback, I will not guess.",
    );
    expect(root.textContent).not.toContain("listening for the mix");
  });

  it("names the silent capture device when the sidecar reports it", () => {
    const root = host();
    const state = defaultState();
    state.status.livekit = "ok";
    state.status.gemini = "ok";
    state.status.midi = 1;
    state.status.screen = "unavailable";
    state.status.captureDevice = "eqMac Export ";

    mountSessionLayout(root, state);

    expect(root.textContent).toContain(
      "eqMac Export silent · Send DJ app to Multi-Output (eqMac), not speaker only.",
    );
  });

  it("warns that speaker output alone is not BlackHole capture proof", () => {
    const root = host();
    const state = defaultState();
    state.status.livekit = "ok";
    state.status.gemini = "ok";
    state.status.midi = 1;
    state.status.screen = "unavailable";
    state.status.captureDevice = "BlackHole 16ch";
    state.timecode.bpm = null;
    state.meters.music = { rms: 0, peak: 0 };

    mountSessionLayout(root, state);

    expect(root.textContent).toContain(
      "BlackHole 16ch silent · Send DJ app to a Multi-Output/Aggregate that includes BlackHole; speaker output alone is not proof.",
    );

    const bpm = root.querySelector<HTMLElement>(".vmx-read__num");
    expect(bpm?.getAttribute("title")).toBe(
      "BPM waits for audio from BlackHole 16ch; speaker output alone is not capture proof.",
    );
    expect(bpm?.getAttribute("aria-label")).toBe(
      "BPM waits for audio from BlackHole 16ch; speaker output alone is not capture proof.",
    );
  });

  it("warns that FLX4 speaker audio is not capture proof", () => {
    const root = host();
    const state = defaultState();
    state.status.livekit = "ok";
    state.status.gemini = "ok";
    state.status.midi = 0;
    state.status.midiActivity = "connected_no_midi_traffic";
    state.status.midiDevice = "DDJ-FLX4";
    state.status.screen = "unavailable";
    state.status.captureDevice = "DDJ-FLX4";

    mountSessionLayout(root, state);

    expect(root.textContent).toContain(
      "DDJ-FLX4 silent · Use BlackHole/eqMac capture, speaker audio is not proof.",
    );

    const bpm = root.querySelector<HTMLElement>(".vmx-read__num");
    expect(bpm?.getAttribute("title")).toBe(
      "BPM waits for master capture. DDJ-FLX4 is not hearing the master.",
    );
  });

  it("explains the blank BPM readout when the capture device is silent", () => {
    const root = host();
    const state = defaultState();
    state.status.livekit = "ok";
    state.status.captureDevice = "eqMac Export";
    state.timecode.bpm = null;
    state.meters.music = { rms: 0, peak: 0 };

    mountSessionLayout(root, state);

    const bpm = root.querySelector<HTMLElement>(".vmx-read__num");
    expect(bpm?.textContent).toBe("—");
    expect(bpm?.getAttribute("title")).toBe("BPM waits for audio from eqMac Export.");
    expect(bpm?.getAttribute("aria-label")).toBe("BPM waits for audio from eqMac Export.");
  });

  it("renders audible capture as hearing, not merely armed", () => {
    const root = host();
    const state = defaultState();
    state.meters.music = { rms: 0.08, peak: 0.14 };
    state.status.livekit = "ok";
    state.status.gemini = "ok";
    state.status.midi = 1;
    state.status.screen = "ok";

    mountSessionLayout(root, state);

    expect(root.textContent).toContain("audio hearing · co-host ready · controller seen");
  });

  it("asks for controller motion once audio is audible but MIDI is unproven", () => {
    const root = host();
    const state = defaultState();
    state.meters.music = { rms: 0.08, peak: 0.14 };
    state.status.livekit = "ok";
    state.status.gemini = "ok";
    state.status.midi = 0;
    state.status.screen = "ok";

    mountSessionLayout(root, state);

    expect(root.textContent).toContain("audio hearing · co-host ready · controller not proven");
    expect(root.textContent).toContain("screen proof ready · Move a control once, I will not guess.");
  });

  it("names the connected controller in the idle readiness line when motion is not proven", () => {
    const root = host();
    const state = defaultState();
    state.meters.music = { rms: 0.08, peak: 0.14 };
    state.status.livekit = "ok";
    state.status.gemini = "ok";
    state.status.midi = 0;
    state.status.midiActivity = "connected_no_midi_traffic";
    state.status.midiDevice = "DDJ-FLX4";
    state.status.screen = "ok";

    mountSessionLayout(root, state);

    expect(root.textContent).toContain("audio hearing · co-host ready · DDJ-FLX4 waiting");
    expect(root.textContent).toContain(
      "screen proof ready · DDJ-FLX4 waiting · Move mixer/deck control.",
    );
  });

  it("shows a passive voice status only when the local voice engine is muted", () => {
    const root = host();
    const mounted = mountSessionLayout(root, defaultState());
    const voice = root.querySelector<HTMLButtonElement>('.vmx-statusrow__i[data-input="voice"]');
    expect(voice).toBeTruthy();
    expect(voice?.hidden).toBe(true);

    renderSessionFrame(mounted, {
      ...defaultState(),
      status: {
        ...defaultState().status,
        livekit: "ok",
        gemini: "ok",
        midi: 1,
        screen: "ok",
        voice: "muted",
      },
    });

    expect(voice?.hidden).toBe(false);
    expect(root.querySelector<HTMLElement>(".vmx-session")?.dataset.statusrow).toBe("alert");
    expect(root.querySelector<HTMLElement>(".vmx-statusrow")?.hidden).toBe(false);
    expect(voice?.disabled).toBe(true);
    expect(voice?.dataset.down).toBe("true");
    expect(voice?.dataset.actionable).toBe("false");
    expect(voice?.getAttribute("aria-label")).toBe("voice status muted");
    expect(root.textContent).toContain("audio waiting · voice muted · controller seen");

    renderSessionFrame(mounted, {
      ...defaultState(),
      status: { ...defaultState().status, voice: "ok" },
    });

    expect(voice?.hidden).toBe(true);
  });

  it("rail controls call the latest rendered handlers", () => {
    const root = host();
    const mounted = mountSessionLayout(root, defaultState());
    let opened = 0;
    let muted = 0;
    const next = {
      ...defaultState(),
      cohost: { ...defaultState().cohost, onMute: () => { muted += 1; } },
      actions: { onOpenVibeEngine: () => { opened += 1; } },
    };
    renderSessionFrame(mounted, next);

    root.querySelector<HTMLElement>('[data-action="vibe-engine"]')?.click();
    root.querySelector<HTMLElement>('[data-action="mute"]')?.click();

    expect(opened).toBe(1);
    expect(muted).toBe(1);
  });

  it("down status-row inputs call the latest rendered recheck handler", () => {
    const root = host();
    const mounted = mountSessionLayout(root, defaultState());
    const rechecked: string[] = [];
    renderSessionFrame(mounted, {
      ...defaultState(),
      status: {
        ...defaultState().status,
        gemini: "down",
        onRecheck: (component) => rechecked.push(component),
      },
    });

    const ai = root.querySelector<HTMLButtonElement>('.vmx-statusrow__i[data-input="ai"]');
    expect(ai).toBeTruthy();
    expect(root.querySelector<HTMLElement>(".vmx-session")?.dataset.statusrow).toBe("alert");
    expect(root.querySelector<HTMLElement>(".vmx-statusrow")?.hidden).toBe(false);
    expect(ai?.disabled).toBe(false);
    expect(ai?.dataset.down).toBe("true");
    expect(ai?.getAttribute("aria-label")).toBe("recheck ai status");

    ai?.click();

    expect(rechecked).toEqual(["gemini"]);
  });

  it("renderSessionFrame is idempotent — same state does not duplicate nodes", () => {
    const root = host();
    const mounted = mountSessionLayout(root);
    const before = root.querySelectorAll(".vmx-now").length;
    renderSessionFrame(mounted, defaultState());
    const after = root.querySelectorAll(".vmx-now").length;
    expect(after).toBe(before);
  });

  it("renderSessionFrame updates clock textContent in place (no rebuild)", () => {
    const root = host();
    const mounted = mountSessionLayout(root, {
      ...defaultState(),
      titlebar: { live: "ok", rec: "ok", sys: "ok", clock: "00:00:00" },
    });
    const clockEl = mounted.titlebar.querySelector<HTMLElement>(".vmx-titlebar__clock");
    const next = { ...defaultState(), titlebar: { live: "ok" as const, rec: "ok" as const, sys: "ok" as const, clock: "02:44:31" } };
    renderSessionFrame(mounted, next);
    // Same node, new text
    expect(clockEl).toBe(mounted.titlebar.querySelector(".vmx-titlebar__clock"));
    expect(clockEl?.textContent).toBe("02:44:31");
  });

  it("mounts the live drop chip only while a drop prediction exists", () => {
    const root = host();
    const mounted = mountSessionLayout(root, defaultState());
    expect(root.querySelector(".vmx-drop-chip")).toBeNull();

    renderSessionFrame(mounted, {
      ...defaultState(),
      drop: { bars: 8, bpmPeriodMs: 500 },
    });
    const chip = root.querySelector<HTMLElement>(".vmx-drop-chip");
    expect(chip).toBeTruthy();
    expect(chip?.dataset.bars).toBe("8");
    expect(chip?.querySelector(".vmx-drop-chip__count")?.textContent).toBe("08:00");
    expect(chip?.style.getPropertyValue("--bpm-period-ms")).toBe("500ms");

    renderSessionFrame(mounted, {
      ...defaultState(),
      drop: { bars: null, bpmPeriodMs: undefined },
    });
    expect(root.querySelector(".vmx-drop-chip")).toBeNull();
  });
});

// === Grep guard — every component's emitted CSS has zero hex outside --paper-* ===

describe("hex grep guard", () => {
  /* Each component injects its CSS into <head> via registerStyle(scope, css).
   * After importing every component module above, the registry should have
   * one <style data-scope="…"> per component. We pull the textContent and
   * assert zero hex matches outside `--paper-*` declarations. */

  beforeEach(() => {
    // Force fresh imports — registerStyle dedupes by scope, so the modules
    // we imported at the top of this file have already injected. We just
    // need to walk the document's <style data-scope> elements.
  });

  function hexFreeOutsidePaper(css: string): { ok: boolean; offending: string[] } {
    const matches = css.match(/#[0-9a-fA-F]{3,8}/g) ?? [];
    if (matches.length === 0) return { ok: true, offending: [] };
    // Allowed iff each match's containing line declares a --paper-* var.
    const offending: string[] = [];
    for (const line of css.split("\n")) {
      const hexMatches = line.match(/#[0-9a-fA-F]{3,8}/g);
      if (!hexMatches) continue;
      const isPaper = /--paper-[a-z0-9_-]+\s*:/i.test(line);
      if (!isPaper) {
        for (const h of hexMatches) offending.push(`${h} in: ${line.trim()}`);
      }
    }
    return { ok: offending.length === 0, offending };
  }

  it("every session component <style data-scope> contains zero hex outside --paper-* vars", () => {
    // Ensure modules registered their styles
    void renderTitlebar({ live: "ok", rec: "ok", sys: "ok", clock: "00:00:00" });
    void renderPanel({ children: document.createElement("div") });
    void renderRocker({ options: [{ id: "x", label: "x" }], active: "x" });
    void renderPicker({ label: "X", value: "x", options: [] });
    void renderMeter({ label: "music" });
    void renderTimecode({ clock: "00:00", bpm: null, key: null, deck: null, track: null, genre: null });
    void renderPhaseTape({ chunks: [], nowPct: 0 });
    void renderDropChip({ bars: 4 });
    void renderEventRibbon({ events: [] });
    void renderCohostPanel({ status: "IDLE", transcript: [], latencyMs: null, grounded: false });
    void renderStatusBar({
      livekit: "ok", gemini: "ok", midi: 1, screen: "ok",
      muted: false, hotkey: "⌘⇧M",
    });
    void renderMutedBanner({ hotkey: "⌘⇧M" });

    const styles = Array.from(document.querySelectorAll<HTMLStyleElement>("style[data-scope]"));
    expect(styles.length).toBeGreaterThan(0);
    const offenders: string[] = [];
    for (const s of styles) {
      const scope = s.dataset.scope ?? "(unknown)";
      const css = s.textContent ?? "";
      const result = hexFreeOutsidePaper(css);
      if (!result.ok) {
        for (const o of result.offending) offenders.push(`[${scope}] ${o}`);
      }
    }
    expect(offenders).toEqual([]);
  });
});
