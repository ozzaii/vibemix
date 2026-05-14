// SPDX-License-Identifier: Apache-2.0
//
// Phase 24 Plan 02 — overlay window runtime.
//
// Reads URL query params (color, duration_ms) and assigns them to CSS
// custom properties on the ring div. The Rust side schedules window close
// after duration_ms, so this script does NOT manage lifetime — it only
// configures the animation.

const params = new URLSearchParams(window.location.search);

// Aligned with the CDJ-Whisper token palette so the overlay ring reads
// against the same colour vocabulary as the rest of the surface. The
// amber matches --amber (#ff8a3d); fault / ok use the LED palette;
// blue is reserved (no current consumer, kept as a named slot).
const COLOR_AMBER = "#ff8a3d";
const COLOR_MAP: Record<string, string> = {
  amber: COLOR_AMBER,
  red: "#d4413a",
  green: "#6dd44a",
  blue: "#4898ff",
};

function resolveColor(raw: string | null): string {
  if (!raw) return COLOR_AMBER;
  const key = raw.toLowerCase();
  // Allowlist-only: refuse arbitrary CSS color injection. Falls back
  // to amber for any unknown token.
  return COLOR_MAP[key] ?? COLOR_AMBER;
}

function resolveDuration(raw: string | null): number {
  const n = raw ? parseInt(raw, 10) : NaN;
  if (!Number.isFinite(n) || n <= 0) return 1300;
  // Clamp to a safety band — Rust enforces the same upper bound via the
  // sidecar publish path, but we re-clamp here so a malformed URL can't
  // freeze a ring on screen.
  return Math.min(Math.max(n, 100), 8000);
}

const color = resolveColor(params.get("color"));
const duration = resolveDuration(params.get("duration_ms"));

const ring = document.getElementById("ring");
if (ring) {
  ring.style.setProperty("--ring-color", color);
  ring.style.setProperty("--ring-duration", `${duration}ms`);
}
