// SPDX-License-Identifier: Apache-2.0

import { expect, test } from "@playwright/test";

test.describe("Learn browser accessibility invariants", () => {
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

  test("visible buttons have accessible names and the page has no duplicate ids", async ({
    page,
  }) => {
    const unnamedButtons = await page.locator("button").evaluateAll((buttons) => {
      const isRendered = (node: Element): boolean => {
        if (node instanceof HTMLElement && node.hidden) return false;
        let current: Element | null = node;
        while (current) {
          if (current instanceof HTMLElement || current instanceof SVGElement) {
            const style = getComputedStyle(current);
            if (style.display === "none" || style.visibility === "hidden") {
              return false;
            }
          }
          current = current.parentElement;
        }
        return true;
      };
      return buttons
        .filter((button) => isRendered(button))
        .map((button) => ({
          id: button.id,
          text: button.textContent?.trim() ?? "",
          ariaLabel: button.getAttribute("aria-label")?.trim() ?? "",
          title: button.getAttribute("title")?.trim() ?? "",
        }))
        .filter((button) => !button.text && !button.ariaLabel && !button.title);
    });

    expect(unnamedButtons).toEqual([]);

    const duplicateIds = await page.locator("[id]").evaluateAll((nodes) => {
      const counts = new Map<string, number>();
      for (const node of nodes) {
        counts.set(node.id, (counts.get(node.id) ?? 0) + 1);
      }
      return Array.from(counts.entries())
        .filter(([, count]) => count > 1)
        .map(([id, count]) => ({ id, count }));
    });

    expect(duplicateIds).toEqual([]);
  });

  test("rendered controller controls expose keyboardable button semantics", async ({
    page,
  }) => {
    const controls = page.locator("svg.learn-controller-schematic [data-control-id]");
    await expect(controls.first()).toBeVisible();

    const violations = await controls.evaluateAll((nodes) => {
      const isRendered = (node: Element): boolean => {
        if (node instanceof HTMLElement && node.hidden) return false;
        let current: Element | null = node;
        while (current) {
          if (current instanceof HTMLElement || current instanceof SVGElement) {
            const style = getComputedStyle(current);
            if (style.display === "none" || style.visibility === "hidden") {
              return false;
            }
          }
          current = current.parentElement;
        }
        return true;
      };
      return nodes
        .filter((node) => isRendered(node))
        .map((node) => ({
          controlId: node.getAttribute("data-control-id"),
          role: node.getAttribute("role"),
          tabIndex: node.getAttribute("tabindex"),
          label: node.getAttribute("aria-label")?.trim() ?? "",
        }))
        .filter(
          (node) =>
            node.role !== "button" ||
            node.tabIndex !== "0" ||
            node.label.length === 0,
        );
    });

    expect(violations).toEqual([]);
  });

  test("visible focus targets are not inside aria-hidden containers", async ({
    page,
  }) => {
    await page.locator("#learn-open-map").click();
    await expect(page.locator("#learn-progress-list-host")).toHaveAttribute(
      "aria-hidden",
      "false",
    );
    await page.locator("#learn-close-map").click();
    await expect(page.locator("#learn-progress-list-host")).toHaveAttribute(
      "aria-hidden",
      "true",
    );

    const hiddenFocusable = await page.evaluate(() => {
      const isRendered = (node: Element): boolean => {
        if (node instanceof HTMLElement && node.hidden) return false;
        let current: Element | null = node;
        while (current) {
          if (current instanceof HTMLElement || current instanceof SVGElement) {
            const style = getComputedStyle(current);
            if (style.display === "none" || style.visibility === "hidden") {
              return false;
            }
          }
          current = current.parentElement;
        }
        return true;
      };
      const focusableSelector = [
        "a[href]",
        "button",
        "input",
        "select",
        "textarea",
        "[tabindex]:not([tabindex='-1'])",
      ].join(",");
      return Array.from(document.querySelectorAll("[aria-hidden='true']")).flatMap(
        (container) =>
          Array.from(container.querySelectorAll<HTMLElement>(focusableSelector))
            .filter((node) => !node.hasAttribute("disabled"))
            .filter((node) => isRendered(node))
            .map((node) => ({
              containerId: (container as HTMLElement).id,
              id: node.id,
              text: node.textContent?.trim() ?? "",
            })),
      );
    });

    expect(hiddenFocusable).toEqual([]);
  });
});
