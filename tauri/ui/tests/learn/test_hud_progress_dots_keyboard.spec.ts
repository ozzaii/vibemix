// SPDX-License-Identifier: Apache-2.0
// REQ-ID: LESSON-02 / A11Y — HUD progress-dots keyboard navigation.
// The LearnLessonLoaded envelope's `progress_dots[]` array (one entry per
// lesson in the active course) becomes the HUD strip. Each dot has
// `status: "pending" | "current" | "completed"`. Keyboard contract per
// UI-SPEC §Accessibility line 329:
//
//   * Tab moves focus across dots in DOM order.
//   * Enter on a COMPLETED dot → emit `ipc.learn.start_lesson { lesson_id, level: "replay" }`.
//   * Enter on the CURRENT dot → no-op (already there).
//   * Enter on a PENDING dot → show tooltip "prerequisite lessons not yet complete."

import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

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
        lesson_id: "L1.02",
        title: "meet your controller",
        controller_id: "pioneer_ddj_flx4",
        progress_dots: [
          { lesson_id: "L1.01", status: "completed" },
          { lesson_id: "L1.02", status: "current" },
          { lesson_id: "L1.03", status: "pending" },
        ],
      },
    }),
  );
}

function pressEnter(el: Element): void {
  el.dispatchEvent(
    new KeyboardEvent("keydown", {
      bubbles: true,
      key: "Enter",
    }),
  );
}

describe("test_hud_progress_dots_keyboard.spec.ts (LESSON-02 a11y)", () => {
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
  });

  it("renders canonical Course 1 label and nonzero progress denominator", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded();

      expect(root.querySelector(".learn-hud .course-chip")?.textContent).toBe(
        "COURSE 1 · ANATOMY",
      );
      expect(root.querySelector(".learn-hud .progress-index")?.textContent).toBe(
        "2 OF 3",
      );
    } finally {
      ws.close();
    }
  });

  it("Enter on completed dot emits start_lesson replay", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded();
      mocks.emitIpc.mockClear();

      const completed = root.querySelector<HTMLElement>(
        ".learn-hud .dot[data-status='completed']",
      )!;
      expect(completed.getAttribute("aria-label")).toBe(
        "lesson L1.01, completed, press to replay",
      );
      expect(completed.getAttribute("title")).toBe("press to replay this lesson.");
      pressEnter(completed);

      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.start_lesson", {
        lesson_id: "L1.01",
        level: "replay",
      });
    } finally {
      ws.close();
    }
  });

  it("Enter on current dot is a no-op", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded();
      mocks.emitIpc.mockClear();

      const current = root.querySelector<HTMLElement>(
        ".learn-hud .dot[data-status='current']",
      )!;
      pressEnter(current);

      expect(mocks.emitIpc).not.toHaveBeenCalled();
      expect(current.getAttribute("aria-current")).toBe("step");
      expect(current.getAttribute("aria-label")).toBe(
        "lesson L1.02, current step",
      );
    } finally {
      ws.close();
    }
  });

  it("Enter on pending dot exposes prerequisite tooltip and emits nothing", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded();
      mocks.emitIpc.mockClear();

      const pending = root.querySelector<HTMLElement>(
        ".learn-hud .dot[data-status='pending']",
      )!;
      pressEnter(pending);

      expect(mocks.emitIpc).not.toHaveBeenCalled();
      expect(pending.getAttribute("aria-disabled")).toBe("true");
      expect(pending.getAttribute("aria-label")).toBe(
        "lesson L1.03, pending, prerequisite lessons not yet complete",
      );
      expect(pending.dataset.tooltipVisible).toBe("true");
      expect(pending.getAttribute("title")).toBe(
        "prerequisite lessons not yet complete.",
      );
    } finally {
      ws.close();
    }
  });
});
