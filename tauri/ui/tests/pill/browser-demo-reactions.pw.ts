// SPDX-License-Identifier: Apache-2.0

import { expect, test, type Page } from "@playwright/test";

const REACTIONS = [
  { tone: "clean", label: "CLEAN", lead: "CLEAN." },
  { tone: "sexy", label: "SEXY", lead: "SEXY." },
  { tone: "mid", label: "MID", lead: "MID," },
  { tone: "bomb", label: "BOMB", lead: "BOMB." },
  { tone: "lit_aff", label: "LIT AFF", lead: "LIT AFF." },
  { tone: "negative", label: "NEG", lead: "NEG." },
] as const;

test.describe("pill demo reaction triggers", () => {
  test("demo pads open every full reaction with tone-specific canvas FX", async ({ page }) => {
    await page.setViewportSize({ width: 760, height: 320 });
    await page.goto("/pill.html?controls=1", { waitUntil: "domcontentloaded" });

    const pill = page.locator("#pill");
    const controls = page.locator("#pill-demo-controls");
    const stage = page.locator("#pill-demo-stage");
    await expect(controls).toBeVisible();
    await expect(stage).toBeAttached();

    for (const reaction of REACTIONS) {
      const button = controls.locator(`button[data-demo-tone="${reaction.tone}"]`);
      await expect(button).toHaveText(reaction.label);

      await button.click();

      await expect(pill).toHaveAttribute("data-state", "expand");
      await expect(pill).toHaveAttribute("data-open", "true");
      await expect(pill).toHaveAttribute("data-reaction-tone", reaction.tone);
      await expect(pill).toHaveAttribute("data-fx", reaction.tone);
      await expect(page.locator("#pill-label")).toHaveText("SVEN");
      await expect(page.locator("#pill-reaction .pill__reaction-lead")).toHaveText(
        reaction.lead,
      );
      await expect(button).toHaveAttribute("aria-pressed", "true");
      await expect(controls).toHaveAttribute("data-active-tone", reaction.tone);
      await expect(stage).toHaveAttribute("data-active-tone", reaction.tone);
      await expect(stage.locator(`.pill-demo-stage__hit[data-tone="${reaction.tone}"]`))
        .toHaveCount(1);

      const pixels = await waitForReactionFxPixels(page, reaction.tone);
      expect(pixels.width).toBeGreaterThan(0);
      expect(pixels.height).toBeGreaterThan(0);
      expect(pixels.litPixels).toBeGreaterThan(0);
      expect(pixels.maxAlpha).toBeGreaterThan(0);
    }
  });

  test("number shortcuts fire full reactions with centered pad feedback", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 760, height: 320 });
    await page.goto("/pill.html?controls=1", { waitUntil: "domcontentloaded" });

    const pill = page.locator("#pill");
    const controls = page.locator("#pill-demo-controls");
    const stage = page.locator("#pill-demo-stage");
    await expect(controls).toBeVisible();
    await expect(stage).toBeAttached();

    for (const [index, reaction] of REACTIONS.entries()) {
      const key = String(index + 1);
      const button = controls.locator(`button[data-demo-tone="${reaction.tone}"]`);

      await page.keyboard.press(key);

      await expect(pill).toHaveAttribute("data-state", "expand");
      await expect(pill).toHaveAttribute("data-open", "true");
      await expect(pill).toHaveAttribute("data-reaction-tone", reaction.tone);
      await expect(button).toHaveAttribute("aria-pressed", "true");
      await expect(controls).toHaveAttribute("data-active-tone", reaction.tone);
      await expect(stage).toHaveAttribute("data-active-tone", reaction.tone);
      await expect(stage.locator(`.pill-demo-stage__hit[data-tone="${reaction.tone}"]`))
        .toHaveCount(1);

      const keyboardPad = await button.evaluate((el) => ({
        padX: el.style.getPropertyValue("--pad-x"),
        padY: el.style.getPropertyValue("--pad-y"),
        tiltX: el.style.getPropertyValue("--pad-tilt-x"),
        tiltY: el.style.getPropertyValue("--pad-tilt-y"),
        hitPulse: el.getAttribute("data-hit-pulse"),
      }));
      expect(keyboardPad).toMatchObject({
        padX: "50%",
        padY: "50%",
        tiltX: "0",
        tiltY: "0",
      });
      expect(keyboardPad.hitPulse).toMatch(/^[ab]$/);
    }
  });

  test("compact controls become a two-row pad bank with readable warning lead", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 360, height: 360 });
    await page.goto("/pill.html?controls=1", { waitUntil: "domcontentloaded" });

    const controls = page.locator("#pill-demo-controls");
    await expect(controls).toBeVisible();

    const compact = await page.evaluate(() => {
      const controlsEl = document.querySelector<HTMLElement>("#pill-demo-controls");
      if (!controlsEl) throw new Error("pill demo controls missing");
      const buttons = Array.from(
        controlsEl.querySelectorAll<HTMLButtonElement>("button[data-demo-tone]"),
      );
      const rowTops = new Set(buttons.map((button) => Math.round(button.getBoundingClientRect().top)));
      return {
        rowCount: rowTops.size,
        minButtonWidth: Math.min(...buttons.map((button) => button.getBoundingClientRect().width)),
        litAffWhiteSpace: getComputedStyle(
          controlsEl.querySelector<HTMLElement>('[data-demo-tone="lit_aff"]')!,
        ).whiteSpace,
      };
    });

    expect(compact.rowCount).toBe(2);
    expect(compact.minButtonWidth).toBeGreaterThan(96);
    expect(compact.litAffWhiteSpace).toBe("nowrap");

    await controls.locator('[data-demo-tone="negative"]').click();
    await expect(page.locator("#pill")).toHaveAttribute("data-reaction-tone", "negative");

    const warning = await page.evaluate(() => {
      const pill = document.querySelector<HTMLElement>("#pill");
      const controlsEl = document.querySelector<HTMLElement>("#pill-demo-controls");
      const lead = document.querySelector<HTMLElement>(".pill__reaction-lead");
      if (!pill || !controlsEl || !lead) throw new Error("negative reaction DOM missing");

      const silkProbe = document.createElement("span");
      silkProbe.style.color = "var(--silk)";
      document.body.append(silkProbe);
      const silkColor = getComputedStyle(silkProbe).color;
      silkProbe.remove();

      const pillRect = pill.getBoundingClientRect();
      const controlsRect = controlsEl.getBoundingClientRect();
      const leadStyle = getComputedStyle(lead);
      return {
        leadColor: leadStyle.color,
        silkColor,
        leadBackground: leadStyle.backgroundColor,
        leadBorderRadius: leadStyle.borderRadius,
        controlsBelowPill: controlsRect.top > pillRect.bottom + 4,
      };
    });

    expect(warning.leadColor).toBe(warning.silkColor);
    expect(warning.leadBackground).not.toBe("rgba(0, 0, 0, 0)");
    expect(warning.leadBorderRadius).not.toBe("0px");
    expect(warning.controlsBelowPill).toBe(true);
  });

  test("full reaction collapses into a durable face echo and resets the pad", async ({
    page,
  }) => {
    test.setTimeout(12_000);
    await page.setViewportSize({ width: 760, height: 320 });
    await page.goto("/pill.html?controls=1", { waitUntil: "domcontentloaded" });

    const pill = page.locator("#pill");
    const label = page.locator("#pill-label");
    const bomb = page.locator('#pill-demo-controls button[data-demo-tone="bomb"]');
    await bomb.click();
    await expect(pill).toHaveAttribute("data-state", "expand");
    await expect(label).toHaveText("SVEN");
    await expect(bomb).toHaveAttribute("aria-pressed", "true");

    await expect(pill).toHaveAttribute("data-state", "idle", { timeout: 7_000 });
    await expect(pill).toHaveAttribute("data-open", "false");
    await expect(pill).toHaveAttribute("data-reaction-echo", "bomb");
    await expect(label).toHaveText("BOMB");
    await expect(bomb).toHaveAttribute("aria-pressed", "false");

    const collapsed = await page.evaluate(() => {
      const pillEl = document.querySelector<HTMLElement>("#pill");
      if (!pillEl) throw new Error("pill missing after reaction collapse");
      return Math.round(pillEl.getBoundingClientRect().height);
    });
    expect(collapsed).toBeLessThanOrEqual(46);

    await page.hover("#pill");
    await expect(pill).toHaveAttribute("data-peek", "true");
    await expect(pill).toHaveAttribute("data-open", "true");
    await expect(label).toHaveText("NEXT READY");
    await expect(pill).not.toHaveAttribute("data-reaction-echo", /.+/);

    await page.mouse.move(740, 300);
    await expect(pill).toHaveAttribute("data-peek", "false");

    await expect(pill).not.toHaveAttribute("data-reaction-echo", /.+/, {
      timeout: 2_400,
    });
    await expect(label).toHaveText("IDLE");
  });

  test("reduced motion keeps full reactions readable without canvas FX", async ({
    page,
  }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize({ width: 760, height: 320 });
    await page.goto("/pill.html?controls=1", { waitUntil: "domcontentloaded" });

    const pill = page.locator("#pill");
    await page.locator('#pill-demo-controls button[data-demo-tone="lit_aff"]').click();

    await expect(pill).toHaveAttribute("data-state", "expand");
    await expect(pill).toHaveAttribute("data-reaction-tone", "lit_aff");
    await expect(pill).not.toHaveAttribute("data-fx", /.+/);
    await expect(page.locator("#pill-reaction .pill__reaction-lead")).toHaveText(
      "LIT AFF.",
    );

    const motion = await page.evaluate(() => {
      const canvas = document.querySelector<HTMLCanvasElement>("#pill-fx");
      const lead = document.querySelector<HTMLElement>(".pill__reaction-lead");
      if (!canvas || !lead) throw new Error("pill reduced-motion reaction DOM missing");
      const context = canvas.getContext("2d");
      const data = context && canvas.width > 0 && canvas.height > 0
        ? context.getImageData(0, 0, canvas.width, canvas.height).data
        : new Uint8ClampedArray();
      let litPixels = 0;
      for (let index = 3; index < data.length; index += 4) {
        if ((data[index] ?? 0) > 0) litPixels += 1;
      }
      return {
        canvasOpacity: getComputedStyle(canvas).opacity,
        leadAnimation: getComputedStyle(lead).animationName,
        litPixels,
      };
    });

    expect(motion).toEqual({
      canvasOpacity: "0",
      leadAnimation: "none",
      litPixels: 0,
    });
  });
});

async function waitForReactionFxPixels(
  page: Page,
  tone: (typeof REACTIONS)[number]["tone"],
): Promise<{ width: number; height: number; litPixels: number; maxAlpha: number }> {
  await page.waitForFunction(
    (expectedTone) => {
      const pill = document.querySelector<HTMLElement>("#pill");
      const canvas = document.querySelector<HTMLCanvasElement>("#pill-fx");
      if (!pill || !canvas || pill.dataset.fx !== expectedTone) return false;
      const context = canvas.getContext("2d");
      if (!context || canvas.width <= 0 || canvas.height <= 0) return false;
      const data = context.getImageData(0, 0, canvas.width, canvas.height).data;
      for (let index = 3; index < data.length; index += 4) {
        if ((data[index] ?? 0) > 0) return true;
      }
      return false;
    },
    tone,
    { timeout: 800 },
  );

  return page.evaluate(() => {
    const canvas = document.querySelector<HTMLCanvasElement>("#pill-fx");
    if (!canvas) throw new Error("pill fx canvas missing");
    const context = canvas.getContext("2d");
    if (!context) throw new Error("pill fx context missing");
    const data = context.getImageData(0, 0, canvas.width, canvas.height).data;
    let litPixels = 0;
    let maxAlpha = 0;
    for (let index = 3; index < data.length; index += 4) {
      const alpha = data[index] ?? 0;
      if (alpha > 0) litPixels += 1;
      maxAlpha = Math.max(maxAlpha, alpha);
    }
    return {
      width: canvas.width,
      height: canvas.height,
      litPixels,
      maxAlpha,
    };
  });
}
