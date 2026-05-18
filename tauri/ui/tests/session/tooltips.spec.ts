/* tooltips.spec.ts — impeccable Wave 6 (closes H6 "recognition over
 * recall").
 *
 * Pins:
 *   - Titlebar LIVE pill has both aria-label + title attributes that
 *     narrate the pill state.
 *   - Settings gear has aria-label + title with shortcut hint.
 *   - Status-bar badges (livekit/gemini/midi/screen) each have a title
 *     attribute describing their state.
 *   - Cohost status row has title + aria-label per state.
 *   - Cohost foot has title narrating grounded / warming / failed.
 *   - First-session hint chip mounts when localStorage flag is unset
 *     and dismisses after the auto-dismiss timeout.
 *   - Hint chip dismisses on `?` keypress.
 *   - Hint chip stays dismissed across remounts (localStorage flag set). */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { renderCohostPanel } from "../../src/session/components/cohost.js";
import { renderStatusBar } from "../../src/session/components/status-bar.js";
import {
  renderTitlebar,
  SHORTCUTS_HINT_STORAGE_KEY,
  SHORTCUTS_HINT_TIMEOUT_MS,
} from "../../src/session/components/titlebar.js";

function host(): HTMLElement {
  const div = document.createElement("div");
  document.body.append(div);
  return div;
}

beforeEach(() => {
  try {
    window.localStorage.removeItem(SHORTCUTS_HINT_STORAGE_KEY);
  } catch {
    /* swallow */
  }
});

afterEach(() => {
  document.body.replaceChildren();
  try {
    window.localStorage.removeItem(SHORTCUTS_HINT_STORAGE_KEY);
  } catch {
    /* swallow */
  }
  vi.useRealTimers();
});

describe("Titlebar tooltips (H6)", () => {
  it("LIVE pill has title + aria-label narrating its state", () => {
    const tb = renderTitlebar({
      live: "ok",
      rec: "ok",
      sys: "ok",
      clock: "00:00:00",
    });
    host().append(tb);
    const pill = tb.querySelector<HTMLElement>(
      '.vmx-titlebar__pill[data-key="live"]',
    );
    expect(pill?.getAttribute("title")).toContain("LIVE");
    expect(pill?.getAttribute("title")).toContain("listening");
    expect(pill?.getAttribute("aria-label")).toBe(pill?.getAttribute("title"));
  });

  it("settings gear has title with shortcut hint + aria-label", () => {
    const tb = renderTitlebar({
      live: "ok",
      rec: "ok",
      sys: "ok",
      clock: "00:00:00",
    });
    host().append(tb);
    const gear = tb.querySelector<HTMLElement>(".vmx-titlebar__settings");
    expect(gear?.getAttribute("aria-label")).toBe("SETTINGS");
    const title = gear?.getAttribute("title") ?? "";
    expect(title).toContain("Settings");
    // Either ⌘, (mac) or Ctrl+, (else). Both contain a comma.
    expect(title).toContain(",");
  });
});

describe("Status bar tooltips (H6)", () => {
  it("each badge has a title attribute describing its state", () => {
    const sb = renderStatusBar({
      livekit: "ok",
      gemini: "down",
      midi: 1,
      screen: "denied",
      muted: false,
      hotkey: "⌘⇧M",
    });
    host().append(sb);
    const live = sb.querySelector<HTMLElement>(
      '.vmx-statusbar__badge[data-key="livekit"]',
    );
    const gemini = sb.querySelector<HTMLElement>(
      '.vmx-statusbar__badge[data-key="gemini"]',
    );
    const midi = sb.querySelector<HTMLElement>(
      '.vmx-statusbar__badge[data-key="midi"]',
    );
    const screen = sb.querySelector<HTMLElement>(
      '.vmx-statusbar__badge[data-key="screen"]',
    );
    expect(live?.getAttribute("title")).toContain("LiveKit");
    expect(live?.getAttribute("title")).toContain("connected");
    expect(gemini?.getAttribute("title")).toContain("Gemini");
    expect(gemini?.getAttribute("title")).toContain("disconnected");
    expect(midi?.getAttribute("title")).toContain("MIDI");
    expect(screen?.getAttribute("title")).toContain("Screen capture");
    expect(screen?.getAttribute("title")).toContain("denied");
  });
});

describe("Cohost tooltips (H6)", () => {
  it("status row has title + aria-label per state", () => {
    const panel = renderCohostPanel({
      status: "TALKING",
      transcript: [],
      latencyMs: null,
      grounded: true,
    });
    host().append(panel);
    const status = panel.querySelector<HTMLElement>(".vmx-cohost__status");
    expect(status?.getAttribute("title")).toContain("talking");
    expect(status?.getAttribute("aria-label")).toBe(
      status?.getAttribute("title"),
    );
  });

  it("foot has title narrating grounded state", () => {
    const grounded = renderCohostPanel({
      status: "LISTENING",
      transcript: [],
      latencyMs: null,
      grounded: true,
    });
    host().append(grounded);
    const foot = grounded.querySelector<HTMLElement>(".vmx-cohost__foot");
    expect(foot?.getAttribute("title")).toContain("grounded");
    expect(foot?.getAttribute("title")).toContain("audio");
  });

  it("foot has title narrating warming-up state", () => {
    const warming = renderCohostPanel({
      status: "IDLE",
      transcript: [],
      latencyMs: null,
      grounded: false,
    });
    host().append(warming);
    const foot = warming.querySelector<HTMLElement>(".vmx-cohost__foot");
    expect(foot?.getAttribute("title")).toContain("warming up");
  });
});

describe("Shortcuts hint chip (H6 — first-session affordance)", () => {
  it("renders on a fresh session (localStorage flag unset)", () => {
    const tb = renderTitlebar({
      live: "ok",
      rec: "ok",
      sys: "ok",
      clock: "00:00:00",
    });
    host().append(tb);
    const chip = tb.querySelector<HTMLElement>(".vmx-titlebar__hint");
    expect(chip).toBeTruthy();
    expect(chip?.textContent).toContain("shortcuts");
    expect(chip?.querySelector("b")?.textContent).toBe("?");
  });

  it("does NOT render when localStorage flag is already set", () => {
    window.localStorage.setItem(SHORTCUTS_HINT_STORAGE_KEY, "1");
    const tb = renderTitlebar({
      live: "ok",
      rec: "ok",
      sys: "ok",
      clock: "00:00:00",
    });
    host().append(tb);
    expect(tb.querySelector(".vmx-titlebar__hint")).toBeNull();
  });

  it("dismisses on ? keypress + sets the localStorage flag", () => {
    vi.useFakeTimers();
    const tb = renderTitlebar({
      live: "ok",
      rec: "ok",
      sys: "ok",
      clock: "00:00:00",
    });
    host().append(tb);
    expect(tb.querySelector(".vmx-titlebar__hint")).toBeTruthy();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "?" }));
    // The chip enters a fade-out (motion-transition = 200ms); after 220ms
    // it's removed from the DOM. We advance the timers past that.
    const chip = tb.querySelector<HTMLElement>(".vmx-titlebar__hint");
    expect(chip?.dataset.dismissing).toBe("true");
    vi.advanceTimersByTime(300);
    expect(tb.querySelector(".vmx-titlebar__hint")).toBeNull();
    expect(window.localStorage.getItem(SHORTCUTS_HINT_STORAGE_KEY)).toBe("1");
  });

  it("auto-dismisses after the timeout fires", () => {
    vi.useFakeTimers();
    const tb = renderTitlebar({
      live: "ok",
      rec: "ok",
      sys: "ok",
      clock: "00:00:00",
    });
    host().append(tb);
    expect(tb.querySelector(".vmx-titlebar__hint")).toBeTruthy();
    vi.advanceTimersByTime(SHORTCUTS_HINT_TIMEOUT_MS + 300);
    expect(tb.querySelector(".vmx-titlebar__hint")).toBeNull();
    expect(window.localStorage.getItem(SHORTCUTS_HINT_STORAGE_KEY)).toBe("1");
  });
});
