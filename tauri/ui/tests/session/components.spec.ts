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
  it("trims to last 12 events when 15 provided", () => {
    const events: MidiEvent[] = Array.from({ length: 15 }, (_, i) => ({
      id: `evt-${i}`,
      label: `EVT ${i}`,
      ageMs: 100 + i * 10,
    }));
    const ribbon = renderEventRibbon({ events });
    host().append(ribbon);
    const chips = ribbon.querySelectorAll(".vmx-event-chip");
    expect(chips).toHaveLength(12);
    // Oldest 3 (ids 0, 1, 2) trimmed — first visible should be evt-3.
    expect((chips[0] as HTMLElement).dataset.id).toBe("evt-3");
    expect((chips[11] as HTMLElement).dataset.id).toBe("evt-14");
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
  it("renders all lines up to 200; last has .now tier, lines 2-6 from end faded", () => {
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
    expect(msgs).toHaveLength(200);
    // Last line = .now
    const last = msgs[msgs.length - 1];
    expect(last?.dataset.tier).toBe("now");
    // Lines at index 199-5 .. 199-1 (i.e. positions 194-198) should be `.faded`
    for (let i = msgs.length - 6; i <= msgs.length - 2; i++) {
      expect(msgs[i]?.dataset.tier).toBe("faded");
    }
    // Anything older than 5 from the end is `.old`
    expect(msgs[100]?.dataset.tier).toBe("old");
  });

  it("caps transcript to MAX_TRANSCRIPT_LINES (200) when more provided", () => {
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
    ).toBe(200);
  });

  it("foot shows GROUNDED + DSEG7 latency when grounded=true", () => {
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
      "GROUNDED ON AUDIO + SCREEN",
    );
    expect(foot?.querySelector(".vmx-cohost__foot-latency")?.textContent).toBe(
      "0.82 s",
    );
  });

  it("foot shows WARMING UP when grounded=false", () => {
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
      "WARMING UP",
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
    // The header still mounts and carries the AVERY chip + status.
    const header = panel.querySelector<HTMLElement>(".vmx-cohost__header");
    expect(header).toBeTruthy();
    expect(panel.querySelector(".vmx-cohost__name")?.textContent).toBe("AVERY");
  });
});

// === StatusBar tooltip =======================================================

describe("renderStatusBar", () => {
  it("renders 4 badges + signature", () => {
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
    expect(sb.querySelector(".vmx-statusbar__sig")?.textContent).toBe(
      "made by bravoh",
    );
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
  });
});

// === Titlebar / rocker / picker smoke =======================================

describe("renderTitlebar", () => {
  it("renders wordmark + 3 pills + clock + settings gear", () => {
    const tb = renderTitlebar({
      live: "ok",
      rec: "ok",
      sys: "ok",
      clock: "02:44:31",
    });
    host().append(tb);
    expect(tb.querySelector(".vmx-titlebar__wordmark")?.textContent).toBe("vibemix");
    expect(tb.querySelectorAll(".vmx-titlebar__pill")).toHaveLength(3);
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
  });
});

describe("renderPicker", () => {
  it("opens dropdown on click", () => {
    const p = renderPicker({
      label: "VOICE",
      value: "kore",
      options: [
        { id: "kore", label: "kore" },
        { id: "puck", label: "puck" },
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
  it("renders hero clock + meta cells", () => {
    const t = renderTimecode({ clock: "02:44:31", bpm: 140, key: "Am", deck: "A" });
    host().append(t);
    expect(t.querySelector(".vmx-timecode__hero")?.textContent).toBe("02:44:31");
    const cells = t.querySelectorAll<HTMLElement>(".vmx-timecode__meta-cell");
    expect(cells).toHaveLength(3);
    expect(cells[0]?.querySelector("b")?.textContent).toBe("140");
    expect(cells[1]?.querySelector("b")?.textContent).toBe("Am");
    expect(cells[2]?.querySelector("b")?.textContent).toBe("A");
  });

  it("handles null bpm/key/deck with em-dash", () => {
    const t = renderTimecode({ clock: "00:00:00", bpm: null, key: null, deck: null });
    host().append(t);
    const dashes = Array.from(t.querySelectorAll<HTMLElement>(".vmx-timecode__meta-cell b"))
      .map((b) => b.textContent);
    expect(dashes).toEqual(["—", "—", "—"]);
  });
});

// === SessionLayout — composer smoke ===========================================

describe("SessionLayout", () => {
  it("mounts the full DOM tree with screws + titlebar + 3-col grid + status bar", () => {
    const root = host();
    mountSessionLayout(root);
    expect(root.querySelector(".vmx-session")).toBeTruthy();
    expect(root.querySelectorAll(".vmx-session__screw")).toHaveLength(4);
    expect(root.querySelector(".vmx-titlebar")).toBeTruthy();
    expect(root.querySelectorAll(".vmx-session__col")).toHaveLength(3);
    expect(root.querySelector(".vmx-statusbar")).toBeTruthy();
  });

  it("renderSessionFrame is idempotent — same state does not duplicate nodes", () => {
    const root = host();
    const mounted = mountSessionLayout(root);
    const before = root.querySelectorAll(".vmx-meter").length;
    renderSessionFrame(mounted, defaultState());
    const after = root.querySelectorAll(".vmx-meter").length;
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
    void renderTimecode({ clock: "00:00", bpm: null, key: null, deck: null });
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
