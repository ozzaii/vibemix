/* Phase 28 Plan 07 — staleness banner.
 *
 * Subscribes to ``ipc.library.staleness_nudge`` and renders an amber banner
 * with the cache age + dismiss + snooze-7d actions. Mount inside the
 * Library section of the Settings drawer (Plan 28-06).
 *
 * IPC contract (Plan 28-09):
 *   inbound:  ipc.library.staleness_nudge { age_days, snoozed_until_ts, schema_version }
 *   outbound: ipc.library.staleness_action { action: "dismiss" | "snooze_7d", schema_version }
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

/** Render the banner. Hidden until ipc.library.staleness_nudge arrives. */
export function renderStalenessBanner(): StalenessBannerHandle {
  const root = document.createElement("div");
  root.className = "vmx-staleness-banner hidden";
  root.setAttribute("role", "status");
  root.innerHTML = `
    <span class="vmx-staleness-text">
      Library is <em class="vmx-staleness-age">…</em> old.
      Re-import to keep me grounded.
    </span>
    <div class="vmx-staleness-actions">
      <button type="button" class="vmx-staleness-dismiss">Dismiss</button>
      <button type="button" class="vmx-staleness-snooze">Snooze 7 days</button>
    </div>
  `;

  const ageEl = root.querySelector(".vmx-staleness-age") as HTMLElement;
  const dismissBtn = root.querySelector(
    ".vmx-staleness-dismiss",
  ) as HTMLButtonElement;
  const snoozeBtn = root.querySelector(
    ".vmx-staleness-snooze",
  ) as HTMLButtonElement;

  const hide = (): void => {
    root.classList.add("hidden");
  };
  const show = (ageDays: number): void => {
    ageEl.textContent = `${ageDays} day${ageDays === 1 ? "" : "s"}`;
    root.classList.remove("hidden");
  };

  dismissBtn.addEventListener("click", () => {
    void emitIpc("ipc.library.staleness_action", {
      action: "dismiss",
      schema_version: "1",
    });
    hide();
  });
  snoozeBtn.addEventListener("click", () => {
    void emitIpc("ipc.library.staleness_action", {
      action: "snooze_7d",
      schema_version: "1",
    });
    hide();
  });

  let unsub: (() => void) | null = null;
  void subscribeIpc<LibraryStalenessNudge>(
    "ipc.library.staleness_nudge",
    (msg) => {
      show(msg.payload.age_days);
    },
  ).then((u) => {
    unsub = u as unknown as () => void;
  });

  return {
    element: root,
    dispose(): void {
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
