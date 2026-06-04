// SPDX-License-Identifier: Apache-2.0

type DragDirection = "" | "up" | "down";

export interface AnalogDragFrame {
  controlId: string;
  visualControlId: string;
  value: number;
  prevValue: number;
  direction: DragDirection;
}

interface AnalogDragOptions {
  event: PointerEvent;
  group: SVGGElement;
  controlId: string;
  ackControlId: string;
  visualControlId: string;
  initialValue: number;
  apply: (positions: Record<string, number>) => void;
  emit: (frame: AnalogDragFrame) => void;
}

type AnalogKind = "vertical" | "horizontal" | "knob" | "jog";

const BUTTON_HEADS = new Set([
  "play",
  "cue",
  "sync",
  "loop_in",
  "loop_out",
  "hotcue",
  "jog_touch",
  "jog_touched",
  "filter_fx",
  "fx_echo",
  "tap_tempo",
  "headphone_cue",
  "lesson_continue",
]);

function clampMidi(value: number): number {
  return Math.min(127, Math.max(0, Math.round(value)));
}

function analogKind(controlId: string): AnalogKind | null {
  const head = controlId.split(":")[0] ?? controlId;
  if (BUTTON_HEADS.has(head)) return null;
  if (head === "xfader") return "horizontal";
  if (head === "vol" || head === "tempo") return "vertical";
  if (head === "jog") return "jog";
  return "knob";
}

function pointerAngle(group: SVGGElement, ev: PointerEvent): number | null {
  const cx = Number(group.dataset.cx);
  const cy = Number(group.dataset.cy);
  if (!Number.isFinite(cx) || !Number.isFinite(cy)) return null;
  const svg = group.ownerSVGElement;
  if (!svg) return null;
  if (typeof svg.createSVGPoint !== "function" || typeof svg.getScreenCTM !== "function") {
    return null;
  }
  const point = svg.createSVGPoint();
  point.x = ev.clientX;
  point.y = ev.clientY;
  const ctm = svg.getScreenCTM();
  if (!ctm) return null;
  const local = point.matrixTransform(ctm.inverse());
  return Math.atan2(local.y - cy, local.x - cx);
}

function shortestAngleDelta(prev: number, next: number): number {
  let delta = next - prev;
  while (delta > Math.PI) delta -= Math.PI * 2;
  while (delta < -Math.PI) delta += Math.PI * 2;
  return delta;
}

export function isAnalogControl(controlId: string): boolean {
  return analogKind(controlId) !== null;
}

export function startAnalogControlDrag(options: AnalogDragOptions): boolean {
  const kind = analogKind(options.ackControlId);
  if (kind === null) return false;

  const target = options.group;
  const pointerId = options.event.pointerId;
  const startValue = clampMidi(options.initialValue);
  let value = startValue;
  let lastX = options.event.clientX;
  let lastY = options.event.clientY;
  let lastAngle = pointerAngle(target, options.event);
  let raf = 0;
  let pending: AnalogDragFrame | null = null;

  const flush = (): void => {
    raf = 0;
    if (!pending) return;
    const frame = pending;
    pending = null;
    options.apply({ [frame.visualControlId]: frame.value });
    options.emit(frame);
  };

  const queue = (nextRaw: number): void => {
    const next = clampMidi(nextRaw);
    if (next === value) return;
    const prevValue = value;
    value = next;
    pending = {
      controlId: options.ackControlId,
      visualControlId: options.visualControlId,
      value,
      prevValue,
      direction: value > prevValue ? "down" : "up",
    };
    if (!raf) {
      raf = window.requestAnimationFrame(flush);
    }
  };

  const move = (ev: PointerEvent): void => {
    if (ev.pointerId !== pointerId) return;
    ev.preventDefault();
    const dx = ev.clientX - lastX;
    const dy = ev.clientY - lastY;
    lastX = ev.clientX;
    lastY = ev.clientY;

    if (kind === "horizontal") {
      queue(value + dx * 0.9);
      return;
    }
    if (kind === "vertical") {
      queue(value - dy * 0.9);
      return;
    }
    if (kind === "jog") {
      const angle = pointerAngle(target, ev);
      if (angle === null || lastAngle === null) {
        queue(value + dx * 1.2 - dy * 0.6);
      } else {
        queue(value + shortestAngleDelta(lastAngle, angle) * 42.0);
        lastAngle = angle;
      }
      return;
    }
    queue(value + dx * 0.35 - dy * 0.75);
  };

  const stop = (ev: PointerEvent): void => {
    if (ev.pointerId !== pointerId) return;
    if (raf) {
      window.cancelAnimationFrame(raf);
      flush();
    }
    try {
      target.releasePointerCapture(pointerId);
    } catch {
      /* best-effort release */
    }
    target.removeAttribute("data-dragging");
    window.removeEventListener("pointermove", move, true);
    window.removeEventListener("pointerup", stop, true);
    window.removeEventListener("pointercancel", stop, true);
  };

  options.event.preventDefault();
  try {
    target.setPointerCapture(pointerId);
  } catch {
    /* capture can fail in synthetic tests; window listeners still carry drag */
  }
  target.setAttribute("data-dragging", "true");
  window.addEventListener("pointermove", move, true);
  window.addEventListener("pointerup", stop, true);
  window.addEventListener("pointercancel", stop, true);
  return true;
}
