// SPDX-License-Identifier: Apache-2.0

import { expect, test } from "@playwright/test";
import axe from "axe-core";

test.describe("Learn browser axe audit", () => {
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
    await page.addScriptTag({ content: axe.source });
  });

  test("practice booth has no serious WCAG axe violations", async ({ page }) => {
    const results = await page.evaluate(async () => {
      const axeApi = (
        window as Window & {
          axe?: typeof import("axe-core");
        }
      ).axe;
      if (!axeApi) throw new Error("axe-core missing from page");
      return await axeApi.run(document, {
        runOnly: {
          type: "tag",
          values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"],
        },
      });
    });

    const serious = results.violations
      .filter((violation) => violation.impact === "critical" || violation.impact === "serious")
      .map((violation) => ({
        id: violation.id,
        impact: violation.impact,
        targets: violation.nodes.map((node) => node.target.join(" ")).slice(0, 5),
      }));

    expect(serious).toEqual([]);
  });
});
