// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 Task 1 — debrief window entry point.

import { mountChapterList, type ChapterPayload } from "./components/chapter-list.js";
import { mountDrillsPanel, type DrillPayload } from "./components/drills-panel.js";
import { mountTldrPlayer, type TldrPayload } from "./components/tldr-player.js";
import {
  mountTimelinePlaceholder,
  type TimelineChapter,
} from "./components/timeline.js";
import {
  showCitationTooltip,
  type CitationTooltipPayload,
} from "./components/citation-tooltip.js";
import {
  mountEarTestToggle,
  type EarTestSubmission,
} from "./components/ear-test-toggle.js";
import { showErrorBanner } from "./components/error-banner.js";
import { DebriefWsClient } from "./ws-client.js";

// Type-only re-export so external callers can reference the submission
// shape via the debrief-window module surface (mirrors the
// CitationTooltipPayload re-export pattern used elsewhere).
export type { EarTestSubmission };

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

const params = new URLSearchParams(location.search);
const sessionDir = decodeURIComponent(params.get("session") ?? "");
const sessionId = sessionDir.split("/").pop() ?? "session";

// Surface the session id in the titlebar.
const titleEl = document.getElementById("vmx-debrief-session");
if (titleEl) titleEl.textContent = sessionId;
document.title = `Debrief — ${sessionId}`;

const errorBanner = document.getElementById("vmx-debrief-error-banner");
const tooltip = document.getElementById("vmx-debrief-tooltip");
const chaptersEl = document.getElementById("vmx-debrief-chapters");
const drillsEl = document.getElementById("vmx-debrief-drills-list");
const tldrEl = document.getElementById("vmx-debrief-tldr-player");
const waveformEl = document.getElementById("vmx-debrief-waveform");
const earTestToggleEl = document.getElementById("vmx-debrief-ear-test-toggle");

if (!sessionDir) {
  if (errorBanner) {
    showErrorBanner(errorBanner, "invalid_session_dir");
  }
} else {
  const client = new DebriefWsClient(8766);

  let chapters: TimelineChapter[] = [];
  let totalDurationS = 0;

  client.addEventListener("session-loaded", (e: Event) => {
    const detail = (e as CustomEvent).detail as {
      duration_s: number;
      genre?: string;
    };
    totalDurationS = detail.duration_s;
    // Plan 42-03 — mount the ear-test toggle once the session loads so
    // the form has a real duration_s for the submission payload.
    if (earTestToggleEl) {
      mountEarTestToggle(
        earTestToggleEl,
        {
          session_id: sessionId,
          duration_s: totalDurationS,
          genre: detail.genre ?? "other",
        },
        {
          errorBannerEl: errorBanner,
          wsSink: {
            send: (msg) => client.sendEarTestSubmit(msg.payload),
          },
        },
      );
    }
  });

  client.addEventListener("chapter-list", (e: Event) => {
    const detail = (e as CustomEvent).detail as {
      chapters: ChapterPayload[];
    };
    if (chaptersEl) mountChapterList(chaptersEl, detail.chapters);
    chapters = detail.chapters.map((c) => ({
      id: c.id,
      start: c.start,
      end: c.end,
      label: c.label,
      citation_event_id: c.citation_event_id,
    }));
    if (waveformEl && totalDurationS > 0) {
      mountTimelinePlaceholder(waveformEl, chapters, totalDurationS);
    }
  });

  client.addEventListener("drills", (e: Event) => {
    const detail = (e as CustomEvent).detail as { drills: DrillPayload[] };
    if (drillsEl) mountDrillsPanel(drillsEl, detail.drills);
  });

  client.addEventListener("tldr-audio", (e: Event) => {
    const detail = (e as CustomEvent).detail as TldrPayload;
    if (tldrEl) mountTldrPlayer(tldrEl, detail, sessionDir);
  });

  client.addEventListener("citation-tooltip", (e: Event) => {
    const detail = (e as CustomEvent).detail as CitationTooltipPayload;
    if (tooltip) showCitationTooltip(tooltip, detail);
  });

  client.addEventListener("error", (e: Event) => {
    const detail = (e as CustomEvent).detail as {
      reason?: string;
      message?: string;
    };
    if (errorBanner) {
      showErrorBanner(
        errorBanner,
        detail?.reason ?? "sidecar_crashed",
        detail?.message ?? "",
      );
    }
  });

  // Wire citation chip clicks → request tooltip via WS.
  if (drillsEl) {
    drillsEl.addEventListener("citation-click", (e: Event) => {
      const detail = (e as CustomEvent).detail as { citation: string };
      client.sendCitationTooltipRequest(detail.citation);
    });
  }
  if (waveformEl) {
    waveformEl.addEventListener("region-clicked", (e: Event) => {
      const detail = (e as CustomEvent).detail as {
        citation_event_id: string;
      };
      client.sendCitationTooltipRequest(detail.citation_event_id);
    });
  }

  // Listen for Rust shell's sidecar-crashed event.
  // The dynamic import keeps the module testable without Tauri runtime.
  (async () => {
    try {
      const event = await import("@tauri-apps/api/event");
      event.listen("sidecar-debrief-crashed", () => {
        if (errorBanner) showErrorBanner(errorBanner, "sidecar_crashed");
      });
      // Phase 44-03 / LAUNCH-02 — focus-existing deep-link channel.
      // When a chip is clicked in the live session UI AND a debrief
      // window is already open, the Rust side `open_debrief_window`
      // emits this event instead of re-mounting the window. The
      // payload mirrors the URL-deep-link shape ({eventId, timestampS})
      // so the same `vmx-debrief-deeplink` listener path serves both
      // surfaces. Re-dispatching as a window-scoped CustomEvent keeps
      // the timeline component's listener simple.
      event.listen("vmx-debrief-deeplink", (ev: { payload: unknown }) => {
        window.dispatchEvent(
          new CustomEvent("vmx-debrief-deeplink", { detail: ev.payload }),
        );
      });
    } catch {
      // Not running under Tauri (dev / test).
    }
  })();

  // Phase 44-03 / LAUNCH-02 — fresh-mount deep-link channel. When the
  // debrief window opens via a chip-click, the Rust side appends
  // `&deepLinkEventId=...&deepLinkTimestampS=...` to the webview URL.
  // We dispatch the CustomEvent AFTER the timeline mounts (waveformEl
  // chapter-list callback above), but since the chapter-list arrives
  // asynchronously over the ws bus, we delay the deep-link dispatch
  // until the FIRST chapter-list event has fired (so the timeline
  // exists in the DOM and can match the region).
  const deepLinkEventId = params.get("deepLinkEventId");
  const deepLinkTimestampS = params.get("deepLinkTimestampS");
  if (deepLinkEventId && deepLinkTimestampS) {
    const payload = {
      eventId: decodeURIComponent(deepLinkEventId),
      timestampS: Number(deepLinkTimestampS),
    };
    client.addEventListener("chapter-list", () => {
      // Fire on the next microtask so mountTimelinePlaceholder has had
      // a chance to attach its `vmx-debrief-deeplink` listener (same
      // tick as the callback above).
      queueMicrotask(() => {
        window.dispatchEvent(
          new CustomEvent("vmx-debrief-deeplink", { detail: payload }),
        );
      });
    });
  }

  client.connect();
}
