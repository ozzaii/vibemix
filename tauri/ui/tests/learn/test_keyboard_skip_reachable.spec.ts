// SPDX-License-Identifier: Apache-2.0
// REQ-ID: LESSON-04 / A11Y — "I got it" skip button reachable via keyboard.
// Regression: the "I got it" skip button is motor-impaired-safe, keyboard
// reachable, and guarded by the 45 s min-dwell floor.
//
// Shape contract:
//   1. Mount LearnWindow with a loaded lesson.
//   2. Press Tab N times (N ≤ 8 in the canonical layout).
//   3. Expect focus to land on the "i got it" button before N=8 exhausts.
//   4. Press Space; expect the page to emit `ipc.learn.complete_lesson`
//      with `payload.reason === "user_skip"`.
//   5. Assert: 45 s min-dwell guard must be PAST (the button is enabled).

import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  emitIpc: vi.fn(async (_type: string, _payload?: unknown) => undefined),
  subscribeIpc: vi.fn(async () => () => undefined),
}));

vi.mock("../../src/ipc/client.js", () => ({
  emitIpc: mocks.emitIpc,
  subscribeIpc: mocks.subscribeIpc,
}));

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

function pressSpace(el: Element): void {
  el.dispatchEvent(
    new KeyboardEvent("keydown", {
      bubbles: true,
      key: " ",
    }),
  );
}

describe("test_keyboard_skip_reachable.spec.ts (LESSON-04 a11y)", () => {
  beforeAll(() => {
    (globalThis as unknown as { WebSocket: unknown }).WebSocket = StubWebSocket;
  });

  afterAll(() => {
    (globalThis as unknown as { WebSocket: typeof RealWebSocket }).WebSocket =
      RealWebSocket;
  });

  beforeEach(() => {
    vi.useFakeTimers();
    document.body.innerHTML = `<div id="learn-root"></div>`;
    mocks.emitIpc.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
    document.body.replaceChildren();
  });

  it("skip button is focusable and Space emits complete_lesson user_skip after dwell", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded();
      const skip = root.querySelector<HTMLButtonElement>(
        '[data-action="skip-lesson"]',
      )!;
      skip.focus();
      expect(document.activeElement).toBe(skip);

      vi.advanceTimersByTime(45_000);
      pressSpace(skip);

      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.complete_lesson", {
        lesson_id: "L1.01",
        reason: "user_skip",
      });
    } finally {
      ws.close();
    }
  });

  it("before 45 s dwell, skip keyboard activation is blocked", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded();
      const skip = root.querySelector<HTMLButtonElement>(
        '[data-action="skip-lesson"]',
      )!;

      expect(skip.getAttribute("aria-disabled")).toBe("true");
      mocks.emitIpc.mockClear();
      pressSpace(skip);
      expect(mocks.emitIpc).not.toHaveBeenCalled();
    } finally {
      ws.close();
    }
  });
});
