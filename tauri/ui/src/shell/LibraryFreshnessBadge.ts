// SPDX-License-Identifier: Apache-2.0
//
// Compact shell readout for the library freshness engine. The backend already
// computes source-aware freshness; this badge makes that truth visible without
// opening Settings or the Viber surface.

import {
  libraryStats,
  onLibraryImportProgress,
  type LibraryImportProgress,
  type LibrarySetupCandidate,
  type LibraryStats,
} from "../library/api.js";

export type LibraryFreshnessBadgeState =
  | "ok"
  | "warn"
  | "fault"
  | "empty"
  | "setup"
  | "indexing"
  | "unknown";

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
  onOpenViber?: () => void;
  subscribeProgress?: (
    cb: (progress: LibraryImportProgress) => void,
  ) => Promise<() => void>;
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

function librarySetupCandidateLabel(kind: string): string {
  if (kind === "rekordbox_xml") return "Rekordbox XML";
  if (kind === "traktor_nml") return "Traktor NML";
  if (kind === "virtualdj_database") return "VirtualDJ database";
  if (kind === "engine_database") return "Engine DJ database";
  if (kind === "serato_database") return "Serato database";
  if (kind === "music_folder") return "music folder";
  return kind.replace(/_/g, " ");
}

function bestLibrarySetupCandidate(stats: LibraryStats | null): LibrarySetupCandidate | null {
  return (
    stats?.library_setup_candidates?.find((candidate) => candidate.kind === "music_folder") ??
    null
  );
}

export function libraryFreshnessBadgeModel(
  stats: LibraryStats | null,
  error?: unknown,
): LibraryFreshnessBadgeModel {
  if (error) {
    return {
      state: "unknown",
      label: "",
      title: `Library freshness unavailable: ${error instanceof Error ? error.message : String(error)}`,
    };
  }

  const setupCandidate = bestLibrarySetupCandidate(stats);
  if (setupCandidate) {
    const source = librarySetupCandidateLabel(setupCandidate.kind);
    const label = setupCandidate.kind === "music_folder" ? "index music" : "import library";
    const reason = setupCandidate.reason ? ` · ${setupCandidate.reason}` : "";
    return {
      state: "setup",
      label,
      title: `Library setup: found ${source} at ${setupCandidate.path}${reason}`,
    };
  }

  const status = normalizeFreshnessStatus(stats);
  const state = stateForFreshness(stats, status);
  const reason = stats?.library_freshness?.reason || stats?.library_staleness_reason || status;
  const age = stats?.library_freshness?.age_days ?? stats?.library_age_days;
  const ageText = typeof age === "number" ? `, ${age}d cache` : "";
  return {
    state,
    label: state === "unknown" ? "" : `library ${readableStatus(status)}`,
    title: `Library freshness: ${readableStatus(reason)}${ageText}`,
  };
}

function renderBadge(
  element: HTMLElement,
  separator: HTMLElement,
  model: LibraryFreshnessBadgeModel,
): void {
  element.dataset.state = model.state;
  element.title = model.title;
  element.setAttribute("aria-label", model.title);
  const label = element.querySelector<HTMLElement>(".library-freshness-label");
  if (label) label.textContent = model.label;
  // "unknown" is the pre-load / backend-hiccup state. It stays honest in
  // dataset.state + title (for AT and dev), but it must not paint a "library
  // unknown" chip that reads as broken from frame zero: a stable indeterminate
  // state shows no chrome (the separator hides with it so nothing dangles).
  const hidden = model.state === "unknown";
  element.hidden = hidden;
  separator.hidden = hidden;
}

export function mountLibraryFreshnessBadge(
  footer: HTMLElement,
  options: LibraryFreshnessBadgeOptions = {},
): LibraryFreshnessBadgeHandle {
  const getStats = options.getStats ?? libraryStats;
  const autoload = options.autoload ?? true;
  const pollMs = options.pollMs === undefined ? DEFAULT_POLL_MS : options.pollMs;
  const onOpenViber = options.onOpenViber;
  const subscribeProgress = options.subscribeProgress ?? onLibraryImportProgress;

  const separator = document.createElement("span");
  separator.className = "footer-separator";
  separator.setAttribute("aria-hidden", "true");

  const badge =
    onOpenViber === undefined
      ? document.createElement("span")
      : document.createElement("button");
  badge.className = "library-freshness-badge";
  if (onOpenViber !== undefined && badge instanceof HTMLButtonElement) {
    badge.type = "button";
    badge.addEventListener("click", onOpenViber);
  }
  badge.setAttribute("data-wire", "shell.library-freshness");
  badge.innerHTML =
    '<span class="library-freshness-dot" aria-hidden="true"></span>' +
    '<span class="library-freshness-label"></span>';
  renderBadge(badge, separator, libraryFreshnessBadgeModel(null));
  footer.append(separator, badge);

  let disposed = false;
  const refresh = async (): Promise<void> => {
    try {
      const stats = await getStats();
      if (!disposed) renderBadge(badge, separator, libraryFreshnessBadgeModel(stats));
    } catch (err) {
      if (!disposed) renderBadge(badge, separator, libraryFreshnessBadgeModel(null, err));
    }
  };

  let timer: ReturnType<typeof globalThis.setInterval> | null = null;
  if (pollMs !== null && pollMs > 0) {
    timer = globalThis.setInterval(refresh, pollMs);
  }
  if (autoload) void refresh();

  let progressUnlisten: () => void = () => {};
  void subscribeProgress((progress) => {
    if (disposed) return;
    const terminal =
      progress.cancelled || progress.total <= 0 || progress.done >= progress.total;
    if (terminal) {
      void refresh();
      return;
    }
    renderBadge(badge, separator, {
      state: "indexing",
      label: `indexing ${progress.done}/${progress.total}`,
      title:
        "Library embedding locally: go run a set, it'll be ready when you're back",
    });
  }).then((un) => {
    if (disposed) {
      un();
      return;
    }
    progressUnlisten = un;
  });

  return {
    element: badge,
    refresh,
    teardown(): void {
      disposed = true;
      progressUnlisten();
      if (timer !== null) globalThis.clearInterval(timer);
      separator.remove();
      badge.remove();
    },
  };
}
