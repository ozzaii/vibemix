/**
 * @vitest-environment jsdom
 *
 * The folded shell Debrief route is a review dock, not a placeholder. It must
 * request real recording summaries, show what is review-ready, and open the
 * dedicated Debrief window only for sessions with enough evidence.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  invokeTauri: vi.fn(() => Promise.resolve()),
  sendIpcRequest: vi.fn(),
}));

vi.mock("../../src/ipc/client.js", () => ({
  sendIpcRequest: mocks.sendIpcRequest,
}));

vi.mock("../../src/tauri-runtime.js", () => ({
  invokeTauri: mocks.invokeTauri,
}));

import { mountDebriefDock } from "../../src/shell/DebriefDock.js";

function sessionsPayload() {
  return {
    type: "ipc.recordings.list_result",
    ts: "2026-06-03T00:00:00Z",
    payload: {
      bytes_total: 99 * 1024 * 1024,
      sessions: [
        {
          session_dir: "20260603-001500",
          started_at_iso: "2026-06-03T00:15:00Z",
          duration_s: 42 * 60,
          event_count: 19,
          bytes_total: 72 * 1024 * 1024,
          crashed: false,
        },
        {
          session_dir: "20260602-235500",
          started_at_iso: "2026-06-02T23:55:00Z",
          duration_s: 90,
          event_count: 2,
          bytes_total: 27 * 1024 * 1024,
          crashed: false,
        },
      ],
    },
  };
}

async function flush(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
}

beforeEach(() => {
  mocks.invokeTauri.mockClear();
  mocks.sendIpcRequest.mockReset();
});

describe("DebriefDock", () => {
  it("lists recent recordings and opens the real debrief window for ready sessions", async () => {
    mocks.sendIpcRequest.mockResolvedValueOnce(sessionsPayload());
    const host = document.createElement("div");

    mountDebriefDock(host);
    await flush();

    expect(mocks.sendIpcRequest).toHaveBeenCalledWith(
      "ipc.recordings.list",
      {},
      "ipc.recordings.list_result",
    );
    expect(host.textContent).toContain("2 sessions");
    expect(host.textContent).toContain("next review");
    expect(host.textContent).toContain("review is armed");
    expect(host.textContent).toContain("can open with cited moments");
    expect(host.textContent).toContain("2026-06-03 00:15");
    expect(host.textContent).toContain("42m");
    expect(host.textContent).toContain("19 events");
    expect(host.textContent).toContain("ready for cited review");

    const openButtons = Array.from(
      host.querySelectorAll<HTMLButtonElement>(".debrief-dock__open"),
    );
    expect(openButtons[0]?.disabled).toBe(false);
    openButtons[0]?.click();

    expect(mocks.invokeTauri).toHaveBeenCalledWith("open_debrief_window", {
      sessionDir: "20260603-001500",
    });
  });

  it("keeps weak recordings visible but prevents fake debrief launch", async () => {
    mocks.sendIpcRequest.mockResolvedValueOnce(sessionsPayload());
    const host = document.createElement("div");

    mountDebriefDock(host);
    await flush();

    const openButtons = Array.from(
      host.querySelectorAll<HTMLButtonElement>(".debrief-dock__open"),
    );
    expect(openButtons[1]?.disabled).toBe(true);
    expect(openButtons[1]?.title).toBe("needs at least 5 minutes");
    expect(host.textContent).toContain("capture more");
    openButtons[1]?.click();

    expect(mocks.invokeTauri).not.toHaveBeenCalled();
  });

  it("explains the empty recording state without pretending a review exists", async () => {
    mocks.sendIpcRequest.mockResolvedValueOnce({
      type: "ipc.recordings.list_result",
      ts: "2026-06-03T00:00:00Z",
      payload: { bytes_total: 0, sessions: [] },
    });
    const host = document.createElement("div");

    mountDebriefDock(host);
    await flush();

    expect(host.textContent).toContain("no sessions recorded");
    expect(host.textContent).toContain("record a real set");
    expect(host.textContent).toContain("Debrief arms after five minutes");
    expect(host.textContent).toContain("Run a real set from Deck");
    expect(host.querySelector(".debrief-dock__open")).toBeNull();
  });
});
