/* Phase 28 Plan 07 — staleness banner.
 *
 * Subscribes to ``ipc.library.staleness_nudge`` and renders an amber banner
 * with the cache age + dismiss + snooze-7d actions. Mount inside the
 * Library section of the Settings drawer (Plan 28-06).
 *
 * IPC contract (Plan 28-09):
 *   inbound:  ipc.library.staleness_nudge { age_days, snoozed_until_ts,
 *                                           source_path?, source_kind?, reason?,
 *                                           schema_version }
 *   outbound: ipc.library.staleness_action { action: "dismiss" | "snooze_7d"
 *                                            | "reindex_folder", schema_version }
 *   outbound: ipc.library.import { path, schema_version } when the stale source is refreshable
 *
 * Visual direction follows project_visual_direction_cdj_whisper:
 *   - amber-2 background tint, amber-3 1px border-bottom
 *   - mono font for age count
 *   - hidden by default (display: none) until a nudge arrives
 */

import { emitIpc, subscribeIpc } from "../../ipc/client.js";
import type { LibraryStalenessNudge } from "../../ipc/messages.js";

export interface StalenessBannerHandle {
  element: HTMLElement;
  dispose(): void;
}

interface StalenessBannerOptions {
  onRefresh?: (path: string, sourceKind: "xml" | "folder") => void | Promise<void>;
}

/** Render the banner. Hidden until ipc.library.staleness_nudge arrives. */
export function renderStalenessBanner(
  opts: StalenessBannerOptions = {},
): StalenessBannerHandle {
  const root = document.createElement("div");
  root.className = "vmx-staleness-banner hidden";
  root.setAttribute("role", "status");
  root.innerHTML = `
    <span class="vmx-staleness-text">
      Library is <em class="vmx-staleness-age">…</em> old.
      <span class="vmx-staleness-copy">Re-import to keep me grounded.</span>
    </span>
    <div class="vmx-staleness-actions">
      <button type="button" class="vmx-staleness-refresh hidden">Refresh library</button>
      <button type="button" class="vmx-staleness-dismiss">Dismiss</button>
      <button type="button" class="vmx-staleness-snooze">Snooze 7 days</button>
    </div>
  `;

  const ageEl = root.querySelector(".vmx-staleness-age") as HTMLElement;
  const copyEl = root.querySelector(".vmx-staleness-copy") as HTMLElement;
  const refreshBtn = root.querySelector(
    ".vmx-staleness-refresh",
  ) as HTMLButtonElement;
  const dismissBtn = root.querySelector(
    ".vmx-staleness-dismiss",
  ) as HTMLButtonElement;
  const snoozeBtn = root.querySelector(
    ".vmx-staleness-snooze",
  ) as HTMLButtonElement;

  let disposed = false;
  let unsub: (() => void) | null = null;
  let refreshPath: string | null = null;
  let refreshKind: "xml" | "folder" | null = null;

  const hide = (): void => {
    root.classList.add("hidden");
  };
  const show = (
    ageDays: number,
    sourcePath: string | null,
    sourceKind: string | null,
    reason: string | null,
  ): void => {
    refreshPath = sourcePath;
    refreshKind = sourceKind === "folder" ? "folder" : sourcePath ? "xml" : null;
    const discoveredButNotIndexed = reason === "source_detected_not_indexed";
    const folderRefresh = refreshKind === "folder";
    ageEl.textContent = discoveredButNotIndexed
      ? "source found"
      : `${ageDays} day${ageDays === 1 ? "" : "s"}`;
    copyEl.textContent = discoveredButNotIndexed
      ? "Import it so Viber can use your tracks."
      : folderRefresh
        ? "Re-index this folder so Viber uses your latest tracks."
        : sourcePath
          ? "Refresh to keep Viber grounded."
          : "Drop the Rekordbox XML or import a folder below.";
    refreshBtn.textContent = discoveredButNotIndexed
      ? "Import library"
      : folderRefresh
        ? "Re-index folder"
        : "Refresh library";
    refreshBtn.classList.toggle("hidden", !sourcePath);
    refreshBtn.disabled = !sourcePath;
    root.classList.remove("hidden");
  };

  refreshBtn.addEventListener("click", () => {
    if (disposed || !refreshPath) return;
    const path = refreshPath;
    const kind = refreshKind || "xml";
    refreshBtn.disabled = true;
    void (async () => {
      try {
        if (opts.onRefresh) {
          await opts.onRefresh(path, kind);
        } else if (kind === "folder") {
          await emitIpc("ipc.library.staleness_action", {
            action: "reindex_folder",
            schema_version: "1",
          });
        } else {
          await emitIpc("ipc.library.import", { path, schema_version: "1" });
        }
        if (!disposed) hide();
      } catch {
        if (!disposed) refreshBtn.disabled = false;
      }
    })();
  });

  dismissBtn.addEventListener("click", () => {
    if (disposed) return;
    void emitIpc("ipc.library.staleness_action", {
      action: "dismiss",
      schema_version: "1",
    });
    hide();
  });
  snoozeBtn.addEventListener("click", () => {
    if (disposed) return;
    void emitIpc("ipc.library.staleness_action", {
      action: "snooze_7d",
      schema_version: "1",
    });
    hide();
  });

  void subscribeIpc<LibraryStalenessNudge>(
    "ipc.library.staleness_nudge",
    (msg) => {
      if (disposed) return;
      show(
        msg.payload.age_days,
        msg.payload.source_path || null,
        msg.payload.source_kind || null,
        msg.payload.reason || null,
      );
    },
  ).then((u) => {
    const disposeSubscription = u as unknown as () => void;
    if (disposed) {
      try {
        disposeSubscription();
      } catch {
        /* ignore */
      }
      return;
    }
    unsub = disposeSubscription;
  });

  return {
    element: root,
    dispose(): void {
      disposed = true;
      if (unsub) {
        try {
          unsub();
        } catch {
          /* ignore */
        }
      }
    },
  };
}
