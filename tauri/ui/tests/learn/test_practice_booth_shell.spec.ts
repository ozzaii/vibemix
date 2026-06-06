// SPDX-License-Identifier: Apache-2.0
// Practice-booth shell contract: Learn opens into one current practice
// surface, with the 36-lesson map available on demand instead of first paint.

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
const RealPointerEvent = globalThis.PointerEvent;

class TestPointerEvent extends MouseEvent {
  readonly pointerId: number;

  constructor(type: string, init: MouseEventInit & { pointerId?: number } = {}) {
    super(type, { bubbles: true, cancelable: true, ...init });
    this.pointerId = init.pointerId ?? 1;
  }
}

class StubWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  static instances: StubWebSocket[] = [];
  static sent: string[] = [];
  readyState = StubWebSocket.CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  constructor(_url: string) {
    StubWebSocket.instances.push(this);
  }
  send(data: string): void {
    StubWebSocket.sent.push(data);
  }
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

function dispatchLessonLoaded(
  lessonId = "L1.01",
  courseId = "course_1_anatomy",
): void {
  window.dispatchEvent(
    new CustomEvent("ipc.learn.lesson_loaded", {
      detail: {
        course_id: courseId,
        lesson_id: lessonId,
        title: "Opening dialog",
        controller_id: "pioneer_ddj_flx4",
        progress_dots: [],
      },
    }),
  );
}

function nextAnimationFrame(): Promise<void> {
  return new Promise((resolve) => {
    window.requestAnimationFrame(() => resolve());
  });
}

const COURSE_1_LESSON_IDS = Array.from(
  { length: 16 },
  (_value, index) => `L1.${String(index + 1).padStart(2, "0")}`,
);

function completedRows(lessonIds: ReadonlyArray<string>): Record<string, {
  completed: boolean;
  completed_at: string;
  strikes_used: number;
}> {
  return Object.fromEntries(
    lessonIds.map((lessonId) => [
      lessonId,
      {
        completed: true,
        completed_at: "2026-05-28T00:00:00Z",
        strikes_used: 0,
      },
    ]),
  );
}

describe("practice booth shell", () => {
  beforeAll(() => {
    (globalThis as unknown as { WebSocket: unknown }).WebSocket = StubWebSocket;
    (globalThis as unknown as { PointerEvent: typeof PointerEvent }).PointerEvent =
      TestPointerEvent as unknown as typeof PointerEvent;
  });

  afterAll(() => {
    (globalThis as unknown as { WebSocket: typeof RealWebSocket }).WebSocket =
      RealWebSocket;
    (globalThis as unknown as { PointerEvent: typeof RealPointerEvent }).PointerEvent =
      RealPointerEvent;
  });

  beforeEach(() => {
    window.history.replaceState(null, "", "/learn.html");
    document.body.innerHTML = `<div id="learn-root"></div>`;
    StubWebSocket.instances = [];
    StubWebSocket.sent = [];
    mocks.emitIpc.mockReset();
    mocks.emitIpc.mockImplementation(async () => undefined);
  });

  it("first paint shows the booth prompt and a usable on-screen deck", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const booth = root.querySelector<HTMLElement>("#learn-booth-panel");
      const map = root.querySelector<HTMLElement>("#learn-progress-list-host");
      const earned = root.querySelector<HTMLElement>("#learn-earned-wall-host");
      await waitForMountedControl(root, "eq_hi:A");
      expect(booth?.dataset.visible).toBe("true");
      expect(map?.dataset.visible).toBe("false");
      expect(map?.getAttribute("aria-hidden")).toBe("true");
      expect(earned?.getAttribute("aria-label")).toBe("earned skill wall");
      expect(earned?.querySelector(".skill-wall__empty")?.textContent).toContain(
        "Your skills light up",
      );
      expect(earned?.querySelector(".skill-wall__empty")?.textContent).toContain(
        "earn their stars",
      );
      expect(
        Array.from(booth?.querySelectorAll("button") ?? []).map(
          (button) => button.id,
        ),
      ).toEqual(["learn-start-recommended", "learn-open-map"]);
      expect(map?.querySelectorAll(".vmx-progress-list__lesson").length).toBe(
        36,
      );
      expect(root.querySelector('[data-control-id="eq_hi:A"]')).not.toBeNull();
      expect(root.textContent).toContain("on-screen deck");
      expect(root.querySelector(".learn-booth-command")).toBeTruthy();
      expect(root.textContent).toContain("your move");
      expect(root.textContent).toContain("use the on-screen controls");
    } finally {
      ws.close();
    }
  });

  it("updates the Earned wall from progress snapshots", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "snapshot",
            progress: {
              schema_version: 2,
              courses: {},
              lessons: {},
              skill_wall: [
                {
                  skill_id: "deck_control",
                  stage: "competent",
                  learn_fill: 1,
                  competent: true,
                  live_proof_count: 1,
                  mastered: false,
                  first_mastered_at: null,
                  what_remains: "2 more cited proofs to Master",
                },
              ],
            },
          },
        }),
      );

      const row = root.querySelector<HTMLElement>(
        "#learn-earned-wall-host .skill-wall__row",
      );
      expect(row?.dataset.skill).toBe("deck_control");
      expect(row?.dataset.stage).toBe("competent");
      expect(row?.querySelector(".skill-wall__name")?.textContent).toBe(
        "Deck Control",
      );
      expect(row?.querySelector(".skill-wall__remains")?.textContent).toBe(
        "2 more cited proofs to Master",
      );
    } finally {
      ws.close();
    }
  });

  it("surfaces tutor voice status without waiting for a MIDI status change", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const voice = root.querySelector<HTMLElement>(".learn-status-voice")!;
      const controller = root.querySelector<HTMLElement>(
        ".learn-status-controller",
      )!;
      expect(voice.textContent).toBe("voice pending");
      expect(voice.dataset.voiceStatus).toBe("pending");

      window.dispatchEvent(
        new CustomEvent("ipc.status.tick", {
          detail: {
            payload: {
              midi: 0,
              voice: "muted",
            },
          },
        }),
      );
      expect(controller.textContent).toBe("on-screen deck");
      expect(voice.textContent).toBe("subtitles only");
      expect(voice.dataset.voiceStatus).toBe("muted");
      expect(voice.getAttribute("aria-label")).toBe(
        "tutor voice is muted or unavailable; lesson subtitles stay visible",
      );

      window.dispatchEvent(
        new CustomEvent("ipc.status.tick", {
          detail: {
            payload: {
              midi: 0,
              voice: "ok",
            },
          },
        }),
      );
      expect(controller.textContent).toBe("on-screen deck");
      expect(voice.textContent).toBe("voice ready");
      expect(voice.dataset.voiceStatus).toBe("ok");
      expect(voice.getAttribute("aria-label")).toBe("local tutor voice is ready");
    } finally {
      ws.close();
    }
  });

  it("free-practice screen deck emits an ack before a lesson starts", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const eq = await waitForMountedControl(root, "eq_hi:A");
      const booth = root.querySelector<HTMLElement>("#learn-booth-panel")!;
      const pulse = root.querySelector<HTMLElement>("#learn-booth-pulse")!;
      const reward = root.querySelector<HTMLElement>("#learn-booth-reward")!;
      const rewardFill = root.querySelector<HTMLElement>(
        "#learn-booth-reward-fill",
      )!;
      const chain = root.querySelector<HTMLElement>("#learn-booth-chain")!;
      const title = root.querySelector<HTMLElement>("#learn-booth-title")!;
      const start = root.querySelector<HTMLButtonElement>(
        "#learn-start-recommended",
      )!;

      mocks.emitIpc.mockClear();
      eq.dispatchEvent(new Event("pointerdown", { bubbles: true, cancelable: true }));

      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.ack", {
        control_id: "eq_hi:A",
        source: "click",
        value: 127,
        prev_value: 0,
        direction: "down",
      });
      expect(booth.dataset.visible).toBe("true");
      expect(pulse.textContent).toBe("screen: deck A high EQ");
      expect(pulse.getAttribute("aria-label")).toBe(
        "free practice screen move, deck A high EQ",
      );
      expect(title.textContent).toBe("channel strip");
      expect(start.textContent).toBe("start channel strip");
      expect(reward.dataset.visible).toBe("true");
      expect(reward.textContent).toContain("warmup 1/3");
      expect(rewardFill.style.width).toBe("33%");
      expect(reward.getAttribute("aria-label")).toContain(
        "no lesson credit awarded",
      );
      expect(chain.dataset.visible).toBe("true");
      expect(
        Array.from(chain.querySelectorAll<HTMLElement>(".learn-booth-chain__label"))
          .map((el) => el.textContent),
      ).toEqual(["warmup 1/3", "lock it in", "next route"]);
      expect(
        Array.from(chain.querySelectorAll<HTMLElement>(".learn-booth-chain__title"))
          .map((el) => el.textContent),
      ).toEqual(["screen: deck A high EQ", "channel strip", "crossfader"]);
      expect(chain.getAttribute("aria-label")).toContain(
        "warmup 1/3: screen: deck A high EQ",
      );

      mocks.emitIpc.mockClear();
      start.click();
      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.start_lesson", {
        lesson_id: "L1.03",
        level: "fresh",
      });
    } finally {
      ws.close();
    }
  });

  it("shows sandbox tutor feedback before a lesson starts", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.live_grade", {
          detail: {
            verdict: "drifting",
            phase_error_beats: 0.25,
            score: 0.5,
            citation: "[ev:BEATMATCH_GRADED@12.345]",
          },
        }),
      );
      window.dispatchEvent(
        new CustomEvent("ipc.learn.tutor_speak", {
          detail: {
            text: "nudge the jog, then hold the downbeat.",
            tts_marker: "practice.beatmatch.hint.1",
            citations: ["[ev:BEATMATCH_GRADED@12.345]"],
            data_state: "hint",
          },
        }),
      );

      const meter = root.querySelector<HTMLElement>("#learn-live-meter");
      const dock = root.querySelector<HTMLElement>(".tutor-dock");
      const booth = root.querySelector<HTMLElement>("#learn-booth-panel");
      expect(root.classList.contains("lesson-mode")).toBe(false);
      expect(booth?.dataset.visible).toBe("true");
      expect(meter?.dataset.state).toBe("active");
      expect(meter?.dataset.verdict).toBe("drifting");
      expect(dock?.dataset.state).toBe("hint");
      expect(dock?.textContent).toContain("nudge the jog, then hold the downbeat.");
      expect(dock?.textContent).toContain("EV BEATMATCH GRADED");
      expect(root.querySelector(".learn-skip")).toBeNull();
      expect(root.querySelector<HTMLElement>("#learn-sr-announcement")?.textContent).toBe(
        "nudge the jog, then hold the downbeat.",
      );
    } finally {
      ws.close();
    }
  });

  it("free-practice hardware deltas emit acks before a lesson starts", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const pulse = root.querySelector<HTMLElement>("#learn-booth-pulse")!;

      mocks.emitIpc.mockClear();
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

      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.ack", {
        control_id: "eq_hi:A",
        source: "midi",
        value: 127,
        prev_value: 0,
        direction: "down",
      });
      expect(pulse.textContent).toBe("hardware: deck A high EQ");
      expect(pulse.getAttribute("aria-label")).toBe(
        "free practice hardware move, deck A high EQ",
      );
    } finally {
      ws.close();
    }
  });

  it("free-practice screen drags emit continuous analog acks before a lesson starts", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const eq = await waitForMountedControl(root, "eq_hi:A");
      const pulse = root.querySelector<HTMLElement>("#learn-booth-pulse")!;

      mocks.emitIpc.mockClear();
      eq.dispatchEvent(
        new PointerEvent("pointerdown", {
          clientX: 120,
          clientY: 120,
          pointerId: 17,
        }),
      );
      window.dispatchEvent(
        new PointerEvent("pointermove", {
          clientX: 120,
          clientY: 96,
          pointerId: 17,
        }),
      );
      await nextAnimationFrame();
      window.dispatchEvent(
        new PointerEvent("pointermove", {
          clientX: 120,
          clientY: 72,
          pointerId: 17,
        }),
      );
      await nextAnimationFrame();
      window.dispatchEvent(new PointerEvent("pointerup", { pointerId: 17 }));

      const ackPayloads = mocks.emitIpc.mock.calls
        .filter(([type]) => type === "ipc.learn.ack")
        .map(([, payload]) => payload) as Array<{
          control_id: string;
          source: string;
          value: number;
          prev_value: number;
          direction: string;
        }>;

      expect(ackPayloads.length).toBeGreaterThanOrEqual(2);
      expect(ackPayloads).toEqual(
        expect.arrayContaining([
          {
            control_id: "eq_hi:A",
            source: "click",
            value: 82,
            prev_value: 64,
            direction: "down",
          },
          {
            control_id: "eq_hi:A",
            source: "click",
            value: 100,
            prev_value: 82,
            direction: "down",
          },
        ]),
      );
      expect(pulse.textContent).toBe("screen: deck A high EQ");
    } finally {
      ws.close();
    }
  });

  it("keyboard deck shortcuts drive free practice through the same ack path", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const pulse = root.querySelector<HTMLElement>("#learn-booth-pulse")!;
      const reward = root.querySelector<HTMLElement>("#learn-booth-reward")!;

      mocks.emitIpc.mockClear();
      window.dispatchEvent(
        new KeyboardEvent("keydown", {
          code: "Space",
          key: " ",
          bubbles: true,
          cancelable: true,
        }),
      );

      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.ack", {
        control_id: "play:A",
        source: "click",
        value: 127,
        prev_value: 0,
        direction: "down",
      });
      expect(pulse.textContent).toBe("screen: deck A play");

      mocks.emitIpc.mockClear();
      window.dispatchEvent(
        new KeyboardEvent("keydown", {
          code: "ArrowRight",
          key: "ArrowRight",
          bubbles: true,
          cancelable: true,
        }),
      );

      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.ack", {
        control_id: "jog:A",
        source: "click",
        value: 80,
        prev_value: 64,
        direction: "down",
      });
      expect(pulse.textContent).toBe("screen: deck A jog wheel");
      expect(
        root.querySelector<HTMLElement>("#learn-booth-title")?.textContent,
      ).toBe("jog wheel");
      expect(reward.textContent).toContain("warmup 2/3");

      mocks.emitIpc.mockClear();
      root.querySelector<HTMLButtonElement>("#learn-start-recommended")?.click();
      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.start_lesson", {
        lesson_id: "L1.07",
        level: "fresh",
      });
    } finally {
      ws.close();
    }
  });

  it("keyboard deck shortcuts do not hijack focused buttons", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const start = root.querySelector<HTMLButtonElement>("#learn-start-recommended")!;
      start.focus();

      mocks.emitIpc.mockClear();
      window.dispatchEvent(
        new KeyboardEvent("keydown", {
          code: "Space",
          key: " ",
          bubbles: true,
          cancelable: true,
        }),
      );

      expect(mocks.emitIpc).not.toHaveBeenCalledWith(
        "ipc.learn.ack",
        expect.anything(),
      );
    } finally {
      ws.close();
    }
  });

  it("mounts the live grade meter and updates it from the learn bus", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      await waitForMountedControl(root, "eq_hi:A");
      dispatchLessonLoaded("L2.01", "course_2_transitions");

      window.dispatchEvent(
        new CustomEvent("ipc.learn.live_grade", {
          detail: {
            verdict: "drifting",
            phase_error_beats: 0.25,
            score: 0.5,
            citation: null,
            save_attempt_active: true,
            save_floor_seconds_total: 14,
            save_floor_seconds_remaining: 8.5,
            save_difficulty_level: 2,
            save_streak: 1,
          },
        }),
      );

      const meter = root.querySelector<HTMLElement>("#learn-live-meter");
      const waveformHost = root.querySelector<HTMLElement>("#learn-waveform-host");
      expect(meter).not.toBeNull();
      expect(meter?.dataset.state).toBe("active");
      expect(meter?.dataset.verdict).toBe("drifting");
      expect(waveformHost?.dataset.gallop).toBe("behind");
      expect(waveformHost?.dataset.gallopPhase).toBe("0.2500");
      expect(waveformHost?.style.getPropertyValue("--gallop-shift")).toBe("24px");
      expect(meter?.dataset.saveActive).toBe("true");
      expect(meter?.dataset.saveRemaining).toBe("8.5");
      expect(meter?.querySelector(".learn-live-meter__save")?.textContent).toContain("L2");
      expect(meter?.querySelector(".learn-live-meter__save")?.textContent).toContain(
        "8.5s",
      );
      expect(meter?.querySelector(".learn-live-meter__save")?.textContent).toContain("x1");
      expect(Number(meter?.dataset.needlePct)).toBeGreaterThan(50);
      const hint = root.querySelector<HTMLElement>(".learn-status-hint")!;
      expect(hint.textContent).toBe("save 9s");
      expect(hint.dataset.practiceFeedback).toBe("correct");
      expect(hint.getAttribute("aria-label")).toContain(
        "save attempt active, 9s before the floor drops",
      );

      window.dispatchEvent(
        new CustomEvent("ipc.learn.live_grade", {
          detail: {
            verdict: "locked",
            phase_error_beats: 0,
            score: 1,
            citation: "[ev:BEATMATCH_GRADED@12.345]",
          },
        }),
      );

      expect(meter?.dataset.verdict).toBe("locked");
      expect(waveformHost?.dataset.gallop).toBe("locked");
      expect(waveformHost?.dataset.gallopSnap).toBe("true");
      expect(Number(meter?.dataset.needlePct)).toBe(50);
      expect(meter?.dataset.citation).toBe("[ev:BEATMATCH_GRADED@12.345]");
      expect(hint.textContent).toBe("locked proof");
      expect(hint.dataset.practiceFeedback).toBe("locked");
      expect(hint.getAttribute("aria-label")).toContain(
        "[ev:BEATMATCH_GRADED@12.345]",
      );
      expect(root.querySelector<HTMLElement>("#learn-booth-panel")?.dataset.visible).toBe(
        "false",
      );
    } finally {
      ws.close();
    }
  });

  it("turns trainwreck live grade into a visible recovery command", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      await waitForMountedControl(root, "eq_hi:A");
      dispatchLessonLoaded("L2.01", "course_2_transitions");

      window.dispatchEvent(
        new CustomEvent("ipc.learn.live_grade", {
          detail: {
            verdict: "trainwreck",
            phase_error_beats: -0.42,
            score: 0.05,
            citation: null,
          },
        }),
      );

      const hint = root.querySelector<HTMLElement>(".learn-status-hint")!;
      expect(hint.textContent).toBe("re-find the 1");
      expect(hint.dataset.practiceFeedback).toBe("danger");
      expect(hint.getAttribute("aria-label")).toContain("0.42 beat ahead");

      window.dispatchEvent(
        new CustomEvent("ipc.learn.live_grade", {
          detail: {
            verdict: "trainwreck",
            phase_error_beats: -0.42,
            score: 0.05,
            citation: null,
            save_floor_expired: true,
            save_floor_seconds_total: 14,
            save_floor_seconds_remaining: 0,
            save_difficulty_level: 2,
            save_streak: 0,
          },
        }),
      );

      const meter = root.querySelector<HTMLElement>("#learn-live-meter");
      expect(hint.textContent).toBe("floor dropped");
      expect(hint.dataset.practiceFeedback).toBe("danger");
      expect(hint.getAttribute("aria-label")).toContain("save window ended");
      expect(meter?.dataset.saveExpired).toBe("true");
      expect(meter?.querySelector(".learn-live-meter__receipt")?.textContent).toBe(
        "floor dropped",
      );
    } finally {
      ws.close();
    }
  });

  it("surfaces Course 3 live cue evidence as one quiet status phrase", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const hint = root.querySelector<HTMLElement>(".learn-status-hint")!;
      expect(hint.textContent).toMatch(/tab to deck/);

      window.dispatchEvent(
        new CustomEvent("learn.course3_lens", {
          detail: {
            session_active: true,
            phrase_position_confidence: 0,
            next_phrase_at: null,
            next_phrase_cue_id: null,
            audio_active: false,
            deck_attributed: false,
            deck_track_citable: false,
            cue_ready: false,
            blockers: [
              "waiting_for_audio",
              "waiting_for_deck",
              "waiting_for_deck_track",
              "waiting_for_cue",
            ],
          },
        }),
      );
      expect(hint.textContent).toBe("press play on deck");
      expect(hint.dataset.course3Lens).toBe("waiting-audio");
      expect(hint.dataset.operatorAction).toBe("active");
      expect(hint.getAttribute("aria-label")).toContain("routed master audio");
      expect(hint.getAttribute("aria-label")).toContain("Press play");
      expect(hint.getAttribute("title")).toContain("real Rekordbox library track");

      window.dispatchEvent(
        new CustomEvent("learn.course3_lens", {
          detail: {
            session_active: false,
            phrase_position_confidence: 0,
            next_phrase_at: null,
            next_phrase_cue_id: null,
            audio_active: true,
            deck_attributed: false,
            deck_track_citable: false,
            cue_ready: false,
            blockers: ["waiting_for_deck", "waiting_for_deck_track", "waiting_for_cue"],
          },
        }),
      );
      expect(hint.textContent).toBe("open one channel");
      expect(hint.dataset.course3Lens).toBe("waiting-deck");
      expect(hint.getAttribute("aria-label")).toContain("Open one deck channel");
      expect(hint.dataset.operatorAction).toBe("active");

      window.dispatchEvent(
        new CustomEvent("learn.course3_lens", {
          detail: {
            session_active: false,
            phrase_position_confidence: 0,
            next_phrase_at: null,
            next_phrase_cue_id: null,
            audio_active: true,
            deck_attributed: true,
            deck_track_citable: false,
            cue_ready: false,
            blockers: ["waiting_for_deck_track", "waiting_for_cue"],
          },
        }),
      );
      expect(hint.textContent).toBe("load a track");
      expect(hint.dataset.course3Lens).toBe("waiting-track");
      expect(hint.getAttribute("aria-label")).toContain("Load a track");
      expect(hint.getAttribute("title")).toContain("coach can cite it");

      window.dispatchEvent(
        new CustomEvent("learn.course3_lens", {
          detail: {
            session_active: true,
            phrase_position_confidence: 0.42,
            next_phrase_at: null,
            next_phrase_cue_id: null,
            audio_active: true,
            deck_attributed: true,
            deck_track_citable: true,
            cue_ready: false,
            blockers: ["waiting_for_cue"],
          },
        }),
      );
      expect(hint.textContent).toBe("keep playing");
      expect(hint.dataset.course3Lens).toBe("listening");
      expect(hint.getAttribute("aria-label")).toContain("Keep playing");
      expect(hint.getAttribute("title")).toContain("cue-section lookahead");

      window.dispatchEvent(
        new CustomEvent("learn.course3_lens", {
          detail: {
            session_active: true,
            phrase_position_confidence: 0.91,
            next_phrase_at: 128.5,
            next_phrase_cue_id: "cue:track-a:phrase",
            audio_active: true,
            deck_attributed: true,
            deck_track_citable: true,
            cue_ready: true,
            blockers: [],
          },
        }),
      );
      expect(hint.textContent).toBe("phrase cue locked");
      expect(hint.dataset.course3Lens).toBe("armed");

      window.dispatchEvent(
        new CustomEvent("learn.course3_lens", {
          detail: {
            session_active: false,
            phrase_position_confidence: 0,
            next_phrase_at: null,
            next_phrase_cue_id: null,
            audio_active: false,
            deck_attributed: false,
            deck_track_citable: false,
            cue_ready: false,
            blockers: [
              "waiting_for_audio",
              "waiting_for_deck",
              "waiting_for_deck_track",
              "waiting_for_cue",
            ],
          },
        }),
      );
      expect(hint.textContent).toMatch(/tab to deck/);
      expect(hint.dataset.course3Lens).toBe("cold");
      expect(hint.dataset.operatorAction).toBe("none");
    } finally {
      ws.close();
    }
  });

  it("keeps Course 3 waiting-audio copy active while the deck is silent", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const hint = root.querySelector<HTMLElement>(".learn-status-hint")!;
      dispatchLessonLoaded("L3.01", "course_3_play_mode");

      window.dispatchEvent(
        new CustomEvent("learn.course3_lens", {
          detail: {
            session_active: false,
            phrase_position_confidence: 0,
            next_phrase_at: null,
            next_phrase_cue_id: null,
            audio_active: false,
            deck_attributed: false,
            deck_track_citable: false,
            cue_ready: false,
            blockers: [
              "waiting_for_audio",
              "waiting_for_deck",
              "waiting_for_deck_track",
              "waiting_for_cue",
            ],
          },
        }),
      );

      expect(hint.textContent).toBe("press play on deck");
      expect(hint.dataset.course3Lens).toBe("waiting-audio");
      expect(hint.getAttribute("aria-label")).toContain("routed master audio");
      expect(hint.getAttribute("title")).toContain("real Rekordbox library track");

      window.dispatchEvent(
        new CustomEvent("ipc.learn.complete_lesson", {
          detail: {
            lesson_id: "L3.01",
            reason: "completed",
          },
        }),
      );

      expect(hint.textContent).toMatch(/tab to deck/);
      expect(hint.dataset.course3Lens).toBe("cold");
    } finally {
      ws.close();
    }
  });

  it("collapses a structured Course 3 operator action into one booth prompt", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const hint = root.querySelector<HTMLElement>(".learn-status-hint")!;
      dispatchLessonLoaded("L3.01", "course_3_play_mode");

      window.dispatchEvent(
        new CustomEvent("learn.course3_lens", {
          detail: {
            session_active: false,
            phrase_position_confidence: 0,
            next_phrase_at: null,
            next_phrase_cue_id: null,
            audio_active: false,
            deck_attributed: false,
            deck_track_citable: false,
            cue_ready: false,
            blockers: ["waiting_for_audio", "waiting_for_cue"],
            operator_action: {
              prompt:
                "Play a real Rekordbox library track through BlackHole 2ch @ 48000Hz with channel and master faders up.",
              route: "BlackHole 2ch @ 48000Hz",
              steps: [
                "Stop unrelated media or make Rekordbox the active playing source.",
                "Raise the playing channel fader and master until loopback capture has signal.",
              ],
            },
          },
        }),
      );

      expect(hint.textContent).toBe("play Rekordbox through BlackHole 2ch");
      expect(hint.dataset.course3Lens).toBe("operator-action");
      expect(hint.dataset.operatorAction).toBe("active");
      expect(hint.getAttribute("aria-label")).toContain(
        "Play a real Rekordbox library track",
      );
      expect(hint.getAttribute("title")).toContain("Stop unrelated media");
    } finally {
      ws.close();
    }
  });

  it("keeps a Course 3 aggregate rate fix precise in the booth status line", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const hint = root.querySelector<HTMLElement>(".learn-status-hint")!;
      dispatchLessonLoaded("L3.01", "course_3_play_mode");

      window.dispatchEvent(
        new CustomEvent("learn.course3_lens", {
          detail: {
            session_active: false,
            phrase_position_confidence: 0,
            next_phrase_at: null,
            next_phrase_cue_id: null,
            audio_active: false,
            deck_attributed: false,
            deck_track_citable: false,
            cue_ready: false,
            blockers: ["waiting_for_audio", "waiting_for_cue"],
            operator_action: {
              prompt:
                "Set Rekordbox's 'Aggregate Device' route, sampled as 'rekordbox Aggregate Device', from 44100Hz to 48000Hz in Audio MIDI Setup.",
              route: "rekordbox Aggregate Device @ 48000Hz",
              steps: [
                "Set Rekordbox's 'Aggregate Device' route, sampled as 'rekordbox Aggregate Device', from 44100Hz to 48000Hz in Audio MIDI Setup.",
                "Play a real Rekordbox library track through the routed master output.",
              ],
            },
          },
        }),
      );

      expect(hint.textContent).toBe("set aggregate route to 48k");
      expect(hint.dataset.course3Lens).toBe("operator-action");
      expect(hint.dataset.operatorAction).toBe("active");
      expect(hint.getAttribute("aria-label")).toContain("44100Hz to 48000Hz");
      expect(hint.getAttribute("title")).toContain(
        "rekordbox Aggregate Device @ 48000Hz",
      );
    } finally {
      ws.close();
    }
  });

  it("keeps a Course 3 route mismatch as one calm booth fix", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const hint = root.querySelector<HTMLElement>(".learn-status-hint")!;
      dispatchLessonLoaded("L3.01", "course_3_play_mode");

      window.dispatchEvent(
        new CustomEvent("learn.course3_lens", {
          detail: {
            session_active: false,
            phrase_position_confidence: 0,
            next_phrase_at: null,
            next_phrase_cue_id: null,
            audio_active: false,
            deck_attributed: false,
            deck_track_citable: false,
            cue_ready: false,
            blockers: ["waiting_for_audio", "waiting_for_cue"],
            operator_action: {
              prompt:
                "Set Rekordbox audio to BlackHole 16ch @ 48000Hz, then play a real library track with channel and master faders up.",
              route: "BlackHole 16ch @ 48000Hz",
              current_rekordbox_route: "DDJ-FLX4 @ 48000Hz",
              target_capture_route: "BlackHole 16ch @ 48000Hz",
              route_mismatch: true,
              steps: [
                "In Rekordbox Audio preferences, set the audio output from DDJ-FLX4 @ 48000Hz to BlackHole 16ch @ 48000Hz.",
              ],
            },
          },
        }),
      );

      expect(hint.textContent).toBe("route Rekordbox to BlackHole 16ch");
      expect(hint.dataset.course3Lens).toBe("operator-action");
      expect(hint.dataset.operatorAction).toBe("active");
      expect(hint.getAttribute("aria-label")).toContain(
        "current Rekordbox route: DDJ-FLX4 @ 48000Hz",
      );
      expect(hint.getAttribute("title")).toContain(
        "target capture route: BlackHole 16ch @ 48000Hz",
      );
    } finally {
      ws.close();
    }
  });

  it("lets future Learn checks publish a generic one-action booth prompt", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const hint = root.querySelector<HTMLElement>(".learn-status-hint")!;

      window.dispatchEvent(
        new CustomEvent("learn.operator_action", {
          detail: {
            prompt: "Listen to the four EQ exemplar loops on MacBook Pro Speakers.",
            recommended_output_devices: [
              { index: 4, name: "MacBook Pro Speakers", score: 102 },
            ],
            steps: [
              "uv run python scripts/audition_learn_exemplars.py --play --device-index 4",
            ],
          },
        }),
      );

      expect(hint.textContent).toBe("audition EQ examples on MacBook Pro Speakers");
      expect(hint.dataset.course3Lens).toBe("external-action");
      expect(hint.dataset.operatorAction).toBe("active");
      expect(hint.getAttribute("aria-label")).toContain("--device-index 4");

      window.dispatchEvent(new CustomEvent("learn.operator_action", { detail: null }));
      expect(hint.textContent).toMatch(/tab to deck/);
      expect(hint.dataset.operatorAction).toBe("none");
    } finally {
      ws.close();
    }
  });

  it("choose lesson opens and closes the practice map", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const map = root.querySelector<HTMLElement>("#learn-progress-list-host")!;
      const openButton = root.querySelector<HTMLButtonElement>("#learn-open-map")!;
      expect(openButton.getAttribute("aria-controls")).toBe(
        "learn-progress-list-host",
      );
      expect(openButton.getAttribute("aria-expanded")).toBe("false");
      openButton.click();
      expect(map.dataset.visible).toBe("true");
      expect(map.getAttribute("aria-hidden")).toBe("false");
      expect(openButton.getAttribute("aria-expanded")).toBe("true");
      expect(document.activeElement).toBe(
        root.querySelector<HTMLButtonElement>(
          ".vmx-progress-list__lesson[data-recommended='true']",
        ),
      );
      root.querySelector<HTMLButtonElement>("#learn-close-map")!.click();
      expect(map.dataset.visible).toBe("false");
      expect(map.getAttribute("aria-hidden")).toBe("true");
      expect(openButton.getAttribute("aria-expanded")).toBe("false");
      expect(document.activeElement).toBe(openButton);

      openButton.click();
      mocks.emitIpc.mockClear();
      root.querySelector<HTMLButtonElement>(
        ".vmx-progress-list__lesson[data-recommended='true']",
      )!.click();
      expect(map.dataset.visible).toBe("false");
      expect(map.getAttribute("aria-hidden")).toBe("true");
      expect(openButton.getAttribute("aria-expanded")).toBe("false");
      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.start_lesson", {
        lesson_id: "L1.01",
        level: "fresh",
      });
    } finally {
      ws.close();
    }
  });

  it("emits start_course from the dev automation event", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const map = root.querySelector<HTMLElement>("#learn-progress-list-host")!;
      const openButton = root.querySelector<HTMLButtonElement>("#learn-open-map")!;
      openButton.click();
      expect(map.dataset.visible).toBe("true");

      mocks.emitIpc.mockClear();
      window.dispatchEvent(
        new CustomEvent("learn.start_course", {
          detail: { course_id: "course_2_transitions" },
        }),
      );

      expect(map.dataset.visible).toBe("false");
      expect(map.getAttribute("aria-hidden")).toBe("true");
      expect(openButton.getAttribute("aria-expanded")).toBe("false");
      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.start_course", {
        course_id: "course_2",
        controller_id: "pioneer_ddj_flx4",
      });
    } finally {
      ws.close();
    }
  });

  it("escape closes the practice map and returns focus", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const map = root.querySelector<HTMLElement>("#learn-progress-list-host")!;
      const openButton = root.querySelector<HTMLButtonElement>("#learn-open-map")!;
      openButton.click();
      expect(map.dataset.visible).toBe("true");
      expect(openButton.getAttribute("aria-expanded")).toBe("true");

      map.dispatchEvent(
        new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
      );

      expect(map.dataset.visible).toBe("false");
      expect(map.getAttribute("aria-hidden")).toBe("true");
      expect(openButton.getAttribute("aria-expanded")).toBe("false");
      expect(document.activeElement).toBe(openButton);
    } finally {
      ws.close();
    }
  });

  it("progress snapshots move the next-practice button without unlocking future courses", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
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

      const locked = root.querySelector<HTMLButtonElement>(
        "[data-lesson-id='L2.01']",
      );
      expect(locked?.dataset.locked).toBe("true");

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

  it("lessonId query starts the referred lesson after progress proves it is unlocked", () => {
    window.history.replaceState(null, "", "/learn.html?lessonId=L2.01");
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      expect(mocks.emitIpc).not.toHaveBeenCalledWith(
        "ipc.learn.start_lesson",
        expect.objectContaining({ lesson_id: "L2.01" }),
      );

      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "snapshot",
            progress: {
              schema_version: 1,
              courses: {},
              lessons: completedRows(COURSE_1_LESSON_IDS),
              course_2_unlocked: true,
              course_3_unlocked: false,
            },
          },
        }),
      );

      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.start_lesson", {
        lesson_id: "L2.01",
        level: "fresh",
      });
    } finally {
      ws.close();
    }
  });

  it("locked lesson picks surface the unlock reason without starting", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
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

      const locked = root.querySelector<HTMLButtonElement>(
        "[data-lesson-id='L2.01']",
      )!;
      const pulse = root.querySelector<HTMLElement>("#learn-booth-pulse")!;

      mocks.emitIpc.mockClear();
      locked.click();

      expect(mocks.emitIpc).not.toHaveBeenCalledWith(
        "ipc.learn.start_lesson",
        expect.objectContaining({ lesson_id: "L2.01" }),
      );
      expect(pulse.textContent).toBe("finish the course 1 check to unlock transitions");
      expect(pulse.dataset.state).toBe("idle");
    } finally {
      ws.close();
    }
  });

  it("turns a completed lesson into a small next-practice reward", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded();
      window.dispatchEvent(
        new CustomEvent("ipc.learn.advance", {
          detail: {
            lesson_id: "L1.01",
            reason: "action_matched",
          },
        }),
      );
      window.dispatchEvent(
        new CustomEvent("ipc.learn.complete_lesson", {
          detail: {
            lesson_id: "L1.01",
            reason: "completed",
          },
        }),
      );

      const booth = root.querySelector<HTMLElement>("#learn-booth-panel")!;
      const pulse = root.querySelector<HTMLElement>("#learn-booth-pulse")!;
      expect(booth.dataset.visible).toBe("true");
      expect(pulse.dataset.state).toBe("success");
      expect(pulse.textContent).toBe(
        "clean pass · 1 move · next: start meet your controller",
      );
      expect(pulse.getAttribute("aria-label")).toBe(
        "clean pass · 1 move. next practice: start meet your controller",
      );
      expect(pulse.getAttribute("title")).toBe(
        "clean pass · 1 move. next practice: start meet your controller",
      );
      expect(
        root.querySelector<HTMLButtonElement>("#learn-start-recommended")
          ?.textContent,
      ).toMatch(/start meet your controller/i);
    } finally {
      ws.close();
    }
  });

  it("folds the screen-deck source into the clean-pass reward", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded();
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
        new CustomEvent("ipc.learn.advance", {
          detail: {
            lesson_id: "L1.01",
            reason: "action_matched",
          },
        }),
      );
      window.dispatchEvent(
        new CustomEvent("ipc.learn.complete_lesson", {
          detail: {
            lesson_id: "L1.01",
            reason: "completed",
          },
        }),
      );

      const pulse = root.querySelector<HTMLElement>("#learn-booth-pulse")!;
      expect(pulse.textContent).toBe(
        "clean pass · screen · 1 move · next: start meet your controller",
      );
      expect(pulse.getAttribute("aria-label")).toBe(
        "clean pass · screen · 1 move. next practice: start meet your controller",
      );
    } finally {
      ws.close();
    }
  });

  it("folds the hardware source into the clean-pass reward", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded("L1.03", "course_1_anatomy");
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

      mocks.emitIpc.mockClear();
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
      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.ack", {
        control_id: "eq_hi:A",
        source: "midi",
        value: 127,
        prev_value: 0,
        direction: "down",
      });

      window.dispatchEvent(
        new CustomEvent("ipc.learn.advance", {
          detail: {
            lesson_id: "L1.03",
            reason: "action_matched",
          },
        }),
      );
      window.dispatchEvent(
        new CustomEvent("ipc.learn.complete_lesson", {
          detail: {
            lesson_id: "L1.03",
            reason: "completed",
          },
        }),
      );

      const pulse = root.querySelector<HTMLElement>("#learn-booth-pulse")!;
      expect(pulse.textContent).toContain("clean pass · hardware · 1 move · next:");
      expect(pulse.getAttribute("aria-label")).toContain(
        "clean pass · hardware · 1 move. next practice:",
      );
    } finally {
      ws.close();
    }
  });

  it("names a hinted completion as a recovered pass", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded("L1.03", "course_1_anatomy");
      window.dispatchEvent(
        new CustomEvent("ipc.learn.highlight", {
          detail: {
            control_id: "eq_mid",
            deck: "A",
            cue_color: "warning",
            cue_shape: "pulse-ring",
            annotation: "move deck A mid EQ.",
            expected_action: {
              type: "cc",
              control: "eq_mid",
              deck: "A",
              direction: "down",
              min_delta: 38,
            },
          },
        }),
      );
      window.dispatchEvent(
        new CustomEvent("ipc.learn.tutor_speak", {
          detail: {
            text: "same deck, mid EQ.",
            tts_marker: "L1.03.hint.1",
            citations: ["[screen:eq_mid:A]"],
            data_state: "hint",
          },
        }),
      );

      mocks.emitIpc.mockClear();
      const control = await waitForMountedControl(root, "eq_mid:A");
      control.dispatchEvent(
        new Event("pointerdown", { bubbles: true, cancelable: true }),
      );
      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.ack", {
        control_id: "eq_mid:A",
        source: "click",
        value: 127,
        prev_value: 0,
        direction: "down",
      });

      window.dispatchEvent(
        new CustomEvent("ipc.learn.advance", {
          detail: {
            lesson_id: "L1.03",
            reason: "action_matched",
          },
        }),
      );
      window.dispatchEvent(
        new CustomEvent("ipc.learn.complete_lesson", {
          detail: {
            lesson_id: "L1.03",
            reason: "completed",
          },
        }),
      );

      const pulse = root.querySelector<HTMLElement>("#learn-booth-pulse")!;
      expect(pulse.textContent).toContain("recovered pass · screen · 1 move · next:");
      expect(pulse.getAttribute("aria-label")).toContain(
        "recovered pass · screen · 1 move. next practice:",
      );
    } finally {
      ws.close();
    }
  });

  it("names mixed hardware and screen completions without a stat panel", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded("L1.03", "course_1_anatomy");
      window.dispatchEvent(
        new CustomEvent("ipc.learn.highlight", {
          detail: {
            control_id: "eq_mid",
            deck: "A",
            cue_color: "amber",
            cue_shape: "pulse-ring",
            annotation: "move deck A mid EQ.",
            expected_action: {
              type: "cc",
              control: "eq_mid",
              deck: "A",
              direction: "down",
              min_delta: 38,
            },
          },
        }),
      );

      const screenControl = await waitForMountedControl(root, "eq_mid:A");
      screenControl.dispatchEvent(
        new Event("pointerdown", { bubbles: true, cancelable: true }),
      );
      window.dispatchEvent(
        new CustomEvent("ipc.learn.advance", {
          detail: {
            lesson_id: "L1.03",
            reason: "action_matched",
          },
        }),
      );

      window.dispatchEvent(
        new CustomEvent("ipc.learn.highlight", {
          detail: {
            control_id: "eq_hi",
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
      window.dispatchEvent(
        new CustomEvent("ipc.learn.complete_lesson", {
          detail: {
            lesson_id: "L1.03",
            reason: "completed",
          },
        }),
      );

      const pulse = root.querySelector<HTMLElement>("#learn-booth-pulse")!;
      expect(pulse.textContent).toContain(
        "clean pass · hardware + screen · 2 moves · next:",
      );
      expect(pulse.getAttribute("aria-label")).toContain(
        "clean pass · hardware + screen · 2 moves. next practice:",
      );
    } finally {
      ws.close();
    }
  });

  it("progress snapshots keep the lesson map opt-in", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const map = root.querySelector<HTMLElement>("#learn-progress-list-host")!;
      const booth = root.querySelector<HTMLElement>("#learn-booth-panel")!;
      const pulse = root.querySelector<HTMLElement>("#learn-booth-pulse")!;
      root.querySelector<HTMLButtonElement>("#learn-open-map")!.click();
      expect(map.dataset.visible).toBe("true");
      root.querySelector<HTMLButtonElement>("#learn-close-map")!.click();
      expect(map.dataset.visible).toBe("false");

      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "snapshot",
            progress: {
              schema_version: 1,
              courses: {},
              lessons: {
                "L1.01": { completed: true },
                "L1.02": { completed: false, strikes_used: 1 },
              },
              course_2_unlocked: false,
              course_3_unlocked: false,
            },
          },
        }),
      );

      expect(booth.dataset.visible).toBe("true");
      expect(map.dataset.visible).toBe("false");
      expect(map.getAttribute("aria-hidden")).toBe("true");
      expect(
        root.querySelector<HTMLButtonElement>("#learn-start-recommended")
          ?.textContent,
      ).toMatch(/retry meet your controller/i);
      expect(pulse.textContent).toBe("hint ready for retry");
      expect(pulse.getAttribute("aria-label")).toBe(
        "retry meet your controller. last attempt used 1 hint; retry starts fresh.",
      );
      expect(pulse.getAttribute("title")).toBe(
        "retry meet your controller. last attempt used 1 hint; retry starts fresh.",
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

  it("reset acknowledgements clear stale recommendations in the booth", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const map = root.querySelector<HTMLElement>("#learn-progress-list-host")!;
      const booth = root.querySelector<HTMLElement>("#learn-booth-panel")!;
      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "snapshot",
            progress: {
              schema_version: 2,
              courses: {},
              lessons: {
                "L1.01": { completed: true },
                "L1.02": { completed: true },
              },
              course_2_unlocked: false,
              course_3_unlocked: false,
            },
          },
        }),
      );
      expect(
        root.querySelector<HTMLButtonElement>("#learn-start-recommended")
          ?.textContent,
      ).toMatch(/start channel strip/i);

      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "reset_ack",
            progress: {
              schema_version: 2,
              courses: {},
              lessons: {},
              course_2_unlocked: false,
              course_3_unlocked: false,
            },
          },
        }),
      );

      expect(booth.dataset.visible).toBe("true");
      expect(map.dataset.visible).toBe("false");
      expect(map.getAttribute("aria-hidden")).toBe("true");
      expect(
        root.querySelector<HTMLButtonElement>("#learn-start-recommended")
          ?.textContent,
      ).toMatch(/start opening dialog/i);
      expect(
        root.querySelector<HTMLButtonElement>("[data-lesson-id='L2.01']")
          ?.dataset.locked,
      ).toBe("true");
    } finally {
      ws.close();
    }
  });

  it("controller unplug falls back to the screen deck without changing the booth shape", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.controller_detected", {
          detail: {
            connected: true,
            controller_id: "pioneer_ddj_flx4",
            display_name: "Pioneer DDJ-FLX4",
            port_name: "DDJ-FLX4",
          },
        }),
      );
      await waitForMountedControl(root, "eq_hi:A");
      expect(root.textContent).toContain(
        "do the move on your FLX4 and I'll confirm it",
      );

      window.dispatchEvent(
        new CustomEvent("ipc.learn.controller_detected", {
          detail: {
            connected: false,
            controller_id: "pioneer_ddj_flx4",
            display_name: "Pioneer DDJ-FLX4",
            port_name: "DDJ-FLX4",
          },
        }),
      );
      await waitForMountedControl(root, "eq_hi:A");

      const booth = root.querySelector<HTMLElement>("#learn-booth-panel")!;
      const map = root.querySelector<HTMLElement>("#learn-progress-list-host")!;
      const status = root.querySelector<HTMLElement>(".learn-status-controller")!;
      expect(booth.dataset.visible).toBe("true");
      expect(map.dataset.visible).toBe("false");
      expect(map.getAttribute("aria-hidden")).toBe("true");
      expect(status.textContent).toBe("on-screen deck");
      expect(root.textContent).toContain(
        "your controller's connected, do the move and I'll confirm it",
      );
      expect(root.querySelector('[data-control-id="eq_hi:A"]')).not.toBeNull();
      expect(
        Array.from(booth.querySelectorAll("button")).map((button) => button.id),
      ).toEqual(["learn-start-recommended", "learn-open-map"]);

      root.querySelector<HTMLButtonElement>("#learn-open-map")!.click();
      expect(
        root.querySelector<HTMLElement>(".vmx-progress-list__no-controller")
          ?.textContent,
      ).toBe("screen deck is ready");
      root.querySelector<HTMLButtonElement>("#learn-close-map")!.click();

      mocks.emitIpc.mockClear();
      root.querySelector<HTMLButtonElement>("#learn-start-recommended")!.click();
      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.start_lesson", {
        lesson_id: "L1.01",
        level: "fresh",
      });
    } finally {
      ws.close();
    }
  });

  it("keeps the current lesson action alive after a mid-lesson unplug", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded("L1.06", "course_1_anatomy");
      window.dispatchEvent(
        new CustomEvent("ipc.learn.highlight", {
          detail: {
            control_id: "play",
            deck: "A",
            cue_color: "amber",
            cue_shape: "pulse-ring",
            annotation: "press play",
            expected_action: {
              type: "button",
              control: "play",
              deck: "A",
              direction: "down",
            },
          },
        }),
      );

      const firstTarget = await waitForMountedControl(root, "play:A");
      expect(firstTarget.getAttribute("data-cue-color")).toBe("amber");

      window.dispatchEvent(
        new CustomEvent("ipc.learn.controller_detected", {
          detail: {
            connected: false,
            controller_id: "pioneer_ddj_flx4",
            display_name: "Pioneer DDJ-FLX4",
            port_name: "DDJ-FLX4",
          },
        }),
      );

      expect(root.querySelector('[data-control-id="play:A"]')).not.toBeNull();

      const remountedTarget = await waitForMountedControl(root, "play:A");
      await vi.waitFor(() => {
        expect(remountedTarget.getAttribute("data-cue-color")).toBe("amber");
        expect(remountedTarget.getAttribute("data-cue-shape")).toBe("pulse-ring");
      });
      expect(
        root.querySelector<HTMLElement>(".learn-status-controller")?.textContent,
      ).toBe("on-screen deck");
      expect(
        root.querySelector<HTMLButtonElement>("#learn-screen-action")?.hidden,
      ).toBe(true);

      mocks.emitIpc.mockClear();
      remountedTarget.dispatchEvent(
        new Event("pointerdown", { bubbles: true, cancelable: true }),
      );
      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.ack", {
        control_id: "play:A",
        source: "click",
        value: 127,
        prev_value: 0,
        direction: "down",
      });
    } finally {
      ws.close();
    }
  });

  it("complete_lesson moves the booth recommendation before the snapshot arrives", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "snapshot",
            progress: {
              schema_version: 2,
              courses: {},
              lessons: {},
              course_2_unlocked: false,
              course_3_unlocked: false,
              next_practice_mission: {
                lesson_id: "L1.01",
                course_id: "course_1_anatomy",
                course_label: "Course 1 · Anatomy",
                skill_id: "deck_control",
                skill_label: "deck control",
                title: "opening dialog",
                mode: "start",
                command: "Practice opening dialog; start the booth.",
                payoff: "You get the first rep moving.",
                proof: "screen deck is enough.",
                why: "This is the first unlocked move.",
                estimated_minutes: 4,
                focus: "first_rep",
                focus_label: "first rep",
                challenge: "Do one move.",
                meter_label: "first rep",
                meter_value: 0,
                meter_max: 1,
                meter_state: "armed",
                meter_caption: "touch the control to begin",
              },
            },
          },
        }),
      );
      window.dispatchEvent(
        new CustomEvent("ipc.learn.lesson_loaded", {
          detail: {
            course_id: "course_1_anatomy",
            lesson_id: "L1.01",
            title: "opening dialog",
            controller_id: "pioneer_ddj_flx4",
            progress_dots: [],
          },
        }),
      );

      window.dispatchEvent(
        new CustomEvent("ipc.learn.complete_lesson", {
          detail: {
            lesson_id: "L1.01",
            reason: "completed",
          },
        }),
      );

      const booth = root.querySelector<HTMLElement>("#learn-booth-panel")!;
      const recommended = root.querySelector<HTMLButtonElement>(
        "#learn-start-recommended",
      )!;
      expect(booth.dataset.visible).toBe("true");
      expect(recommended.textContent).toMatch(/start meet your controller/i);
      expect(
        root.querySelector<HTMLElement>("#learn-booth-pulse")?.getAttribute(
          "aria-label",
        ),
      ).toContain("next practice: start meet your controller");

      mocks.emitIpc.mockClear();
      recommended.click();
      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.start_lesson", {
        lesson_id: "L1.02",
        level: "fresh",
      });
    } finally {
      ws.close();
    }
  });

  it("labels the primary booth action as replay when only completed lessons are available", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "snapshot",
            progress: {
              schema_version: 1,
              courses: {},
              lessons: completedRows(COURSE_1_LESSON_IDS),
              course_2_unlocked: false,
              course_3_unlocked: false,
            },
          },
        }),
      );

      const recommended = root.querySelector<HTMLButtonElement>(
        "#learn-start-recommended",
      )!;
      expect(recommended.textContent).toMatch(/replay opening dialog/i);

      mocks.emitIpc.mockClear();
      recommended.click();
      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.start_lesson", {
        lesson_id: "L1.01",
        level: "replay",
      });
    } finally {
      ws.close();
    }
  });

  it("lets the backend mission drive booth copy and the primary lesson", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "snapshot",
            progress: {
              schema_version: 2,
              courses: {},
              lessons: completedRows(["L1.01", "L1.02"]),
              course_2_unlocked: false,
              course_3_unlocked: false,
              next_practice_mission: {
                lesson_id: "L1.03",
                course_id: "course_1_anatomy",
                course_label: "Course 1 · Anatomy",
                skill_id: "deck_control",
                skill_label: "deck control",
                title: "channel strip",
                mode: "start",
                command: "Practice channel strip; build one useful deck control rep.",
                payoff: "You learn which part of the track each band changes.",
                proof: "Learn waits for a real deck control move",
                why: "Finish the lessons to reach Competent",
                estimated_minutes: 4,
                focus: "first_rep",
                focus_label: "first rep",
                challenge: "Touch the control before you read ahead.",
                chain: [
                  {
                    lesson_id: "L1.03",
                    course_id: "course_1_anatomy",
                    course_label: "Course 1 · Anatomy",
                    title: "channel strip",
                    state: "now",
                    mode: "start",
                    label: "first rep",
                  },
                  {
                    lesson_id: "L1.04",
                    course_id: "course_1_anatomy",
                    course_label: "Course 1 · Anatomy",
                    title: "crossfader",
                    state: "next",
                    mode: "start",
                    label: "next rep",
                  },
                  {
                    lesson_id: "L1.05",
                    course_id: "course_1_anatomy",
                    course_label: "Course 1 · Anatomy",
                    title: "pitch fader",
                    state: "next",
                    mode: "start",
                    label: "next rep",
                  },
                ],
                meter_label: "first rep",
                meter_value: 0,
                meter_max: 1,
                meter_state: "armed",
                meter_caption: "touch the control to begin",
              },
            },
          },
        }),
      );

      expect(root.querySelector<HTMLElement>("#learn-booth-title")?.textContent).toBe(
        "channel strip",
      );
      expect(
        root.querySelector<HTMLElement>("#learn-booth-command-text")?.textContent,
      ).toBe("Practice channel strip; build one useful deck control rep.");
      expect(root.querySelector<HTMLElement>("#learn-booth-proof")?.textContent).toBe(
        "Learn waits for a real deck control move",
      );
      expect(root.querySelector<HTMLElement>("#learn-booth-pulse")?.textContent).toBe(
        "first rep",
      );
      const reward = root.querySelector<HTMLElement>("#learn-booth-reward")!;
      expect(reward.dataset.visible).toBe("true");
      expect(reward.dataset.state).toBe("armed");
      expect(
        root.querySelector<HTMLElement>("#learn-booth-reward-label")?.textContent,
      ).toBe("first rep 0/1");
      expect(
        root.querySelector<HTMLElement>("#learn-booth-reward-caption")?.textContent,
      ).toBe("touch the control to begin");
      expect(
        root.querySelector<HTMLElement>("#learn-booth-reward-fill")?.style.width,
      ).toBe("0%");
      const chain = Array.from(
        root.querySelectorAll<HTMLElement>(".learn-booth-chain__step"),
      );
      expect(root.querySelector<HTMLElement>("#learn-booth-chain")?.dataset.visible).toBe(
        "true",
      );
      expect(chain.map((step) => step.dataset.state)).toEqual(["now", "next", "next"]);
      expect(chain.map((step) => step.dataset.lessonId)).toEqual([
        "L1.03",
        "L1.04",
        "L1.05",
      ]);
      expect(chain[0]?.textContent).toContain("first rep");
      expect(chain[1]?.textContent).toContain("crossfader");
      expect(
        root.querySelector<HTMLElement>("#learn-booth-pulse")?.getAttribute("aria-label"),
      ).toContain("Touch the control before you read ahead.");
      expect(
        root.querySelector<HTMLElement>("#learn-booth-pulse")?.getAttribute("title"),
      ).toContain("You learn which part of the track each band changes.");
      expect(
        root.querySelector<HTMLElement>(
          ".vmx-progress-list__lesson[data-recommended='true']",
        )?.textContent,
      ).toContain("channel strip");

      mocks.emitIpc.mockClear();
      root.querySelector<HTMLButtonElement>("#learn-start-recommended")!.click();
      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.start_lesson", {
        lesson_id: "L1.03",
        level: "fresh",
      });
    } finally {
      ws.close();
    }
  });

  it("renders banked practice labels inside the booth run chain", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "snapshot",
            progress: {
              schema_version: 2,
              courses: {},
              lessons: {},
              course_2_unlocked: false,
              course_3_unlocked: false,
              next_practice_mission: {
                lesson_id: "L1.03",
                course_id: "course_1_anatomy",
                course_label: "Course 1 · Anatomy",
                skill_id: "deck_control",
                skill_label: "deck control",
                title: "channel strip",
                mode: "finish",
                command: "Finish channel strip; repeat the banked move.",
                payoff: "Your hands learn where the booth lives before the music gets busy.",
                proof: "screen deck has worked; repeat it cleanly",
                why: "1 banked practice rep; finish the matching lesson to keep it",
                estimated_minutes: 4,
                focus: "first_rep",
                focus_label: "practice bank 1/3",
                challenge: "Repeat a banked move inside the lesson.",
                chain: [
                  {
                    lesson_id: "L1.03",
                    course_id: "course_1_anatomy",
                    course_label: "Course 1 · Anatomy",
                    title: "channel strip",
                    state: "now",
                    mode: "finish",
                    label: "practice bank 1/3",
                  },
                  {
                    lesson_id: "L1.04",
                    course_id: "course_1_anatomy",
                    course_label: "Course 1 · Anatomy",
                    title: "crossfader",
                    state: "next",
                    mode: "finish",
                    label: "banked 2/3",
                  },
                  {
                    lesson_id: "L1.05",
                    course_id: "course_1_anatomy",
                    course_label: "Course 1 · Anatomy",
                    title: "pitch fader",
                    state: "next",
                    mode: "start",
                    label: "next rep",
                  },
                ],
                meter_label: "practice bank",
                meter_value: 1,
                meter_max: 3,
                meter_state: "armed",
                meter_caption: "1 screen rep banked",
              },
            },
          },
        }),
      );

      const labels = Array.from(
        root.querySelectorAll<HTMLElement>(".learn-booth-chain__label"),
      ).map((el) => el.textContent);
      expect(labels).toEqual([
        "practice bank 1/3",
        "banked 2/3",
        "next rep",
      ]);
      expect(
        root.querySelector<HTMLElement>("#learn-booth-chain")?.getAttribute("aria-label"),
      ).toContain("banked 2/3: crossfader");
    } finally {
      ws.close();
    }
  });

  it("renders banked free-practice reps as a booth reward meter", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "snapshot",
            progress: {
              schema_version: 2,
              courses: {},
              lessons: {
                "L1.03": {
                  completed: false,
                  completed_at: null,
                  strikes_used: 0,
                  practice_sources: { hardware: 1, screen: 2 },
                  last_practice_source: "screen",
                },
              },
              course_2_unlocked: false,
              course_3_unlocked: false,
              next_practice_mission: {
                lesson_id: "L1.03",
                course_id: "course_1_anatomy",
                course_label: "Course 1 · Anatomy",
                skill_id: "deck_control",
                skill_label: "deck control",
                title: "channel strip",
                mode: "finish",
                command: "Finish channel strip; use one clean move, then let Learn verify it.",
                payoff: "You learn which part of the track each band actually changes.",
                proof: "screen deck has worked; repeat it cleanly",
                why: "Finish the lessons to reach Competent",
                estimated_minutes: 4,
                focus: "hardware",
                focus_label: "practice bank 3/3",
                challenge: "Repeat a banked move inside the lesson.",
                meter_label: "practice bank",
                meter_value: 3,
                meter_max: 3,
                meter_state: "armed",
                meter_caption: "3 reps banked: screen + hardware",
              },
            },
          },
        }),
      );

      const reward = root.querySelector<HTMLElement>("#learn-booth-reward")!;
      expect(root.querySelector<HTMLElement>("#learn-booth-pulse")?.textContent).toBe(
        "practice bank 3/3",
      );
      expect(reward.dataset.visible).toBe("true");
      expect(reward.dataset.state).toBe("armed");
      expect(reward.getAttribute("aria-label")).toBe(
        "practice bank 3 of 3. 3 reps banked: screen + hardware",
      );
      expect(
        root.querySelector<HTMLElement>("#learn-booth-reward-label")?.textContent,
      ).toBe("practice bank 3/3");
      expect(
        root.querySelector<HTMLElement>("#learn-booth-reward-caption")?.textContent,
      ).toBe("3 reps banked: screen + hardware");
      expect(
        root.querySelector<HTMLElement>("#learn-booth-reward-fill")?.style.width,
      ).toBe("100%");
      expect(
        root.querySelector<HTMLButtonElement>("#learn-start-recommended")
          ?.textContent,
      ).toMatch(/finish channel strip/i);
    } finally {
      ws.close();
    }
  });

  it("renders proof-bank progress as a small booth reward meter", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "snapshot",
            progress: {
              schema_version: 2,
              courses: {},
              lessons: completedRows(["L2.01", "L2.02"]),
              course_2_unlocked: true,
              course_3_unlocked: false,
              next_practice_mission: {
                lesson_id: "L2.01",
                course_id: "course_2_transitions",
                course_label: "Course 2 · Transitions",
                skill_id: "beatmatching",
                skill_label: "beatmatching",
                title: "beatmatching by ear",
                mode: "prove",
                command: "Prove beatmatching; earn the next cited proof on beatmatching by ear.",
                payoff: "You hear drift tighten into lock instead of reading about it.",
                proof: "2 cited proofs banked; 1 left",
                why: "1 more cited proof to Master",
                estimated_minutes: 6,
                focus: "proof",
                focus_label: "proof 2/3",
                challenge: "Only cited live proof moves Mastery.",
                meter_label: "proof bank",
                meter_value: 2,
                meter_max: 3,
                meter_state: "proof",
                meter_caption: "1 proof left to Mastery",
              },
            },
          },
        }),
      );

      const reward = root.querySelector<HTMLElement>("#learn-booth-reward")!;
      expect(reward.dataset.visible).toBe("true");
      expect(reward.dataset.state).toBe("proof");
      expect(reward.getAttribute("aria-label")).toBe(
        "proof bank 2 of 3. 1 proof left to Mastery",
      );
      expect(
        root.querySelector<HTMLElement>("#learn-booth-reward-label")?.textContent,
      ).toBe("proof bank 2/3");
      expect(
        root.querySelector<HTMLElement>("#learn-booth-reward-caption")?.textContent,
      ).toBe("1 proof left to Mastery");
      expect(
        root.querySelector<HTMLElement>("#learn-booth-reward-fill")?.style.width,
      ).toBe("67%");
      expect(
        root.querySelector<HTMLButtonElement>("#learn-start-recommended")
          ?.textContent,
      ).toMatch(/prove beatmatching by ear/i);
    } finally {
      ws.close();
    }
  });

  it("renders measured-miss recovery missions as fix loops", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "snapshot",
            progress: {
              schema_version: 2,
              courses: {},
              lessons: completedRows(["L2.01", "L2.02"]),
              course_2_unlocked: true,
              course_3_unlocked: false,
              next_practice_mission: {
                lesson_id: "L2.01",
                course_id: "course_2_transitions",
                course_label: "Course 2 · Transitions",
                skill_id: "beatmatching",
                skill_label: "beatmatching",
                title: "beatmatching by ear",
                mode: "prove",
                command: "Fix phase drift on beatmatching by ear; deck B is late.",
                payoff: "You hear drift tighten into lock instead of reading about it.",
                proof: "last measured miss: phase drift",
                why: "fix the measured miss before chasing the next proof",
                estimated_minutes: 6,
                focus: "recovery",
                focus_label: "phase drift",
                challenge: "Deck B is late; nudge it forward before chasing proof.",
                meter_label: "recovery target",
                meter_value: 0,
                meter_max: 1,
                meter_state: "retry",
                meter_caption: "0.05 beats from lock",
              },
            },
          },
        }),
      );

      expect(
        root.querySelector<HTMLButtonElement>("#learn-start-recommended")
          ?.textContent,
      ).toMatch(/fix beatmatching by ear/i);
      expect(root.querySelector<HTMLElement>("#learn-booth-pulse")?.textContent).toBe(
        "phase drift",
      );
      expect(
        root.querySelector<HTMLElement>("#learn-booth-command-text")?.textContent,
      ).toBe("Fix phase drift on beatmatching by ear; deck B is late.");
      expect(root.querySelector<HTMLElement>("#learn-booth-proof")?.textContent).toBe(
        "last measured miss: phase drift",
      );
      const reward = root.querySelector<HTMLElement>("#learn-booth-reward")!;
      expect(reward.dataset.visible).toBe("true");
      expect(reward.dataset.state).toBe("retry");
      expect(
        root.querySelector<HTMLElement>("#learn-booth-reward-label")?.textContent,
      ).toBe("recovery target 0/1");
      expect(
        root.querySelector<HTMLElement>("#learn-booth-reward-caption")?.textContent,
      ).toBe("0.05 beats from lock");
    } finally {
      ws.close();
    }
  });

  it("turns earned mastery into a review mission with a full booth meter", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "snapshot",
            progress: {
              schema_version: 2,
              courses: {},
              lessons: completedRows(["L2.01", "L2.02"]),
              course_2_unlocked: true,
              course_3_unlocked: false,
              next_practice_mission: {
                lesson_id: "L2.01",
                course_id: "course_2_transitions",
                course_label: "Course 2 · Transitions",
                skill_id: "beatmatching",
                skill_label: "beatmatching",
                title: "beatmatching by ear",
                mode: "mastered",
                command:
                  "Review beatmatching by ear; carry the mastered beatmatching move into a real set.",
                payoff: "You hear drift tighten into lock instead of reading about it.",
                proof: "3 cited proofs banked; Mastery earned",
                why: "Mastery earned from cited live proof",
                estimated_minutes: 6,
                focus: "mastery",
                focus_label: "mastered",
                challenge: "Carry it into a real set while it is fresh.",
                meter_label: "mastery",
                meter_value: 3,
                meter_max: 3,
                meter_state: "mastered",
                meter_caption: "Mastery earned",
              },
            },
          },
        }),
      );

      const reward = root.querySelector<HTMLElement>("#learn-booth-reward")!;
      expect(reward.dataset.visible).toBe("true");
      expect(reward.dataset.state).toBe("mastered");
      expect(reward.getAttribute("aria-label")).toBe("mastery 3 of 3. Mastery earned");
      expect(
        root.querySelector<HTMLElement>("#learn-booth-reward-label")?.textContent,
      ).toBe("mastery 3/3");
      expect(
        root.querySelector<HTMLElement>("#learn-booth-reward-caption")?.textContent,
      ).toBe("Mastery earned");
      expect(
        root.querySelector<HTMLElement>("#learn-booth-reward-fill")?.style.width,
      ).toBe("100%");
      expect(
        root.querySelector<HTMLButtonElement>("#learn-start-recommended")
          ?.textContent,
      ).toMatch(/review beatmatching by ear/i);

      mocks.emitIpc.mockClear();
      root.querySelector<HTMLButtonElement>("#learn-start-recommended")!.click();
      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.start_lesson", {
        lesson_id: "L2.01",
        level: "replay",
      });
    } finally {
      ws.close();
    }
  });

  it("refreshes the active lesson mission hint after live proof lands", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded("L2.01", "course_2_transitions");
      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "snapshot",
            progress: {
              schema_version: 2,
              courses: {},
              lessons: completedRows(["L2.01", "L2.02"]),
              course_2_unlocked: true,
              course_3_unlocked: false,
              next_practice_mission: {
                lesson_id: "L2.01",
                course_id: "course_2_transitions",
                course_label: "Course 2 · Transitions",
                skill_id: "beatmatching",
                skill_label: "beatmatching",
                title: "beatmatch lock",
                mode: "prove",
                command: "Prove beatmatching; earn the next cited proof on beatmatch lock.",
                payoff: "You hear drift tighten into lock instead of reading about it.",
                proof: "1 cited proof banked; 2 left",
                why: "1 more cited proof to Master",
                estimated_minutes: 6,
                focus: "proof",
                focus_label: "proof 1/3",
                challenge: "Only cited live proof moves Mastery.",
                meter_label: "proof bank",
                meter_value: 1,
                meter_max: 3,
                meter_state: "proof",
                meter_caption: "2 proofs left to Mastery",
              },
            },
          },
        }),
      );

      const hint = root.querySelector<HTMLElement>(".learn-status-hint")!;
      expect(hint.textContent).toBe("proof 1/3");
      expect(hint.getAttribute("data-practice-feedback")).toBe("proof");
      expect(hint.getAttribute("aria-label")).toContain(
        "Only cited live proof moves Mastery.",
      );
      expect(hint.getAttribute("aria-label")).toContain(
        "1 cited proof banked; 2 left",
      );
      expect(hint.getAttribute("aria-label")).toContain(
        "2 proofs left to Mastery",
      );
      expect(root.querySelector<HTMLElement>("#learn-booth-panel")?.dataset.visible).toBe(
        "false",
      );
    } finally {
      ws.close();
    }
  });

  it("refreshes the active lesson hint when live proof earns mastery", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded("L2.01", "course_2_transitions");
      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "snapshot",
            progress: {
              schema_version: 2,
              courses: {},
              lessons: completedRows(["L2.01", "L2.02"]),
              course_2_unlocked: true,
              course_3_unlocked: false,
              next_practice_mission: {
                lesson_id: "L2.01",
                course_id: "course_2_transitions",
                course_label: "Course 2 · Transitions",
                skill_id: "beatmatching",
                skill_label: "beatmatching",
                title: "beatmatch lock",
                mode: "mastered",
                command:
                  "Review beatmatch lock; carry the mastered beatmatching move into a real set.",
                payoff: "You hear drift tighten into lock instead of reading about it.",
                proof: "3 cited proofs banked; Mastery earned",
                why: "Mastery earned from cited live proof",
                estimated_minutes: 6,
                focus: "mastery",
                focus_label: "mastered",
                challenge: "Carry it into a real set while it is fresh.",
                meter_label: "mastery",
                meter_value: 3,
                meter_max: 3,
                meter_state: "mastered",
                meter_caption: "Mastery earned",
              },
            },
          },
        }),
      );

      const hint = root.querySelector<HTMLElement>(".learn-status-hint")!;
      expect(hint.textContent).toBe("mastered");
      expect(hint.getAttribute("data-practice-feedback")).toBe("mastered");
      expect(hint.getAttribute("aria-label")).toContain(
        "Carry it into a real set while it is fresh.",
      );
      expect(hint.getAttribute("aria-label")).toContain(
        "3 cited proofs banked; Mastery earned",
      );
      expect(hint.getAttribute("aria-label")).toContain("Mastery earned");
      expect(root.querySelector<HTMLElement>("#learn-booth-panel")?.dataset.visible).toBe(
        "false",
      );
    } finally {
      ws.close();
    }
  });

  it("falls back to direct ws outbound when Tauri invoke is unavailable", async () => {
    mocks.emitIpc.mockImplementation(async () => {
      throw new Error("Tauri unavailable");
    });
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const socket = StubWebSocket.instances[0]!;
      root.querySelector<HTMLButtonElement>("#learn-start-recommended")!.click();
      socket.readyState = StubWebSocket.OPEN;
      socket.onopen?.(new Event("open"));

      await vi.waitFor(() => {
        const sent = StubWebSocket.sent.map((frame) => JSON.parse(frame) as {
          type: string;
          payload: Record<string, unknown>;
        });
        expect(
          sent.some(
            (message) =>
              message.type === "ipc.learn.progress_state" &&
              message.payload.action === "snapshot",
          ),
        ).toBe(true);
        expect(
          sent.some(
            (message) =>
              message.type === "ipc.learn.start_lesson" &&
              message.payload.lesson_id === "L1.01" &&
              message.payload.level === "fresh",
          ),
        ).toBe(true);
      });
    } finally {
      ws.close();
    }
  });

  it("lets completed locked-course lessons replay without opening the gate", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.progress_state", {
          detail: {
            action: "snapshot",
            progress: {
              schema_version: 1,
              courses: {},
              lessons: {
                "L2.01": {
                  completed: true,
                  completed_at: "2026-05-28T00:00:00Z",
                  strikes_used: 0,
                },
              },
              course_2_unlocked: false,
              course_3_unlocked: false,
            },
          },
        }),
      );

      const replayable = root.querySelector<HTMLButtonElement>(
        "[data-lesson-id='L2.01']",
      )!;
      const stillLocked = root.querySelector<HTMLButtonElement>(
        "[data-lesson-id='L2.02']",
      )!;
      expect(replayable.dataset.locked).toBe("false");
      expect(replayable.dataset.status).toBe("completed");
      expect(stillLocked.dataset.locked).toBe("true");

      mocks.emitIpc.mockClear();
      replayable.click();
      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.start_lesson", {
        lesson_id: "L2.01",
        level: "replay",
      });
    } finally {
      ws.close();
    }
  });

  it("screen continue emits the same ack shape as a controller button", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
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

      const action = root.querySelector<HTMLButtonElement>(
        "#learn-screen-action",
      )!;
      expect(action.hidden).toBe(false);
      expect(action.getAttribute("aria-label")).toBe("continue lesson");
      expect(action.getAttribute("title")).toBe("continue lesson");
      action.click();

      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.ack", {
        control_id: "lesson_continue",
        source: "click",
        value: 127,
        prev_value: 0,
        direction: "down",
      });
    } finally {
      ws.close();
    }
  });

  it("clicking a highlighted on-screen knob emits a deterministic cc ack", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const eq = await waitForMountedControl(root, "eq_hi:A");
      dispatchLessonLoaded("L1.03");
      window.dispatchEvent(
        new CustomEvent("ipc.learn.highlight", {
          detail: {
            control_id: "eq_hi",
            deck: "A",
            cue_color: "amber",
            cue_shape: "pulse-ring",
            annotation: "turn high EQ",
            expected_action: {
              type: "cc",
              control: "eq_hi",
              deck: "A",
              min_delta: 38,
            },
          },
        }),
      );

      eq.dispatchEvent(new Event("pointerdown", { bubbles: true, cancelable: true }));

      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.ack", {
        control_id: "eq_hi:A",
        source: "click",
        value: 127,
        prev_value: 0,
        direction: "down",
      });
    } finally {
      ws.close();
    }
  });

  it("aliases the rendered jog wheel to the curriculum jog action", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      const jog = await waitForMountedControl(root, "jog_touch:A");
      dispatchLessonLoaded("L1.07");
      window.dispatchEvent(
        new CustomEvent("ipc.learn.highlight", {
          detail: {
            control_id: "jog",
            deck: "A",
            cue_color: "amber",
            cue_shape: "pulse-ring",
            annotation: "nudge jog",
            expected_action: {
              type: "cc",
              control: "jog",
              deck: "A",
              min_delta: 10,
            },
          },
        }),
      );

      expect(jog.getAttribute("data-cue-color")).toBe("amber");
      jog.dispatchEvent(new Event("pointerdown", { bubbles: true, cancelable: true }));

      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.ack", {
        control_id: "jog:A",
        source: "click",
        value: 127,
        prev_value: 0,
        direction: "down",
      });
    } finally {
      ws.close();
    }
  });

  it.each([
    {
      lessonId: "L1.08",
      highlight: {
        control_id: "headphone_cue",
        deck: "A",
        cue_color: "amber",
        cue_shape: "pulse-ring",
        annotation: "cue headphones",
        expected_action: {
          type: "button",
          control: "headphone_cue",
          deck: "A",
          direction: "down",
        },
      },
      ack: {
        control_id: "headphone_cue:A",
        source: "click",
        value: 127,
        prev_value: 0,
        direction: "down",
      },
      label: "press deck A headphone cue",
    },
    {
      lessonId: "L1.09",
      highlight: {
        control_id: "master_vol",
        deck: "",
        cue_color: "amber",
        cue_shape: "pulse-ring",
        annotation: "move master",
        expected_action: {
          type: "cc",
          control: "master_vol",
          deck: "",
          min_delta: 5,
        },
      },
      ack: {
        control_id: "master_vol",
        source: "click",
        value: 127,
        prev_value: 0,
        direction: "down",
      },
      label: "move master volume",
    },
  ])("shows a screen fallback for $highlight.control_id", ({ lessonId, highlight, ack, label }) => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    try {
      dispatchLessonLoaded(lessonId);
      window.dispatchEvent(
        new CustomEvent("ipc.learn.highlight", {
          detail: highlight,
        }),
      );

      const action = root.querySelector<HTMLButtonElement>(
        "#learn-screen-action",
      )!;
      expect(action.hidden).toBe(false);
      expect(action.textContent).toBe(label);
      expect(action.getAttribute("aria-label")).toBe(
        `screen fallback: ${label}`,
      );
      expect(action.getAttribute("title")).toBe(`screen fallback: ${label}`);
      const warnMessages = warnSpy.mock.calls.map((args) => args.join(" "));
      expect(
        warnMessages.some((message) =>
          message.includes("[learn] highlight: control_id"),
        ),
      ).toBe(false);
      action.click();

      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.ack", ack);
    } finally {
      warnSpy.mockRestore();
      ws.close();
    }
  });

  it("emits a midi ack for first-seen one-shot button pulses", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded("L2.02");
      window.dispatchEvent(
        new CustomEvent("ipc.learn.highlight", {
          detail: {
            control_id: "sync",
            deck: "B",
            cue_color: "amber",
            cue_shape: "pulse-ring",
            annotation: "sync deck B",
            expected_action: {
              type: "button",
              control: "sync",
              deck: "B",
              direction: "down",
            },
          },
        }),
      );

      mocks.emitIpc.mockClear();
      window.dispatchEvent(
        new CustomEvent("ipc.learn.midi_position", {
          detail: {
            controller_id: "pioneer_ddj_flx4",
            positions: { "sync:B": 127 },
          },
        }),
      );

      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.ack", {
        control_id: "sync:B",
        source: "midi",
        value: 127,
        prev_value: 0,
        direction: "down",
      });
    } finally {
      ws.close();
    }
  });

  it("emits a midi ack for first-seen relative jog pulses", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      dispatchLessonLoaded("L1.07");
      window.dispatchEvent(
        new CustomEvent("ipc.learn.highlight", {
          detail: {
            control_id: "jog",
            deck: "A",
            cue_color: "amber",
            cue_shape: "pulse-ring",
            annotation: "nudge jog",
            expected_action: {
              type: "cc",
              control: "jog",
              deck: "A",
              min_delta: 10,
            },
          },
        }),
      );

      mocks.emitIpc.mockClear();
      window.dispatchEvent(
        new CustomEvent("ipc.learn.midi_position", {
          detail: {
            controller_id: "pioneer_ddj_flx4",
            positions: { "jog:A": 127 },
          },
        }),
      );

      expect(mocks.emitIpc).toHaveBeenCalledWith("ipc.learn.ack", {
        control_id: "jog:A",
        source: "midi",
        value: 127,
        prev_value: 0,
        direction: "down",
      });
    } finally {
      ws.close();
    }
  });

  it("exemplar lessons show the listening chip instead of console-only state", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.exemplar_play", {
          detail: {
            track_id: "track_123456789abcdef",
            duration_s: 12.4,
            gain_db: -9,
          },
        }),
      );

      const chip = root.querySelector<HTMLElement>("#learn-exemplar-chip")!;
      expect(chip.hidden).toBe(false);
      expect(chip.dataset.active).toBe("true");
      expect(chip.textContent).toContain("example playing");
      expect(chip.textContent).toContain("track_12...cdef");

      window.dispatchEvent(
        new CustomEvent("ipc.learn.exemplar_stop", {
          detail: {
            track_id: "track_123456789abcdef",
            reason: "completed",
          },
        }),
      );

      expect(chip.dataset.active).toBe("false");
      expect(chip.textContent).toContain("example complete");
    } finally {
      ws.close();
    }
  });
});
