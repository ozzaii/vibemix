// SPDX-License-Identifier: Apache-2.0

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { convertFileSrcMock } = vi.hoisted(() => ({
  convertFileSrcMock: vi.fn((path: string) => `asset://converted${path}`),
}));

vi.mock("@tauri-apps/api/core", () => ({
  convertFileSrc: convertFileSrcMock,
}));

import { mountTimelinePlaceholder } from "../components/timeline.js";
import { mountMorningMirror } from "../components/morning-mirror.js";

let container: HTMLElement;
let timeline: HTMLElement;
const originalPlayDescriptor = Object.getOwnPropertyDescriptor(
  HTMLMediaElement.prototype,
  "play",
);

beforeEach(() => {
  container = document.createElement("div");
  timeline = document.createElement("div");
  document.body.append(container, timeline);
  convertFileSrcMock.mockClear();
  Reflect.deleteProperty(window, "__TAURI_INTERNALS__");
  Object.defineProperty(HTMLMediaElement.prototype, "play", {
    configurable: true,
    value: vi.fn(() => Promise.resolve()),
  });
});

afterEach(() => {
  document.body.replaceChildren();
  vi.restoreAllMocks();
  Reflect.deleteProperty(window, "__TAURI_INTERNALS__");
  if (originalPlayDescriptor) {
    Object.defineProperty(HTMLMediaElement.prototype, "play", originalPlayDescriptor);
  }
});

describe("morning mirror", () => {
  it("renders a grounded replay card and highlights the timeline window", () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {},
    });
    mountTimelinePlaceholder(
      timeline,
      [
        {
          id: "mix",
          start: 0,
          end: 600,
          label: "Mix",
          citation_event_id: "ev:MIX_MOVE@40",
        },
      ],
      600,
    );

    mountMorningMirror(
      container,
      {
        input_wav_relative_path: "input.wav",
        t_center: 42,
        window: [36, 46],
        receipt_text: "the mix recovered by ear [mix:near_miss@42.000]",
        friend_line_text: "I heard the mix pull back in [mix:near_miss@42.000]",
        duration_s: 600,
        friend_line_audio_relative_path: "debrief_friend_line.mp3",
        waveform_peaks: [
          [0, 0, 0],
          [255, 120, 30],
          [40, 90, 180],
        ],
      },
      "/recordings/set-001",
      { timelineEl: timeline },
    );

    expect(container.dataset.state).toBe("replay");
    expect(container.textContent).toContain("I was there");
    expect(container.textContent).toContain("the mix recovered by ear");
    expect(convertFileSrcMock).toHaveBeenCalledWith("/recordings/set-001/input.wav");
    expect(convertFileSrcMock).toHaveBeenCalledWith(
      "/recordings/set-001/debrief_friend_line.mp3",
    );
    expect(container.textContent).toContain("Play line");
    expect(
      container.querySelector(".vmx-morning-mirror__friend-audio")?.getAttribute("src"),
    ).toBe("asset://converted/recordings/set-001/debrief_friend_line.mp3");
    expect(container.querySelector(".vmx-morning-mirror__rail")?.getAttribute("data-source")).toBe(
      "master-input",
    );
    expect(
      timeline.querySelector(".vmx-debrief-replay-window")?.getAttribute("aria-label"),
    ).toContain("0:36");
  });

  it("renders calm-night state without audio when the detector abstains", () => {
    mountMorningMirror(
      container,
      {
        input_wav_relative_path: "input.wav",
        t_center: null,
        window: null,
        receipt_text: "",
        friend_line_text: "",
        duration_s: 600,
      },
      "/recordings/set-001",
      { timelineEl: timeline },
    );

    expect(container.dataset.state).toBe("quiet");
    expect(container.textContent).toContain("Nothing sharp enough to flag");
    expect(container.querySelector("audio")).toBeNull();
    expect(timeline.querySelector(".vmx-debrief-replay-window")).toBeNull();
  });

  it("can play the grounded friend line even when there is no replay window", () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {},
    });

    mountMorningMirror(
      container,
      {
        input_wav_relative_path: "input.wav",
        t_center: null,
        window: null,
        receipt_text: "",
        friend_line_text: "Your recovery stayed musical [mix:near_miss@42.000]",
        duration_s: 600,
        friend_line_audio_relative_path: "debrief_friend_line.mp3",
      },
      "/recordings/set-001",
      { timelineEl: timeline },
    );

    expect(container.dataset.state).toBe("quiet");
    expect(container.textContent).toContain("Your recovery stayed musical");
    expect(container.textContent).toContain("Play line");
    expect(container.querySelector(".vmx-morning-mirror__audio")).toBeNull();
    expect(container.querySelector(".vmx-morning-mirror__friend-audio")).not.toBeNull();
  });
});
