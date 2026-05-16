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
import { showErrorBanner } from "./components/error-banner.js";
import { DebriefWsClient } from "./ws-client.js";

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

if (!sessionDir) {
  if (errorBanner) {
    showErrorBanner(errorBanner, "invalid_session_dir");
  }
} else {
  const client = new DebriefWsClient(8766);

  let chapters: TimelineChapter[] = [];
  let totalDurationS = 0;

  client.addEventListener("session-loaded", (e: Event) => {
    const detail = (e as CustomEvent).detail as { duration_s: number };
    totalDurationS = detail.duration_s;
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
    } catch {
      // Not running under Tauri (dev / test).
    }
  })();

  client.connect();
}
