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
  it("can mount cold inside the keep-alive shell without loading recording history", async () => {
    const host = document.createElement("div");

    mountDebriefDock(host, { autoRefresh: false });
    await flush();

    expect(mocks.sendIpcRequest).not.toHaveBeenCalled();
    expect(host.textContent).toContain("ready when you are");
    expect(host.textContent).toContain("Refresh when you want the latest local set receipts.");
    expect(host.textContent).toContain("record a real set");

    const refresh = host.querySelector<HTMLButtonElement>(".debrief-dock__refresh");
    mocks.sendIpcRequest.mockResolvedValueOnce(sessionsPayload());
    refresh?.click();
    await flush();

    expect(mocks.sendIpcRequest).toHaveBeenCalledWith(
      "ipc.recordings.list",
      {},
      "ipc.recordings.list_result",
    );
    expect(host.textContent).toContain("2 sessions");
  });

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
    expect(host.textContent).toContain("is ready, with the why behind every call");
    expect(host.textContent).toContain("last set");
    expect(host.textContent).toContain("blocker");
    expect(host.textContent).toContain("open your review");
    expect(host.textContent).toContain("one drill or Viber move");
    expect(host.textContent).toContain("2026-06-03 00:15");
    expect(host.textContent).toContain("42m");
    expect(host.textContent).toContain("19 events");
    expect(host.textContent).toContain("ready to review");
    expect(host.textContent).toContain("Payback: open review to leave with one drill or Viber move.");

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
    expect(host.textContent).toContain("4m more and I can review this set.");
    openButtons[1]?.click();

    expect(mocks.invokeTauri).not.toHaveBeenCalled();
  });

  it("selects the closest weak recording and tells the DJ the fastest payback action", async () => {
    mocks.sendIpcRequest.mockResolvedValueOnce({
      type: "ipc.recordings.list_result",
      ts: "2026-06-03T00:00:00Z",
      payload: {
        bytes_total: 35 * 1024 * 1024,
        sessions: [
          {
            session_dir: "20260603-003000",
            started_at_iso: "2026-06-03T00:30:00Z",
            duration_s: 4 * 60 + 12,
            event_count: 7,
            bytes_total: 20 * 1024 * 1024,
            crashed: false,
          },
          {
            session_dir: "20260602-233000",
            started_at_iso: "2026-06-02T23:30:00Z",
            duration_s: 6 * 60,
            event_count: 2,
            bytes_total: 15 * 1024 * 1024,
            crashed: false,
          },
          {
            session_dir: "20260603-004500",
            started_at_iso: "2026-06-03T00:45:00Z",
            duration_s: 0,
            event_count: 0,
            bytes_total: 1 * 1024 * 1024,
            crashed: true,
          },
        ],
      },
    });
    const host = document.createElement("div");

    mountDebriefDock(host);
    await flush();

    expect(host.textContent).toContain("capture 1m more");
    expect(host.textContent).toContain("2026-06-03 00:30");
    expect(host.textContent).toContain("1m short");
    expect(host.textContent).toContain("keep Deck running");
    expect(host.textContent).toContain("your review");
    expect(host.querySelector('[data-payback="target"]')?.textContent).toBe("2026-06-03 00:30");
    expect(host.querySelector('[data-payback="blocker"]')?.textContent).toBe("1m short");
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

  it("shows one calm summary when every recent set stopped early", async () => {
    mocks.sendIpcRequest.mockResolvedValueOnce({
      type: "ipc.recordings.list_result",
      ts: "2026-06-03T00:00:00Z",
      payload: {
        bytes_total: 5 * 1024 * 1024,
        sessions: [
          {
            session_dir: "20260603-010000",
            started_at_iso: "2026-06-03T01:00:00Z",
            duration_s: 0,
            event_count: 0,
            bytes_total: 3 * 1024 * 1024,
            crashed: true,
          },
          {
            session_dir: "20260603-005000",
            started_at_iso: "2026-06-03T00:50:00Z",
            duration_s: 0,
            event_count: 0,
            bytes_total: 2 * 1024 * 1024,
            crashed: true,
          },
        ],
      },
    });
    const host = document.createElement("div");

    mountDebriefDock(host);
    await flush();

    expect(host.textContent).toContain("nothing to review yet");
    expect(host.textContent).toContain("Run one start to finish");
    const openButtons = Array.from(
      host.querySelectorAll<HTMLButtonElement>(".debrief-dock__open"),
    );
    expect(openButtons.length).toBe(2);
    expect(openButtons.every((button) => button.disabled)).toBe(true);
  });
});
