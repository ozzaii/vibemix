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
}

function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${sec}`;
}
