// SPDX-License-Identifier: Apache-2.0
// Wreck Room booth contract: one button starts the round over the EXISTING
// ipc.learn.ack wire (control_id wreck_round / wreck_stop — zero new IPC
// types), the surface renders only measured wire truth, and streak/difficulty
// never appear as number chips.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  emitIpc: vi.fn(async (_type: string, _payload?: unknown) => undefined),
  subscribeIpc: vi.fn(async () => () => undefined),
}));

vi.mock("../../src/ipc/client.js", () => ({
  emitIpc: mocks.emitIpc,
  subscribeIpc: mocks.subscribeIpc,
}));

import {
  mountWreckBooth,
  type WreckBoothHandle,
} from "../../src/learn/booth/wreck-booth";

function liveGrade(detail: Record<string, unknown>): void {
  window.dispatchEvent(new CustomEvent("ipc.learn.live_grade", { detail }));
}

async function flush(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
}

describe("wreck booth", () => {
  let host: HTMLElement;
  let booth: WreckBoothHandle | null = null;

  beforeEach(() => {
    mocks.emitIpc.mockClear();
    host = document.createElement("div");
    document.body.append(host);
  });

  afterEach(() => {
    booth?.teardown();
    booth = null;
    host.remove();
  });

  it("renders the idle booth with one primary action and honest copy", () => {
    booth = mountWreckBooth(host, { connectWs: false });
    expect(booth.root.dataset.round).toBe("idle");
    const go = host.querySelector<HTMLButtonElement>(".wreck-booth__go");
    expect(go?.textContent).toBe("drop the needle");
    expect(host.querySelector(".wreck-booth__sven")?.textContent).toContain(
      "drop the needle",
    );
    expect(host.querySelector(".wreck-booth__receipt")?.textContent).toContain(
      "headphones",
    );
  });

  it("starts the round over the existing ack wire on the button", async () => {
    booth = mountWreckBooth(host, { connectWs: false });
    host.querySelector<HTMLButtonElement>(".wreck-booth__go")?.click();
    await flush();
    expect(mocks.emitIpc).toHaveBeenCalledWith(
      "ipc.learn.ack",
      expect.objectContaining({ control_id: "wreck_round", source: "click" }),
    );
    expect(
      host.querySelector<HTMLButtonElement>(".wreck-booth__go")?.textContent,
    ).toBe("lift the needle");
  });

  it("stops the round with wreck_stop on the second press", async () => {
    booth = mountWreckBooth(host, { connectWs: false });
    const go = host.querySelector<HTMLButtonElement>(".wreck-booth__go");
    go?.click();
    await flush();
    go?.click();
    await flush();
    expect(mocks.emitIpc).toHaveBeenCalledWith(
      "ipc.learn.ack",
      expect.objectContaining({ control_id: "wreck_stop", source: "click" }),
    );
    expect(go?.textContent).toBe("drop the needle");
  });

  it("paints the hunt state and countdown words from live_grade save fields", () => {
    booth = mountWreckBooth(host, { connectWs: false });
    liveGrade({
      verdict: "tempo_off",
      phase_error_beats: 0.2,
      score: 0.1,
      citation: null,
      save_attempt_active: true,
      save_floor_seconds_total: 14,
      save_floor_seconds_remaining: 9.4,
      save_difficulty_level: 2,
      save_streak: 1,
    });
    expect(booth.root.dataset.round).toBe("hunt");
    const receipt = host.querySelector(".wreck-booth__receipt")?.textContent ?? "";
    expect(receipt).toContain("9.4 seconds");
    // measured state reaches the user as words, never xN / L-number chips
    expect(receipt).not.toMatch(/x\d|L\d/);
  });

  it("paints landed and missed verdicts as plain receipt words", () => {
    booth = mountWreckBooth(host, { connectWs: false });
    liveGrade({
      verdict: "locked",
      phase_error_beats: 0,
      score: 1,
      citation: null,
      save_landed: true,
      save_difficulty_level: 2,
      save_streak: 3,
    });
    expect(booth.root.dataset.round).toBe("landed");
    expect(host.querySelector(".wreck-booth__receipt")?.textContent).toBe(
      "3 clean saves in a row.",
    );
    liveGrade({
      verdict: "trainwreck",
      phase_error_beats: 0.4,
      score: 0,
      citation: null,
      save_floor_expired: true,
      save_difficulty_level: 2,
      save_streak: 0,
    });
    expect(booth.root.dataset.round).toBe("missed");
    expect(host.querySelector(".wreck-booth__receipt")?.textContent).toContain(
      "window closed",
    );
  });

  it("treats a refusal bark as the truth, never a false device diagnosis", async () => {
    vi.useFakeTimers();
    try {
      booth = mountWreckBooth(host, { connectWs: false });
      const go = host.querySelector<HTMLButtonElement>(".wreck-booth__go");
      go?.click();
      await flush();
      window.dispatchEvent(
        new CustomEvent("ipc.learn.tutor_speak", {
          detail: {
            text: "your set has the decks. the booth waits until you're off the air.",
            tts_marker: "wreck_round.busy",
          },
        }),
      );
      // the backend refused and said why; the button resets honestly
      expect(go?.textContent).toBe("drop the needle");
      // and the audio watchdog must not overrule Sven with "check your sound output"
      vi.advanceTimersByTime(5000);
      const receipt =
        host.querySelector(".wreck-booth__receipt")?.textContent ?? "";
      expect(receipt).not.toContain("check your sound output");
      expect(host.querySelector(".wreck-booth__sven")?.textContent).toContain(
        "booth waits",
      );
    } finally {
      vi.useRealTimers();
    }
  });

  it("speaks Sven lines from tutor_speak", () => {
    booth = mountWreckBooth(host, { connectWs: false });
    window.dispatchEvent(
      new CustomEvent("ipc.learn.tutor_speak", {
        detail: { text: "that's the pocket. 4 seconds." },
      }),
    );
    expect(host.querySelector(".wreck-booth__sven")?.textContent).toBe(
      "that's the pocket. 4 seconds.",
    );
  });

  it("exposes deck B controls as accessible sliders", () => {
    booth = mountWreckBooth(host, { connectWs: false });
    const fader = host.querySelector('[data-control="tempo:B"]');
    const jog = host.querySelector('[data-control="jog:B"]');
    expect(fader?.getAttribute("role")).toBe("slider");
    expect(jog?.getAttribute("role")).toBe("slider");
    expect(fader?.getAttribute("aria-valuenow")).toBe("64");
  });
});
