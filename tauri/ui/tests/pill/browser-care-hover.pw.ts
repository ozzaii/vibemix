// SPDX-License-Identifier: Apache-2.0

import { expect, test, type Page } from "@playwright/test";

const CARE_FRAME = {
  type: "snapshot",
  cohost_status: "LISTENING",
  voice: 0.08,
  next_suggestion: {
    track_id: "care:strobe",
    title: "Strobe",
    artist: "Test Booth",
    why: "similar vibe",
    transition: {
      candidate_id: "care:tr_001",
      target_deck: "B",
      start_in_bars: 4,
      move_grade: {
        slug: "negative",
        label: "NEG",
        xp: 0,
        intensity: 0,
        reason: "key clash",
        deserved: false,
        overdrive: false,
      },
    },
    decision: {
      candidate_id: "care:tr_001",
      timing_text: "in 4 bars",
      spoken_text: "load B in 4 bars",
    },
  },
};

const CARE_FRAME_RETIMER = {
  ...CARE_FRAME,
  next_suggestion: {
    ...CARE_FRAME.next_suggestion,
    transition: {
      ...CARE_FRAME.next_suggestion.transition,
      start_in_bars: 8,
    },
    decision: {
      ...CARE_FRAME.next_suggestion.decision,
      timing_text: "in 8 bars",
      spoken_text: "load B in 8 bars",
    },
  },
};

const KEEP_FRAME = {
  type: "snapshot",
  cohost_status: "LISTENING",
  voice: 0.08,
  next_suggestion: {
    track_id: "keep:velvet-pressure",
    title: "Velvet Pressure",
    artist: "Mira Vale",
    why: "same late-night pulse",
    transition: {
      candidate_id: "keep:tr_001",
      target_deck: "B",
      start_in_bars: 8,
      move_grade: {
        slug: "sexy",
        label: "SEXY",
        xp: 48,
        intensity: 66,
        reason: "smooth blend",
        deserved: true,
        overdrive: false,
      },
    },
    decision: {
      candidate_id: "keep:tr_001",
      timing_text: "in 8 bars",
      spoken_text: "load B in 8 bars",
    },
  },
};

const REACTION_FRAME = {
  type: "cohost-reaction",
  cohost_status: "TALKING",
  voice: 0.48,
  peak: 0.76,
  text: "BOMB. Drop landed. Floor opens.",
  citation_strip: [
    {
      event_id: "demo:bomb:128.0",
      verb: "BOMB",
      timestamp_s: 128,
    },
  ],
};

const LONG_CARE_FRAME = {
  type: "snapshot",
  cohost_status: "LISTENING",
  voice: 0.08,
  next_suggestion: {
    track_id: "care:very-long-name",
    title: "The Velvet Pressure Dub With The Extremely Long Booth Name",
    artist: "Mira Vale And The Late Room Pressure Ensemble",
    why: "same late-night pulse with a long crate note",
    transition: {
      candidate_id: "care:tr_long",
      target_deck: "B",
      cue_slot: "A",
      start_in_bars: 16,
      from_role: "outro",
      to_role: "intro",
      move_grade: {
        slug: "negative",
        label: "NEG",
        xp: 0,
        intensity: 0,
        reason: "harmonic rub with vocal stack, wait for cleaner exit",
        deserved: false,
        overdrive: false,
      },
    },
    decision: {
      candidate_id: "care:tr_long",
      timing_text: "in 16 bars",
      spoken_text: "load B in 16 bars",
    },
  },
};

test.describe("pill DJ KNOWS hover and completion", () => {
  test("risky suggestion owns hover/click even when demo controls overlap", async ({ page }) => {
    await installFakePillBus(page);
    await page.setViewportSize({ width: 600, height: 260 });
    await page.goto("/pill.html?controls=1", { waitUntil: "domcontentloaded" });
    await waitForPillBus(page);
    await emitPillBusFrame(page, CARE_FRAME);

    await page.waitForFunction(
      () => document.querySelector<HTMLElement>("#pill")?.dataset.moveGrade === "negative",
    );

    await page.hover("#pill");
    await page.waitForFunction(
      () => document.querySelector<HTMLElement>("#pill")?.dataset.peek === "true",
    );
    await page.waitForTimeout(420);

    const result = await page.evaluate(() => {
      const pill = document.querySelector<HTMLElement>("#pill");
      const row = document.querySelector<HTMLElement>(".pill__row");
      const controls = document.querySelector<HTMLElement>("#pill-demo-controls");
      const card = document.querySelector<HTMLElement>(".pill__peek .vmx-next-card");
      const action = document.querySelector<HTMLElement>(
        ".pill__peek .vmx-next-card__peek-action",
      );
      const reason = document.querySelector<HTMLElement>(
        ".pill__peek .vmx-next-card__grade-reason",
      );
      if (!pill || !row || !controls || !card || !action || !reason) {
        throw new Error("pill care hover DOM missing");
      }

      const pillRect = pill.getBoundingClientRect();
      const controlsRect = controls.getBoundingClientRect();
      const overlapLeft = Math.max(pillRect.left, controlsRect.left);
      const overlapTop = Math.max(pillRect.top, controlsRect.top);
      const overlapRight = Math.min(pillRect.right, controlsRect.right);
      const overlapBottom = Math.min(pillRect.bottom, controlsRect.bottom);
      const overlapWidth = Math.max(0, overlapRight - overlapLeft);
      const overlapHeight = Math.max(0, overlapBottom - overlapTop);
      const overlapArea = overlapWidth * overlapHeight;
      const hit = document.elementFromPoint(overlapLeft + 2, overlapTop + 2);
      const actionRect = action.getBoundingClientRect();
      const actionStyle = getComputedStyle(action);
      const rowRail = getComputedStyle(row, "::after");
      const reasonDot = getComputedStyle(reason, "::before");

      return {
        open: pill.dataset.open,
        peek: pill.dataset.peek,
        intel: pill.dataset.intel,
        actionable: pill.dataset.actionable,
        rootGrade: pill.dataset.moveGrade,
        rootGradeEarned: pill.dataset.gradeEarned,
        cardGrade: card.dataset.moveGrade,
        cardDeserved: card.dataset.gradeDeserved,
        actionText: action.textContent,
        actionCare: action.getAttribute("data-care"),
        actionAnimation: actionStyle.animationName,
        actionWidth: Math.round(actionRect.width),
        actionHeight: Math.round(actionRect.height),
        actionBorderStyle: actionStyle.borderStyle,
        controlsZ: getComputedStyle(controls).zIndex,
        pillZ: getComputedStyle(pill).zIndex,
        hitInsidePill: hit instanceof Element && Boolean(hit.closest("#pill")),
        overlapArea: Math.round(overlapArea),
        reasonText: reason.textContent,
        reasonDotBackground: reasonDot.backgroundColor,
        rowRailBackground: rowRail.backgroundImage || rowRail.backgroundColor,
      };
    });

    expect(result).toMatchObject({
      open: "true",
      peek: "true",
      intel: "care",
      actionable: "true",
      rootGrade: "negative",
      rootGradeEarned: "false",
      cardGrade: "negative",
      cardDeserved: "false",
      actionText: "CARE",
      actionCare: "true",
      actionAnimation: "pill-peek-care-arm",
      controlsZ: "8",
      pillZ: "10",
      hitInsidePill: true,
      reasonText: "key clash",
    });
    expect(result.overlapArea).toBeGreaterThan(0);
    expect(result.actionWidth).toBeGreaterThanOrEqual(50);
    expect(result.actionHeight).toBeGreaterThanOrEqual(17);
    expect(result.actionBorderStyle).toBe("solid");
    expect(result.reasonDotBackground).toContain("244");
    expect(result.rowRailBackground).toContain("244");

    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.waitForTimeout(80);
    const reduced = await page.evaluate(() => {
      const row = document.querySelector<HTMLElement>(".pill__row");
      const action = document.querySelector<HTMLElement>(
        ".pill__peek .vmx-next-card__peek-action",
      );
      if (!row || !action) throw new Error("pill reduced-motion DOM missing");
      const rowRail = getComputedStyle(row, "::after");
      const actionStyle = getComputedStyle(action);
      return {
        actionAnimation: actionStyle.animationName,
        rowRailAnimation: rowRail.animationName,
        rowRailOpacity: rowRail.opacity,
      };
    });

    expect(reduced).toEqual({
      actionAnimation: "none",
      rowRailAnimation: "none",
      rowRailOpacity: "0.54",
    });
  });

  test("CARE click completes the pill task and suppresses stale suggestions", async ({
    page,
  }) => {
    await installFakePillBus(page);
    await page.setViewportSize({ width: 600, height: 260 });
    await page.goto("/pill.html?controls=1", { waitUntil: "domcontentloaded" });
    await waitForPillBus(page);
    await emitPillBusFrame(page, CARE_FRAME);

    await page.waitForFunction(
      () => document.querySelector<HTMLElement>("#pill")?.dataset.moveGrade === "negative",
    );
    await page.hover("#pill");
    await expect(page.locator("#pill")).toHaveAttribute("data-peek", "true");
    await page.locator(".pill__peek .vmx-next-card").click();

    const pill = page.locator("#pill");
    await expect(pill).toHaveAttribute("data-feedback", "accept");
    await expect(pill).toHaveAttribute("data-feedback-care", "true");
    await expect(pill).toHaveAttribute("data-has-next", "false");
    await expect(pill).toHaveAttribute("data-open", "false");
    await expect(page.locator("#pill-label")).toHaveText("CARE");
    await expect(page.locator("#pill-peek")).toBeEmpty();

    await page.waitForTimeout(900);
    await expect(page.locator("#pill-label")).toHaveText("CARE");

    await emitPillBusFrame(page, CARE_FRAME);
    await page.hover("#pill");
    await page.waitForTimeout(160);
    await expect(pill).toHaveAttribute("data-peek", "false");
    await expect(pill).toHaveAttribute("data-has-next", "false");
    await expect(page.locator("#pill-peek")).toBeEmpty();

    await emitPillBusFrame(page, CARE_FRAME_RETIMER);
    await page.hover("#pill");
    await expect(pill).toHaveAttribute("data-peek", "true");
    await expect(pill).toHaveAttribute("data-has-next", "true");
    await expect(page.locator(".pill__peek .vmx-next-card__transition")).toContainText(
      "in 8 bars",
    );
  });

  test("narrow DJ KNOWS card keeps long care copy readable without spill", async ({
    page,
  }) => {
    await installFakePillBus(page);
    await page.setViewportSize({ width: 320, height: 260 });
    await page.goto("/pill.html?controls=1", { waitUntil: "domcontentloaded" });
    await waitForPillBus(page);
    await emitPillBusFrame(page, LONG_CARE_FRAME);

    const pill = page.locator("#pill");
    await page.waitForFunction(
      () => document.querySelector<HTMLElement>("#pill")?.dataset.moveGrade === "negative",
    );

    await page.hover("#pill");
    await expect(pill).toHaveAttribute("data-peek", "true");
    await expect(page.locator("#pill-label")).toHaveText("DJ KNOWS");
    await expect(page.locator(".pill__peek .vmx-next-card__peek-action")).toHaveText("CARE");
    await page.waitForFunction(() => {
      const peek = document.querySelector<HTMLElement>("#pill-peek");
      const card = document.querySelector<HTMLElement>(".pill__peek .vmx-next-card");
      if (!peek || !card) return false;
      const peekRect = peek.getBoundingClientRect();
      const cardRect = card.getBoundingClientRect();
      return cardRect.bottom <= peekRect.bottom + 1;
    });

    const layout = await page.evaluate(() => {
      const pillEl = document.querySelector<HTMLElement>("#pill");
      const peek = document.querySelector<HTMLElement>("#pill-peek");
      const card = document.querySelector<HTMLElement>(".pill__peek .vmx-next-card");
      const title = card?.querySelector<HTMLElement>(".vmx-next-card__title");
      const transition = card?.querySelector<HTMLElement>(".vmx-next-card__transition");
      const grade = card?.querySelector<HTMLElement>(".vmx-next-card__grade");
      const reason = card?.querySelector<HTMLElement>(".vmx-next-card__grade-reason");
      if (!pillEl || !peek || !card || !title || !transition || !grade || !reason) {
        throw new Error("long care peek DOM missing");
      }
      const pillRect = pillEl.getBoundingClientRect();
      const peekRect = peek.getBoundingClientRect();
      const cardRect = card.getBoundingClientRect();
      const titleRect = title.getBoundingClientRect();
      const transitionRect = transition.getBoundingClientRect();
      const gradeRect = grade.getBoundingClientRect();
      const reasonStyle = getComputedStyle(reason);
      const reasonRect = reason.getBoundingClientRect();
      const tolerance = 1;

      return {
        pillWidth: Math.round(pillRect.width),
        pillAria: pillEl.getAttribute("aria-label"),
        pillScrollWidth: pillEl.scrollWidth,
        pillClientWidth: pillEl.clientWidth,
        cardAria: card.getAttribute("aria-label"),
        cardInsidePill:
          cardRect.left >= pillRect.left - tolerance &&
          cardRect.right <= pillRect.right + tolerance,
        cardInsidePeek:
          cardRect.top >= peekRect.top - tolerance &&
          cardRect.bottom <= peekRect.bottom + tolerance,
        ordered:
          titleRect.bottom <= transitionRect.top + tolerance &&
          transitionRect.bottom <= gradeRect.top + tolerance,
        titleVisible: title.textContent,
        transitionText: transition.textContent,
        transitionTitle: transition.getAttribute("title"),
        reasonText: reason.textContent,
        reasonOverflow: reasonStyle.overflow,
        reasonTextOverflow: reasonStyle.textOverflow,
        reasonWhiteSpace: reasonStyle.whiteSpace,
        reasonFontSize: reasonStyle.fontSize,
        reasonMinHeight: reasonStyle.minHeight,
        reasonTextTransform: reasonStyle.textTransform,
        reasonBackground: reasonStyle.backgroundColor,
        reasonHeight: Math.round(reasonRect.height),
      };
    });

    expect(layout).toMatchObject({
      pillWidth: 280,
      cardInsidePill: true,
      cardInsidePeek: true,
      ordered: true,
      titleVisible: LONG_CARE_FRAME.next_suggestion.title,
      transitionText: "load B · in 16 bars",
      transitionTitle: "load B · cue A · outro→intro · in 16 bars",
      reasonText: "harmonic rub with vocal stack, wait for cleaner exit",
      reasonOverflow: "hidden",
      reasonTextOverflow: "ellipsis",
      reasonWhiteSpace: "nowrap",
      reasonFontSize: "9px",
      reasonMinHeight: "13px",
      reasonTextTransform: "none",
    });
    expect(layout.pillAria).toContain("detail: load B · cue A · outro→intro · in 16 bars");
    expect(layout.cardAria).toContain("detail: load B · cue A · outro→intro · in 16 bars");
    expect(layout.reasonHeight).toBeGreaterThanOrEqual(13);
    expect(layout.reasonBackground).not.toBe("rgba(0, 0, 0, 0)");
    expect(layout.pillScrollWidth).toBeLessThanOrEqual(layout.pillClientWidth + 1);
  });

  test("focused DJ KNOWS completes KEEP with Enter and clears shortcuts", async ({
    page,
  }) => {
    await installFakePillBus(page);
    await page.setViewportSize({ width: 600, height: 260 });
    await page.goto("/pill.html?controls=1", { waitUntil: "domcontentloaded" });
    await waitForPillBus(page);
    await emitPillBusFrame(page, KEEP_FRAME);

    const pill = page.locator("#pill");
    await page.waitForFunction(
      () => document.querySelector<HTMLElement>("#pill")?.dataset.moveGrade === "sexy",
    );

    await pill.focus();
    await expect(pill).toHaveAttribute("data-peek", "true");
    await expect(pill).toHaveAttribute("data-open", "true");
    await expect(pill).toHaveAttribute("data-actionable", "true");
    await expect(pill).toHaveAttribute("aria-keyshortcuts", "Enter Space");
    await expect(pill).toHaveAttribute("aria-controls", "pill-peek");
    await expect(pill).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator("#pill-label")).toHaveText("DJ KNOWS");
    await expect(page.locator(".pill__peek .vmx-next-card__peek-action")).toHaveText("KEEP");

    const focusedAction = await pill.getAttribute("aria-label");
    expect(focusedAction).toContain("Velvet Pressure");
    expect(focusedAction).toContain("grade: SEXY, 48 xp, smooth blend");
    expect(focusedAction).toContain("activate to keep suggestion");

    await page.keyboard.press("Enter");

    await expect(pill).toHaveAttribute("data-feedback", "accept");
    await expect(pill).toHaveAttribute("data-feedback-care", "false");
    await expect(pill).toHaveAttribute("data-has-next", "false");
    await expect(pill).toHaveAttribute("data-open", "false");
    await expect(pill).toHaveAttribute("data-actionable", "false");
    await expect(pill).not.toHaveAttribute("aria-keyshortcuts", /.+/);
    await expect(pill).not.toHaveAttribute("aria-controls", /.+/);
    await expect(pill).not.toHaveAttribute("aria-expanded", /.+/);
    await expect(page.locator("#pill-label")).toHaveText("KEEP");
    await expect(page.locator("#pill-peek")).toBeEmpty();

    await expect
      .poll(() => page.evaluate(() => document.activeElement?.id))
      .toBe("pill");
  });

  test("focused peek card completes KEEP with Enter", async ({ page }) => {
    await installFakePillBus(page);
    await page.setViewportSize({ width: 600, height: 260 });
    await page.goto("/pill.html?controls=1", { waitUntil: "domcontentloaded" });
    await waitForPillBus(page);
    await emitPillBusFrame(page, KEEP_FRAME);

    const pill = page.locator("#pill");
    const card = page.locator(".pill__peek .vmx-next-card");
    await page.waitForFunction(
      () => document.querySelector<HTMLElement>("#pill")?.dataset.moveGrade === "sexy",
    );

    await page.hover("#pill");
    await expect(pill).toHaveAttribute("data-peek", "true");
    await expect(card).toHaveAttribute("role", "button");
    await expect(card).toHaveAttribute("aria-keyshortcuts", "Enter Space");
    await expect(card.locator(".vmx-next-card__peek-action")).toHaveText("KEEP");

    await card.focus();
    await expect
      .poll(() =>
        page.evaluate(() =>
          document.activeElement instanceof HTMLElement
            ? document.activeElement.className
            : "",
        ),
      )
      .toContain("vmx-next-card");

    await page.keyboard.press("Enter");

    await expect(pill).toHaveAttribute("data-feedback", "accept");
    await expect(pill).toHaveAttribute("data-feedback-care", "false");
    await expect(pill).toHaveAttribute("data-has-next", "false");
    await expect(pill).toHaveAttribute("data-open", "false");
    await expect(pill).toHaveAttribute("data-actionable", "false");
    await expect(pill).not.toHaveAttribute("aria-keyshortcuts", /.+/);
    await expect(pill).not.toHaveAttribute("aria-controls", /.+/);
    await expect(pill).not.toHaveAttribute("aria-expanded", /.+/);
    await expect(page.locator("#pill-label")).toHaveText("KEEP");
    await expect(page.locator("#pill-peek")).toBeEmpty();

    await expect
      .poll(() => page.evaluate(() => document.activeElement?.id))
      .toBe("pill");
  });

  test("focused peek card completes CARE with Space", async ({ page }) => {
    await installFakePillBus(page);
    await page.setViewportSize({ width: 600, height: 260 });
    await page.goto("/pill.html?controls=1", { waitUntil: "domcontentloaded" });
    await waitForPillBus(page);
    await emitPillBusFrame(page, CARE_FRAME);

    const pill = page.locator("#pill");
    const card = page.locator(".pill__peek .vmx-next-card");
    await page.waitForFunction(
      () => document.querySelector<HTMLElement>("#pill")?.dataset.moveGrade === "negative",
    );

    await page.hover("#pill");
    await expect(pill).toHaveAttribute("data-peek", "true");
    await expect(card).toHaveAttribute("role", "button");
    await expect(card).toHaveAttribute("aria-keyshortcuts", "Enter Space");
    await expect(card.locator(".vmx-next-card__peek-action")).toHaveText("CARE");

    await card.focus();
    await expect
      .poll(() =>
        page.evaluate(() =>
          document.activeElement instanceof HTMLElement
            ? document.activeElement.className
            : "",
        ),
      )
      .toContain("vmx-next-card");

    await page.keyboard.press("Space");

    await expect(pill).toHaveAttribute("data-feedback", "accept");
    await expect(pill).toHaveAttribute("data-feedback-care", "true");
    await expect(pill).toHaveAttribute("data-has-next", "false");
    await expect(pill).toHaveAttribute("data-open", "false");
    await expect(pill).toHaveAttribute("data-actionable", "false");
    await expect(pill).not.toHaveAttribute("aria-keyshortcuts", /.+/);
    await expect(pill).not.toHaveAttribute("aria-controls", /.+/);
    await expect(pill).not.toHaveAttribute("aria-expanded", /.+/);
    await expect(page.locator("#pill-label")).toHaveText("CARE");
    await expect(page.locator("#pill-peek")).toBeEmpty();

    await expect
      .poll(() => page.evaluate(() => document.activeElement?.id))
      .toBe("pill");
  });

  test("focused peek card returns focus to the pill when a reaction interrupts", async ({
    page,
  }) => {
    await installFakePillBus(page);
    await page.setViewportSize({ width: 600, height: 260 });
    await page.goto("/pill.html?controls=1", { waitUntil: "domcontentloaded" });
    await waitForPillBus(page);
    await emitPillBusFrame(page, KEEP_FRAME);

    const pill = page.locator("#pill");
    const card = page.locator(".pill__peek .vmx-next-card");
    await page.waitForFunction(
      () => document.querySelector<HTMLElement>("#pill")?.dataset.moveGrade === "sexy",
    );

    await page.hover("#pill");
    await expect(pill).toHaveAttribute("data-peek", "true");
    await card.focus();
    await expect
      .poll(() =>
        page.evaluate(() =>
          document.activeElement instanceof HTMLElement
            ? document.activeElement.className
            : "",
        ),
      )
      .toContain("vmx-next-card");

    await emitPillBusFrame(page, REACTION_FRAME);

    await expect(pill).toHaveAttribute("data-state", "expand");
    await expect(pill).toHaveAttribute("data-open", "true");
    await expect(page.locator("#pill-label")).toHaveText("COHOST");
    await expect(page.locator("#pill-peek")).toBeEmpty();
    await expect
      .poll(() => page.evaluate(() => document.activeElement?.id))
      .toBe("pill");
  });

  test("focused risky DJ KNOWS completes CARE with Space", async ({ page }) => {
    await installFakePillBus(page);
    await page.setViewportSize({ width: 600, height: 260 });
    await page.goto("/pill.html?controls=1", { waitUntil: "domcontentloaded" });
    await waitForPillBus(page);
    await emitPillBusFrame(page, CARE_FRAME);

    const pill = page.locator("#pill");
    await page.waitForFunction(
      () => document.querySelector<HTMLElement>("#pill")?.dataset.moveGrade === "negative",
    );

    await pill.focus();
    await expect(pill).toHaveAttribute("data-peek", "true");
    await expect(pill).toHaveAttribute("data-intel", "care");
    await expect(pill).toHaveAttribute("data-actionable", "true");
    await expect(pill).toHaveAttribute("aria-keyshortcuts", "Enter Space");
    await expect(pill).toHaveAttribute("aria-controls", "pill-peek");
    await expect(pill).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator("#pill-label")).toHaveText("DJ KNOWS");
    await expect(page.locator(".pill__peek .vmx-next-card__peek-action")).toHaveText("CARE");

    const focusedAction = await pill.getAttribute("aria-label");
    expect(focusedAction).toContain("Strobe");
    expect(focusedAction).toContain("care: key clash");
    expect(focusedAction).toContain("activate to accept with care");

    await page.keyboard.press("Space");

    await expect(pill).toHaveAttribute("data-feedback", "accept");
    await expect(pill).toHaveAttribute("data-feedback-care", "true");
    await expect(pill).toHaveAttribute("data-has-next", "false");
    await expect(pill).toHaveAttribute("data-open", "false");
    await expect(pill).toHaveAttribute("data-actionable", "false");
    await expect(pill).not.toHaveAttribute("aria-keyshortcuts", /.+/);
    await expect(pill).not.toHaveAttribute("aria-controls", /.+/);
    await expect(pill).not.toHaveAttribute("aria-expanded", /.+/);
    await expect(page.locator("#pill-label")).toHaveText("CARE");
    await expect(page.locator("#pill-peek")).toBeEmpty();
  });

  test("Escape dismisses focused DJ KNOWS without consuming the suggestion", async ({
    page,
  }) => {
    await installFakePillBus(page);
    await page.setViewportSize({ width: 600, height: 260 });
    await page.goto("/pill.html?controls=1", { waitUntil: "domcontentloaded" });
    await waitForPillBus(page);
    await emitPillBusFrame(page, KEEP_FRAME);

    const pill = page.locator("#pill");
    await page.waitForFunction(
      () => document.querySelector<HTMLElement>("#pill")?.dataset.moveGrade === "sexy",
    );

    await pill.focus();
    await expect(pill).toHaveAttribute("data-peek", "true");
    await expect(pill).toHaveAttribute("data-actionable", "true");
    await expect(pill).toHaveAttribute("aria-controls", "pill-peek");
    await expect(pill).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator("#pill-label")).toHaveText("DJ KNOWS");

    await page.keyboard.press("Escape");

    await expect(pill).toHaveAttribute("data-peek", "false");
    await expect(pill).toHaveAttribute("data-open", "false");
    await expect(pill).toHaveAttribute("data-actionable", "false");
    await expect(pill).toHaveAttribute("data-has-next", "true");
    await expect(pill).not.toHaveAttribute("data-feedback", /.+/);
    await expect(pill).not.toHaveAttribute("aria-keyshortcuts", /.+/);
    await expect(pill).not.toHaveAttribute("aria-controls", /.+/);
    await expect(pill).not.toHaveAttribute("aria-expanded", /.+/);
    await expect(page.locator("#pill-label")).toHaveText("LISTENING");
    await expect(page.locator("#pill-peek")).toHaveAttribute("aria-hidden", "true");
    await expect(page.locator("#pill-peek")).toHaveAttribute("inert", "");
    await expect(page.locator("#pill-peek .vmx-next-card")).toHaveCount(1);
    await expect(page.locator("#pill-peek .vmx-next-card")).toHaveAttribute(
      "tabindex",
      "-1",
    );

    const dismissedLabel = await pill.getAttribute("aria-label");
    expect(dismissedLabel).toBe("vibemix cohost pill");

    await page.mouse.move(580, 240);
    await page.hover("#pill");
    await expect(pill).toHaveAttribute("data-peek", "true");
    await expect(pill).toHaveAttribute("aria-controls", "pill-peek");
    await expect(pill).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator("#pill-peek")).not.toHaveAttribute("inert", /.+/);
    await expect(page.locator("#pill-label")).toHaveText("DJ KNOWS");
    await expect(page.locator("#pill-peek .vmx-next-card")).toHaveAttribute("tabindex", "0");
    await expect(page.locator(".pill__peek .vmx-next-card__peek-action")).toHaveText("KEEP");
  });

  test("Escape from the focused peek card returns to the pill without completing", async ({
    page,
  }) => {
    await installFakePillBus(page);
    await page.setViewportSize({ width: 600, height: 260 });
    await page.goto("/pill.html?controls=1", { waitUntil: "domcontentloaded" });
    await waitForPillBus(page);
    await emitPillBusFrame(page, KEEP_FRAME);

    const pill = page.locator("#pill");
    const peekCard = page.locator("#pill-peek .vmx-next-card");
    await page.waitForFunction(
      () => document.querySelector<HTMLElement>("#pill")?.dataset.moveGrade === "sexy",
    );

    await page.hover("#pill");
    await expect(pill).toHaveAttribute("data-peek", "true");
    await expect(pill).toHaveAttribute("data-actionable", "true");
    await expect(peekCard).toHaveAttribute("tabindex", "0");

    await peekCard.focus();
    await expect(peekCard).toBeFocused();

    await page.keyboard.press("Escape");

    await expect(pill).toBeFocused();
    await expect(pill).toHaveAttribute("data-peek", "false");
    await expect(pill).toHaveAttribute("data-open", "false");
    await expect(pill).toHaveAttribute("data-actionable", "false");
    await expect(pill).toHaveAttribute("data-has-next", "true");
    await expect(pill).not.toHaveAttribute("data-feedback", /.+/);
    await expect(page.locator("#pill-label")).toHaveText("LISTENING");
    await expect(page.locator("#pill-peek")).toHaveAttribute("aria-hidden", "true");
    await expect(page.locator("#pill-peek")).toHaveAttribute("inert", "");
    await expect(peekCard).toHaveAttribute("tabindex", "-1");
  });

  test("face click completes visible DJ KNOWS without aiming at the peek card", async ({
    page,
  }) => {
    await installFakePillBus(page);
    await page.setViewportSize({ width: 600, height: 260 });
    await page.goto("/pill.html?controls=1", { waitUntil: "domcontentloaded" });
    await waitForPillBus(page);
    await emitPillBusFrame(page, KEEP_FRAME);

    const pill = page.locator("#pill");
    const label = page.locator("#pill-label");
    await page.waitForFunction(
      () => document.querySelector<HTMLElement>("#pill")?.dataset.moveGrade === "sexy",
    );

    await page.hover("#pill");
    await expect(pill).toHaveAttribute("data-peek", "true");
    await expect(pill).toHaveAttribute("data-actionable", "true");
    await expect(pill).toHaveAttribute("aria-controls", "pill-peek");
    await expect(pill).toHaveAttribute("aria-expanded", "true");
    await expect(label).toHaveText("DJ KNOWS");
    await expect(page.locator(".pill__peek .vmx-next-card__peek-action")).toHaveText("KEEP");

    const clickedZone = await page.evaluate(() => {
      const labelEl = document.querySelector<HTMLElement>("#pill-label");
      const row = labelEl?.closest(".pill__row");
      const card = document.querySelector<HTMLElement>(".pill__peek .vmx-next-card");
      if (!labelEl || !row || !card) throw new Error("face-click DOM missing");
      const labelRect = labelEl.getBoundingClientRect();
      const centerX = labelRect.left + labelRect.width / 2;
      const centerY = labelRect.top + labelRect.height / 2;
      const hit = document.elementFromPoint(centerX, centerY);
      return {
        hitLabel: hit === labelEl || Boolean(hit?.closest("#pill-label")),
        hitRow: Boolean(hit?.closest(".pill__row")),
        hitCard: Boolean(hit?.closest(".vmx-next-card")),
      };
    });
    expect(clickedZone).toEqual({
      hitLabel: true,
      hitRow: true,
      hitCard: false,
    });

    await label.click();

    await expect(pill).toHaveAttribute("data-feedback", "accept");
    await expect(pill).toHaveAttribute("data-feedback-care", "false");
    await expect(pill).toHaveAttribute("data-has-next", "false");
    await expect(pill).toHaveAttribute("data-open", "false");
    await expect(pill).toHaveAttribute("data-actionable", "false");
    await expect(pill).not.toHaveAttribute("aria-keyshortcuts", /.+/);
    await expect(pill).not.toHaveAttribute("aria-controls", /.+/);
    await expect(pill).not.toHaveAttribute("aria-expanded", /.+/);
    await expect(label).toHaveText("KEEP");
    await expect(page.locator("#pill-peek")).toBeEmpty();
  });
});

async function installFakePillBus(page: Page): Promise<void> {
  await page.addInitScript(() => {
    type FakeSocketWindow = Window & { __vmxFakeSockets?: FakeWebSocket[] };
    const sockets: FakeWebSocket[] = [];

    class FakeWebSocket {
      static readonly CONNECTING = 0;
      static readonly OPEN = 1;
      static readonly CLOSING = 2;
      static readonly CLOSED = 3;

      readonly url: string;
      readyState = FakeWebSocket.CONNECTING;
      onopen: ((ev: Event) => void) | null = null;
      onmessage: ((ev: MessageEvent<string>) => void) | null = null;
      onclose: ((ev: Event) => void) | null = null;
      onerror: ((ev: Event) => void) | null = null;

      constructor(url: string | URL) {
        this.url = String(url);
        sockets.push(this);
        (window as FakeSocketWindow).__vmxFakeSockets = sockets;
        setTimeout(() => {
          this.readyState = FakeWebSocket.OPEN;
          this.onopen?.(new Event("open"));
        }, 0);
      }

      send(): void {}

      close(): void {
        this.readyState = FakeWebSocket.CLOSED;
        this.onclose?.(new Event("close"));
      }

      emit(data: unknown): void {
        this.onmessage?.(new MessageEvent("message", { data: JSON.stringify(data) }));
      }

      addEventListener(type: string, listener: EventListener): void {
        if (type === "open") this.onopen = listener as (ev: Event) => void;
        if (type === "message") {
          this.onmessage = listener as (ev: MessageEvent<string>) => void;
        }
        if (type === "close") this.onclose = listener as (ev: Event) => void;
        if (type === "error") this.onerror = listener as (ev: Event) => void;
      }

      removeEventListener(): void {}
    }

    (window as unknown as { WebSocket: typeof FakeWebSocket }).WebSocket = FakeWebSocket;
  });
}

async function waitForPillBus(page: Page): Promise<void> {
  await page.waitForFunction(() => {
    const sockets = (window as Window & { __vmxFakeSockets?: { url: string }[] })
      .__vmxFakeSockets;
    return Array.isArray(sockets) && sockets.some((socket) => socket.url.includes("8765"));
  });
}

async function emitPillBusFrame(page: Page, frame: unknown): Promise<void> {
  await page.evaluate((nextFrame) => {
    type FakeSocket = { url: string; emit: (data: unknown) => void };
    const sockets = (window as Window & { __vmxFakeSockets?: FakeSocket[] })
      .__vmxFakeSockets;
    const socket = sockets?.find((candidate) => candidate.url.includes("8765"));
    if (!socket) throw new Error("pill bus socket missing");
    socket.emit(nextFrame);
  }, frame);
}
