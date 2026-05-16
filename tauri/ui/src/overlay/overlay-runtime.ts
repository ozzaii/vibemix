// SPDX-License-Identifier: Apache-2.0
//
// Phase 24 Plan 02 — overlay window runtime.
//
// Reads URL query params (color, duration_ms) and assigns them to CSS
// custom properties on the ring div. The Rust side schedules window close
// after duration_ms, so this script does NOT manage lifetime — it only
// configures the animation.
//
// VIS-02 (43-02) token-only contract — the 4 ring colours are sourced
// from tokens.css at runtime via getComputedStyle(documentElement). The
// 4 hex literals previously inlined here were duplicates of --amber /
// --led-fault / --led-ok / (the unused 'blue' slot). When tokens.css
// shifts the CDJ-Whisper palette, the overlay ring follows automatically
// instead of drifting silently. Allowlist semantics survive: any
// non-matched key returns the resolved --amber.

const params = new URLSearchParams(window.location.search);

/** Token name per allowlisted ring colour. Note: the overlay webview
 *  loads tokens.css indirectly via the entry HTML's <link>, so by the
 *  time this module runs the CSS custom properties resolve. We keep a
 *  literal-free fallback by computing the value at boot. */
const TOKEN_FOR_KEY: Record<string, string> = {
  amber: "--amber",
  red: "--led-fault",
  green: "--led-ok",
  // Reserved slot — kept as a named entry for future consumers; resolves
  // to --silk so a stray `?color=blue` request degrades gracefully into
  // the silk palette rather than a hard-coded literal.
  blue: "--silk",
};

function resolveTokenValue(token: string): string {
  // The webview rasterises tokens.css before our module runs (link in
  // overlay.html); getComputedStyle reads the resolved string. Trim
  // because CSS variable bodies often carry a leading space.
  if (typeof document === "undefined" || !document.documentElement) return "";
  return getComputedStyle(document.documentElement)
    .getPropertyValue(token)
    .trim();
}

function resolveColor(raw: string | null): string {
  // Allowlist-only: refuse arbitrary CSS color injection. Unknown keys
  // (including raw=null) fall through to the amber token.
  const key = (raw ?? "amber").toLowerCase();
  const tokenName = TOKEN_FOR_KEY[key] ?? "--amber";
  const value = resolveTokenValue(tokenName);
  // Defensive: if tokens.css has not yet cascaded (e.g. webview boot
  // race), fall back to a var() reference so the CSS engine resolves
  // on the next paint cycle. The `var()` body is the token name itself
  // — no inline literal — so the token-only contract holds.
  return value || `var(${tokenName})`;
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
