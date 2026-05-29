// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-03 — Tab cycles through control groups in canonical DOM
//                    order so hardware-free users can browse the controller
//                    surface via keyboard alone.
// Regression: every rendered SVG control exposes the same focusable order as
// its DOM order, so browser keyboard navigation does not jump around the deck.

import { describe, expect, it } from "vitest";

import { PIONEER_DDJ_FLX4_SVG } from "../../src/learn/controllers/pioneer_ddj_flx4.svg";

describe("test_keyboard_nav_order.spec.ts (RENDER-03)", () => {
  it("controller groups are focusable in DOM order", () => {
    document.body.innerHTML = PIONEER_DDJ_FLX4_SVG;
    const controls = Array.from(
      document.querySelectorAll<SVGGElement>("[data-control-id]"),
    );
    const focusable = Array.from(
      document.querySelectorAll<SVGGElement>('[data-control-id][tabindex="0"]'),
    );

    expect(controls.length).toBeGreaterThan(0);
    expect(focusable.map((el) => el.dataset.controlId)).toEqual(
      controls.map((el) => el.dataset.controlId),
    );
    for (const control of focusable) {
      expect(control.getAttribute("role")).toBe("button");
      expect(control.getAttribute("aria-label")).toBeTruthy();
    }
  });
});
