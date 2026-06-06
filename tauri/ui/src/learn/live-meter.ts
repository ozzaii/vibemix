// SPDX-License-Identifier: Apache-2.0
// Beatmatch lock meter fed by ipc.learn.live_grade.

type LiveGradeVerdict = "locked" | "drifting" | "tempo_off" | "trainwreck" | "abstain";

export interface LiveGradePayload {
  verdict: LiveGradeVerdict;
  phase_error_beats: number;
  score: number;
  citation: string | null;
  save_landed?: boolean;
  save_attempt_active?: boolean;
  save_floor_seconds_total?: number | null;
  save_floor_seconds_remaining?: number | null;
  save_floor_expired?: boolean;
  save_difficulty_level?: number;
  save_streak?: number;
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
  if (payload.save_landed) {
    return "save landed";
  }
  if (payload.save_floor_expired) {
    return "floor dropped";
  }
  if (payload.save_attempt_active) {
    return "save window";
  }
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

function finiteNumber(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function boundedLevel(value: number | undefined): number {
  const level = finiteNumber(value);
  if (level === null) return 1;
  return clamp(Math.round(level), 1, 5);
}

function boundedStreak(value: number | undefined): number {
  const streak = finiteNumber(value);
  if (streak === null) return 0;
  return Math.max(0, Math.round(streak));
}

function saveSecondsText(value: number | null | undefined): string {
  const seconds = finiteNumber(value);
  if (seconds === null) return "--.-s";
  return `${Math.max(0, seconds).toFixed(1)}s`;
}

function saveHudVisible(payload: LiveGradePayload): boolean {
  return Boolean(
    payload.save_attempt_active ||
      payload.save_floor_expired ||
      payload.save_landed ||
      boundedStreak(payload.save_streak) > 0,
  );
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

  const save = document.createElement("div");
  save.className = "learn-live-meter__save";
  save.hidden = true;
  const saveLevel = document.createElement("span");
  saveLevel.className = "learn-live-meter__save-level";
  const saveTimer = document.createElement("strong");
  saveTimer.className = "learn-live-meter__save-timer";
  const saveStreak = document.createElement("span");
  saveStreak.className = "learn-live-meter__save-streak";
  save.append(saveLevel, saveTimer, saveStreak);

  root.append(header, canvas, phaseText, save, receipt);
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
    root.dataset.saveActive = payload.save_attempt_active ? "true" : "false";
    root.dataset.saveExpired = payload.save_floor_expired ? "true" : "false";
    root.dataset.saveLanded = payload.save_landed ? "true" : "false";
    root.dataset.saveLevel = String(boundedLevel(payload.save_difficulty_level));
    root.dataset.saveStreak = String(boundedStreak(payload.save_streak));
    const remaining = finiteNumber(payload.save_floor_seconds_remaining);
    if (remaining === null) {
      root.removeAttribute("data-save-remaining");
    } else {
      root.dataset.saveRemaining = remaining.toFixed(1);
    }
    if (payload.citation) {
      root.dataset.citation = payload.citation;
    } else {
      root.removeAttribute("data-citation");
    }
    const showSaveHud = saveHudVisible(payload);
    save.hidden = !showSaveHud;
    if (showSaveHud) {
      const level = boundedLevel(payload.save_difficulty_level);
      const streak = boundedStreak(payload.save_streak);
      saveLevel.textContent = `L${level}`;
      if (payload.save_landed) {
        saveTimer.textContent = "landed";
      } else if (payload.save_floor_expired) {
        saveTimer.textContent = "00.0s";
      } else {
        saveTimer.textContent = saveSecondsText(payload.save_floor_seconds_remaining);
      }
      saveStreak.textContent = streak > 0 ? `x${streak}` : "x0";
    }
    const receiptLine = receiptText(payload, phase);
    verdict.textContent = payload.verdict.replace("_", " ");
    phaseText.textContent = formatPhase(phase);
    receipt.textContent = receiptLine;
    root.setAttribute(
      "aria-label",
      `beatmatch ${payload.verdict.replace("_", " ")}, ${formatPhase(phase)}, ${receiptLine}`,
    );
    if (showSaveHud) {
      const level = boundedLevel(payload.save_difficulty_level);
      const streak = boundedStreak(payload.save_streak);
      let remainingText = saveSecondsText(payload.save_floor_seconds_remaining);
      if (payload.save_landed) {
        remainingText = "save landed";
      } else if (payload.save_floor_expired) {
        remainingText = "floor dropped";
      }
      root.setAttribute(
        "aria-label",
        `beatmatch ${payload.verdict.replace("_", " ")}, ${formatPhase(phase)}, save level ${level}, ${remainingText}, streak ${streak}, ${receiptLine}`,
      );
    }
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
    root.removeAttribute("data-save-active");
    root.removeAttribute("data-save-expired");
    root.removeAttribute("data-save-landed");
    root.removeAttribute("data-save-level");
    root.removeAttribute("data-save-remaining");
    root.removeAttribute("data-save-streak");
    save.hidden = true;
    saveLevel.textContent = "";
    saveTimer.textContent = "";
    saveStreak.textContent = "";
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
