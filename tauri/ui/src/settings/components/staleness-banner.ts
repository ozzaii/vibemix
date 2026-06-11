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
 *
 * Visual direction follows project_visual_direction_cdj_whisper:
 *   - amber-2 background tint, amber-3 1px border-bottom
 *   - mono font for age count
 *   - hidden by default (display: none) until a nudge arrives
 */

import { emitIpc, subscribeIpc } from "../../ipc/client.js";
import type { LibraryStalenessNudge } from "../../ipc/messages.js";
import { registerStyle } from "../../session/components/_style-registry.js";

/* The banner shipped with NO registered styles: permanently visible raw text
 * reading "Library is … old." over three default buttons. The material below
 * is the drawer's brand-wash banner recipe, and `.hidden` finally works. */
registerStyle(
  "vmx-staleness-banner",
  `
  .vmx-staleness-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-3);
    padding: 10px var(--sp-3);
    border: 1px solid var(--border-default);
    border-radius: var(--rad-sm);
    background:
      linear-gradient(180deg, var(--brand-08), transparent 60%),
      rgba(0, 0, 0, 0.18);
    box-shadow:
      inset 0 1px 0 rgba(246, 243, 245, 0.05),
      inset 0 -1px 0 rgba(0, 0, 0, 0.4);
  }
  .vmx-staleness-banner.hidden { display: none; }
  .vmx-staleness-text {
    font-family: var(--type-body);
    font-size: 12px;
    line-height: 1.4;
    color: var(--text-secondary);
    min-width: 0;
  }
  .vmx-staleness-age {
    font-family: var(--type-mono);
    font-style: normal;
    font-size: 11px;
    letter-spacing: 0.08em;
    color: var(--brand);
  }
  .vmx-staleness-copy { color: var(--text-muted); }
  .vmx-staleness-actions {
    display: flex;
    align-items: center;
    gap: var(--sp-2);
    flex: 0 0 auto;
  }
  .vmx-staleness-actions button {
    font-family: var(--type-mono);
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    padding: 6px 10px;
    color: var(--text-secondary);
    background: linear-gradient(180deg, var(--void-12), var(--void-8));
    border: 1px solid var(--border-default);
    border-radius: var(--rad-sm);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.05),
      inset 0 -1px 0 rgba(0, 0, 0, 0.4);
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s, filter 0.15s;
  }
  .vmx-staleness-actions button:hover {
    color: var(--text-primary);
    border-color: var(--brand-35);
    filter: brightness(1.1);
  }
  .vmx-staleness-actions button.hidden { display: none; }
  .vmx-staleness-actions .vmx-staleness-refresh {
    color: var(--text-primary);
    border-color: var(--brand-35);
    background:
      linear-gradient(180deg, var(--brand-10), var(--brand-04)),
      linear-gradient(180deg, var(--void-12), var(--void-8));
  }
  .vmx-staleness-actions button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
`,
);

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
      <span class="vmx-staleness-copy">Re-index to keep me grounded.</span>
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
    refreshKind = sourceKind === "folder" ? "folder" : null;
    const discoveredButNotIndexed = reason === "source_detected_not_indexed";
    const folderRefresh = refreshKind === "folder";
    ageEl.textContent = discoveredButNotIndexed
      ? "source found"
      : `${ageDays} day${ageDays === 1 ? "" : "s"}`;
    copyEl.textContent = discoveredButNotIndexed
      ? "Index it so Viber can use your tracks."
      : folderRefresh
        ? "Re-index this folder so Viber uses your latest tracks."
        : sourcePath
          ? "Choose a music folder below so Viber can listen locally."
          : "Drop a music folder below.";
    refreshBtn.textContent = discoveredButNotIndexed
      ? "Index folder"
      : "Re-index folder";
    refreshBtn.classList.toggle("hidden", !folderRefresh || !sourcePath);
    refreshBtn.disabled = !folderRefresh || !sourcePath;
    root.classList.remove("hidden");
  };

  refreshBtn.addEventListener("click", () => {
    if (disposed || !refreshPath) return;
    const path = refreshPath;
    const kind = refreshKind;
    refreshBtn.disabled = true;
    void (async () => {
      try {
        if (!kind) {
          return;
        }
        if (opts.onRefresh) {
          await opts.onRefresh(path, kind);
        } else if (kind === "folder") {
          await emitIpc("ipc.library.staleness_action", {
            action: "reindex_folder",
            schema_version: "1",
          });
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
