/* Impeccable Wave 1.2 (2026-05-14) — wizard intro hero spec.
 *
 * Pins the brand-handshake first paint: three-line hero (VIBEMIX /
 * DJ FRIEND / IN YOUR EAR) + single armed CTA. The hero is the
 * answer to the impeccable critique's [P0] "wizard has no hero
 * moment" — if a future refactor accidentally collapses the
 * intro back to a generic settings dialog, this spec catches it. */

import { afterEach, describe, expect, it } from "vitest";

import { renderStep0Intro } from "../../src/wizard/step0-intro.js";

function host(): HTMLElement {
  const div = document.createElement("div");
  document.body.append(div);
  return div;
}

afterEach(() => {
  document.body.replaceChildren();
});

describe("wizard intro hero (impeccable Wave 1.2)", () => {
  it("renders three-line hero with amber V-lead + DJ FRIEND + slogan", () => {
    const rendered = renderStep0Intro({ onBegin: () => {} });
    host().append(rendered);

    const wordmark = rendered.querySelector<HTMLElement>(".wizard-intro__wordmark");
    const lead = rendered.querySelector<HTMLElement>(".wizard-intro__wordmark-lead");
    const phrase = rendered.querySelector<HTMLElement>(".wizard-intro__phrase");
    const slogan = rendered.querySelector<HTMLElement>(".wizard-intro__slogan");

    expect(wordmark?.textContent).toBe("VIBEMIX");
    expect(lead?.textContent).toBe("V");
    expect(phrase?.textContent).toBe("DJ FRIEND");
    expect(slogan?.textContent?.toLowerCase()).toContain("in your ear");
  });

  it("renders ONE primary armed CTA that fires onBegin", () => {
    let called = 0;
    const rendered = renderStep0Intro({ onBegin: () => called++ });
    host().append(rendered);

    const buttons = rendered.querySelectorAll<HTMLButtonElement>("button");
    expect(buttons).toHaveLength(1);
    buttons[0]!.click();
    expect(called).toBe(1);
  });

  it("has NO border-anim sweep, NO glass-tile shell (full-void brand surface)", () => {
    const rendered = renderStep0Intro({ onBegin: () => {} });
    host().append(rendered);
    expect(rendered.querySelector(".border-anim")).toBeNull();
    expect(rendered.classList.contains("vmx-tile")).toBe(false);
  });
});
