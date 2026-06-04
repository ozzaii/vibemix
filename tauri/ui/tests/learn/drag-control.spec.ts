// SPDX-License-Identifier: Apache-2.0

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  isAnalogControl,
  startAnalogControlDrag,
  type AnalogDragFrame,
} from "../../src/learn/drag-control";

function pointer(type: string, init: Partial<PointerEvent>): PointerEvent {
  return new Event(type, { bubbles: true, cancelable: true }) as PointerEvent & {
    clientX: number;
    clientY: number;
    pointerId: number;
  };
}

function assignPointer(ev: PointerEvent, init: Partial<PointerEvent>): PointerEvent {
  Object.defineProperty(ev, "clientX", { value: init.clientX ?? 0 });
  Object.defineProperty(ev, "clientY", { value: init.clientY ?? 0 });
  Object.defineProperty(ev, "pointerId", { value: init.pointerId ?? 1 });
  return ev;
}

function makeFader(): SVGGElement {
  const wrapper = document.createElement("div");
  wrapper.innerHTML = `
    <svg viewBox="0 0 120 240" xmlns="http://www.w3.org/2000/svg">
      <g data-control-id="vol:A" data-cx="60" data-cy="120">
        <rect x="55" y="20" width="10" height="160"></rect>
        <rect x="48" y="150" width="24" height="20"></rect>
      </g>
    </svg>
  `;
  const group = wrapper.querySelector<SVGGElement>('[data-control-id="vol:A"]');
  expect(group).not.toBeNull();
  group!.setPointerCapture = vi.fn();
  group!.releasePointerCapture = vi.fn();
  return group!;
}

describe("learn drag-control", () => {
  beforeEach(() => {
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
      cb(0);
      return 1;
    });
    vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("classifies faders, knobs, and jog as analog while keeping buttons discrete", () => {
    expect(isAnalogControl("vol:A")).toBe(true);
    expect(isAnalogControl("xfader")).toBe(true);
    expect(isAnalogControl("eq_hi:A")).toBe(true);
    expect(isAnalogControl("jog:A")).toBe(true);
    expect(isAnalogControl("sync:B")).toBe(false);
  });

  it("emits continuous 0..127 deltas while the pointer is captured", () => {
    const group = makeFader();
    const applied: Record<string, number>[] = [];
    const frames: AnalogDragFrame[] = [];

    const started = startAnalogControlDrag({
      event: assignPointer(pointer("pointerdown", {}), {
        clientX: 10,
        clientY: 100,
        pointerId: 7,
      }),
      group,
      controlId: "vol:A",
      ackControlId: "vol:A",
      visualControlId: "vol:A",
      initialValue: 64,
      apply: (positions) => applied.push(positions),
      emit: (frame) => frames.push(frame),
    });

    window.dispatchEvent(
      assignPointer(pointer("pointermove", {}), {
        clientX: 10,
        clientY: 80,
        pointerId: 7,
      }),
    );
    window.dispatchEvent(
      assignPointer(pointer("pointermove", {}), {
        clientX: 10,
        clientY: 60,
        pointerId: 7,
      }),
    );
    window.dispatchEvent(assignPointer(pointer("pointerup", {}), { pointerId: 7 }));

    expect(started).toBe(true);
    expect(group.setPointerCapture).toHaveBeenCalledWith(7);
    expect(group.releasePointerCapture).toHaveBeenCalledWith(7);
    expect(frames.length).toBeGreaterThanOrEqual(2);
    const firstFrame = frames[0];
    if (!firstFrame) throw new Error("expected first drag frame");
    expect(firstFrame).toMatchObject({
      controlId: "vol:A",
      value: 82,
      prevValue: 64,
      direction: "down",
    });
    expect(frames.at(-1)?.value).toBeGreaterThan(firstFrame.value);
    expect(applied.at(-1)).toEqual({ "vol:A": frames.at(-1)?.value });
  });
});
