/* grounding-failure.spec.ts — impeccable Wave 6 (closes H9 "error
 * recovery").
 *
 * Pins:
 *   - Default render shows "TUNING IN" when grounded=false, no retry.
 *   - After GROUNDING_FAILURE_MS elapse (failureElapsedMs >= 5000), the
 *     foot swaps to "AI SERVICE OFFLINE" + retry button.
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
  it("grounded=false + elapsed < 5s → shows TUNING IN, no retry", () => {
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
    expect(foot?.textContent).toContain("TUNING IN");
    expect(panel.querySelector(".vmx-cohost__foot-retry")).toBeNull();
  });

  it("grounded=false + elapsed >= 5s → shows AI SERVICE OFFLINE + retry", () => {
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
    expect(foot?.textContent).toContain("AI SERVICE OFFLINE");
    const retry = panel.querySelector<HTMLElement>(".vmx-cohost__foot-retry");
    expect(retry).toBeTruthy();
    // 2026-05-26 /impeccable critique P3: label tells the truth — the
    // button restarts the co-host (restart_sidecar), it isn't a
    // lightweight reconnect.
    expect(retry?.textContent).toContain("RESTART COHOST");
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
    expect(foot?.textContent).toContain("READING THE ROOM");
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

describe("SessionLayout grounding-failure → fault state (H9)", () => {
  // "The Deck Speaks" rebuild (2026-05-26): a sustained ungrounded co-host
  // surfaces as the deck's `data-mode="fault"` state (the fault liveness
  // label names the cause), replacing the old cohost-panel foot copy.
  it("does not show the fault state immediately on boot with grounded=false", () => {
    const root = host();
    // grounded is already false in defaultState — the timer starts now, but
    // <5s + cohost IDLE reads as calm 'silent', not 'fault'.
    mountSessionLayout(root, defaultState());
    expect(root.querySelector<HTMLElement>(".vmx-session")?.dataset.mode).toBe(
      "silent",
    );
  });

  it("after >= 5s of grounded=false on an ACTIVE co-host the deck flips to fault", () => {
    vi.useFakeTimers();
    const t0 = 1_000_000_000;
    vi.setSystemTime(t0);

    const root = host();
    // 2026-05-26 (c6b8b814): the grounding-failure timer only runs while the
    // co-host is ACTIVE. At IDLE, grounded=false is expected (no music to
    // ground to) — so an active+ungrounded state is what surfaces a real
    // fault. defaultState boots IDLE; promote it to LISTENING here.
    const active = defaultState();
    active.cohost = { ...active.cohost, status: "LISTENING", grounded: false };
    const mounted = mountSessionLayout(root, active);
    // groundedFalseSinceMs initialized to t0 on mount (active + ungrounded).
    expect(mounted.groundedFalseSinceMs).toBe(t0);

    // Advance past the threshold and run a render frame.
    vi.setSystemTime(t0 + GROUNDING_FAILURE_MS + 500);
    renderSessionFrame(mounted, active);

    const session = root.querySelector<HTMLElement>(".vmx-session");
    expect(session?.dataset.mode).toBe("fault");
    // The fault liveness label names the grounding cause.
    const fault = root.querySelector<HTMLElement>(".vmx-live__s--fault");
    expect(fault?.textContent).toContain("ai service");
  });

  it("an IDLE co-host never faults on grounded=false (empty-screen regression guard)", () => {
    // The recurring "empty screen / AI SERVICE OFFLINE / always broken" bug:
    // a quiet idle session (no music) is ungrounded forever, and the old timer
    // flipped it to fault after 5s → blank hero. The fix: idle never faults.
    vi.useFakeTimers();
    const t0 = 1_000_000_000;
    vi.setSystemTime(t0);

    const root = host();
    const mounted = mountSessionLayout(root, defaultState()); // status IDLE
    // Long past the threshold — still must read as calm 'silent', never fault.
    vi.setSystemTime(t0 + GROUNDING_FAILURE_MS * 10);
    renderSessionFrame(mounted, defaultState());

    expect(mounted.groundedFalseSinceMs).toBeNull();
    expect(
      root.querySelector<HTMLElement>(".vmx-session")?.dataset.mode,
    ).toBe("silent");
  });

  it("screen=denied lights the badge but never faults the deck (audio-only is valid)", () => {
    // 2026-05-26: with the new ~1Hz ipc.status.tick emitting a live screen
    // probe, a user who denied screen recording would have flipped the whole
    // deck to fault. Audio-only is a valid mode — screen=denied is badge-only.
    const root = host();
    const s = defaultState();
    // Active + grounded so the grounding timer can't fault; only screen denied.
    s.cohost = { ...s.cohost, status: "LISTENING", grounded: true };
    s.status = { ...s.status, screen: "denied", livekit: "ok", gemini: "ok" };
    const mounted = mountSessionLayout(root, s);
    renderSessionFrame(mounted, s);

    // Deck stays live (NOT fault).
    expect(
      root.querySelector<HTMLElement>(".vmx-session")?.dataset.mode,
    ).not.toBe("fault");
    // But the SCREEN status badge still reads down (honest degraded input).
    const screenInput = root.querySelector<HTMLElement>(
      '.vmx-statusrow__i[data-input="screen"]',
    );
    expect(screenInput?.dataset.down).toBe("true");
  });

  it("screen=unavailable is neutral and never faults the deck", () => {
    const root = host();
    const s = defaultState();
    s.cohost = { ...s.cohost, status: "LISTENING", grounded: true };
    s.status = { ...s.status, screen: "unavailable", livekit: "ok", gemini: "ok" };
    const mounted = mountSessionLayout(root, s);
    renderSessionFrame(mounted, s);

    expect(
      root.querySelector<HTMLElement>(".vmx-session")?.dataset.mode,
    ).not.toBe("fault");
    const screenInput = root.querySelector<HTMLElement>(
      '.vmx-statusrow__i[data-input="screen"]',
    );
    expect(screenInput?.dataset.down).toBe("false");
  });

  it("grounded flip to true resets the timer (active co-host)", () => {
    vi.useFakeTimers();
    const t0 = 1_000_000_000;
    vi.setSystemTime(t0);

    const root = host();
    const active = defaultState();
    active.cohost = { ...active.cohost, status: "LISTENING", grounded: false };
    const mounted = mountSessionLayout(root, active);

    // Active + grounded → reset timer.
    const grounded = defaultState();
    grounded.cohost = { ...grounded.cohost, status: "LISTENING", grounded: true };
    renderSessionFrame(mounted, grounded);
    expect(mounted.groundedFalseSinceMs).toBeNull();

    // Flip back to false (still active) → timer re-arms with the current time.
    vi.setSystemTime(t0 + 10_000);
    const unground = defaultState();
    unground.cohost = { ...unground.cohost, status: "LISTENING", grounded: false };
    renderSessionFrame(mounted, unground);
    expect(mounted.groundedFalseSinceMs).toBe(t0 + 10_000);

    // Only just flipped (<5s) → not fault yet.
    expect(
      root.querySelector<HTMLElement>(".vmx-session")?.dataset.mode,
    ).not.toBe("fault");
  });
});
