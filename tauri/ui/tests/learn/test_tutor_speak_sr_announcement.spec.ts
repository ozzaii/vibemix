// SPDX-License-Identifier: Apache-2.0
// REQ-ID: LESSON-05 / A11Y — Screen-reader announcement on
//                  `ipc.learn.tutor_speak`.
// The LearnWindow's `#learn-sr-announcement` aria-live region surfaces tutor
// narration text for VoiceOver / NVDA.
//
// Shape contract (per UI-SPEC §Accessibility lines 330-331):
//   1. Dispatch a CustomEvent("ipc.learn.tutor_speak", { detail: {
//        type: "ipc.learn.tutor_speak",
//        payload: {
//          text: "find deck A play button",
//          tts_marker: "L000.beat0",
//          citations: [],
//          data_state: "active",
//        },
//      }}) on window.
//   2. Within one event loop turn, the `[data-sr-region="tutor"]`
//      aria-live="polite" element's textContent equals the
//      payload.text VERBATIM.
//   3. data-state="active" → aria-live="polite"; data-state="hint" →
//      aria-live="assertive" (the 3-strike hint surface raises urgency).

import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";

import { mountLearnWindow } from "../../src/learn/learn-window";

const RealWebSocket = globalThis.WebSocket;

class StubWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  readyState = StubWebSocket.CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  constructor(_url: string) {}
  send(): void {}
  close(): void {
    this.readyState = StubWebSocket.CLOSED;
  }
  addEventListener(): void {}
  removeEventListener(): void {}
  dispatchEvent(): boolean {
    return true;
  }
}

function dispatchLessonLoaded(): void {
  window.dispatchEvent(
    new CustomEvent("ipc.learn.lesson_loaded", {
      detail: {
        course_id: "course_1_anatomy",
        lesson_id: "L1.01",
        title: "Opening dialog",
        controller_id: "pioneer_ddj_flx4",
        progress_dots: [],
      },
    }),
  );
}

describe("test_tutor_speak_sr_announcement.spec.ts (LESSON-05 a11y)", () => {
  beforeAll(() => {
    (globalThis as unknown as { WebSocket: unknown }).WebSocket = StubWebSocket;
  });

  afterAll(() => {
    (globalThis as unknown as { WebSocket: typeof RealWebSocket }).WebSocket =
      RealWebSocket;
  });

  beforeEach(() => {
    document.body.innerHTML = `<div id="learn-root"></div>`;
  });

  it("aria-live polite region receives tutor_speak text within one tick", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded();
      window.dispatchEvent(
        new CustomEvent("ipc.learn.tutor_speak", {
          detail: {
            text: "find deck A play button",
            tts_marker: "L1.01.beat0",
            citations: [],
            data_state: "active",
          },
        }),
      );
      await Promise.resolve();

      const sr = root.querySelector<HTMLElement>('[data-sr-region="tutor"]');
      expect(sr?.textContent).toBe("find deck A play button");
      expect(sr?.getAttribute("aria-live")).toBe("polite");
    } finally {
      ws.close();
    }
  });

  it("data-state='hint' raises aria-live to assertive", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded();
      window.dispatchEvent(
        new CustomEvent("ipc.learn.tutor_speak", {
          detail: {
            text: "turn the same knob farther",
            tts_marker: "L1.03.hint1",
            citations: [],
            data_state: "hint",
          },
        }),
      );
      await Promise.resolve();

      const sr = root.querySelector<HTMLElement>('[data-sr-region="tutor"]');
      expect(sr?.textContent).toBe("turn the same knob farther");
      expect(sr?.getAttribute("aria-live")).toBe("assertive");
    } finally {
      ws.close();
    }
  });

  it("hint citations light the existing control evidence chip", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded();
      window.dispatchEvent(
        new CustomEvent("ipc.learn.tutor_speak", {
          detail: {
            text: "turn the same knob farther",
            tts_marker: "L1.03.hint1",
            citations: ["[screen:eq_hi:A]"],
            data_state: "hint",
          },
        }),
      );
      await Promise.resolve();

      const cite = root.querySelector<HTMLElement>(".tutor-dock .cite");
      expect(cite?.textContent).toBe("◂ SCREEN DECK A HIGH EQ");
      expect(cite?.getAttribute("data-active")).toBe("true");
    } finally {
      ws.close();
    }
  });

  it("citation chips hide time-keyed evidence grammar", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded();
      window.dispatchEvent(
        new CustomEvent("ipc.learn.tutor_speak", {
          detail: {
            text: "move deck A high EQ farther.",
            tts_marker: "L1.03.adapt.mismatch",
            citations: ["[midi:eq_hi:A@12.7]"],
            data_state: "active",
          },
        }),
      );
      await Promise.resolve();

      const cite = root.querySelector<HTMLElement>(".tutor-dock .cite");
      expect(cite?.textContent).toBe("◂ MIDI DECK A HIGH EQ");
      expect(cite?.getAttribute("data-active")).toBe("true");
    } finally {
      ws.close();
    }
  });

  it("matched advances leave a deterministic action receipt", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded();
      window.dispatchEvent(
        new CustomEvent("ipc.learn.tutor_speak", {
          detail: {
            text: "move deck A high EQ.",
            tts_marker: "L1.03.beat0",
            citations: ["[midi:eq_hi:A@12.7]"],
            data_state: "active",
          },
        }),
      );
      window.dispatchEvent(
        new CustomEvent("ipc.learn.advance", {
          detail: {
            lesson_id: "L1.03",
            reason: "action_matched",
          },
        }),
      );
      await Promise.resolve();

      const pulse = root.querySelector<HTMLElement>(
        ".tutor-dock .take-pulse",
      );
      const sr = root.querySelector<HTMLElement>('[data-sr-region="tutor"]');
      expect(pulse?.textContent).toBe("clean touch · 01");
      expect(pulse?.getAttribute("aria-label")).toBe(
        "matched clean touch · 01",
      );
      expect(pulse?.getAttribute("data-active")).toBe("true");
      expect(sr?.textContent).toBe("matched clean touch · 01");
    } finally {
      ws.close();
    }
  });

  it("matched advances name the expected control in the receipt", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded();
      window.dispatchEvent(
        new CustomEvent("ipc.learn.highlight", {
          detail: {
            control_id: "eq_hi:A",
            deck: "A",
            cue_color: "amber",
            cue_shape: "pulse-ring",
            annotation: "move deck A high EQ.",
            expected_action: {
              type: "cc",
              control: "eq_hi",
              deck: "A",
              direction: "down",
              min_delta: 38,
            },
          },
        }),
      );
      window.dispatchEvent(
        new CustomEvent("ipc.learn.advance", {
          detail: {
            lesson_id: "L1.03",
            reason: "action_matched",
          },
        }),
      );
      await Promise.resolve();

      const pulse = root.querySelector<HTMLElement>(
        ".tutor-dock .take-pulse",
      );
      expect(pulse?.textContent).toBe("eq turn · 01");
      expect(pulse?.getAttribute("data-active")).toBe("true");
    } finally {
      ws.close();
    }
  });

  it("matched advance receipts remember hardware versus screen source", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded();
      window.dispatchEvent(
        new CustomEvent("ipc.learn.highlight", {
          detail: {
            control_id: "eq_hi:A",
            deck: "A",
            cue_color: "amber",
            cue_shape: "pulse-ring",
            annotation: "move deck A high EQ.",
            expected_action: {
              type: "cc",
              control: "eq_hi",
              deck: "A",
              direction: "down",
              min_delta: 38,
            },
          },
        }),
      );
      window.dispatchEvent(
        new CustomEvent("ipc.learn.midi_position", {
          detail: {
            controller_id: "pioneer_ddj_flx4",
            positions: { "eq_hi:A": 0 },
          },
        }),
      );
      window.dispatchEvent(
        new CustomEvent("ipc.learn.midi_position", {
          detail: {
            controller_id: "pioneer_ddj_flx4",
            positions: { "eq_hi:A": 127 },
          },
        }),
      );
      window.dispatchEvent(
        new CustomEvent("ipc.learn.advance", {
          detail: {
            lesson_id: "L1.03",
            reason: "action_matched",
          },
        }),
      );
      await Promise.resolve();

      const pulse = root.querySelector<HTMLElement>(
        ".tutor-dock .take-pulse",
      );
      expect(pulse?.textContent).toBe("eq turn · hardware · 01");
      expect(pulse?.getAttribute("aria-label")).toBe(
        "matched eq turn · hardware · 01",
      );

      window.dispatchEvent(
        new CustomEvent("ipc.learn.highlight", {
          detail: {
            control_id: "cue:A",
            deck: "A",
            cue_color: "amber",
            cue_shape: "pulse-ring",
            annotation: "press deck A cue.",
            expected_action: {
              type: "button",
              control: "cue",
              deck: "A",
              direction: "down",
            },
          },
        }),
      );
      root.querySelector<HTMLButtonElement>("#learn-screen-action")?.click();
      window.dispatchEvent(
        new CustomEvent("ipc.learn.advance", {
          detail: {
            lesson_id: "L1.03",
            reason: "action_matched",
          },
        }),
      );
      await Promise.resolve();

      expect(pulse?.textContent).toBe("cue hit · screen · 02");
      expect(pulse?.getAttribute("aria-label")).toBe(
        "matched cue hit · screen · 02",
      );
      expect(pulse?.getAttribute("data-active")).toBe("true");
      const sr = root.querySelector<HTMLElement>('[data-sr-region="tutor"]');
      expect(sr?.textContent).toBe("matched cue hit · screen · 02");
    } finally {
      ws.close();
    }
  });
});
