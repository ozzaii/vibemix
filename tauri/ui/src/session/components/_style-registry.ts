/* Component-style registry — one shared <style> element per component class.
 *
 * Lifted verbatim from tauri/ui/src/wizard/components/_style-registry.ts. The
 * session components inject their scoped CSS at module load via this singleton
 * so the live session UI carries the same "self-contained component" discipline
 * as the Phase 11 wizard — every component is `(state) => HTMLElement` with
 * its own stylesheet registered exactly once per scope key, regardless of
 * how many instances mount.
 *
 * Anti-pattern guard: components MUST NOT declare hex colours. Every value
 * inside these <style> blocks reads from tokens.css var(--*). The two
 * "paper" surfaces (phase-tape + transcript) are the only exception — they
 * locally scope `--paper-*` variables per Phase 12 UI-SPEC §Color/Paper Family.
 * The grep guard in tests/session/components.spec.ts asserts each component
 * emits zero literal hex outside its declared `--paper-*` scope. */

const registered = new Set<string>();

export function registerStyle(scopeKey: string, css: string): void {
  if (registered.has(scopeKey)) return;
  registered.add(scopeKey);
  const style = document.createElement("style");
  style.dataset.scope = scopeKey;
  style.textContent = css;
  document.head.appendChild(style);
}
