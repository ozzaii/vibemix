/* start-gate.spec.ts — SHIP-WIRE START-gate.
 *
 * The live deck is ARMED (idle, no reactions) until the user presses Start;
 * Stop returns it to armed. This is the pre-ship "the only thing": the app
 * must not react before the user explicitly goes live.
 *
 * Pins:
 *   - boot armed → data-runstate="armed", the Start gate renders, no Stop.
 *   - running deck → data-runstate="running", Stop renders; defaultState() is
 *     "running" so every existing session fixture keeps the live deck.
 *   - Start click flips the deck to running OPTIMISTICALLY (the repaint
 *     convention) and fires the onStart handler exactly once.
 *   - Stop click flips back to armed optimistically and fires onStop once.
 *   - armed hides the reaction zone (the no-reactions contract) and the gate
 *     CSS is on-brand (rose/var, zero raw hex).
 *
 * jsdom never applies stylesheet `display`, so the visual-hiding assertions
 * read the data-runstate attribute (the contract the CSS keys off) and the
 * injected component <style> rule, not computed visibility.
 */

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  defaultState,
  mountSessionLayout,
} from "../../src/session/SessionLayout.js";

function host(): HTMLElement {
  const div = document.createElement("div");
  document.body.append(div);
  return div;
}

function sessionRoot(h: HTMLElement): HTMLElement {
  const root = h.querySelector<HTMLElement>(".vmx-session");
  if (!root) throw new Error("no .vmx-session mounted");
  return root;
}

function layoutStyle(): string {
  const style = document.head.querySelector<HTMLStyleElement>(
    'style[data-scope="vmx-session"]',
  );
  return style?.textContent ?? "";
}

function cssBlock(css: string, selector: string): string {
  const needle = `\n  ${selector} {`;
  const start = css.indexOf(needle);
  if (start === -1) return "";
  const end = css.indexOf("\n  }", start);
  return end === -1 ? css.slice(start) : css.slice(start + 3, end + 4);
}

afterEach(() => {
  document.body.replaceChildren();
});

describe("SHIP-WIRE START-gate", () => {
  it("boots armed: data-runstate=armed, the Start gate renders", () => {
    const h = host();
    mountSessionLayout(h, { ...defaultState(), runState: "armed" });
    const root = sessionRoot(h);

    expect(root.dataset.runstate).toBe("armed");
    expect(root.querySelector(".vmx-armed")).toBeTruthy();
    expect(root.querySelector('[data-action="start"]')).toBeTruthy();
    expect(
      root.querySelector<HTMLElement>('[data-action="start"]')?.textContent,
    ).toBe("Go live");
  });

  it("boots armed as a composed premium deck face with grounded context", () => {
    const h = host();
    const state = defaultState();
    state.runState = "armed";
    state.status.livekit = "ok";
    state.status.midi = 2;
    state.status.midiDevice = "DDJ-FLX4";
    state.persona.mood = "HYPE";
    state.persona.voice = "Adam";
    state.output.profile = "HP";
    state.output.device = "AUTO";
    mountSessionLayout(h, state);
    const root = sessionRoot(h);

    expect(root.querySelector(".vmx-armed__title")?.textContent).toBe(
      "I'm awake before the first bar.",
    );
    expect(root.querySelector(".vmx-armed__field")).toBeTruthy();
    expect(root.querySelector(".vmx-armed__module")).toBeTruthy();
    const contextValues = Array.from(
      root.querySelectorAll(".vmx-armed__context-value"),
      (el) => el.textContent,
    );
    expect(contextValues).toEqual([
      "armed",
      "DDJ-FLX4 seen",
      "HP default out",
      "hype / Adam",
    ]);
  });

  it("running deck shows Stop; defaultState() is running (existing fixtures keep the live deck)", () => {
    const h = host();
    mountSessionLayout(h); // defaultState() → runState "running"
    const root = sessionRoot(h);

    expect(root.dataset.runstate).toBe("running");
    expect(root.querySelector('[data-action="stop"]')).toBeTruthy();
    // the armed gate node still exists in the DOM (CSS hides it when running),
    // so the Stop→armed transition has a gate to reveal without a remount.
    expect(root.querySelector(".vmx-armed")).toBeTruthy();
  });

  it("pressing Start flips the deck to running optimistically and fires onStart once", () => {
    const onStart = vi.fn();
    const h = host();
    mountSessionLayout(h, { ...defaultState(), runState: "armed", onStart });
    const root = sessionRoot(h);

    root.querySelector<HTMLElement>('[data-action="start"]')?.click();

    // Optimistic repaint: the deck reads running the instant Start is pressed,
    // before any wire round-trip (the render-loop's onStart makes it
    // authoritative via setSessionState + ipc.session.start).
    expect(root.dataset.runstate).toBe("running");
    expect(onStart).toHaveBeenCalledTimes(1);
  });

  it("pressing Stop flips the deck to armed optimistically and fires onStop once", () => {
    const onStop = vi.fn();
    const h = host();
    mountSessionLayout(h, { ...defaultState(), runState: "running", onStop });
    const root = sessionRoot(h);

    root.querySelector<HTMLElement>('[data-action="stop"]')?.click();

    expect(root.dataset.runstate).toBe("armed");
    expect(onStop).toHaveBeenCalledTimes(1);
  });

  it("armed hides the reaction zone (the no-reactions contract lives in the gate CSS)", () => {
    const css = layoutStyle();
    expect(css).toContain('[data-runstate="armed"] .vmx-voice');
    expect(css).toMatch(/\[data-runstate="armed"\]\s+\.vmx-voice\s*\{\s*display:\s*none/);
    // Stop is a running-only control; the gate owns the armed deck.
    expect(css).toContain('[data-runstate="running"] .vmx-deck__controls button[data-action="stop"]');
  });

  it("running voice well is frameless — glows on the open void, no slab frame or bevel", () => {
    const css = layoutStyle();
    const voice = cssBlock(css, ".vmx-voice");
    const voiceFrame = cssBlock(css, ".vmx-voice::before");
    const foot = cssBlock(css, ".vmx-deck__foot");

    // BOLD REDESIGN (2026-06-08, "go bold"): the glass slab + engraved bevel are
    // gone; the voice reads off the raw obsidian, lit only by one rose key-light.
    expect(voice).toContain("border: 0");
    expect(voice).toContain("radial-gradient");
    expect(voice).not.toContain("var(--bevel-raised)");
    expect(voiceFrame).toContain("display: none");
    expect(foot).toContain("border-top: 0");
    expect(foot).toContain("box-shadow: inset 0 1px 0");
  });

  it("the Start gate is on-brand: zero raw hex in the gate CSS (rose rgba/var only)", () => {
    const css = layoutStyle();
    const gateLines = css
      .split("\n")
      .filter((l) => l.includes("vmx-armed") || l.includes("data-runstate"));
    expect(gateLines.length).toBeGreaterThan(0);
    for (const line of gateLines) {
      expect(line).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    }
  });
});
