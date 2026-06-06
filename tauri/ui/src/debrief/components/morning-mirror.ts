// SPDX-License-Identifier: Apache-2.0
// Last Night, Heard card. Renders the grounded near-miss/gap frame and
// mounts the recorded master input.wav through the existing Tauri asset scope.

import { convertFileSrc } from "@tauri-apps/api/core";
import {
  setTimelinePlayhead,
  setTimelineReplayWindow,
} from "./timeline.js";

export interface MorningMirrorPayload {
  input_wav_relative_path: string;
  t_center: number | null;
  window: [number, number] | null;
  receipt_text: string;
  friend_line_text: string;
  duration_s: number;
}

export interface MorningMirrorOptions {
  timelineEl?: HTMLElement | null;
}

interface TauriAssetWindow {
  __TAURI_INTERNALS__?: unknown;
  __TAURI__?: { core?: { convertFileSrc?: (s: string) => string } };
}

interface TimelineMirrorHost {
  __vmxMorningReplayListener?: EventListener;
}

export function mountMorningMirror(
  container: HTMLElement,
  payload: MorningMirrorPayload,
  sessionDirAbs: string,
  opts: MorningMirrorOptions = {},
): void {
  container.textContent = "";
  const hasReplay =
    typeof payload.t_center === "number" &&
    Number.isFinite(payload.t_center) &&
    Array.isArray(payload.window) &&
    payload.window.length === 2 &&
    payload.duration_s > 0;

  container.dataset.state = hasReplay ? "replay" : "quiet";
  if (opts.timelineEl) {
    setTimelineReplayWindow(
      opts.timelineEl,
      hasReplay ? { start: payload.window![0], end: payload.window![1] } : null,
      payload.duration_s,
    );
  }

  const eyebrow = document.createElement("p");
  eyebrow.className = "vmx-morning-mirror__eyebrow";
  eyebrow.textContent = hasReplay ? "Last night, heard" : "Last night, held";

  const line = document.createElement("p");
  line.className = "vmx-morning-mirror__line";
  line.textContent = hasReplay
    ? "I was there. Want to hear the part you held your breath through?"
    : "Nothing sharp enough to flag. The mix held together.";

  const receipt = document.createElement("p");
  receipt.className = "vmx-morning-mirror__receipt";
  receipt.textContent = payload.receipt_text.trim() || "No confident near-miss receipt.";

  const friend = document.createElement("p");
  friend.className = "vmx-morning-mirror__friend";
  friend.textContent = payload.friend_line_text.trim() || "No extra line tonight.";

  const rail = document.createElement("div");
  rail.className = "vmx-morning-mirror__rail";
  rail.setAttribute("aria-hidden", "true");
  for (let i = 0; i < 34; i += 1) {
    const tick = document.createElement("span");
    tick.style.setProperty("--vmx-mirror-tick", String(2 + ((i * 7) % 9)));
    rail.append(tick);
  }

  container.append(eyebrow, line, receipt, friend, rail);

  if (!hasReplay) return;

  const controls = document.createElement("div");
  controls.className = "vmx-morning-mirror__controls";

  const play = document.createElement("button");
  play.type = "button";
  play.className = "vmx-morning-mirror__play";
  play.textContent = "Play window";

  const time = document.createElement("span");
  time.className = "vmx-morning-mirror__time";
  time.textContent = `${formatClock(payload.window![0])} to ${formatClock(payload.window![1])}`;

  const audio = document.createElement("audio");
  audio.className = "vmx-morning-mirror__audio";
  audio.controls = true;
  audio.preload = "metadata";
  audio.src = buildAssetUrl(`${sessionDirAbs}/${payload.input_wav_relative_path}`);

  const syncTimeline = (active: boolean): void => {
    if (!opts.timelineEl) return;
    const duration = payload.duration_s > 0 ? payload.duration_s : audio.duration;
    const fraction = duration && Number.isFinite(duration)
      ? audio.currentTime / duration
      : 0;
    setTimelinePlayhead(opts.timelineEl, fraction, active);
  };

  const seekToWindow = (): void => {
    const [start] = payload.window!;
    audio.currentTime = Math.max(0, start);
    syncTimeline(true);
  };

  play.addEventListener("click", () => {
    seekToWindow();
    const maybePromise = audio.play?.();
    if (maybePromise && "catch" in maybePromise) {
      maybePromise.catch(() => undefined);
    }
  });
  audio.addEventListener("timeupdate", () => syncTimeline(true));
  audio.addEventListener("play", () => syncTimeline(true));
  audio.addEventListener("pause", () => syncTimeline(false));
  audio.addEventListener("ended", () => syncTimeline(false));
  if (opts.timelineEl) {
    const timelineHost = opts.timelineEl as TimelineMirrorHost;
    if (timelineHost.__vmxMorningReplayListener) {
      opts.timelineEl.removeEventListener(
        "replay-window-clicked",
        timelineHost.__vmxMorningReplayListener,
      );
    }
    timelineHost.__vmxMorningReplayListener = seekToWindow;
    opts.timelineEl.addEventListener("replay-window-clicked", seekToWindow);
  }

  controls.append(play, time);
  container.append(controls, audio);
}

function formatClock(totalS: number): string {
  const safe = Math.max(0, Math.round(totalS));
  const minutes = Math.floor(safe / 60);
  const seconds = String(safe % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function buildAssetUrl(path: string): string {
  const w = window as unknown as TauriAssetWindow;
  if (w.__TAURI_INTERNALS__ || w.__TAURI__?.core?.convertFileSrc) {
    return convertFileSrc(path);
  }
  return `asset://localhost/${path}`;
}
