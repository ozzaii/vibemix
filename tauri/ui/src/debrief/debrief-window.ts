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
import {
  mountBravohWaitlistToggle,
  type BravohWaitlistToggleHandle,
} from "./components/bravoh-waitlist-toggle.js";
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
document.title = `Debrief · ${sessionId}`;

const errorBanner = document.getElementById("vmx-debrief-error-banner");
const tooltip = document.getElementById("vmx-debrief-tooltip");
const chaptersEl = document.getElementById("vmx-debrief-chapters");
const drillsEl = document.getElementById("vmx-debrief-drills-list");
const tldrEl = document.getElementById("vmx-debrief-tldr-player");
const waveformEl = document.getElementById("vmx-debrief-waveform");
const earTestToggleEl = document.getElementById("vmx-debrief-ear-test-toggle");
const bravohWaitlistToggleEl = document.getElementById(
  "vmx-debrief-bravoh-waitlist-toggle",
);

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

// ---------------------------------------------------------------------------
// Plan 44-04 / LAUNCH-05 — Bravoh waitlist toggle mount
//
// Independent of the debrief WS session — the toggle reads/writes a
// user-level config field (config_store.bravoh_waitlist_opt_in, Plan
// 44-04 Task 1) and only affects whether a subtle link to the canonical
// Bravoh waitlist URL is visible in the debrief surface.
//
// Persistence boundary:
//   - On mount, read initial state via Tauri IPC `read_bravoh_waitlist_opt_in`
//     (falls back to OFF when the runtime isn't present — e.g. vitest,
//     `vite dev`, or pre-IPC-wiring builds).
//   - On user toggle, persist via `write_bravoh_waitlist_opt_in`. Failure
//     surfaces via the error banner; the toggle state is rolled back so
//     the UI stays consistent with disk.
//
// Anti-scope-creep (memory `feedback_no_scope_creep_clean_utility`):
//   - No analytics fire. The IPC call is local-only — it writes
//     `bravoh_waitlist_opt_in: bool` to config_store via the sidecar.
//   - No second IPC for "diagnostic event" — the contract is "the
//     config-write IS the diagnostic". Avoids a second telemetry surface.
// ---------------------------------------------------------------------------

(async () => {
  if (!bravohWaitlistToggleEl) return;

  // Tauri invoke shim — kept loose so the file remains importable in
  // dev / vitest where `@tauri-apps/api/core` may not resolve.
  type InvokeFn = <T>(cmd: string, args?: Record<string, unknown>) => Promise<T>;
  let invokeFn: InvokeFn | null = null;
  try {
    const core = await import("@tauri-apps/api/core");
    // Two-step cast through `unknown` — Tauri's invoke is generic; we
    // narrow at each call site below.
    invokeFn = core.invoke as unknown as InvokeFn;
  } catch {
    // Not running under Tauri (dev / test) — invokeFn stays null,
    // initial state stays OFF, onToggle is a no-op write.
  }

  // Read initial state — graceful fallback to OFF when the runtime is
  // absent OR the Rust command isn't yet wired (treat as "user has
  // never opted in", which is the default-OFF contract).
  let initialOptIn = false;
  if (invokeFn) {
    try {
      const value = await invokeFn<unknown>("read_bravoh_waitlist_opt_in");
      if (typeof value === "boolean") {
        initialOptIn = value;
      }
    } catch {
      // Command not yet wired on the Rust side — keep default OFF.
    }
  }

  const localInvoke = invokeFn;
  let handle: BravohWaitlistToggleHandle | null = null;
  handle = mountBravohWaitlistToggle(bravohWaitlistToggleEl, {
    initialOptIn,
    onToggle: (next: boolean): void => {
      // Persist via Tauri IPC. Rollback the toggle on failure so the
      // visible state stays consistent with disk.
      if (!localInvoke) return;
      void (async () => {
        try {
          await localInvoke<void>("write_bravoh_waitlist_opt_in", {
            value: next,
          });
        } catch (err) {
          // Roll back via the imperative setter (does NOT re-fire
          // onToggle, so we avoid a write loop).
          handle?.setOptIn(!next);
          if (errorBanner) {
            showErrorBanner(
              errorBanner,
              "tldr_generation_failed",
              `Couldn't save Bravoh waitlist preference: ${String(
                (err as Error)?.message ?? err,
              )}`,
            );
          }
        }
      })();
    },
  });
})();
