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
}

export interface TimelineSeekEvent extends CustomEvent {
  detail: { time: number; citation_event_id: string };
}

export function mountTimelinePlaceholder(
  container: HTMLElement,
  chapters: TimelineChapter[],
  totalDurationS: number,
): void {
  container.textContent = "";
  container.classList.add("vmx-debrief-timeline-placeholder");

  if (chapters.length === 0 || totalDurationS <= 0) {
    const empty = document.createElement("p");
    empty.className = "vmx-debrief-timeline-empty";
    empty.textContent = "No regions to render.";
    container.append(empty);
    return;
  }

  for (const c of chapters) {
    const region = document.createElement("button");
    region.type = "button";
    region.className = "vmx-debrief-region";
    region.dataset.chapterId = c.id;
    region.dataset.citationEventId = c.citation_event_id;
    const width = ((c.end - c.start) / totalDurationS) * 100;
    const left = (c.start / totalDurationS) * 100;
    region.style.left = `${left}%`;
    region.style.width = `${width}%`;
    region.title = c.label;
    region.setAttribute(
      "aria-label",
      `Seek to ${c.label} at ${formatTime(c.start)}`,
    );
    region.addEventListener("click", (e) => {
      e.stopPropagation();
      container.dispatchEvent(
        new CustomEvent("region-clicked", {
          detail: {
            time: c.start,
            citation_event_id: c.citation_event_id,
          },
          bubbles: true,
        }),
      );
    });
    container.append(region);
  }

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
    if (!region && typeof detail.timestampS === "number") {
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
    region.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    region.classList.add("vmx-debrief-region--highlight");
    window.setTimeout(() => {
      region!.classList.remove("vmx-debrief-region--highlight");
    }, TIMELINE_DEEP_LINK_HIGHLIGHT_MS);
  };

  // Store the listener on the container so subsequent mounts can detach
  // the previous handler (the debrief window currently only mounts the
  // timeline once, but the dataset key keeps the pattern safe under
  // hot-reload). The `as any` cast keeps the dataset-key write off the
  // public TS surface.
  const existing = (container as unknown as { __vmxDeepLink?: EventListener })
    .__vmxDeepLink;
  if (existing) window.removeEventListener("vmx-debrief-deeplink", existing);
  (container as unknown as { __vmxDeepLink?: EventListener }).__vmxDeepLink =
    onDeepLink;
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

function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${sec}`;
}
