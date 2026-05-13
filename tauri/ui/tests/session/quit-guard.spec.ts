/* quit-guard.spec.ts — impeccable Wave 6 (closes H5 "error prevention").
 *
 * Pins:
 *   - confirmQuitDuringRecording() mounts the styled dialog with the
 *     STILL LIVE copy and the expected button labels.
 *   - Clicking STAY resolves the promise with false (don't quit).
 *   - Clicking QUIT ANYWAY resolves with true (close).
 *   - isRecording() reads the SessionState.status.livekit flag.
 *   - The dialog uses the danger variant (red-tinted destructive button).
 *
 * The beforeunload listener itself is harder to assert directly — vitest's
 * jsdom doesn't dispatch beforeunload through a real page-close event, but
 * we verify the listener installer is wired by checking it sets returnValue
 * when invoked with a synthetic event. */

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  confirmQuitDuringRecording,
  installQuitGuard,
  isRecording,
} from "../../src/session/quit-guard.js";
import {
  _resetSessionStateForTests,
  setSessionState,
} from "../../src/session/state.js";

beforeEach(() => {
  _resetSessionStateForTests();
  document.body.replaceChildren();
});

afterEach(() => {
  _resetSessionStateForTests();
  document.body.replaceChildren();
});

describe("isRecording", () => {
  it("returns false when livekit is null", () => {
    expect(isRecording()).toBe(false);
  });

  it("returns true when livekit === 'ok'", () => {
    setSessionState({
      status: {
        livekit: "ok",
        gemini: "ok",
        midi: 1,
        screen: "ok",
      },
    });
    expect(isRecording()).toBe(true);
  });

  it("returns false when livekit === 'down'", () => {
    setSessionState({
      status: {
        livekit: "down",
        gemini: "ok",
        midi: 1,
        screen: "ok",
      },
    });
    expect(isRecording()).toBe(false);
  });
});

describe("confirmQuitDuringRecording", () => {
  it("mounts a dialog with the STILL LIVE heading + STAY + QUIT ANYWAY buttons", () => {
    void confirmQuitDuringRecording();
    const dialog = document.querySelector<HTMLElement>(".vmx-confirm__dialog");
    expect(dialog).toBeTruthy();
    expect(dialog?.dataset.variant).toBe("danger");
    expect(document.querySelector(".vmx-confirm__heading")?.textContent).toBe(
      "STILL LIVE",
    );
    expect(document.querySelector(".vmx-confirm__body")?.textContent).toBe(
      "your set is recording. quit anyway?",
    );
    const buttons = Array.from(
      document.querySelectorAll<HTMLButtonElement>(".vmx-confirm__btn"),
    );
    expect(buttons.map((b) => b.textContent)).toEqual([
      "STAY",
      "QUIT ANYWAY",
    ]);
  });

  it("clicking STAY resolves false + removes the dialog", async () => {
    const p = confirmQuitDuringRecording();
    const cancel = document.querySelector<HTMLButtonElement>(
      '.vmx-confirm__btn[data-kind="cancel"]',
    );
    expect(cancel).toBeTruthy();
    cancel!.click();
    const result = await p;
    expect(result).toBe(false);
    expect(document.querySelector(".vmx-confirm__dialog")).toBeNull();
  });

  it("clicking QUIT ANYWAY resolves true + removes the dialog", async () => {
    const p = confirmQuitDuringRecording();
    const confirm = document.querySelector<HTMLButtonElement>(
      '.vmx-confirm__btn[data-kind="confirm"]',
    );
    expect(confirm).toBeTruthy();
    confirm!.click();
    const result = await p;
    expect(result).toBe(true);
    expect(document.querySelector(".vmx-confirm__dialog")).toBeNull();
  });
});

describe("installQuitGuard beforeunload listener", () => {
  it("sets returnValue when isRecording=true so the browser shows native confirm", () => {
    setSessionState({
      status: {
        livekit: "ok",
        gemini: "ok",
        midi: 1,
        screen: "ok",
      },
    });
    const unregister = installQuitGuard();
    const event = new Event("beforeunload", { cancelable: true });
    // jsdom doesn't populate `returnValue` on plain Events; we tag it
    // post-construction so the listener has a property to set.
    Object.defineProperty(event, "returnValue", {
      value: "",
      writable: true,
    });
    window.dispatchEvent(event);
    expect((event as BeforeUnloadEvent).returnValue).toBe(
      "your set is recording. quit anyway?",
    );
    unregister();
  });

  it("is a no-op when isRecording=false", () => {
    // Default state: livekit=null → isRecording=false
    const unregister = installQuitGuard();
    const event = new Event("beforeunload", { cancelable: true });
    Object.defineProperty(event, "returnValue", {
      value: "",
      writable: true,
    });
    window.dispatchEvent(event);
    expect((event as BeforeUnloadEvent).returnValue).toBe("");
    unregister();
  });

  it("unregister fn removes the listener", () => {
    setSessionState({
      status: {
        livekit: "ok",
        gemini: "ok",
        midi: 1,
        screen: "ok",
      },
    });
    const unregister = installQuitGuard();
    unregister();
    // After unregister, dispatching again should not set returnValue.
    const event = new Event("beforeunload", { cancelable: true });
    Object.defineProperty(event, "returnValue", {
      value: "",
      writable: true,
    });
    window.dispatchEvent(event);
    expect((event as BeforeUnloadEvent).returnValue).toBe("");
  });
});
