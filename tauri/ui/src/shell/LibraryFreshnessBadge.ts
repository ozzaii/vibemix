// SPDX-License-Identifier: Apache-2.0
//
// Compact shell readout for the library freshness engine. The backend already
// computes source-aware freshness; this badge makes that truth visible without
// opening Settings or Crate.

import { libraryStats, type LibraryStats } from "../library/api.js";

export type LibraryFreshnessBadgeState = "ok" | "warn" | "fault" | "empty" | "unknown";

export interface LibraryFreshnessBadgeModel {
  readonly state: LibraryFreshnessBadgeState;
  readonly label: string;
  readonly title: string;
}

export interface LibraryFreshnessBadgeHandle {
  readonly element: HTMLElement;
  refresh(): Promise<void>;
  teardown(): void;
}

export interface LibraryFreshnessBadgeOptions {
  getStats?: () => Promise<LibraryStats>;
  autoload?: boolean;
  pollMs?: number | null;
  onOpenCrate?: () => void;
}

const DEFAULT_POLL_MS = 60_000;

function normalizeFreshnessStatus(stats: LibraryStats | null): string {
  const nested = stats?.library_freshness?.status;
  const topLevel = stats?.library_freshness_status;
  return (nested || topLevel || "unknown").trim().toLowerCase();
}

function stateForFreshness(stats: LibraryStats | null, status: string): LibraryFreshnessBadgeState {
  if (!stats || status === "unknown") return "unknown";
  if (status === "fresh") return "ok";
  if (status === "not_indexed") return "empty";
  if (status === "source_missing" || status === "cache_unreadable") return "fault";
  if (stats.library_stale === true || stats.library_freshness?.stale === true || status === "stale") {
    return "warn";
  }
  return "unknown";
}

function readableStatus(status: string): string {
  return status.replace(/_/g, " ");
}

export function libraryFreshnessBadgeModel(
  stats: LibraryStats | null,
  error?: unknown,
): LibraryFreshnessBadgeModel {
  if (error) {
    return {
      state: "unknown",
      label: "library unknown",
      title: `Library freshness unavailable: ${error instanceof Error ? error.message : String(error)}`,
    };
  }

  const status = normalizeFreshnessStatus(stats);
  const state = stateForFreshness(stats, status);
  const reason = stats?.library_freshness?.reason || stats?.library_staleness_reason || status;
  const age = stats?.library_freshness?.age_days ?? stats?.library_age_days;
  const ageText = typeof age === "number" ? `, ${age}d cache` : "";
  return {
    state,
    label: `library ${readableStatus(status)}`,
    title: `Library freshness: ${readableStatus(reason)}${ageText}`,
  };
}

function renderBadge(element: HTMLElement, model: LibraryFreshnessBadgeModel): void {
  element.dataset.state = model.state;
  element.title = model.title;
  element.setAttribute("aria-label", model.title);
  const label = element.querySelector<HTMLElement>(".library-freshness-label");
  if (label) label.textContent = model.label;
}

export function mountLibraryFreshnessBadge(
  footer: HTMLElement,
  options: LibraryFreshnessBadgeOptions = {},
): LibraryFreshnessBadgeHandle {
  const getStats = options.getStats ?? libraryStats;
  const autoload = options.autoload ?? true;
  const pollMs = options.pollMs === undefined ? DEFAULT_POLL_MS : options.pollMs;
  const onOpenCrate = options.onOpenCrate;

  const separator = document.createElement("span");
  separator.className = "footer-separator";
  separator.setAttribute("aria-hidden", "true");

  const badge =
    onOpenCrate === undefined
      ? document.createElement("span")
      : document.createElement("button");
  badge.className = "library-freshness-badge";
  if (onOpenCrate !== undefined && badge instanceof HTMLButtonElement) {
    badge.type = "button";
    badge.addEventListener("click", onOpenCrate);
  }
  badge.setAttribute("data-wire", "shell.library-freshness");
  badge.innerHTML =
    '<span class="library-freshness-dot" aria-hidden="true"></span>' +
    '<span class="library-freshness-label">library unknown</span>';
  renderBadge(badge, libraryFreshnessBadgeModel(null));
  footer.append(separator, badge);

  let disposed = false;
  const refresh = async (): Promise<void> => {
    try {
      const stats = await getStats();
      if (!disposed) renderBadge(badge, libraryFreshnessBadgeModel(stats));
    } catch (err) {
      if (!disposed) renderBadge(badge, libraryFreshnessBadgeModel(null, err));
    }
  };

  let timer: ReturnType<typeof globalThis.setInterval> | null = null;
  if (pollMs !== null && pollMs > 0) {
    timer = globalThis.setInterval(refresh, pollMs);
  }
  if (autoload) void refresh();

  return {
    element: badge,
    refresh,
    teardown(): void {
      disposed = true;
      if (timer !== null) globalThis.clearInterval(timer);
      separator.remove();
      badge.remove();
    },
  };
}
