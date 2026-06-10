// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 Task 2 — TLDR audio player (HTML5 audio + duration display).

import { convertFileSrc } from "@tauri-apps/api/core";
import { setTimelinePlayhead } from "./timeline.js";

export interface TldrPayload {
  audio_relative_path: string;
  duration_s: number;
  tldr_sha256: string;
  mime_type: string;
}

/**
 * Mounts an <audio controls> element for the TL;DR MP3.
 *
 * The session_dir is required so the asset:// URL resolves correctly
 * against the Tauri filesystem scope.
 */
/** Optional wiring so the TL;DR player can drive the P1-a uplift-1
 *  amber playhead across the timeline. `timelineEl` is the timeline
 *  placeholder container (the one mountTimelinePlaceholder ran on);
 *  `sessionDurationS` is the FULL session length (not the TL;DR length)
 *  so the playhead maps onto the same axis as the regions. Omit both to
 *  keep the player standalone (the playhead simply never lights). */
export interface TldrPlayerOptions {
  timelineEl?: HTMLElement | null;
  sessionDurationS?: number;
}

interface TauriAssetWindow {
  __TAURI_INTERNALS__?: unknown;
  __TAURI__?: { core?: { convertFileSrc?: (s: string) => string } };
}

export function mountTldrPlayer(
  container: HTMLElement,
  payload: TldrPayload,
  sessionDirAbs: string,
  opts: TldrPlayerOptions = {},
): void {
  container.textContent = "";

  const duration = document.createElement("p");
  duration.className = "vmx-debrief-tldr-meta";
  duration.textContent = `${Math.round(payload.duration_s)}s recap`;

  const audio = document.createElement("audio");
  audio.controls = true;
  audio.preload = "metadata";
  audio.className = "vmx-debrief-tldr-audio";

  // The Rust shell passes the session-dir absolute path via the URL
  // query; we point the <audio> src at asset://<host>/<abs_path>.
  // buildAssetUrl uses convertFileSrc only when the desktop runtime is present,
  // keeping browser dev and unit tests on the deterministic fallback URL.
  const url = buildAssetUrl(`${sessionDirAbs}/${payload.audio_relative_path}`);
  audio.src = url;

  // P1-a uplift 1 — wire the amber playhead to TL;DR playback. The
  // TL;DR is a short voiced summary; mapping its progress (0..1) onto
  // the full-session timeline axis gives the "TL;DR audio plays → a
  // thin amber line sweeps the master waveform" CDJ feel. Native
  // `timeupdate` fires ~4Hz — GPU-cheap, no rAF loop. Pause/ended hide
  // the line so a stopped player leaves the timeline clean.
  const timelineEl = opts.timelineEl ?? null;
  if (timelineEl) {
    const sync = (active: boolean): void => {
      const dur = audio.duration;
      const frac = dur && isFinite(dur) && dur > 0 ? audio.currentTime / dur : 0;
      setTimelinePlayhead(timelineEl, frac, active);
    };
    audio.addEventListener("timeupdate", () => sync(true));
    audio.addEventListener("play", () => sync(true));
    audio.addEventListener("pause", () => sync(false));
    audio.addEventListener("ended", () => sync(false));
  }

  container.append(duration, audio);
}

/**
 * P1-a uplift 3 — the single amber verdict headline.
 *
 * Renders ONE grounded standout stat for the session into the TL;DR
 * panel (inserted right after the silk section title, above the player).
 * The copy is built by the caller from REAL session structure (track
 * count + duration from the chapter-list / session-loaded frames) — no
 * invented numbers (cardinal invariant 3: trust the audio). Idempotent:
 * re-rendering replaces the prior line rather than stacking.
 *
 * `panelEl` is the `.vmx-debrief-tldr` panel; `text` is the pre-built
 * verdict string (e.g. "9 TRACKS · 1H 12M IN THE MIX").
 */
export function renderVerdictLine(panelEl: HTMLElement, text: string): void {
  let line = panelEl.querySelector<HTMLElement>(".vmx-debrief-verdict");
  if (!line) {
    line = document.createElement("p");
    line.className = "vmx-debrief-verdict";
    // Insert after the section title (first <h2>) if present, else prepend.
    const title = panelEl.querySelector("h2");
    if (title && title.parentElement === panelEl) {
      title.insertAdjacentElement("afterend", line);
    } else {
      panelEl.prepend(line);
    }
  }
  line.textContent = text;
}

/**
 * P1-a uplift 3 — build the grounded verdict string from real session
 * structure. Kept pure + exported so it's unit-testable and so the
 * "no invented numbers" contract is verifiable. Picks the most
 * impressive REAL stat available; falls back gracefully when data is thin.
 *
 * trackCount must be the count of kind=="track" chapters ONLY — chapters
 * also break on phase/layer/mix/crowd movement, so the raw chapter count
 * overstates tracks on any real set (a 3-track set with phase movement
 * proudly read "9 TRACKS"). When no track chapters exist, the raw chapter
 * count speaks under its truthful noun: MOMENTS.
 */
export function buildVerdictText(
  trackCount: number,
  sessionDurationS: number,
  chapterCount = 0,
): string {
  const parts: string[] = [];
  if (trackCount > 0) {
    parts.push(`${trackCount} ${trackCount === 1 ? "TRACK" : "TRACKS"}`);
  } else if (chapterCount > 0) {
    parts.push(`${chapterCount} ${chapterCount === 1 ? "MOMENT" : "MOMENTS"}`);
  }
  if (sessionDurationS > 0) {
    parts.push(`${formatDuration(sessionDurationS)} IN THE MIX`);
  }
  // Thin-data fallback — never fabricate a number we don't have.
  if (parts.length === 0) return "SET LOGGED";
  return parts.join(" · ");
}

function formatDuration(totalS: number): string {
  const h = Math.floor(totalS / 3600);
  const m = Math.round((totalS % 3600) / 60);
  if (h > 0) return m > 0 ? `${h}H ${m}M` : `${h}H`;
  if (m > 0) return `${m}M`;
  return `${Math.round(totalS)}S`;
}

function buildAssetUrl(path: string): string {
  // In production, `@tauri-apps/api/core::convertFileSrc` renders the
  // platform-correct asset URL even when the window.__TAURI__ global is
  // disabled. The fallback keeps browser dev and unit tests synchronous.
  try {
    const tauriWindow = window as unknown as TauriAssetWindow;
    if (tauriWindow.__TAURI_INTERNALS__) {
      return convertFileSrc(path);
    }
    const legacyConvert = tauriWindow.__TAURI__?.core?.convertFileSrc;
    if (legacyConvert) {
      return legacyConvert(path);
    }
  } catch {
    // fall through
  }
  return `asset://localhost/${encodeURI(path)}`;
}
