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
          ear_test_clip_relative_path: "near_miss_ear_test.wav",
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
      ear_test_clip_relative_path: "near_miss_ear_test.wav",
    });
  });

  it("sends moment feedback on the debrief websocket", () => {
    const client = new DebriefWsClient(8766);
    const send = vi.fn();
    (
      client as unknown as {
        ws: { readyState: number; send: (frame: string) => void };
      }
    ).ws = {
      readyState: WebSocket.OPEN,
      send,
    };

    client.sendMomentFeedback({
      moment_id: "drill-0",
      citation_id: "[ev:M@1]",
      verdict: "agree",
      surface: "transition",
    });

    expect(send).toHaveBeenCalledTimes(1);
    expect(JSON.parse(send.mock.calls[0]?.[0] as string)).toMatchObject({
      type: "ipc.debrief.moment-feedback",
      payload: {
        moment_id: "drill-0",
        citation_id: "[ev:M@1]",
        verdict: "agree",
        surface: "transition",
      },
    });
  });
});
