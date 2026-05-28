/**
 * mode-picker.ts — Phase 97 / ONBOARD-01 contract.
 *
 * Pins the optimistic-repaint pattern (CLAUDE.md rule): click flips
 * data-active locally BEFORE the ipc round-trip; subsequent identical
 * clicks no-op. Mirrors the rocker.test.ts shape — same DOM-assertion
 * pattern, same jsdom env.
 */
import { describe, test, expect, vi } from "vitest";
import {
  renderModePicker,
  setModePickerActive,
  MODE_PICKER_OPTIONS,
  type ModePickerMode,
} from "./mode-picker.js";

function mount(active: ModePickerMode = "cohost", onChange = vi.fn()): {
  root: HTMLElement;
  segs: HTMLButtonElement[];
  onChange: ReturnType<typeof vi.fn>;
} {
  const root = renderModePicker({ active, onChange });
  document.body.append(root);
  return {
    root,
    segs: Array.from(
      root.querySelectorAll<HTMLButtonElement>(".vmx-mode-picker__seg"),
    ),
    onChange,
  };
}

describe("mode-picker — wire shape", () => {
  test("renders 4 segments in canonical order (cohost / learn / build / debrief)", () => {
    const { segs } = mount();
    expect(segs).toHaveLength(4);
    expect(segs.map((s) => s.dataset.id)).toEqual([
      "cohost",
      "learn",
      "build",
      "debrief",
    ]);
    expect(segs.map((s) => s.textContent)).toEqual([
      "COHOST",
      "LEARN",
      "BUILD",
      "DEBRIEF",
    ]);
  });

  test("MODE_PICKER_OPTIONS is the single source of truth for order + labels", () => {
    expect(MODE_PICKER_OPTIONS.map((o) => o.id)).toEqual([
      "cohost",
      "learn",
      "build",
      "debrief",
    ]);
    expect(MODE_PICKER_OPTIONS.every((o) => /^[A-Z]+$/.test(o.label))).toBe(true);
  });

  test("active segment carries data-active + aria-checked truthy; others falsey", () => {
    const { segs } = mount("learn");
    const active = segs.filter((s) => s.dataset.active === "true");
    expect(active).toHaveLength(1);
    expect(active[0]!.dataset.id).toBe("learn");
    expect(active[0]!.getAttribute("aria-checked")).toBe("true");
    const inactive = segs.filter((s) => s.dataset.active === "false");
    expect(inactive).toHaveLength(3);
    for (const seg of inactive) {
      expect(seg.getAttribute("aria-checked")).toBe("false");
    }
  });

  test("role=radiogroup with aria-label on root + role=radio on each seg", () => {
    const { root, segs } = mount();
    expect(root.getAttribute("role")).toBe("radiogroup");
    expect(root.getAttribute("aria-label")).toBe("vibemix mode");
    for (const seg of segs) {
      expect(seg.getAttribute("role")).toBe("radio");
    }
  });
});

describe("mode-picker — optimistic repaint (CLAUDE.md rule)", () => {
  test("click on inactive segment flips data-active LOCALLY before onChange returns", () => {
    let observedActiveAtChange: string | null = null;
    const root = renderModePicker({
      active: "cohost",
      onChange: (id) => {
        // At the moment onChange fires, the DOM should ALREADY reflect
        // the new active segment (optimistic repaint, not awaiting the
        // ipc round-trip).
        observedActiveAtChange =
          root.querySelector<HTMLElement>(
            '.vmx-mode-picker__seg[data-active="true"]',
          )?.dataset.id ?? null;
        return id;
      },
    });
    document.body.append(root);
    const learnSeg = root.querySelector<HTMLButtonElement>(
      '.vmx-mode-picker__seg[data-id="learn"]',
    )!;
    learnSeg.click();
    expect(observedActiveAtChange).toBe("learn");
  });

  test("click on already-active segment is a no-op (no onChange call)", () => {
    const { segs, onChange } = mount("cohost");
    segs.find((s) => s.dataset.id === "cohost")!.click();
    expect(onChange).not.toHaveBeenCalled();
  });

  test("click flips DOM AND fires onChange exactly once with the new id", () => {
    const { segs, onChange } = mount("cohost");
    const learn = segs.find((s) => s.dataset.id === "learn")!;
    learn.click();
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith("learn");
    expect(learn.dataset.active).toBe("true");
    expect(segs.find((s) => s.dataset.id === "cohost")!.dataset.active).toBe(
      "false",
    );
  });
});

describe("mode-picker — setModePickerActive (external sync)", () => {
  test("flips data-active + aria-checked without rebuilding the picker", () => {
    const { root, segs } = mount("cohost");
    setModePickerActive(root, "build");
    expect(segs.find((s) => s.dataset.id === "build")!.dataset.active).toBe(
      "true",
    );
    expect(segs.find((s) => s.dataset.id === "cohost")!.dataset.active).toBe(
      "false",
    );
    expect(
      segs
        .find((s) => s.dataset.id === "build")!
        .getAttribute("aria-checked"),
    ).toBe("true");
  });
});
