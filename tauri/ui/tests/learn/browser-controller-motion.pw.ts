// SPDX-License-Identifier: Apache-2.0

import { expect, test } from "@playwright/test";

test.describe("Learn browser controller motion", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      class StubWebSocket extends EventTarget {
        static readonly CONNECTING = 0;
        static readonly OPEN = 1;
        static readonly CLOSING = 2;
        static readonly CLOSED = 3;
        readyState = StubWebSocket.OPEN;
        onopen: ((ev: Event) => void) | null = null;
        onmessage: ((ev: MessageEvent) => void) | null = null;
        onclose: ((ev: CloseEvent) => void) | null = null;
        onerror: ((ev: Event) => void) | null = null;

        constructor() {
          super();
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

  test("screen-deck fader thumbs translate while parent controls stay stable", async ({
    page,
  }) => {
    await page.evaluate(() => {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.midi_position", {
          detail: {
            controller_id: "pioneer_ddj_flx4",
            positions: {
              "vol:A": 127,
              xfader: 0,
            },
          },
        }),
      );
    });

    const volumeGroup = page.locator('[data-control-id="vol:A"]');
    const volumeThumb = page.locator(
      '[data-control-id="vol:A"] > rect[data-fader-thumb="true"]',
    );
    await expect(volumeGroup).not.toHaveAttribute("transform", /rotate/);
    await expect(volumeThumb).toHaveAttribute("transform", "translate(0 -200)");

    const crossfaderGroup = page.locator('[data-control-id="xfader"]');
    const crossfaderThumb = page.locator(
      '[data-control-id="xfader"] > rect[data-fader-thumb="true"]',
    );
    await expect(crossfaderGroup).not.toHaveAttribute("transform", /rotate/);
    await expect(crossfaderThumb).toHaveAttribute("transform", "translate(-142 0)");
  });
});
