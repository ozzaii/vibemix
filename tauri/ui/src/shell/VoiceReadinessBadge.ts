// SPDX-License-Identifier: Apache-2.0
//
// Compact shell readout for the local MOSS voice model. The real install/check
// surface already lives in Crate; this badge only makes the fresh-machine truth
// visible from the live deck and routes the user there.

import {
  libraryModels,
  type LibraryModelAsset,
  type LibraryModelsResult,
} from "../library/api.js";

export type VoiceReadinessBadgeState = "ok" | "warn" | "fault" | "unknown";

export interface VoiceReadinessBadgeModel {
  readonly state: VoiceReadinessBadgeState;
  readonly label: string;
  readonly title: string;
}

export interface VoiceReadinessBadgeHandle {
  readonly element: HTMLElement;
  refresh(): Promise<void>;
  teardown(): void;
}

export interface VoiceReadinessBadgeOptions {
  getModels?: () => Promise<LibraryModelsResult>;
  autoload?: boolean;
  pollMs?: number | null;
  onOpenCrate?: () => void;
}

const DEFAULT_POLL_MS = 120_000;

function mossModel(models: LibraryModelsResult | null): LibraryModelAsset | null {
  return models?.models.find((model) => model.id === "moss-tts") ?? null;
}

export function voiceReadinessBadgeModel(
  models: LibraryModelsResult | null,
  error?: unknown,
): VoiceReadinessBadgeModel {
  if (error) {
    return {
      state: "unknown",
      label: "voice unknown",
      title: `MOSS voice status unavailable: ${
        error instanceof Error ? error.message : String(error)
      }`,
    };
  }

  const moss = mossModel(models);
  if (!moss) {
    return {
      state: "unknown",
      label: "voice unknown",
      title: "MOSS voice status unavailable: model row missing",
    };
  }

  const mismatched = (moss.mismatched?.length ?? 0) > 0;
  const installable = moss.installable === true;
  const missing = moss.missing.length > 0 ? `, missing ${moss.missing.length} files` : "";
  const path = moss.path ? ` (${moss.path})` : "";

  if (moss.installed && !mismatched) {
    return {
      state: "ok",
      label: "voice ready",
      title: `MOSS voice ready${path}`,
    };
  }

  if (mismatched) {
    return {
      state: installable ? "warn" : "fault",
      label: installable ? "voice repair" : "voice manual",
      title: `MOSS voice needs repair${missing}${path}`,
    };
  }

  return {
    state: installable ? "warn" : "fault",
    label: installable ? "voice missing" : "voice manual",
    title: `MOSS voice model missing${missing}${path}`,
  };
}

function renderBadge(element: HTMLElement, model: VoiceReadinessBadgeModel): void {
  element.dataset.state = model.state;
  element.title = model.title;
  element.setAttribute("aria-label", model.title);
  const label = element.querySelector<HTMLElement>(".voice-readiness-label");
  if (label) label.textContent = model.label;
}

export function mountVoiceReadinessBadge(
  footer: HTMLElement,
  options: VoiceReadinessBadgeOptions = {},
): VoiceReadinessBadgeHandle {
  const getModels = options.getModels ?? (() => libraryModels());
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
  badge.className = "voice-readiness-badge";
  if (onOpenCrate !== undefined && badge instanceof HTMLButtonElement) {
    badge.type = "button";
    badge.addEventListener("click", onOpenCrate);
  }
  badge.setAttribute("data-wire", "shell.voice-readiness");
  badge.innerHTML =
    '<span class="voice-readiness-dot" aria-hidden="true"></span>' +
    '<span class="voice-readiness-label">voice unknown</span>';
  renderBadge(badge, voiceReadinessBadgeModel(null));
  footer.append(separator, badge);

  let disposed = false;
  const refresh = async (): Promise<void> => {
    try {
      const models = await getModels();
      if (!disposed) renderBadge(badge, voiceReadinessBadgeModel(models));
    } catch (err) {
      if (!disposed) renderBadge(badge, voiceReadinessBadgeModel(null, err));
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
