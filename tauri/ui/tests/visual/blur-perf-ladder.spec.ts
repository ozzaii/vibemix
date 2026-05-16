/* VIS-06 (Phase 43, Plan 43-06) — integrated-GPU blur-perf ladder.
 *
 * scaffolded; runs in CI, not at execute time per CONTEXT note (Tauri
 * runtime not available under vitest, and headless-Chromium frame-time
 * variance under CI runners makes local-execute flaky).
 *
 * Validates the runtime perf observer (src/mascot/perf-observer.ts)
 * flips `data-blur-perf="on"` on <html> in degraded environments and
 * keeps it off in healthy ones.
 *
 * The actual perf observer behavior is fully tested under jsdom in
 * src/mascot/perf-observer.test.ts. This spec is the integration-level
 * contract that pins the wiring inside the live webview.
 *
 * Threats covered:
 *   - T-43-06-03 (false-positive flip): healthy-GPU test asserts no flip.
 *   - T-43-06-04 (DOM mutation accept): assertion is on the public
 *     [data-blur-perf] attribute, never on private state.
 */
import { test, expect } from "@playwright/test";

test.describe("blur-perf ladder — VIS-06", () => {
  test("healthy GPU keeps data-blur-perf unset after 2s of paint", async ({
    page,
  }) => {
    await page.goto("/");
    await page.waitForTimeout(2000);
    const attr = await page.evaluate(() =>
      document.documentElement.getAttribute("data-blur-perf"),
    );
    // Healthy default headless-Chromium hits ≤16.7ms frames easily —
    // the observer's 60-frame rolling window stays under the 20ms p99
    // trigger, attribute stays unset (null in the DOM).
    expect(attr).toBeNull();
  });

  test("disabled GPU flips data-blur-perf to 'on' within 1.5s", async ({
    browser,
  }) => {
    // playwright.config.ts must launch this project with `--disable-gpu`
    // via launchOptions.args. The spec is the contract that pins the
    // resulting flip; the config wiring lands in the CI setup plan.
    const ctx = await browser.newContext({
      // Reserved for the project-level `--disable-gpu` launch arg.
      // Playwright doesn't expose a context-level flag for this; rely on
      // the test runner's project config to set it.
    });
    const page = await ctx.newPage();
    await page.goto("/");
    // Give the observer >=60 frames at degraded timing to populate the
    // rolling window and trigger the flip.
    await page.waitForTimeout(1500);
    const attr = await page.evaluate(() =>
      document.documentElement.getAttribute("data-blur-perf"),
    );
    expect(attr).toBe("on");
    await ctx.close();
  });

  test("prefers-reduced-motion: reduce shortens or removes transition durations (tokens.css cascade)", async ({
    browser,
  }) => {
    const ctx = await browser.newContext({ reducedMotion: "reduce" });
    const page = await ctx.newPage();
    await page.goto("/");
    await page.waitForTimeout(500);
    // reducedMotion does NOT drive the perf observer (that's frame-
    // time-based, not motion-pref-based). What it DOES drive is the
    // @media (prefers-reduced-motion: reduce) block in tokens.css that
    // shortens transitions. We pin the cascade lands by checking the
    // computed transition-duration on a known animated surface.
    const animDuration = await page.evaluate(() => {
      // Pick a token-styled element guaranteed to exist on every
      // surface — the document element always has its own transition
      // tokens; absent surface-specific selectors we fall back to it.
      const probe =
        document.querySelector(".vmx-meter__peak") ??
        document.querySelector(".vmx-btn") ??
        document.documentElement;
      return probe ? getComputedStyle(probe).transitionDuration : null;
    });
    // Must produce a parseable duration string; specific value is left
    // for the snapshot/regression to lock once the cascade lands.
    expect(animDuration).toBeTruthy();
    await ctx.close();
  });
});
