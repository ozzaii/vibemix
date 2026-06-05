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

  test("ready waveforms take their own row below the controller stage", async ({
    page,
  }) => {
    await page.evaluate(() => {
      const deck = {
        bpm: 128,
        duration_s: 180,
        peaks: Array.from({ length: 96 }, (_, i) => [
          48 + (i % 6) * 18,
          32 + (i % 5) * 14,
          20 + (i % 4) * 10,
        ]),
        cues: [{ label: "drop", start_s: 80, end_s: 96 }],
      };
      window.dispatchEvent(
        new CustomEvent("ipc.learn.waveform_ready", {
          detail: {
            sample_rate: 48000,
            beat_interval_s: 0.468,
            decks: { A: deck, B: deck },
          },
        }),
      );
    });

    const waveformHost = page.locator("#learn-waveform-host");
    await expect(waveformHost).toHaveAttribute("data-ready", "true");
    await expect(waveformHost).toBeVisible();

    const rects = await page.evaluate(() => {
      const stage = document.querySelector("#learn-stage")!.getBoundingClientRect();
      const waveform = document
        .querySelector("#learn-waveform-host")!
        .getBoundingClientRect();
      return {
        stageBottom: Math.round(stage.bottom),
        waveformTop: Math.round(waveform.top),
        waveformHeight: Math.round(waveform.height),
      };
    });

    expect(rects.waveformHeight).toBeGreaterThan(100);
    expect(rects.waveformTop).toBeGreaterThanOrEqual(rects.stageBottom - 1);
  });
});
