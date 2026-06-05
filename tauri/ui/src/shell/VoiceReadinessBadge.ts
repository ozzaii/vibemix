// SPDX-License-Identifier: Apache-2.0
//
// Compact shell readout for the local MOSS voice model. The real install/check
// surface already lives in Viber; this badge only makes the fresh-machine truth
// visible from the live deck and routes the user there.

import {
  libraryModels,
  type LibraryModelAsset,
  type LibraryModelsResult,
} from "../library/api.js";
import { subscribeIpc } from "../ipc/client.js";
import type { StatusTick } from "../ipc/messages.js";

export type VoiceReadinessBadgeState = "ok" | "warn" | "fault" | "unknown";
export type RuntimeVoiceStatus = "ok" | "muted" | null;

export interface VoiceReadinessBadgeModel {
  readonly state: VoiceReadinessBadgeState;
  readonly label: string;
  readonly title: string;
}

export interface VoiceReadinessBadgeHandle {
  readonly element: HTMLElement;
  refresh(): Promise<void>;
  setVoiceStatus(status: RuntimeVoiceStatus): void;
  teardown(): void;
}

export interface VoiceReadinessBadgeOptions {
  getModels?: () => Promise<LibraryModelsResult>;
  autoload?: boolean;
  pollMs?: number | null;
  subscribeStatusTick?: boolean;
  onOpenCrate?: () => void;
}

const DEFAULT_POLL_MS = 120_000;

function mossModel(models: LibraryModelsResult | null): LibraryModelAsset | null {
  return models?.models.find((model) => model.id === "moss-tts") ?? null;
}

export function voiceReadinessBadgeModel(
  models: LibraryModelsResult | null,
  error?: unknown,
  runtimeVoice: RuntimeVoiceStatus = null,
): VoiceReadinessBadgeModel {
  if (runtimeVoice === "muted") {
    return {
      state: "warn",
      label: "voice muted",
      title: "Local MOSS voice is muted for this session.",
    };
  }

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

function renderBadge(
  element: HTMLElement,
  separator: HTMLElement,
  model: VoiceReadinessBadgeModel,
): void {
  element.dataset.state = model.state;
  element.title = model.title;
  element.setAttribute("aria-label", model.title);
  const label = element.querySelector<HTMLElement>(".voice-readiness-label");
  if (label) label.textContent = model.label;
  // "unknown" is the pre-load / backend-hiccup state. It stays honest in
  // dataset.state + title (for AT and dev), but it must not paint a "voice
  // unknown" chip that reads as broken from frame zero: a stable indeterminate
  // state shows no chrome (the separator hides with it so nothing dangles).
  const hidden = model.state === "unknown";
  element.hidden = hidden;
  separator.hidden = hidden;
}

export function mountVoiceReadinessBadge(
  footer: HTMLElement,
  options: VoiceReadinessBadgeOptions = {},
): VoiceReadinessBadgeHandle {
  const getModels = options.getModels ?? (() => libraryModels());
  const autoload = options.autoload ?? true;
  const pollMs = options.pollMs === undefined ? DEFAULT_POLL_MS : options.pollMs;
  const subscribeStatusTick = options.subscribeStatusTick ?? true;
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
  renderBadge(badge, separator, voiceReadinessBadgeModel(null));
  footer.append(separator, badge);

  let disposed = false;
  let latestModels: LibraryModelsResult | null = null;
  let latestError: unknown;
  let latestRuntimeVoice: RuntimeVoiceStatus = null;

  const renderCurrent = (): void => {
    if (!disposed) {
      renderBadge(
        badge,
        separator,
        voiceReadinessBadgeModel(latestModels, latestError, latestRuntimeVoice),
      );
    }
  };

  const refresh = async (): Promise<void> => {
    try {
      const models = await getModels();
      latestModels = models;
      latestError = undefined;
      renderCurrent();
    } catch (err) {
      latestModels = null;
      latestError = err;
      renderCurrent();
    }
  };

  const setVoiceStatus = (status: RuntimeVoiceStatus): void => {
    if (status === latestRuntimeVoice) return;
    latestRuntimeVoice = status;
    renderCurrent();
  };

  let timer: ReturnType<typeof globalThis.setInterval> | null = null;
  if (pollMs !== null && pollMs > 0) {
    timer = globalThis.setInterval(refresh, pollMs);
  }
  if (autoload) void refresh();

  const unlistenStatusPromise = subscribeStatusTick
    ? subscribeIpc<StatusTick>("ipc.status.tick", (msg) => {
        setVoiceStatus(msg.payload.voice ?? null);
      })
    : Promise.resolve(() => {});

  return {
    element: badge,
    refresh,
    setVoiceStatus,
    teardown(): void {
      disposed = true;
      if (timer !== null) globalThis.clearInterval(timer);
      void unlistenStatusPromise.then((unlisten) => unlisten?.()).catch(() => {});
      separator.remove();
      badge.remove();
    },
  };
}
