// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 Task 2 — Timeline placeholder.
//
// Full WaveSurfer.js v7.12.7 + RegionsPlugin integration is deferred to
// the wave 5 polish pass (requires `npm install wavesurfer.js` in the
// dev environment); this module renders a minimal click-to-seek surface
// over a div sized to the voice.wav duration. The renderer in the
// browser will mount the real WaveSurfer instance on top of this surface
// once wavesurfer.js is installed (the timeline div is here as the
// mount target so the layout doesn't shift between placeholder and
// real waveform).

export interface TimelineChapter {
  id: string;
  start: number;
  end: number;
  label: string;
  citation_event_id: string;
  kind?: string;
}

export interface TimelineSeekEvent extends CustomEvent {
  detail: { time: number; citation_event_id: string };
}

let activeDeepLinkListener: EventListener | null = null;

export interface TimelineReplayWindow {
  start: number;
  end: number;
}

export type TimelineWaveformPeak = [number, number, number];

export function mountTimelinePlaceholder(
  container: HTMLElement,
  chapters: TimelineChapter[],
  totalDurationS: number,
  waveformPeaks: TimelineWaveformPeak[] | null = null,
): void {
  container.textContent = "";
  container.classList.add("vmx-debrief-timeline-placeholder");
  container.style.setProperty("--vmx-region-count", String(chapters.length));

  if (chapters.length === 0 || totalDurationS <= 0) {
    const empty = document.createElement("p");
    empty.className = "vmx-debrief-timeline-empty";
    empty.textContent =
      "No moments yet. Play a set with me live and they'll land here.";
    container.append(empty);
    return;
  }

  const signalBed = document.createElement("div");
  signalBed.className = "vmx-debrief-signal-bed";
  signalBed.setAttribute("aria-hidden", "true");
  const realPeaks = sanitizeWaveformPeaks(waveformPeaks);
  const barCount = realPeaks.length > 0 ? realPeaks.length : 96;
  signalBed.dataset.source = realPeaks.length > 0 ? "master-input" : "synthetic";
  signalBed.style.setProperty("--vmx-signal-bars", String(barCount));
  const firstChapter = chapters[0]!;
  for (let i = 0; i < barCount; i += 1) {
    const bar = document.createElement("span");
    const realPeak = realPeaks[i];
    if (realPeak) {
      const strength = peakStrength(realPeak);
      const height = 10 + Math.round(strength * 82);
      bar.dataset.low = String(realPeak[0]);
      bar.dataset.mid = String(realPeak[1]);
      bar.dataset.high = String(realPeak[2]);
      bar.style.setProperty("--vmx-bar-h", `${Math.max(8, Math.min(92, height))}%`);
      bar.style.setProperty("--vmx-bar-alpha", String(0.14 + strength * 0.42));
    } else {
      const chapter = chapters[Math.floor((i / 96) * chapters.length)] ?? firstChapter;
      const chapterSpan = Math.max(1, chapter.end - chapter.start);
      const normalizedSpan = Math.min(1, chapterSpan / Math.max(1, totalDurationS));
      const pulse =
        Math.sin(i * 0.48) * 0.5 +
        Math.cos(i * 0.17) * 0.32 +
        Math.sin(i * 0.91) * 0.18;
      const height = 22 + Math.round((pulse + 1) * 18 + normalizedSpan * 42);
      bar.style.setProperty("--vmx-bar-h", `${Math.max(12, Math.min(84, height))}%`);
      bar.style.setProperty("--vmx-bar-alpha", String(0.12 + (i % 5) * 0.025));
    }
    signalBed.append(bar);
  }

  const phaseRail = document.createElement("div");
  phaseRail.className = "vmx-debrief-phase-rail";
  phaseRail.setAttribute("aria-hidden", "true");
  for (const fraction of [0, 0.25, 0.5, 0.75, 1]) {
    const mark = document.createElement("span");
    mark.textContent = formatTime(totalDurationS * fraction);
    phaseRail.append(mark);
  }

  const regionLayer = document.createElement("div");
  regionLayer.className = "vmx-debrief-region-layer";

  const readout = document.createElement("div");
  readout.className = "vmx-debrief-timeline-readout";
  readout.setAttribute("aria-live", "polite");
  renderReadout(readout, [
    `${chapters.length} moments`,
    `${formatTime(totalDurationS)} set`,
    "ready",
  ]);

  container.append(signalBed, phaseRail, regionLayer, readout);

  for (const [i, c] of chapters.entries()) {
    const region = document.createElement("button");
    region.type = "button";
    region.className = "vmx-debrief-region";
    region.dataset.chapterId = c.id;
    region.dataset.citationEventId = c.citation_event_id;
    if (c.kind) region.dataset.kind = c.kind;
    const width = ((c.end - c.start) / totalDurationS) * 100;
    const left = (c.start / totalDurationS) * 100;
    region.style.left = `${left}%`;
    region.style.width = `${width}%`;
    region.style.setProperty("--vmx-region-y", `${30 + (i % 3) * 9}%`);
    region.style.setProperty(
      "--vmx-region-h",
      `${Math.max(18, Math.min(34, 18 + width * 0.45))}%`,
    );
    region.title = c.label;
    region.textContent = compactLabel(c.label);
    region.setAttribute(
      "aria-label",
      `Seek to ${c.label} at ${formatTime(c.start)}`,
    );
    const inspect = (): void => {
      for (const active of Array.from(
        regionLayer.querySelectorAll<HTMLElement>(".vmx-debrief-region[data-active='true']"),
      )) {
        delete active.dataset.active;
      }
      region.dataset.active = "true";
      renderReadout(readout, [
        c.kind ?? "moment",
        `${formatTime(c.start)} → ${formatTime(c.end)}`,
        compactLabel(c.label),
      ]);
    };
    region.addEventListener("mouseenter", inspect);
    region.addEventListener("focus", inspect);
    region.addEventListener("click", (e) => {
      e.stopPropagation();
      inspect();
      // Evidence arrives async over the ws bus — the click position rides
      // along so the tooltip can open at the region, not the page tail.
      const rect = region.getBoundingClientRect();
      const fromKeyboard = e.detail === 0;
      container.dispatchEvent(
        new CustomEvent("region-clicked", {
          detail: {
            time: c.start,
            citation_event_id: c.citation_event_id,
            anchorX: fromKeyboard ? rect.left : e.clientX,
            anchorY: fromKeyboard ? rect.bottom : e.clientY,
          },
          bubbles: true,
        }),
      );
    });
    regionLayer.append(region);
  }

  // P1-a uplift 1 — thin amber playhead. Appended once over the regions;
  // the tldr-player drives it via setTimelinePlayhead() on audio
  // timeupdate. It stays hidden (data-active unset) until the first
  // position update, so a stopped/never-played TL;DR shows no stray line.
  const playhead = document.createElement("div");
  playhead.className = "vmx-debrief-playhead";
  playhead.setAttribute("aria-hidden", "true");
  container.append(playhead);
  (container as unknown as { __vmxPlayhead?: HTMLElement }).__vmxPlayhead =
    playhead;

  // Phase 44-03 / LAUNCH-02 — listen for chip-click deep-link events
  // dispatched from `debrief-window.ts` after a session-cohost-reaction
  // chip is clicked in the live session UI. The handler looks up the
  // region that matches `event_id` (chapters.citation_event_id), scrolls
  // it into view, and applies the `vmx-debrief-region--highlight` class
  // for ~2s so the user can spot the targeted region without reading.
  // When no exact match is found, we fall back to the nearest region by
  // timestamp (within ±2.0s tol — matches the EvidenceRegistry.has()
  // debrief-mode tolerance band locked in GROUND-07).
  const onDeepLink = (e: Event) => {
    const detail = (e as CustomEvent).detail as
      | { eventId?: string; timestampS?: number }
      | undefined;
    if (!detail) return;
    let region = container.querySelector<HTMLElement>(
      `.vmx-debrief-region[data-citation-event-id="${cssEscape(detail.eventId ?? "")}"]`,
    );
    // Tolerance fallback — pick the nearest region whose start is within
    // ±2.0s of the requested timestamp_s (matches the debrief-mode
    // tolerance band on EvidenceRegistry.has()).
    if (
      !region &&
      typeof detail.timestampS === "number" &&
      Number.isFinite(detail.timestampS)
    ) {
      let bestDelta = Number.POSITIVE_INFINITY;
      let bestEl: HTMLElement | null = null;
      for (const c of chapters) {
        const delta = Math.abs(c.start - detail.timestampS);
        if (delta < bestDelta && delta <= TIMELINE_DEEP_LINK_TOL_S) {
          bestDelta = delta;
          bestEl = container.querySelector<HTMLElement>(
            `.vmx-debrief-region[data-chapter-id="${cssEscape(c.id)}"]`,
          );
        }
      }
      region = bestEl;
    }
    if (!region) return;
    region.scrollIntoView?.({
      behavior: "smooth",
      block: "nearest",
      inline: "center",
    });
    region.classList.add("vmx-debrief-region--highlight");
    window.setTimeout(() => {
      region!.classList.remove("vmx-debrief-region--highlight");
    }, TIMELINE_DEEP_LINK_HIGHLIGHT_MS);
  };

  // Keep a single window-scoped deep-link listener. The debrief app only
  // shows one active timeline, and this prevents stale remounts from
  // keeping detached DOM nodes alive.
  if (activeDeepLinkListener) {
    window.removeEventListener("vmx-debrief-deeplink", activeDeepLinkListener);
  }
  activeDeepLinkListener = onDeepLink;
  window.addEventListener("vmx-debrief-deeplink", onDeepLink);
}

/** Phase 44-03 / LAUNCH-02 — debrief-mode tolerance band (seconds) for
 *  citation→region matching, mirrors the EvidenceRegistry.has() debrief
 *  default (GROUND-07). When no exact citation_event_id match is found,
 *  pick the region whose `start` is within ±this many seconds. */
export const TIMELINE_DEEP_LINK_TOL_S = 2.0;

/** Phase 44-03 / LAUNCH-02 — highlight pulse duration (ms) for the
 *  deep-link target region. 2s is long enough for the user to spot
 *  the region without the highlight becoming permanent noise. */
export const TIMELINE_DEEP_LINK_HIGHLIGHT_MS = 2000;

/** Minimal CSS.escape polyfill for jsdom + older browsers. The chip
 *  event_ids and chapter ids carry `:`, `@`, `.` — all special in
 *  attribute selectors. Native CSS.escape exists in modern browsers
 *  but is missing in some test environments. */
function cssEscape(s: string): string {
  if (typeof CSS !== "undefined" && typeof CSS.escape === "function") {
    return CSS.escape(s);
  }
  // Minimal fallback — escape the characters we actually expect.
  return s.replace(/(["\\.:@\[\]#])/g, "\\$1");
}

/**
 * P1-a uplift 1 — position the timeline playhead.
 *
 * Driven by the TL;DR audio element's `timeupdate` (and play/pause/ended)
 * in tldr-player.ts. `fraction` is the playback position 0..1 across the
 * full session duration. Passing `active=false` (e.g. on pause/ended)
 * hides the line. No-ops cleanly when the timeline hasn't mounted a
 * playhead yet (chapters not yet rendered), so call ordering is safe.
 */
export function setTimelinePlayhead(
  container: HTMLElement,
  fraction: number,
  active: boolean,
): void {
  const playhead = (container as unknown as { __vmxPlayhead?: HTMLElement })
    .__vmxPlayhead;
  if (!playhead) return;
  if (!active) {
    delete playhead.dataset.active;
    return;
  }
  const clamped = Math.min(1, Math.max(0, fraction));
  playhead.style.setProperty("--vmx-playhead", `${clamped * 100}%`);
  playhead.dataset.active = "true";
}

export function setTimelineReplayWindow(
  container: HTMLElement,
  replayWindow: TimelineReplayWindow | null,
  totalDurationS: number,
): void {
  const host = container as unknown as { __vmxReplayWindow?: HTMLButtonElement };
  const existing = host.__vmxReplayWindow;
  if (!replayWindow || totalDurationS <= 0) {
    if (existing) existing.remove();
    host.__vmxReplayWindow = undefined;
    return;
  }

  const start = Math.max(0, Math.min(totalDurationS, replayWindow.start));
  const end = Math.max(start, Math.min(totalDurationS, replayWindow.end));
  if (end <= start) {
    if (existing) existing.remove();
    host.__vmxReplayWindow = undefined;
    return;
  }

  let marker = existing;
  if (!marker) {
    marker = document.createElement("button");
    marker.type = "button";
    marker.className = "vmx-debrief-replay-window";
    marker.dataset.kind = "near-miss";
    marker.textContent = "replay";
    marker.addEventListener("click", (e) => {
      e.stopPropagation();
      const clickStart = Number(marker!.dataset.startS ?? 0);
      const clickEnd = Number(marker!.dataset.endS ?? clickStart);
      container.dispatchEvent(
        new CustomEvent("replay-window-clicked", {
          detail: { time: clickStart, window: [clickStart, clickEnd] },
          bubbles: true,
        }),
      );
    });
    container.append(marker);
    host.__vmxReplayWindow = marker;
  }

  marker.style.left = `${(start / totalDurationS) * 100}%`;
  marker.style.width = `${Math.max(1.5, ((end - start) / totalDurationS) * 100)}%`;
  marker.dataset.startS = String(start);
  marker.dataset.endS = String(end);
  marker.setAttribute(
    "aria-label",
    `Replay near miss from ${formatTime(start)} to ${formatTime(end)}`,
  );
  marker.dataset.active = "true";
}

function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${sec}`;
}

function compactLabel(label: string): string {
  return label.replace(/^\d{1,2}:\d{2}\s+/, "").trim() || label;
}

function renderReadout(container: HTMLElement, values: string[]): void {
  container.textContent = "";
  for (const value of values) {
    const item = document.createElement("span");
    item.textContent = value;
    container.append(item);
  }
}

function sanitizeWaveformPeaks(
  peaks: TimelineWaveformPeak[] | null | undefined,
): TimelineWaveformPeak[] {
  if (!Array.isArray(peaks)) return [];
  const out: TimelineWaveformPeak[] = [];
  for (const row of peaks.slice(0, 512)) {
    if (!Array.isArray(row) || row.length < 3) continue;
    const low = clampPeak(row[0]);
    const mid = clampPeak(row[1]);
    const high = clampPeak(row[2]);
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
