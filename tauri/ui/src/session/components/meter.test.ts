/**
 * VIS-03 (Phase 43, Plan 43-04) — meter contract.
 * Polychrome migration (2026-05-19) — decision #2 from /impeccable critique.
 *
 * Pins the hardware-LED-strip aesthetic: 16 discrete segments,
 * polychrome safe/warm/clip mapping (green / amber / magenta),
 * amber peak-hold with 1.2s decay, silk-12 minor grid lines, token-only
 * CSS (zero rgba() literals).
 *
 * `_CSS_FOR_TEST` is a test-only export from meter.ts — exposed
 * so this suite can grep the registered stylesheet for token usage
 * and reject regressions (rgba() literals re-introduced, silk-22
 * accidentally restored on the scale ticks, peak decay shortened,
 * polychrome rolled back to all-amber).
 */
import { describe, test, expect, beforeEach } from "vitest";
import {
  renderMeter,
  setMeterLevels,
  _CSS_FOR_TEST,
  type MeterLabel,
} from "./meter.js";

function mount(label: MeterLabel = "music"): HTMLElement {
  return renderMeter({ label });
}

describe("meter — VIS-03 contract", () => {
  beforeEach(() => {
    // Each test starts from a fresh DOM root. jsdom persists document.head
    // <style> tags from registerStyle across tests, which is fine — the
    // style is idempotent per scope key.
    document.body.innerHTML = "";
  });

  test("1 — renders exactly 16 .vmx-meter__seg + 1 .vmx-meter__peak", () => {
    const root = mount();
    const segs = root.querySelectorAll(".vmx-meter__seg");
    const peaks = root.querySelectorAll(".vmx-meter__peak");
    expect(segs.length).toBe(16);
    expect(peaks.length).toBe(1);
  });

  test("2 — zone bands: 1-5 safe, 6-13 warm, 14-16 clip", () => {
    const root = mount();
    const segs = root.querySelectorAll<HTMLElement>(".vmx-meter__seg");
    const byIndex = new Map<number, string>();
    segs.forEach((seg) => {
      const idx = Number(seg.dataset.index ?? "0");
      byIndex.set(idx, seg.dataset.zone ?? "");
    });
    // safe
    for (let i = 1; i <= 5; i++) expect(byIndex.get(i)).toBe("safe");
    // warm
    for (let i = 6; i <= 13; i++) expect(byIndex.get(i)).toBe("warm");
    // clip
    for (let i = 14; i <= 16; i++) expect(byIndex.get(i)).toBe("clip");
  });

  test("3 — polychrome zone mapping: safe=green, warm=amber, clip=magenta", () => {
    // Pioneer-mapping the safe/warm/clip ladder. Each lit zone references
    // its own color family — meter-safe-* for green, --amber-* for warm,
    // --meter-clip-* for magenta. This pins decision #2 from the
    // 2026-05-19 /impeccable critique: the meter is the single polychrome
    // surface in v5 (mood block follows). Regressing to all-amber would
    // drop the second-order category-reflex test back into
    // Linear/Vercel/Railway territory.
    const css = _CSS_FOR_TEST;
    const safe = css.match(
      /\.vmx-meter__seg\[data-zone="safe"\]\[data-lit="true"\]\s*\{[^}]*\}/,
    );
    const warm = css.match(
      /\.vmx-meter__seg\[data-zone="warm"\]\[data-lit="true"\]\s*\{[^}]*\}/,
    );
    const clip = css.match(
      /\.vmx-meter__seg\[data-zone="clip"\]\[data-lit="true"\]\s*\{[^}]*\}/,
    );
    expect(safe).not.toBeNull();
    expect(warm).not.toBeNull();
    expect(clip).not.toBeNull();
    expect(safe![0]).toMatch(/var\(--meter-safe-pale\)/);
    expect(safe![0]).toMatch(/var\(--meter-safe-pale-70\)/);
    expect(safe![0]).toMatch(/var\(--meter-safe-22\)/);
    expect(warm![0]).toMatch(/var\(--amber\)/);
    expect(warm![0]).toMatch(/var\(--amber-78\)/);
    expect(clip![0]).toMatch(/var\(--meter-clip\)/);
    expect(clip![0]).toMatch(/var\(--meter-clip-deep-85\)/);
    expect(clip![0]).toMatch(/var\(--meter-clip-glow\)/);
    // Cross-zone leak guards — safe must NOT consume amber/clip families,
    // warm must NOT consume safe/clip, clip must NOT consume safe/amber.
    expect(safe![0]).not.toMatch(/var\(--amber/);
    expect(safe![0]).not.toMatch(/var\(--meter-clip/);
    expect(warm![0]).not.toMatch(/var\(--meter-safe/);
    expect(warm![0]).not.toMatch(/var\(--meter-clip/);
    expect(clip![0]).not.toMatch(/var\(--meter-safe/);
    expect(clip![0]).not.toMatch(/var\(--amber/);
    // The pre-polychrome segment-5 green hairline rule is gone — the
    // color transition between green and amber zones IS the marker now.
    expect(css).not.toMatch(/\.vmx-meter__seg\[data-index="5"\]::after/);
  });

  test("4 — silk-12 minor grid lines on indices 4/8/12/16 (NOT silk-22)", () => {
    const css = _CSS_FOR_TEST;
    // Find the scale-tick rule covering ::before selectors on the four
    // grid indices. The rule body must reference var(--silk-12).
    const tickBlock = css.match(
      /\.vmx-meter__seg\[data-index="4"\]::before[\s\S]*?\.vmx-meter__seg\[data-index="16"\]::before\s*\{[^}]*\}/,
    );
    expect(tickBlock).not.toBeNull();
    expect(tickBlock![0]).toMatch(/var\(--silk-12\)/);
    // And the silk-22 fallback must NOT appear inside this same scale-tick
    // block (it's allowed elsewhere if other rules need it — but on the
    // minor-grid tick it's the regression we explicitly downgraded from).
    expect(tickBlock![0]).not.toMatch(/var\(--silk-22\)/);
  });

  test("5 — amber peak-hold lozenge fades over exactly 1200ms", () => {
    const css = _CSS_FOR_TEST;
    const peakRule = css.match(/\.vmx-meter__peak\s*\{[^}]*\}/);
    expect(peakRule).not.toBeNull();
    // Transition must include the 1.2s opacity fade. Bottom-position
    // transition is shorter (80ms ease-out for level recoil); the
    // 1200ms decay is the visceral CDJ Whisper signal per VIS-03.
    expect(peakRule![0]).toMatch(/opacity\s+1200ms\s+ease-out/);
  });

  test("6 — zero rgba() literals in meter.ts CSS (token-only)", () => {
    // Reject both rgb() and rgba() — every color must resolve via
    // var(--token). This is the VIS-03 token-discipline grep gate.
    expect(_CSS_FOR_TEST).not.toMatch(/rgba?\(/);
  });

  test("7 — setMeterLevels({rms:0.5, peak:0.8}) lights 8 segments + sets peak pct", () => {
    const root = mount();
    const lit = setMeterLevels(root, { rms: 0.5, peak: 0.8 });
    expect(lit).toBe(8);
    expect(root.dataset.litCount).toBe("8");
    // 16 segments still present
    expect(root.querySelectorAll(".vmx-meter__seg").length).toBe(16);
    // Peak element carries the inline custom property.
    const peakEl = root.querySelector<HTMLElement>(".vmx-meter__peak");
    expect(peakEl).not.toBeNull();
    expect(peakEl!.style.getPropertyValue("--meter-peak-pct")).toBe("0.8");
  });

  test("8 — idempotent hot-update: second call with identical input writes nothing", () => {
    const root = mount();
    setMeterLevels(root, { rms: 0.5, peak: 0.8 });
    // Snapshot the lit-count + every segment's data-lit + peak custom prop.
    const before = root.dataset.litCount;
    const segsBefore = Array.from(
      root.querySelectorAll<HTMLElement>(".vmx-meter__seg"),
    ).map((s) => s.dataset.lit);
    const peakElBefore = root.querySelector<HTMLElement>(".vmx-meter__peak")!;
    const peakBefore = peakElBefore.style.getPropertyValue("--meter-peak-pct");

    // Wire a MutationObserver before the second call; expect ZERO
    // mutations on the seg attributes (rms unchanged ⇒ no DOM writes).
    let mutationCount = 0;
    const observer = new MutationObserver((records) => {
      mutationCount += records.length;
    });
    observer.observe(root, {
      attributes: true,
      attributeFilter: ["data-lit", "data-lit-count"],
      subtree: true,
    });

    setMeterLevels(root, { rms: 0.5, peak: 0.8 });

    // Flush microtasks to let MutationObserver deliver.
    return new Promise<void>((resolve) => {
      queueMicrotask(() => {
        observer.disconnect();
        expect(root.dataset.litCount).toBe(before);
        const segsAfter = Array.from(
          root.querySelectorAll<HTMLElement>(".vmx-meter__seg"),
        ).map((s) => s.dataset.lit);
        expect(segsAfter).toEqual(segsBefore);
        const peakElAfter =
          root.querySelector<HTMLElement>(".vmx-meter__peak")!;
        expect(peakElAfter.style.getPropertyValue("--meter-peak-pct")).toBe(
          peakBefore,
        );
        // The lit-count attribute write is guarded by the `if (!== litCount)`
        // branch in setMeterLevels — so zero data-lit mutations is the
        // strongest contract we can pin in jsdom.
        expect(mutationCount).toBe(0);
        resolve();
      });
    });
  });
});
