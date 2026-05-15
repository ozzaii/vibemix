// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 Task 2 — TLDR audio player (HTML5 audio + duration display).

export interface TldrPayload {
  audio_relative_path: string;
  duration_s: number;
  tldr_sha256: string;
  mime_type: string;
}

/**
 * Mounts an <audio controls> element for the TL;DR MP3.
 *
 * The session_dir is required so the asset:// URL resolves correctly
 * against the Tauri filesystem scope.
 */
export function mountTldrPlayer(
  container: HTMLElement,
  payload: TldrPayload,
  sessionDirAbs: string,
): void {
  container.textContent = "";

  const duration = document.createElement("p");
  duration.className = "vmx-debrief-tldr-meta";
  duration.textContent = `${Math.round(payload.duration_s)}s • ${payload.mime_type}`;

  const audio = document.createElement("audio");
  audio.controls = true;
  audio.preload = "metadata";
  audio.className = "vmx-debrief-tldr-audio";

  // The Rust shell passes the session-dir absolute path via the URL
  // query; we point the <audio> src at asset://<host>/<abs_path>.
  // convertFileSrc handles the platform-specific prefix; we use it lazily
  // (the @tauri-apps/api/core dynamic import keeps the module testable
  // without Tauri runtime present).
  const url = buildAssetUrl(`${sessionDirAbs}/${payload.audio_relative_path}`);
  audio.src = url;

  container.append(duration, audio);
}

function buildAssetUrl(path: string): string {
  // In production, `@tauri-apps/api/core::convertFileSrc` renders
  // `asset://localhost/<encoded path>`. The function-level import keeps
  // unit tests synchronous; the imports below are static so vitest can
  // hook them.
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const core = (window as unknown as {
      __TAURI__?: { core?: { convertFileSrc?: (s: string) => string } };
    }).__TAURI__?.core;
    if (core?.convertFileSrc) {
      return core.convertFileSrc(path);
    }
  } catch {
    // fall through
  }
  return `asset://localhost/${encodeURI(path)}`;
}
