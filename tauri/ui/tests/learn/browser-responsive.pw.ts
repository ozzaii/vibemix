// SPDX-License-Identifier: Apache-2.0

import { expect, test } from "@playwright/test";

test.describe("Learn browser responsive shell", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
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

  test("first paint does not overflow a narrow practice-booth viewport", async ({
    page,
  }) => {
    const overflow = await page.evaluate(() => {
      const viewportWidth = document.documentElement.clientWidth;
      const shellSelectors = [
        "#learn-root",
        "#learn-titlebar",
        "#learn-stage",
        "#learn-status-bar",
      ];
      return shellSelectors
        .map((selector) => {
          const node = document.querySelector(selector);
          if (!node) return null;
          const rect = node.getBoundingClientRect();
          return {
            selector,
            left: Math.round(rect.left),
            right: Math.round(rect.right),
            width: Math.round(rect.width),
            viewportWidth,
          };
        })
        .filter((row) => row !== null)
        .filter(
          (row) =>
            row.left < -1 ||
            row.right > viewportWidth + 1 ||
            row.width > viewportWidth + 1,
        );
    });

    expect(overflow).toEqual([]);
    await expect(page.locator("#learn-booth-panel")).toBeVisible();
    await expect(page.locator("#learn-start-recommended")).toBeVisible();
    await expect(page.locator("#learn-open-map")).toBeVisible();
  });
});
