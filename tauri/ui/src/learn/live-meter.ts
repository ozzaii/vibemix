// SPDX-License-Identifier: Apache-2.0
// Beatmatch lock meter fed by ipc.learn.live_grade.

type LiveGradeVerdict = "locked" | "drifting" | "tempo_off" | "trainwreck" | "abstain";

export interface LiveGradePayload {
  verdict: LiveGradeVerdict;
  phase_error_beats: number;
  score: number;
  citation: string | null;
}

export interface LiveGradeMeterHandle {
  root: HTMLElement;
  update: (payload: LiveGradePayload) => void;
  reset: () => void;
  dispose: () => void;
}

const CANVAS_WIDTH = 220;
const CANVAS_HEIGHT = 96;

function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

function formatPhase(phase: number): string {
  if (Math.abs(phase) < 0.005) return "center";
  const side = phase > 0 ? "behind" : "ahead";
  return `${Math.abs(phase).toFixed(2)} beat ${side}`;
}

function receiptText(payload: LiveGradePayload, phase: number): string {
  if (payload.verdict === "locked") {
    return payload.citation ? "proof caught" : "hold pocket";
  }
  if (payload.verdict === "drifting") {
    return phase > 0 ? "deck B late" : "deck B early";
  }
  if (payload.verdict === "tempo_off") {
    return "tempo first";
  }
  if (payload.verdict === "trainwreck") {
    return "reset the 1";
  }
  return "listening";
}

function drawNeedle(canvas: HTMLCanvasElement, payload: LiveGradePayload | null): void {
  if (/jsdom/i.test(globalThis.navigator?.userAgent ?? "")) return;
  let ctx: CanvasRenderingContext2D | null = null;
  try {
    ctx = canvas.getContext("2d");
  } catch {
    ctx = null;
  }
  if (!ctx) return;

  const styles = getComputedStyle(canvas);
  const silk = styles.getPropertyValue("--silk").trim() || "#f4ede3";
  const amber = styles.getPropertyValue("--amber").trim() || "#f6bd60";
  const teal = styles.getPropertyValue("--teal").trim() || "#62d6c6";
  const muted = styles.getPropertyValue("--silk-22").trim() || "rgba(244,237,227,0.22)";
  const phase = payload ? clamp(payload.phase_error_beats, -0.5, 0.5) : 0;
  const score = payload ? clamp(payload.score, 0, 1) : 0;
  const centerX = CANVAS_WIDTH / 2;
  const baselineY = 64;
  const radius = 72;
  const needleX = centerX + phase * 2 * radius;

  ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
  ctx.lineCap = "round";
  ctx.lineWidth = 2;

  ctx.strokeStyle = muted;
  ctx.beginPath();
  ctx.moveTo(centerX - radius, baselineY);
  ctx.lineTo(centerX + radius, baselineY);
  ctx.stroke();

  ctx.strokeStyle = payload?.verdict === "locked" ? teal : amber;
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(centerX - radius, baselineY);
  ctx.lineTo(centerX - radius + radius * 2 * score, baselineY);
  ctx.stroke();

  ctx.strokeStyle = silk;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(centerX, 22);
  ctx.lineTo(centerX, baselineY + 8);
  ctx.stroke();

  ctx.fillStyle = payload?.verdict === "locked" ? teal : amber;
  ctx.beginPath();
  ctx.moveTo(needleX, 20);
  ctx.lineTo(needleX - 9, baselineY - 10);
  ctx.lineTo(needleX + 9, baselineY - 10);
  ctx.closePath();
  ctx.fill();
}

export function LiveGradeMeter(host: HTMLElement): LiveGradeMeterHandle {
  const root = document.createElement("section");
  root.id = "learn-live-meter";
  root.className = "learn-live-meter";
  root.dataset.state = "idle";
  root.dataset.needlePct = "50.0";
  root.dataset.lockEdge = "false";
  root.dataset.lockCount = "0";
  root.setAttribute("aria-label", "beatmatch lock meter idle");

  const header = document.createElement("div");
  header.className = "learn-live-meter__header";
  const label = document.createElement("span");
  label.className = "learn-live-meter__label";
  label.textContent = "lock";
  const verdict = document.createElement("strong");
  verdict.className = "learn-live-meter__verdict";
  verdict.textContent = "idle";
  header.append(label, verdict);

  const canvas = document.createElement("canvas");
  canvas.className = "learn-live-meter__canvas";
  canvas.width = CANVAS_WIDTH;
  canvas.height = CANVAS_HEIGHT;

  const phaseText = document.createElement("div");
  phaseText.className = "learn-live-meter__phase";
  phaseText.textContent = "waiting for decks";

  const receipt = document.createElement("div");
  receipt.className = "learn-live-meter__receipt";
  receipt.textContent = "no proof yet";

  root.append(header, canvas, phaseText, receipt);
  host.replaceChildren(root);

  let pending: LiveGradePayload | null = null;
  let frame: number | null = null;
  let previousVerdict: LiveGradeVerdict | null = null;
  let lockCount = 0;
  const flush = (): void => {
    frame = null;
    drawNeedle(canvas, pending);
  };

  const scheduleDraw = (): void => {
    if (frame !== null) return;
    frame = requestAnimationFrame(flush);
  };

  const update = (payload: LiveGradePayload): void => {
    const phase = clamp(payload.phase_error_beats, -0.5, 0.5);
    const score = clamp(payload.score, 0, 1);
    const enteredLock = payload.verdict === "locked" && previousVerdict !== "locked";
    previousVerdict = payload.verdict;
    if (enteredLock) {
      lockCount += 1;
    }
    pending = {
      verdict: payload.verdict,
      phase_error_beats: phase,
      score,
      citation: payload.citation,
    };
    const needlePct = 50 + phase * 100;
    root.dataset.state = "active";
    root.dataset.verdict = payload.verdict;
    root.dataset.phase = phase.toFixed(4);
    root.dataset.score = score.toFixed(4);
    root.dataset.needlePct = needlePct.toFixed(1);
    root.dataset.lockEdge = enteredLock ? "true" : "false";
    root.dataset.lockCount = String(lockCount);
    root.dataset.locked = payload.verdict === "locked" ? "true" : "false";
    if (payload.citation) {
      root.dataset.citation = payload.citation;
    } else {
      root.removeAttribute("data-citation");
    }
    const receiptLine = receiptText(payload, phase);
    verdict.textContent = payload.verdict.replace("_", " ");
    phaseText.textContent = formatPhase(phase);
    receipt.textContent = receiptLine;
    root.setAttribute(
      "aria-label",
      `beatmatch ${payload.verdict.replace("_", " ")}, ${formatPhase(phase)}, ${receiptLine}`,
    );
    scheduleDraw();
  };

  const reset = (): void => {
    pending = null;
    previousVerdict = null;
    lockCount = 0;
    root.dataset.state = "idle";
    root.dataset.needlePct = "50.0";
    root.dataset.lockEdge = "false";
    root.dataset.lockCount = "0";
    root.removeAttribute("data-locked");
    root.removeAttribute("data-verdict");
    root.removeAttribute("data-phase");
    root.removeAttribute("data-score");
    root.removeAttribute("data-citation");
    verdict.textContent = "idle";
    phaseText.textContent = "waiting for decks";
    receipt.textContent = "no proof yet";
    root.setAttribute("aria-label", "beatmatch lock meter idle");
    scheduleDraw();
  };

  const dispose = (): void => {
    if (frame !== null) {
      cancelAnimationFrame(frame);
      frame = null;
    }
    host.replaceChildren();
  };

  reset();
  return { root, update, reset, dispose };
}
