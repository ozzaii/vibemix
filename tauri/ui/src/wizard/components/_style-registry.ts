/* Component-style registry — one shared <style> element per component class.
 *
 * Each component declares its scoped CSS via a class name like
 * `.cmp-step-indicator` and registers the stylesheet ONCE at module load.
 * This keeps every component self-contained (no global CSS sprawl) while
 * avoiding duplicate <style> emission when the component renders many
 * times in a single screen.
 *
 * Anti-pattern guard: components MUST NOT declare hex colors. Every value
 * inside these <style> blocks reads from tokens.css var(--*). The
 * grep gate in PLAN §verification (`! grep -E "#[0-9a-fA-F]{6}"`) fails
 * if any component .ts file slips a literal hex. */

const registered = new Set<string>();

export function registerStyle(scopeKey: string, css: string): void {
  if (registered.has(scopeKey)) return;
  registered.add(scopeKey);
  const style = document.createElement("style");
  style.dataset.scope = scopeKey;
  style.textContent = css;
  document.head.appendChild(style);
}
