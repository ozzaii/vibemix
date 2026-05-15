/* Phase 33 / Plan 33-06 — TCC revoke mid-session graceful degrade.
 *
 * Pins the P71 contract:
 *   - granted → denied transition fires a single runtime.permission_lost
 *     event with permission name + new state.
 *   - The handler pauses audio, shows the localized toast, and renders
 *     the re-grant button.
 *   - A listener that throws does NOT crash the watcher (graceful).
 *   - A listener that throws inside the handler does NOT prevent the
 *     other hooks from firing.
 */

import { afterEach, describe, expect, it, vi } from "vitest";

import { TccWatcher } from "../tcc-watcher.js";
import { handlePermissionLost } from "../permission-lost-handler.js";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("TccWatcher", () => {
  it("test_tcc_revoke_event_triggers_pause", () => {
    const watcher = new TccWatcher({ microphone: "granted" });
    const events: string[] = [];
    watcher.subscribe((e) => events.push(`${e.permission}:${e.newState}`));
    const fired = watcher.observe("microphone", "denied", () => 1_700_000_000_000);
    expect(fired).not.toBeNull();
    expect(fired!.type).toBe("runtime.permission_lost");
    expect(fired!.permission).toBe("microphone");
    expect(fired!.newState).toBe("denied");
    expect(fired!.observedAtMs).toBe(1_700_000_000_000);
    expect(events).toEqual(["microphone:denied"]);
  });

  it("does not fire on initial not_determined → granted transition", () => {
    const watcher = new TccWatcher();
    const events: unknown[] = [];
    watcher.subscribe((e) => events.push(e));
    expect(watcher.observe("microphone", "granted")).toBeNull();
    expect(events).toEqual([]);
  });

  it("test_tcc_revoke_does_not_crash_session — buggy listener is isolated", () => {
    const watcher = new TccWatcher({ microphone: "granted" });
    const goodEvents: unknown[] = [];
    vi.spyOn(console, "error").mockImplementation(() => {});
    watcher.subscribe(() => {
      throw new Error("listener boom");
    });
    watcher.subscribe((e) => goodEvents.push(e));
    expect(() => watcher.observe("microphone", "denied")).not.toThrow();
    expect(goodEvents).toHaveLength(1);
  });
});

describe("handlePermissionLost", () => {
  it("test_tcc_revoke_renders_toast_and_re_grant_button", () => {
    const watcher = new TccWatcher({ microphone: "granted" });
    let pauseCalls = 0;
    let toastCopy = "";
    let reGrantFor: string | null = null;
    watcher.subscribe((event) => {
      handlePermissionLost(event, {
        pauseAudioCapture: () => pauseCalls++,
        showToast: (copy) => {
          toastCopy = copy;
        },
        renderReGrantButton: (perm) => {
          reGrantFor = perm;
        },
      });
    });
    watcher.observe("microphone", "denied");
    expect(pauseCalls).toBe(1);
    expect(toastCopy).toBe("Microphone access lost — paused");
    expect(reGrantFor).toBe("microphone");
  });

  it("one failing hook does not block the other hooks", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const watcher = new TccWatcher({ "screen-recording": "granted" });
    let toastCalled = false;
    let reGrantCalled = false;
    watcher.subscribe((event) => {
      const result = handlePermissionLost(event, {
        pauseAudioCapture: () => {
          throw new Error("pause boom");
        },
        showToast: () => {
          toastCalled = true;
        },
        renderReGrantButton: () => {
          reGrantCalled = true;
        },
      });
      expect(result.paused).toBe(false);
      expect(result.toastShown).toBe(true);
      expect(result.reGrantRendered).toBe(true);
    });
    watcher.observe("screen-recording", "denied");
    expect(toastCalled).toBe(true);
    expect(reGrantCalled).toBe(true);
  });
});
