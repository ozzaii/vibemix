/* debug-log.ts — headless-operator observability sink.
 *
 * Console alone is invisible outside the webview's DevTools, so a headless
 * operator (or an autonomous agent) can't read it. This module mirrors every
 * tagged log line to BOTH:
 *   (a) the webview console (`console.log`) — visible in DevTools, and
 *   (b) a tailable file on disk via the Rust `debug_log` Tauri command
 *       (appends to ~/Library/Application Support/vibemix/logs/ui.log on
 *       macOS; the OS-specific app-local-data dir on Windows). See
 *       tauri/src-tauri/src/debug_log.rs.
 *
 * Contract:
 *   vmxLog(tag, msg, data?) → emits one line shaped:
 *     <ISO-ts> [vmx:click] mood-rocker → set HYPE {"value":"hype-man"}
 *   The tag carries the category ([vmx:click] / [vmx:ipc>] / [vmx:ipc<] /
 *   [vmx:ws] / [vmx:state] / [vmx:error]). `data` is JSON-stringified and
 *   truncated so a large audio/screenshot blob never floods the file.
 *
 * Non-fatal-by-design:
 *   - The file forward is fire-and-forget; a forward failure (not in a Tauri
 *     env, command not registered, disk error) is swallowed so logging never
 *     throws into the call site. Outside Tauri we fall back to console-only.
 *   - We resolve `invoke` lazily (dynamic import) so this module is safe to
 *     import in a plain browser / vitest env where `@tauri-apps/api/core`
 *     would otherwise pull the Tauri IPC shim.
 */

/** Max characters of stringified `data` written per line. A 7s PCM snapshot
 *  or a base64 screenshot would otherwise bloat ui.log; truncate hard. */
const MAX_DATA_CHARS = 2000;

/** Cached lazy `invoke`. `undefined` = not yet resolved; `null` = resolved
 *  to "unavailable" (non-Tauri env) so we stop retrying the dynamic import. */
let cachedInvoke: ((cmd: string, args?: Record<string, unknown>) => Promise<unknown>) | null | undefined;

async function getInvoke(): Promise<
  ((cmd: string, args?: Record<string, unknown>) => Promise<unknown>) | null
> {
  if (cachedInvoke !== undefined) return cachedInvoke;
  try {
    const mod = await import("@tauri-apps/api/core");
    cachedInvoke = mod.invoke as (
      cmd: string,
      args?: Record<string, unknown>,
    ) => Promise<unknown>;
  } catch {
    // Not in a Tauri env (plain browser / test) — disable the file forward.
    cachedInvoke = null;
  }
  return cachedInvoke;
}

/** Stringify + truncate the optional structured payload for one log line. */
export function formatData(data: unknown): string {
  if (data === undefined) return "";
  let s: string;
  try {
    s = typeof data === "string" ? data : JSON.stringify(data);
  } catch {
    // Circular / non-serialisable — fall back to a coarse description.
    s = String(data);
  }
  if (s.length > MAX_DATA_CHARS) {
    s = `${s.slice(0, MAX_DATA_CHARS)}…(+${s.length - MAX_DATA_CHARS} chars)`;
  }
  return s;
}

/** Build the single-line log string (no timestamp — the Rust sink stamps the
 *  file copy; the console copy is timestamped by DevTools itself). Exported
 *  for the unit test so the tag/format contract is pinned. */
export function formatLine(tag: string, msg: string, data?: unknown): string {
  const tail = data === undefined ? "" : ` ${formatData(data)}`;
  return `${tag} ${msg}${tail}`;
}

/**
 * Log one tagged line to the console AND forward it to the on-disk ui.log.
 *
 * @param tag  category tag, e.g. "[vmx:click]" / "[vmx:ipc>]" / "[vmx:error]".
 * @param msg  short human-readable message.
 * @param data optional structured payload (JSON-stringified + truncated).
 */
export function vmxLog(tag: string, msg: string, data?: unknown): void {
  const line = formatLine(tag, msg, data);

  // (a) Console — always, synchronously. Never throws.
  // eslint-disable-next-line no-console
  console.log(line);

  // (b) File forward — fire-and-forget, non-fatal. Errors are swallowed so a
  // logging call can never break a UI interaction.
  void (async () => {
    try {
      const invoke = await getInvoke();
      if (invoke === null) return; // non-Tauri env — console-only.
      await invoke("debug_log", { line });
    } catch {
      // Swallow: command unregistered, disk error, etc. Console copy stands.
    }
  })();
}

/** Reset the lazy invoke cache. Test-only — lets a spec swap the Tauri mock
 *  between cases without a stale resolution leaking across them. */
export function _resetInvokeCacheForTests(): void {
  cachedInvoke = undefined;
}
