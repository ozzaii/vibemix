/* grounding-failure.spec.ts — impeccable Wave 6 (closes H9 "error
 * recovery").
 *
 * Pins:
 *   - Default render shows "WARMING UP" when grounded=false, no retry.
 *   - After GROUNDING_FAILURE_MS elapse (failureElapsedMs >= 5000), the
 *     foot swaps to "COULDN'T REACH GEMINI" + retry button.
 *   - Grounded=true clears the failure state regardless of elapsed.
 *   - Clicking retry invokes the onRetry handler.
 *   - SessionLayout's diff path crosses the 5s threshold automatically. */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  GROUNDING_FAILURE_MS,
  renderCohostPanel,
  setCohost,
} from "../../src/session/components/cohost.js";
import {
  defaultState,
  mountSessionLayout,
  renderSessionFrame,
} from "../../src/session/SessionLayout.js";

function host(): HTMLElement {
  const div = document.createElement("div");
  document.body.append(div);
  return div;
}

beforeEach(() => {
  vi.useRealTimers();
});

afterEach(() => {
  document.body.replaceChildren();
  vi.useRealTimers();
});

describe("Cohost grounding-failure recovery (H9)", () => {
  it("grounded=false + elapsed < 5s → shows WARMING UP, no retry", () => {
    const panel = renderCohostPanel({
      status: "IDLE",
      transcript: [],
      latencyMs: null,
      grounded: false,
      failureElapsedMs: 1000,
    });
    host().append(panel);
    const foot = panel.querySelector<HTMLElement>(".vmx-cohost__foot");
    expect(foot?.dataset.failed).toBe("false");
    expect(foot?.textContent).toContain("WARMING UP");
    expect(panel.querySelector(".vmx-cohost__foot-retry")).toBeNull();
  });

  it("grounded=false + elapsed >= 5s → shows COULDN'T REACH GEMINI + retry", () => {
    const panel = renderCohostPanel({
      status: "IDLE",
      transcript: [],
      latencyMs: null,
      grounded: false,
      failureElapsedMs: GROUNDING_FAILURE_MS,
      onRetry: () => {},
    });
    host().append(panel);
    const foot = panel.querySelector<HTMLElement>(".vmx-cohost__foot");
    expect(foot?.dataset.failed).toBe("true");
    expect(foot?.textContent).toContain("COULDN'T REACH GEMINI");
    const retry = panel.querySelector<HTMLElement>(".vmx-cohost__foot-retry");
    expect(retry).toBeTruthy();
    expect(retry?.textContent).toContain("RETRY");
  });

  it("grounded=true clears the failure state regardless of elapsed", () => {
    const panel = renderCohostPanel({
      status: "LISTENING",
      transcript: [],
      latencyMs: null,
      grounded: true,
      failureElapsedMs: 99999,
    });
    host().append(panel);
    const foot = panel.querySelector<HTMLElement>(".vmx-cohost__foot");
    expect(foot?.dataset.grounded).toBe("true");
    expect(foot?.dataset.failed).toBe("false");
    expect(foot?.textContent).toContain("GROUNDED");
    expect(panel.querySelector(".vmx-cohost__foot-retry")).toBeNull();
  });

  it("retry button invokes onRetry on click", () => {
    let fired = 0;
    const panel = renderCohostPanel({
      status: "IDLE",
      transcript: [],
      latencyMs: null,
      grounded: false,
      failureElapsedMs: GROUNDING_FAILURE_MS,
      onRetry: () => fired++,
    });
    host().append(panel);
    const retry = panel.querySelector<HTMLButtonElement>(
      ".vmx-cohost__foot-retry",
    );
    expect(retry).toBeTruthy();
    retry!.click();
    expect(fired).toBe(1);
  });

  it("setCohost mounts the retry button when crossing the 5s threshold", () => {
    const panel = renderCohostPanel({
      status: "IDLE",
      transcript: [],
      latencyMs: null,
      grounded: false,
      failureElapsedMs: 2000,
    });
    host().append(panel);
    expect(panel.querySelector(".vmx-cohost__foot-retry")).toBeNull();

    setCohost(panel, {
      status: "IDLE",
      transcript: [],
      latencyMs: null,
      grounded: false,
      failureElapsedMs: GROUNDING_FAILURE_MS + 100,
      onRetry: () => {},
    });
    expect(panel.querySelector(".vmx-cohost__foot-retry")).toBeTruthy();
    expect(
      panel.querySelector<HTMLElement>(".vmx-cohost__foot")?.dataset.failed,
    ).toBe("true");
  });

  it("setCohost unmounts the retry on grounded flip to true", () => {
    const panel = renderCohostPanel({
      status: "IDLE",
      transcript: [],
      latencyMs: null,
      grounded: false,
      failureElapsedMs: GROUNDING_FAILURE_MS + 500,
      onRetry: () => {},
    });
    host().append(panel);
    expect(panel.querySelector(".vmx-cohost__foot-retry")).toBeTruthy();

    setCohost(panel, {
      status: "LISTENING",
      transcript: [],
      latencyMs: null,
      grounded: true,
      failureElapsedMs: null,
    });
    expect(panel.querySelector(".vmx-cohost__foot-retry")).toBeNull();
    expect(
      panel.querySelector<HTMLElement>(".vmx-cohost__foot")?.dataset.failed,
    ).toBe("false");
  });
});

describe("SessionLayout grounding-failure timer (H9)", () => {
  it("foot does not show failure copy immediately on boot with grounded=false", () => {
    const root = host();
    const initial = defaultState();
    // grounded is already false in defaultState — the timer starts now.
    mountSessionLayout(root, initial);
    const foot = root.querySelector<HTMLElement>(".vmx-cohost__foot");
    expect(foot?.dataset.failed).toBe("false");
    expect(foot?.textContent).toContain("WARMING UP");
  });

  it("after >= 5s of grounded=false the foot flips to failure copy", () => {
    vi.useFakeTimers();
    const t0 = 1_000_000_000;
    vi.setSystemTime(t0);

    const root = host();
    const initial = defaultState();
    const mounted = mountSessionLayout(root, initial);
    // groundedFalseSinceMs initialized to t0 on mount.
    expect(mounted.groundedFalseSinceMs).toBe(t0);

    // Advance past the threshold and run a render frame.
    vi.setSystemTime(t0 + GROUNDING_FAILURE_MS + 500);
    renderSessionFrame(mounted, defaultState());

    const foot = root.querySelector<HTMLElement>(".vmx-cohost__foot");
    expect(foot?.dataset.failed).toBe("true");
    expect(foot?.textContent).toContain("COULDN'T REACH GEMINI");
    expect(root.querySelector(".vmx-cohost__foot-retry")).toBeTruthy();
  });

  it("grounded flip to true resets the timer", () => {
    vi.useFakeTimers();
    const t0 = 1_000_000_000;
    vi.setSystemTime(t0);

    const root = host();
    const initial = defaultState();
    const mounted = mountSessionLayout(root, initial);

    // Boot grounded → reset timer.
    const grounded = defaultState();
    grounded.cohost = { ...grounded.cohost, grounded: true };
    renderSessionFrame(mounted, grounded);
    expect(mounted.groundedFalseSinceMs).toBeNull();

    // Flip back to false → timer re-arms with the current system time.
    vi.setSystemTime(t0 + 10_000);
    const unground = defaultState();
    unground.cohost = { ...unground.cohost, grounded: false };
    renderSessionFrame(mounted, unground);
    expect(mounted.groundedFalseSinceMs).toBe(t0 + 10_000);

    // Foot is still WARMING UP at this point — only just flipped.
    const foot = root.querySelector<HTMLElement>(".vmx-cohost__foot");
    expect(foot?.dataset.failed).toBe("false");
  });
});
