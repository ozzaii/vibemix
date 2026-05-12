/* Phase 12 Wave 4 — retention slider (Plan 12-05 §7).
 *
 * Asserts:
 *   - 6 knobs render in fixed stop order.
 *   - daysToStopIndex maps every documented stop value back to its index.
 *   - daysToStopIndex(36500) and (Infinity) both → last stop (∞).
 *   - Off-grid values snap to nearest stop.
 *   - Clicking a knob fires onChange with the stop's `days` (wire form).
 *   - DSEG7 readout updates on selection.
 *   - Arrow-key nav moves between stops and fires onChange.
 *   - setValue updates without firing onChange.
 */

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  daysToStopIndex,
  renderRetentionSlider,
  RETENTION_STOPS,
} from "../../src/settings/components/retention-slider.js";

afterEach(() => {
  document.body.replaceChildren();
});

describe("RETENTION_STOPS shape", () => {
  it("has 6 stops in fixed order with correct days + labels", () => {
    expect(RETENTION_STOPS.map((s) => s.days)).toEqual([
      1, 3, 7, 14, 30, 36500,
    ]);
    expect(RETENTION_STOPS.map((s) => s.label)).toEqual([
      "1d",
      "3d",
      "7d",
      "14d",
      "30d",
      "∞",
    ]);
    expect(RETENTION_STOPS.map((s) => s.readout)).toEqual([
      "1 D",
      "3 D",
      "7 D",
      "14 D",
      "30 D",
      "INF",
    ]);
  });
});

describe("daysToStopIndex", () => {
  it("maps every defined stop to its index", () => {
    expect(daysToStopIndex(1)).toBe(0);
    expect(daysToStopIndex(3)).toBe(1);
    expect(daysToStopIndex(7)).toBe(2);
    expect(daysToStopIndex(14)).toBe(3);
    expect(daysToStopIndex(30)).toBe(4);
    expect(daysToStopIndex(36500)).toBe(5);
  });

  it("maps Infinity / >=36500 to the ∞ stop", () => {
    expect(daysToStopIndex(Infinity)).toBe(5);
    expect(daysToStopIndex(50000)).toBe(5);
  });

  it("snaps off-grid values to the nearest stop", () => {
    expect(daysToStopIndex(2)).toBe(0); // closer to 1 than 3
    expect(daysToStopIndex(10)).toBe(2); // closer to 7 than 14 (dist 3 vs 4)
    expect(daysToStopIndex(20)).toBe(3); // closer to 14 than 30
  });
});

describe("renderRetentionSlider", () => {
  it("renders exactly 6 knobs", () => {
    const { root } = renderRetentionSlider({
      value: 7,
      onChange: vi.fn(),
    });
    document.body.append(root);
    expect(root.querySelectorAll(".vmx-retention__knob").length).toBe(6);
  });

  it("activates the knob matching the initial value", () => {
    const { root } = renderRetentionSlider({
      value: 14,
      onChange: vi.fn(),
    });
    document.body.append(root);
    const active = root.querySelector<HTMLElement>(
      '.vmx-retention__knob[data-active="true"]',
    );
    expect(active?.dataset.idx).toBe("3");
  });

  it("DSEG7 readout reflects the initial value", () => {
    const { root } = renderRetentionSlider({
      value: 30,
      onChange: vi.fn(),
    });
    document.body.append(root);
    const readout = root.querySelector<HTMLElement>(
      ".vmx-retention__readout",
    );
    expect(readout?.textContent).toBe("30 D");
  });

  it("DSEG7 shows INF for ∞ stop", () => {
    const { root } = renderRetentionSlider({
      value: 36500,
      onChange: vi.fn(),
    });
    document.body.append(root);
    const readout = root.querySelector<HTMLElement>(
      ".vmx-retention__readout",
    );
    expect(readout?.textContent).toBe("INF");
  });

  it("clicking a knob fires onChange with the stop's days (wire form)", () => {
    const onChange = vi.fn();
    const { root } = renderRetentionSlider({ value: 1, onChange });
    document.body.append(root);
    const knobs = root.querySelectorAll<HTMLElement>(".vmx-retention__knob");
    // Click the 30d knob (idx 4)
    knobs[4]!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(onChange).toHaveBeenCalledWith(30);
  });

  it("clicking ∞ knob fires onChange(36500)", () => {
    const onChange = vi.fn();
    const { root } = renderRetentionSlider({ value: 1, onChange });
    document.body.append(root);
    const knobs = root.querySelectorAll<HTMLElement>(".vmx-retention__knob");
    knobs[5]!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(onChange).toHaveBeenCalledWith(36500);
  });

  it("readout updates after a knob click", () => {
    const { root } = renderRetentionSlider({
      value: 1,
      onChange: vi.fn(),
    });
    document.body.append(root);
    const knobs = root.querySelectorAll<HTMLElement>(".vmx-retention__knob");
    knobs[2]!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    const readout = root.querySelector<HTMLElement>(
      ".vmx-retention__readout",
    );
    expect(readout?.textContent).toBe("7 D");
  });

  it("ArrowRight moves selection to the next stop and fires onChange", () => {
    const onChange = vi.fn();
    const { root } = renderRetentionSlider({ value: 7, onChange });
    document.body.append(root);
    root.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }),
    );
    expect(onChange).toHaveBeenCalledWith(14);
  });

  it("ArrowLeft moves selection to the previous stop", () => {
    const onChange = vi.fn();
    const { root } = renderRetentionSlider({ value: 7, onChange });
    document.body.append(root);
    root.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }),
    );
    expect(onChange).toHaveBeenCalledWith(3);
  });

  it("setValue updates the slider without firing onChange", () => {
    const onChange = vi.fn();
    const { root, setValue } = renderRetentionSlider({
      value: 1,
      onChange,
    });
    document.body.append(root);
    setValue(30);
    expect(onChange).not.toHaveBeenCalled();
    const active = root.querySelector<HTMLElement>(
      '.vmx-retention__knob[data-active="true"]',
    );
    expect(active?.dataset.idx).toBe("4");
  });
});
