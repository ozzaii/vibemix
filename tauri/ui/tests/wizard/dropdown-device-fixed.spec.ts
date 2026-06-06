// SPDX-License-Identifier: Apache-2.0
//
// F6: the Step-2 output-device menu must escape the primary panel's
// overflow:hidden box. jsdom cannot prove clipping, so this pins the mechanism.

import { afterEach, describe, expect, it, vi } from "vitest";
import { DropdownDevice } from "../../src/wizard/components/dropdown-device.js";

afterEach(() => {
  document.body.replaceChildren();
  document.head.querySelectorAll("style").forEach((s) => s.remove());
});

describe("wizard dropdown-device fixed panel (F6)", () => {
  it("registers the panel as position:fixed at z-index 1000", () => {
    DropdownDevice({
      devices: [{ id: "a", name: "Out A", isSpeaker: true }],
      onSelect: () => {},
    });
    const css = Array.from(document.head.querySelectorAll("style"))
      .map((s) => s.textContent ?? "")
      .join("\n");
    expect(css).toContain("position: fixed");
    expect(css).toContain("z-index: 1000");
    expect(css).not.toContain("position: absolute");
  });

  it("positions the open panel from the head bounding rect", () => {
    const el = DropdownDevice({
      devices: [{ id: "a", name: "Out A", isSpeaker: true }],
      onSelect: () => {},
    });
    document.body.append(el);
    const head = el.querySelector<HTMLElement>(".cmp-dropdown-device__head")!;
    const panel = el.querySelector<HTMLElement>(".cmp-dropdown-device__panel")!;

    expect(panel.hidden).toBe(true);
    head.click();
    expect(panel.hidden).toBe(false);
    expect(panel.parentElement).toBe(document.body);
    expect(head.getAttribute("aria-expanded")).toBe("true");
    expect(panel.style.top).toMatch(/px$/);
    expect(panel.style.left).toMatch(/px$/);
    expect(panel.style.width).toMatch(/px$/);
  });

  it("removes scroll and resize listeners when the panel closes", () => {
    const removeSpy = vi.spyOn(window, "removeEventListener");
    const el = DropdownDevice({
      devices: [{ id: "a", name: "Out A", isSpeaker: true }],
      onSelect: () => {},
    });
    document.body.append(el);
    const head = el.querySelector<HTMLElement>(".cmp-dropdown-device__head")!;

    head.click();
    head.click();
    const panel = el.querySelector<HTMLElement>(".cmp-dropdown-device__panel")!;
    expect(panel.parentElement).toBe(el);
    expect(removeSpy).toHaveBeenCalledWith("scroll", expect.any(Function), true);
    expect(removeSpy).toHaveBeenCalledWith("resize", expect.any(Function));
    removeSpy.mockRestore();
  });
});
