// SPDX-License-Identifier: Apache-2.0
// Beginner-path contract: the main app can open Learn, start the recommended
// lesson, accept one visible action, and move the recommendation forward.

import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  emitIpc: vi.fn(async (_type: string, _payload?: unknown) => undefined),
  invoke: vi.fn(async (_cmd: string, _args?: unknown) => undefined),
  subscribeIpc: vi.fn(async () => () => undefined),
}));

vi.mock("@tauri-apps/api/core", () => ({
  invoke: mocks.invoke,
}));

vi.mock("../../src/ipc/client.js", () => ({
  emitIpc: mocks.emitIpc,
  subscribeIpc: mocks.subscribeIpc,
}));

import { mountLearnWindow } from "../../src/learn/learn-window";
import { _internals } from "../../src/session/render-loop.js";
import {
  _resetSessionStateForTests,
  getSessionState,
} from "../../src/session/state.js";

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

async function waitForMountedControl(
  root: HTMLElement,
  controlId: string,
): Promise<SVGGElement> {
  for (let i = 0; i < 25; i += 1) {
    const hit = root.querySelector<SVGGElement>(
      `[data-control-id="${controlId}"]`,
    );
    if (hit) return hit;
    await new Promise((r) => setTimeout(r, 10));
  }
  throw new Error(`control ${controlId} did not mount`);
}

function dispatchLessonLoaded(lessonId = "L1.01"): void {
  window.dispatchEvent(
    new CustomEvent("ipc.learn.lesson_loaded", {
      detail: {
        course_id: "course_1_anatomy",
        lesson_id: lessonId,
        title: "Opening dialog",
        controller_id: "pioneer_ddj_flx4",
        progress_dots: [],
      },
    }),
  );
}

describe("beginner Learn path contract", () => {
  beforeAll(() => {
    (globalThis as unknown as { WebSocket: unknown }).WebSocket = StubWebSocket;
  });

  afterAll(() => {
    (globalThis as unknown as { WebSocket: typeof RealWebSocket }).WebSocket =
      RealWebSocket;
  });

  beforeEach(() => {
    document.body.innerHTML = `<div id="learn-root"></div>`;
    mocks.emitIpc.mockClear();
    mocks.invoke.mockClear();
    _resetSessionStateForTests();
  });

  it("opens Learn from the main app and advances the first booth action", async () => {
    _internals.modeChangeHandler("learn");
    await Promise.resolve();

    expect(getSessionState().mode).toBe("learn");
    expect(mocks.invoke).toHaveBeenCalledWith("open_learn_window");
    expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.session.set_mode", {
      mode: "learn",
    });

    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      await waitForMountedControl(root, "eq_hi:A");

      mocks.emitIpc.mockClear();
      root.querySelector<HTMLButtonElement>("#learn-start-recommended")!.click();
      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.start_lesson", {
        lesson_id: "L1.01",
        level: "fresh",
      });

      dispatchLessonLoaded("L1.01");
      window.dispatchEvent(
        new CustomEvent("ipc.learn.highlight", {
          detail: {
            control_id: "lesson_continue",
            deck: "",
            cue_color: "amber",
            cue_shape: "pulse-ring",
            annotation: "continue",
            expected_action: {
              type: "button",
              control: "lesson_continue",
              deck: "",
              direction: "down",
            },
          },
        }),
      );

      mocks.emitIpc.mockClear();
      root.querySelector<HTMLButtonElement>("#learn-screen-action")!.click();
      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.ack", {
        control_id: "lesson_continue",
        source: "click",
        value: 127,
        prev_value: 0,
        direction: "down",
      });

      window.dispatchEvent(
        new CustomEvent("ipc.learn.complete_lesson", {
          detail: {
            lesson_id: "L1.01",
            reason: "completed",
          },
        }),
      );
      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "snapshot",
            progress: {
              schema_version: 1,
              courses: {},
              lessons: {
                "L1.01": { completed: true },
              },
              course_2_unlocked: false,
              course_3_unlocked: false,
            },
          },
        }),
      );

      mocks.emitIpc.mockClear();
      root.querySelector<HTMLButtonElement>("#learn-start-recommended")!.click();
      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.start_lesson", {
        lesson_id: "L1.02",
        level: "fresh",
      });
    } finally {
      ws.close();
    }
  });
});
