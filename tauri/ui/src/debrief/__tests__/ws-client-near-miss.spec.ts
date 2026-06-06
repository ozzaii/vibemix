// SPDX-License-Identifier: Apache-2.0

import { describe, expect, it, vi } from "vitest";

import { DebriefWsClient } from "../ws-client.js";

describe("DebriefWsClient near-miss frame", () => {
  it("dispatches ipc.debrief.near-miss instead of dropping it as unknown", () => {
    const client = new DebriefWsClient(8766);
    const onNearMiss = vi.fn();
    client.addEventListener("near-miss", (e: Event) => {
      onNearMiss((e as CustomEvent).detail);
    });

    (
      client as unknown as {
        _onMessage(raw: string): void;
      }
    )._onMessage(
      JSON.stringify({
        type: "ipc.debrief.near-miss",
        ts: "2026-06-06T00:00:00Z",
        payload: {
          input_wav_relative_path: "input.wav",
          t_center: 42,
          window: [36, 46],
          receipt_text: "the mix recovered by ear [mix:near_miss@42.000]",
          friend_line_text: "I heard it [mix:near_miss@42.000]",
          duration_s: 600,
        },
      }),
    );

    expect(onNearMiss).toHaveBeenCalledWith({
      input_wav_relative_path: "input.wav",
      t_center: 42,
      window: [36, 46],
      receipt_text: "the mix recovered by ear [mix:near_miss@42.000]",
      friend_line_text: "I heard it [mix:near_miss@42.000]",
      duration_s: 600,
    });
  });
});
