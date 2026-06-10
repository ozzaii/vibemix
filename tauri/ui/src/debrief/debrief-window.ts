// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 Task 1 — debrief window entry point.

import { mountChapterList, type ChapterPayload } from "./components/chapter-list.js";
import {
  mountDrillsPanel,
  type DrillPayload,
  type MomentFeedbackClickEvent,
} from "./components/drills-panel.js";
import {
  mountTldrPlayer,
  renderVerdictLine,
  buildVerdictText,
  type TldrPayload,
} from "./components/tldr-player.js";
import {
  mountTimelinePlaceholder,
  setTimelineReplayWindow,
  type TimelineChapter,
} from "./components/timeline.js";
import {
  mountMorningMirror,
  type MorningMirrorPayload,
} from "./components/morning-mirror.js";
import {
  showCitationTooltip,
  type CitationTooltipPayload,
} from "./components/citation-tooltip.js";
import {
  showErrorBanner,
  showWorkingBanner,
  resolveSkeletonsToTerminal,
} from "./components/error-banner.js";
import { DebriefWsClient } from "./ws-client.js";
import { parseDebriefBootUrl } from "./url-state.js";

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

const bootState = parseDebriefBootUrl(location.search);
const { sessionDir, sessionId, isMockMode } = bootState;

// The raw session id is dev telemetry, not a DJ's review heading; keep the
// window title clean and leave the titlebar slot empty.
document.title = "Debrief";

const errorBanner = document.getElementById("vmx-debrief-error-banner");
const tooltip = document.getElementById("vmx-debrief-tooltip");
const chaptersEl = document.getElementById("vmx-debrief-chapters");
const drillsEl = document.getElementById("vmx-debrief-drills-list");
const morningEl = document.getElementById("vmx-debrief-morning-card");
const tldrEl = document.getElementById("vmx-debrief-tldr-player");
// The TL;DR panel host (carries the silk section title) — the verdict
// headline (P1-a uplift 3) is inserted here, above the player.
const tldrPanelEl = document.getElementById("vmx-debrief-tldr");
const waveformEl = document.getElementById("vmx-debrief-waveform");

const skeletonHosts = { morning: morningEl, tldr: tldrEl, drills: drillsEl };

if (isMockMode) {
  mountMockDebrief();
} else if (!sessionDir) {
  if (errorBanner) {
    showErrorBanner(errorBanner, "invalid_session_dir");
  }
  resolveSkeletonsToTerminal(skeletonHosts, "invalid_session_dir");
} else {
  const client = new DebriefWsClient(8766);

  let chapters: TimelineChapter[] = [];
  let totalDurationS = 0;
  let morningPayload: MorningMirrorPayload | null = null;
  // The evidence frame returns async; the click that requested it stashes
  // its viewport position here so the tooltip opens at the chip, not at
  // the document tail.
  let pendingTooltipAnchor: { x: number; y: number } | null = null;

  client.addEventListener("session-loaded", (e: Event) => {
    const detail = (e as CustomEvent).detail as {
      duration_s: number;
      genre?: string;
    };
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
      kind: c.kind,
    }));
    if (waveformEl && totalDurationS > 0) {
      mountTimelinePlaceholder(
        waveformEl,
        chapters,
        totalDurationS,
        morningPayload?.waveform_peaks ?? null,
      );
      if (morningPayload?.window) {
        setTimelineReplayWindow(
          waveformEl,
          { start: morningPayload.window[0], end: morningPayload.window[1] },
          morningPayload.duration_s || totalDurationS,
        );
      }
    }
    // P1-a uplift 3 — the verdict headline. Built from REAL session
    // structure, not invented: chapters break on phase/layer/mix movement
    // too, so only kind=="track" chapters may be counted as TRACKS.
    if (tldrPanelEl) {
      const trackCount = chapters.filter((c) => c.kind === "track").length;
      renderVerdictLine(
        tldrPanelEl,
        buildVerdictText(trackCount, totalDurationS, chapters.length),
      );
    }
  });

  client.addEventListener("drills", (e: Event) => {
    const detail = (e as CustomEvent).detail as { drills: DrillPayload[] };
    if (drillsEl) mountDrillsPanel(drillsEl, detail.drills);
  });

  client.addEventListener("near-miss", (e: Event) => {
    morningPayload = (e as CustomEvent).detail as MorningMirrorPayload;
    totalDurationS = Math.max(totalDurationS, morningPayload.duration_s || 0);
    if (morningEl) {
      mountMorningMirror(morningEl, morningPayload, sessionDir, {
        timelineEl: waveformEl,
      });
    }
    if (waveformEl && chapters.length > 0 && totalDurationS > 0) {
      mountTimelinePlaceholder(
        waveformEl,
        chapters,
        totalDurationS,
        morningPayload.waveform_peaks ?? null,
      );
      if (morningPayload.window) {
        setTimelineReplayWindow(
          waveformEl,
          { start: morningPayload.window[0], end: morningPayload.window[1] },
          morningPayload.duration_s || totalDurationS,
        );
      }
    }
  });

  client.addEventListener("tldr-audio", (e: Event) => {
    const detail = (e as CustomEvent).detail as TldrPayload;
    // P1-a uplift 1 — hand the timeline container + full session
    // duration to the player so TL;DR playback sweeps the amber playhead
    // across the master-waveform timeline.
    if (tldrEl)
      mountTldrPlayer(tldrEl, detail, sessionDir, {
        timelineEl: waveformEl,
        sessionDurationS: totalDurationS,
      });
  });

  client.addEventListener("citation-tooltip", (e: Event) => {
    const detail = (e as CustomEvent).detail as CitationTooltipPayload;
    if (tooltip) {
      showCitationTooltip(tooltip, detail, pendingTooltipAnchor ?? undefined);
    }
    pendingTooltipAnchor = null;
  });

  client.addEventListener("error", (e: Event) => {
    const detail = (e as CustomEvent).detail as {
      reason?: string;
      message?: string;
    };
    // Only verdict-carrying errors reach the banner: schema
    // ipc.debrief.error frames and the reconnect-budget's synthetic
    // {reason:"sidecar_crashed"}. A detail without a reason is transport
    // noise — never a crash verdict (Invariant #5: in-between ≠ fault).
    if (!detail?.reason) return;
    if (errorBanner) {
      showErrorBanner(errorBanner, detail.reason, detail?.message ?? "");
    }
    resolveSkeletonsToTerminal(skeletonHosts, detail.reason);
  });

  // Honest in-between state: the sidecar binds 8766 only after boot (and,
  // first time, after generation starts emitting). Past a 10s grace, say
  // so — never over a real error banner.
  client.addEventListener("connecting", (e: Event) => {
    const detail = (e as CustomEvent).detail as { elapsedMs?: number };
    if (!errorBanner) return;
    if ((detail?.elapsedMs ?? 0) < 10_000) return;
    if (!errorBanner.hidden && errorBanner.dataset.reason !== "still_working")
      return;
    showWorkingBanner(errorBanner);
  });

  client.addEventListener("open", () => {
    if (!errorBanner) return;
    // A late-binding sidecar is healthy — clear the waiting line and any
    // premature crash verdict.
    const reason = errorBanner.dataset.reason;
    if (reason === "still_working" || reason === "sidecar_crashed") {
      errorBanner.hidden = true;
      errorBanner.textContent = "";
    }
  });

  // Wire the chapter rail → timeline deep-link. The rail's buttons were a
  // dead control: they dispatched chapter-selected and nobody listened —
  // ~320px of fully-styled affordance that did nothing. Route through the
  // existing vmx-debrief-deeplink path (same scroll+pulse the live
  // chip-click uses); covers both the live and mock mounts.
  if (chaptersEl) {
    chaptersEl.addEventListener("chapter-selected", (e: Event) => {
      const detail = (e as CustomEvent).detail as {
        id: string;
        start: number;
        citation_event_id: string;
      };
      window.dispatchEvent(
        new CustomEvent("vmx-debrief-deeplink", {
          detail: { eventId: detail.citation_event_id, timestampS: detail.start },
        }),
      );
    });
  }

  // Wire citation chip clicks → request tooltip via WS.
  if (drillsEl) {
    drillsEl.addEventListener("citation-click", (e: Event) => {
      const detail = (e as CustomEvent).detail as {
        citation: string;
        anchorX?: number;
        anchorY?: number;
      };
      pendingTooltipAnchor =
        typeof detail.anchorX === "number" && typeof detail.anchorY === "number"
          ? { x: detail.anchorX, y: detail.anchorY }
          : null;
      client.sendCitationTooltipRequest(detail.citation);
    });
    drillsEl.addEventListener("moment-feedback-click", (e: Event) => {
      const detail = (e as MomentFeedbackClickEvent).detail;
      client.sendMomentFeedback({
        moment_id: detail.momentId,
        citation_id: detail.citationId,
        verdict: detail.verdict,
        surface: detail.surface,
      });
    });
  }
  if (waveformEl) {
    waveformEl.addEventListener("region-clicked", (e: Event) => {
      const detail = (e as CustomEvent).detail as {
        citation_event_id: string;
        anchorX?: number;
        anchorY?: number;
      };
      pendingTooltipAnchor =
        typeof detail.anchorX === "number" && typeof detail.anchorY === "number"
          ? { x: detail.anchorX, y: detail.anchorY }
          : null;
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
        resolveSkeletonsToTerminal(skeletonHosts, "sidecar_crashed");
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
  if (bootState.deepLink) {
    const payload = bootState.deepLink;
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

function mountMockDebrief(): void {
  if (errorBanner) errorBanner.hidden = true;

  const totalDurationS = 47 * 60;
  const waveformPeaks = mockWaveformPeaks(192);
  const chapters: ChapterPayload[] = [
    {
      id: "warm-pressure",
      start: 0,
      end: 420,
      label: "00:00 warm pressure",
      kind: "section",
      citation_event_id: "mock:00:00",
    },
    {
      id: "bass-handoff",
      start: 420,
      end: 980,
      label: "07:40 bass handoff",
      kind: "transition",
      citation_event_id: "mock:07:40",
    },
    {
      id: "vocal-drift",
      start: 980,
      end: 1650,
      label: "18:12 vocal drift",
      kind: "tension",
      citation_event_id: "mock:18:12",
    },
    {
      id: "peak-blend",
      start: 1650,
      end: 2310,
      label: "27:55 peak blend",
      kind: "peak",
      citation_event_id: "mock:27:55",
    },
    {
      id: "reset-window",
      start: 2310,
      end: totalDurationS,
      label: "38:30 reset window",
      kind: "release",
      citation_event_id: "mock:38:30",
    },
  ];

  if (chaptersEl) mountChapterList(chaptersEl, chapters);
  if (waveformEl) {
    mountTimelinePlaceholder(
      waveformEl,
      chapters.map((c) => ({
        id: c.id,
        start: c.start,
        end: c.end,
        label: c.label,
        citation_event_id: c.citation_event_id,
        kind: c.kind,
      })),
      totalDurationS,
      waveformPeaks,
    );
  }
  if (morningEl) {
    mountMorningMirror(
      morningEl,
      {
        input_wav_relative_path: "input.wav",
        t_center: 744,
        window: [736, 752],
        receipt_text:
          "the mix recovered by ear at 12:24; clean low end; wall clock 01:42:08 last night.",
        friend_line_text:
          "I heard the mix drift, then you pulled it back inside two bars.",
        duration_s: totalDurationS,
        waveform_peaks: waveformPeaks,
      },
      "/recordings/mock",
      { timelineEl: waveformEl },
    );
  }
  if (tldrPanelEl) {
    // Mock chapters carry no kind=="track" — they speak as MOMENTS, same
    // honest rule as the live path.
    const mockTrackCount = chapters.filter((c) => c.kind === "track").length;
    renderVerdictLine(
      tldrPanelEl,
      buildVerdictText(mockTrackCount, totalDurationS, chapters.length),
    );
  }
  mountMockTldrPlayer(totalDurationS, chapters.length);
  if (drillsEl) {
    mountDrillsPanel(drillsEl, [
      {
        situation: "Bar 24 into the handoff",
        behavior: "Bass swap lands three beats before the old groove releases.",
        impact: "The floor feels the lift as compression instead of forward motion.",
        action_recommended:
          "Hold the new low until bar 33, then lift the filter across eight beats.",
        citation: "mock:12:44",
      },
      {
        situation: "Second blend, phrase overlap",
        behavior: "Two lead vocal phrases sit on top of each other for a full bar.",
        impact: "The hook loses front position and the transition reads less intentional.",
        action_recommended:
          "Kill incoming mids until the outgoing phrase clears, then reopen on the downbeat.",
        citation: "mock:24:18",
      },
      {
        situation: "Reset after the peak blend",
        behavior: "The breakdown clears more bandwidth than the next track can refill.",
        impact: "The room gets a stop signal when it needed a breath signal.",
        action_recommended:
          "Shorten the echo tail and return hats before the next downbeat.",
        citation: "mock:36:02",
      },
    ]);
  }
}

function mockWaveformPeaks(count: number): [number, number, number][] {
  const peaks: [number, number, number][] = [];
  for (let i = 0; i < count; i += 1) {
    const phraseLift = 0.5 + 0.5 * Math.sin(i * 0.08);
    const kick = 0.5 + 0.5 * Math.sin(i * 0.31);
    const hats = 0.5 + 0.5 * Math.cos(i * 0.19);
    peaks.push([
      Math.round(55 + kick * 170),
      Math.round(40 + phraseLift * 130),
      Math.round(24 + hats * 92),
    ]);
  }
  return peaks;
}

function mountMockTldrPlayer(totalDurationS: number, regionCount: number): void {
  if (!tldrEl) return;
  tldrEl.textContent = "";

  const meta = document.createElement("p");
  meta.className = "vmx-debrief-tldr-meta";
  meta.textContent = "74s recap queued · local render";

  const hud = document.createElement("div");
  hud.className = "vmx-debrief-tldr-hud";
  for (const [label, value] of [
    ["Moments", String(regionCount)],
    ["Runtime", formatMockDuration(totalDurationS)],
  ] as const) {
    const cell = document.createElement("span");
    cell.className = "vmx-debrief-tldr-hud-cell";
    const key = document.createElement("small");
    key.textContent = label;
    const readout = document.createElement("strong");
    readout.textContent = value;
    cell.append(key, readout);
    hud.append(cell);
  }

  const rail = document.createElement("div");
  rail.className = "vmx-debrief-tldr-mock-rail";
  rail.setAttribute("aria-hidden", "true");

  for (let i = 0; i < 32; i += 1) {
    const tick = document.createElement("span");
    tick.style.setProperty("--vmx-tick", String((i % 7) + 2));
    rail.append(tick);
  }

  tldrEl.append(meta, hud, rail);
}

function formatMockDuration(totalS: number): string {
  const minutes = Math.round(totalS / 60);
  return `${minutes}m`;
}
