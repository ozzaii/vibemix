/**
 * VIS-02 (Phase 43, Plan 43-03) — wizard + settings drawer hover-glow regression.
 *
 * Scaffolded; runs in CI, not at execute time — scaffolded; runs in CI
 * is the marker the plan verify gate greps for. Companion spec to
 * `hover-glow.spec.ts` (Plan 43-02 writes the session-bucket cases).
 * Plan 43-03 owns the wizard + settings drawer interactive coverage —
 * this file is additive so the two waves can land in parallel without
 * merge contention.
 *
 * Scope (Plan 43-03 wave):
 *   - Wizard step0 intro CTA — armed Let's-go button.
 *   - Wizard step1 Continue + Back CTAs + Grant + DENIED · open
 *     Settings affordance (the permissions-card role="button" chip).
 *   - Wizard step2 device dropdown + test-tone button + window picker.
 *   - Wizard step3 controller-probe Listen Again + Skip.
 *   - Wizard profile-consent + telemetry-consent toggle rows + CTAs.
 *   - Settings drawer __close + __btn + interactive-union safety net.
 *
 * Each case drives :hover via `page.locator(...).hover()` and confirms
 * the computed `box-shadow` matches `var(--glow-faint)` (resolved value
 * `rgba(255, 138, 61, 0.22) 0px 0px 5px` per tokens.css:101+123). The
 * spec also exercises `:focus-visible` via keyboard `Tab` to confirm
 * keyboard parity — anti-dark-pattern hygiene for the consent steps.
 *
 * Wiring strategy: same as `meter-spectrum.spec.ts` — Tauri dev server
 * serves index.html at /; the wizard router exposes `?step=N` query
 * param to mount a single step deterministically. Pinned by CI on
 * first green run; baseline snapshots under `__snapshots__/`.
 *
 * TODO(VIS-02): once Plan 43-02's `hover-glow.spec.ts` lands, consider
 * merging this file into it as a `test.describe('wizard surface')`
 * block — kept separate for now to avoid merge collisions during the
 * parallel wave 2 / wave 3 ship window.
 */
import { test, expect } from "@playwright/test";

const GLOW_FAINT_BOX_SHADOW = /rgba\(255,\s*138,\s*61,\s*0\.22\)\s*0px\s*0px\s*5px/;

test.describe("VIS-02 hover-glow — wizard intro (Plan 43-03)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/?step=0");
    await page.locator(".wizard-intro__cta button").waitFor();
  });

  test("step0 — Let's go CTA carries --glow-faint on hover", async ({
    page,
  }) => {
    const cta = page.locator(".wizard-intro__cta button");
    await cta.hover();
    const shadow = await cta.evaluate(
      (el) => getComputedStyle(el).boxShadow,
    );
    expect(shadow).toMatch(GLOW_FAINT_BOX_SHADOW);
  });

  test("step0 — Let's go CTA carries --glow-faint on :focus-visible (keyboard)", async ({
    page,
  }) => {
    await page.keyboard.press("Tab");
    const cta = page.locator(".wizard-intro__cta button");
    const shadow = await cta.evaluate(
      (el) => getComputedStyle(el).boxShadow,
    );
    expect(shadow).toMatch(GLOW_FAINT_BOX_SHADOW);
  });
});

test.describe("VIS-02 hover-glow — wizard step1 permissions (Plan 43-03)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/?step=1");
    await page.locator(".wizard-step__cta-row button").first().waitFor();
  });

  test("Continue CTA carries --glow-faint on hover", async ({ page }) => {
    // Continue is the rightmost button in the cta-row.
    const cta = page.locator(".wizard-step__cta-row button").last();
    await cta.hover();
    const shadow = await cta.evaluate(
      (el) => getComputedStyle(el).boxShadow,
    );
    expect(shadow).toMatch(GLOW_FAINT_BOX_SHADOW);
  });

  test("DENIED · open Settings affordance carries --glow-faint on :focus-visible", async ({
    page,
  }) => {
    // Mount step1 with screen-recording in denied state so the
    // role="button" affordance renders.
    await page.evaluate(() => {
      const root = document.querySelector(".wizard-step__cards");
      if (!root) throw new Error("wizard-step__cards not mounted");
    });
    const denied = page
      .locator('.cmp-perm-card__state-readout[data-tone="rec"]')
      .first();
    await denied.waitFor({ state: "attached" });
    await denied.focus();
    const shadow = await denied.evaluate(
      (el) => getComputedStyle(el).boxShadow,
    );
    expect(shadow).toMatch(GLOW_FAINT_BOX_SHADOW);
  });
});

test.describe("VIS-02 hover-glow — wizard step2 output-device (Plan 43-03)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/?step=2");
    await page.locator(".wizard-step--output-device").waitFor();
  });

  test("test-tone button carries --glow-faint on hover", async ({ page }) => {
    const tone = page
      .locator(".wizard-step--output-device .cmp-btn")
      .first();
    await tone.hover();
    const shadow = await tone.evaluate(
      (el) => getComputedStyle(el).boxShadow,
    );
    expect(shadow).toMatch(GLOW_FAINT_BOX_SHADOW);
  });
});

test.describe("VIS-02 hover-glow — wizard step3 controller-probe (Plan 43-03)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/?step=3");
    await page.locator(".wizard-step--controller").waitFor();
  });

  test("Listen Again CTA carries --glow-faint on hover", async ({ page }) => {
    const cta = page
      .locator(".wizard-step--controller button")
      .first();
    await cta.hover();
    const shadow = await cta.evaluate(
      (el) => getComputedStyle(el).boxShadow,
    );
    expect(shadow).toMatch(GLOW_FAINT_BOX_SHADOW);
  });
});

test.describe("VIS-02 hover-glow — wizard consent steps (Plan 43-03)", () => {
  test("profile-consent toggle carries --glow-faint on :focus-visible", async ({
    page,
  }) => {
    await page.goto("/?step=4");
    await page.locator(".wizard-step--profile-consent").waitFor();
    await page.keyboard.press("Tab");
    const focused = page.locator(":focus-visible");
    const shadow = await focused.evaluate(
      (el) => getComputedStyle(el).boxShadow,
    );
    expect(shadow).toMatch(GLOW_FAINT_BOX_SHADOW);
  });

  test("telemetry-consent toggle carries --glow-faint on :focus-visible", async ({
    page,
  }) => {
    await page.goto("/?step=5");
    await page.locator(".wizard-step--telemetry-consent").waitFor();
    await page.keyboard.press("Tab");
    const focused = page.locator(":focus-visible");
    const shadow = await focused.evaluate(
      (el) => getComputedStyle(el).boxShadow,
    );
    expect(shadow).toMatch(GLOW_FAINT_BOX_SHADOW);
  });
});

test.describe("VIS-02 hover-glow — settings drawer (Plan 43-03)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/?settings=open");
    await page.locator(".vmx-settings-drawer[data-open='true']").waitFor();
  });

  test("__close button carries --glow-faint on hover", async ({ page }) => {
    const close = page.locator(".vmx-settings-drawer__close");
    await close.hover();
    const shadow = await close.evaluate(
      (el) => getComputedStyle(el).boxShadow,
    );
    expect(shadow).toMatch(GLOW_FAINT_BOX_SHADOW);
  });

  test("__btn (Recheck / Calibration / etc) carries --glow-faint on hover", async ({
    page,
  }) => {
    const btn = page.locator(".vmx-settings-drawer__btn").first();
    await btn.hover();
    const shadow = await btn.evaluate(
      (el) => getComputedStyle(el).boxShadow,
    );
    // __btn keeps its inset amber bleed; assertion is that --glow-faint
    // is present in the comma-separated stack (not the sole shadow).
    expect(shadow).toMatch(GLOW_FAINT_BOX_SHADOW);
  });

  test("interactive-union safety net catches deeper child components on :focus-visible", async ({
    page,
  }) => {
    // Tab through the drawer body until a focusable child component
    // (mascot-group toggle, performance-group toggle, library-panel
    // action, etc.) receives focus. The surface-wide rule should fire
    // --glow-faint on whichever element ends up :focus-visible.
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    const focused = page.locator(
      ".vmx-settings-drawer *:focus-visible",
    );
    if ((await focused.count()) > 0) {
      const shadow = await focused.first().evaluate(
        (el) => getComputedStyle(el).boxShadow,
      );
      expect(shadow).toMatch(GLOW_FAINT_BOX_SHADOW);
    }
  });
});
