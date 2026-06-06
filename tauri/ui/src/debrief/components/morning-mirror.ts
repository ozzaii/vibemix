// SPDX-License-Identifier: Apache-2.0
// Last Night, Heard card. Renders the grounded near-miss/gap frame and
// mounts the recorded master input.wav through the existing Tauri asset scope.

import { convertFileSrc } from "@tauri-apps/api/core";
import {
  setTimelinePlayhead,
  setTimelineReplayWindow,
  type TimelineWaveformPeak,
} from "./timeline.js";

export interface MorningMirrorPayload {
  input_wav_relative_path: string;
  t_center: number | null;
  window: [number, number] | null;
  receipt_text: string;
  friend_line_text: string;
  duration_s: number;
  ear_test_clip_relative_path?: string | null;
  friend_line_audio_relative_path?: string | null;
  waveform_peaks?: TimelineWaveformPeak[] | null;
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
  const mirrorPeaks = sampleMirrorPeaks(payload.waveform_peaks, 34);
  rail.dataset.source = mirrorPeaks.length > 0 ? "master-input" : "synthetic";
  const tickCount = mirrorPeaks.length > 0 ? mirrorPeaks.length : 34;
  rail.style.setProperty("--vmx-mirror-bars", String(tickCount));
  for (let i = 0; i < tickCount; i += 1) {
    const tick = document.createElement("span");
    const realPeak = mirrorPeaks[i];
    if (realPeak) {
      tick.style.setProperty("--vmx-mirror-tick", String(2 + Math.round(peakStrength(realPeak) * 11)));
      tick.dataset.low = String(realPeak[0]);
      tick.dataset.mid = String(realPeak[1]);
      tick.dataset.high = String(realPeak[2]);
    } else {
      tick.style.setProperty("--vmx-mirror-tick", String(2 + ((i * 7) % 9)));
    }
    rail.append(tick);
  }

  container.append(eyebrow, line, receipt, friend, rail);

  const friendAudioPath = String(payload.friend_line_audio_relative_path ?? "").trim();
  const hasFriendAudio = friendAudioPath.length > 0;
  if (!hasReplay && !hasFriendAudio) return;

  const controls = document.createElement("div");
  controls.className = "vmx-morning-mirror__controls";

  let masterAudio: HTMLAudioElement | null = null;
  if (hasReplay) {
    const clipAudioPath = String(payload.ear_test_clip_relative_path ?? "").trim();
    const replayUsesClip = clipAudioPath.length > 0;
    const replayAudioPath = replayUsesClip ? clipAudioPath : payload.input_wav_relative_path;
    const replayStart = payload.window![0];

    const play = document.createElement("button");
    play.type = "button";
    play.className = "vmx-morning-mirror__play";
    play.textContent = "Play window";

    const time = document.createElement("span");
    time.className = "vmx-morning-mirror__time";
    time.textContent = `${formatClock(payload.window![0])} to ${formatClock(payload.window![1])}`;

    masterAudio = document.createElement("audio");
    masterAudio.className = "vmx-morning-mirror__audio";
    masterAudio.controls = true;
    masterAudio.preload = "metadata";
    masterAudio.src = buildAssetUrl(`${sessionDirAbs}/${replayAudioPath}`);

    const syncTimeline = (active: boolean): void => {
      if (!opts.timelineEl || !masterAudio) return;
      const duration = payload.duration_s > 0 ? payload.duration_s : masterAudio.duration;
      const sessionTime = replayUsesClip
        ? replayStart + masterAudio.currentTime
        : masterAudio.currentTime;
      const fraction = duration && Number.isFinite(duration)
        ? sessionTime / duration
        : 0;
      setTimelinePlayhead(opts.timelineEl, fraction, active);
    };

    const seekToWindow = (): void => {
      if (!masterAudio) return;
      masterAudio.currentTime = replayUsesClip ? 0 : Math.max(0, replayStart);
      syncTimeline(true);
    };

    play.addEventListener("click", () => {
      seekToWindow();
      const maybePromise = masterAudio?.play?.();
      if (maybePromise && "catch" in maybePromise) {
        maybePromise.catch(() => undefined);
      }
    });
    masterAudio.addEventListener("timeupdate", () => syncTimeline(true));
    masterAudio.addEventListener("play", () => syncTimeline(true));
    masterAudio.addEventListener("pause", () => syncTimeline(false));
    masterAudio.addEventListener("ended", () => syncTimeline(false));
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
  }

  let friendAudio: HTMLAudioElement | null = null;
  if (hasFriendAudio) {
    const playLine = document.createElement("button");
    playLine.type = "button";
    playLine.className = "vmx-morning-mirror__play vmx-morning-mirror__play--voice";
    playLine.textContent = "Play line";

    friendAudio = document.createElement("audio");
    friendAudio.className = "vmx-morning-mirror__friend-audio";
    friendAudio.preload = "metadata";
    friendAudio.src = buildAssetUrl(`${sessionDirAbs}/${friendAudioPath}`);

    playLine.addEventListener("click", () => {
      if (!friendAudio) return;
      friendAudio.currentTime = 0;
      const maybePromise = friendAudio.play?.();
      if (maybePromise && "catch" in maybePromise) {
        maybePromise.catch(() => undefined);
      }
    });
    controls.append(playLine);
  }

  container.append(controls);
  if (masterAudio) container.append(masterAudio);
  if (friendAudio) container.append(friendAudio);
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

function sampleMirrorPeaks(
  peaks: TimelineWaveformPeak[] | null | undefined,
  count: number,
): TimelineWaveformPeak[] {
  if (!Array.isArray(peaks) || peaks.length === 0 || count <= 0) return [];
  const out: TimelineWaveformPeak[] = [];
  const max = Math.min(512, peaks.length);
  for (let i = 0; i < count; i += 1) {
    const start = Math.floor((i / count) * max);
    const end = Math.max(start + 1, Math.floor(((i + 1) / count) * max));
    let low = 0;
    let mid = 0;
    let high = 0;
    for (let j = start; j < end; j += 1) {
      const row = peaks[j];
      if (!row) continue;
      low = Math.max(low, clampPeak(row[0]));
      mid = Math.max(mid, clampPeak(row[1]));
      high = Math.max(high, clampPeak(row[2]));
    }
    out.push([low, mid, high]);
  }
  return out;
}

function clampPeak(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(255, Math.round(value)));
}

function peakStrength(peak: TimelineWaveformPeak): number {
  return Math.max(0, Math.min(1, (peak[0] * 0.5 + peak[1] * 0.32 + peak[2] * 0.18) / 255));
}
