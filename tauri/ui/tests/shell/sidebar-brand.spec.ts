/**
 * @vitest-environment jsdom
 *
 * The shell sidebar carries vibemix's single persistent brand mark (the session
 * titlebar is suppressed inside the fold, so this is THE trademark the user sees
 * on every surface). This contract locks the two-tone lockup — "vibe" in ink,
 * "mix" lit in brand rose — so a future edit can't quietly flatten it back to
 * the corporate all-caps chrome word it started as.
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { mountDesktopShell, type MountedShell } from "../../src/shell/DesktopShell.js";

let shell: MountedShell | null = null;
let host: HTMLElement;

beforeEach(() => {
  globalThis.localStorage?.clear();
  host = document.createElement("div");
  document.body.append(host);
});

afterEach(() => {
  shell?.teardown();
  shell = null;
  host.remove();
});

describe("sidebar brand mark", () => {
  it("renders the wordmark as a two-tone lockup: 'vibe' + 'mix' in their own marks", () => {
    shell = mountDesktopShell(host);
    const wm = host.querySelector<HTMLElement>(".sb-wordmark");
    expect(wm).toBeTruthy();
    // The reading order is unbroken — the mark still says one word.
    expect(wm!.textContent).toBe("vibemix");
    // ...but split so the second syllable can carry the lit brand color.
    const vibe = wm!.querySelector<HTMLElement>(".wm-vibe");
    const mix = wm!.querySelector<HTMLElement>(".wm-mix");
    expect(vibe?.textContent).toBe("vibe");
    expect(mix?.textContent).toBe("mix");
  });

  it("keeps the listening ear as the brand sign-of-life beside the wordmark", () => {
    shell = mountDesktopShell(host);
    const brand = host.querySelector<HTMLElement>(".sb-brand")!;
    // The ear (breathing rose dot) stays — it survives collapse as the lone
    // brand glyph, so the wordmark split must not displace it.
    expect(brand.querySelector(".sb-ear")).toBeTruthy();
    expect(brand.querySelector(".sb-wordmark")).toBeTruthy();
  });
});
