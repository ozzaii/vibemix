// SPDX-License-Identifier: Apache-2.0

import { expect, test, type Locator } from "@playwright/test";

import { contrastRatio, tokenColor, type Rgba } from "./contrast-helpers";

const AA_NORMAL = 4.5;
const AAA_NORMAL = 7;

test.describe("Learn browser contrast", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      class StubWebSocket extends EventTarget {
        static readonly CONNECTING = 0;
        static readonly OPEN = 1;
        static readonly CLOSING = 2;
        static readonly CLOSED = 3;
        readonly url: string;
        readyState = StubWebSocket.OPEN;
        onopen: ((ev: Event) => void) | null = null;
        onmessage: ((ev: MessageEvent) => void) | null = null;
        onclose: ((ev: CloseEvent) => void) | null = null;
        onerror: ((ev: Event) => void) | null = null;

        constructor(url: string) {
          super();
          this.url = url;
          setTimeout(() => this.onopen?.(new Event("open")), 0);
        }

        send(): void {}

        close(): void {
          this.readyState = StubWebSocket.CLOSED;
          this.onclose?.(new CloseEvent("close"));
        }
      }

      Object.defineProperty(window, "WebSocket", {
        configurable: true,
        value: StubWebSocket,
      });
    });

    await page.goto("/learn.html");
    await page.locator("#learn-root").waitFor();
    await page.locator("svg.learn-controller-schematic").waitFor();
  });

  test("tutor dock text clears contrast thresholds in computed browser styles", async ({
    page,
  }) => {
    await page.evaluate(() => {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.lesson_loaded", {
          detail: {
            course_id: "course_1_anatomy",
            lesson_id: "L1.01",
            title: "Opening dialog",
            controller_id: "pioneer_ddj_flx4",
            progress_dots: [{ lesson_id: "L1.01", status: "current" }],
          },
        }),
      );
      window.dispatchEvent(
        new CustomEvent("ipc.learn.tutor_speak", {
          detail: {
            text: "Press play on deck A.",
            tts_marker: "L1.01.beat0",
            citations: [],
            data_state: "active",
          },
        }),
      );
      window.dispatchEvent(
        new CustomEvent("ipc.learn.tutor_speak", {
          detail: {
            text: "Use the lit control; do not rush it.",
            tts_marker: "L1.01.hint0",
            citations: [],
            data_state: "hint",
          },
        }),
      );
    });

    const now = page.locator(".tutor-dock .now");
    const hint = page.locator(".tutor-dock .hint-line");
    await expect(now).toHaveText("Press play on deck A.");
    await expect(hint).toHaveText("Use the lit control; do not rush it.");

    expect(await fontSizePx(now)).toBe(28);
    expect(contrastRatio(await computedColor(now), tokenColor("void"))).toBeGreaterThanOrEqual(
      AAA_NORMAL,
    );
    expect(contrastRatio(await computedColor(hint), tokenColor("void"))).toBeGreaterThanOrEqual(
      AA_NORMAL,
    );
  });

  test("amber and warning cue highlights render with AA computed contrast", async ({
    page,
  }) => {
    await page.evaluate(() => {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.highlight", {
          detail: {
            control_id: "play",
            deck: "A",
            cue_color: "amber",
            cue_shape: "pulse-ring",
            annotation: "Press play.",
            expected_action: { type: "button", control: "play", deck: "A" },
          },
        }),
      );
    });

    const play = page.locator('[data-control-id="play:A"]');
    await expect(play).toHaveAttribute("data-cue-color", "amber");
    expect(contrastRatio(await computedColor(play), tokenColor("void"))).toBeGreaterThanOrEqual(
      AA_NORMAL,
    );

    await page.evaluate(() => {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.highlight", {
          detail: {
            control_id: "play",
            deck: "A",
            cue_color: "warning",
            cue_shape: "static-glow",
            annotation: "Check this control.",
            expected_action: { type: "button", control: "play", deck: "A" },
          },
        }),
      );
    });

    await expect(play).toHaveAttribute("data-cue-color", "warning");
    expect(contrastRatio(await computedColor(play), tokenColor("void"))).toBeGreaterThanOrEqual(
      AA_NORMAL,
    );
  });
});

async function computedColor(locator: Locator): Promise<Rgba> {
  const value = await locator.evaluate((el) => getComputedStyle(el).color);
  return parseComputedColor(value);
}

async function fontSizePx(locator: Locator): Promise<number> {
  const value = await locator.evaluate((el) => getComputedStyle(el).fontSize);
  return Number.parseFloat(value);
}

function parseComputedColor(value: string): Rgba {
  const match = value.match(/^rgba?\(([^)]+)\)$/i);
  if (!match) throw new Error(`Unsupported computed color: ${value}`);
  const parts = match[1]!.split(",").map((part) => Number.parseFloat(part.trim()));
  return {
    r: parts[0]!,
    g: parts[1]!,
    b: parts[2]!,
    a: parts[3] ?? 1,
  };
}
