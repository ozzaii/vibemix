// SPDX-License-Identifier: Apache-2.0
//
// Surface-scaffold extraction. Some surfaces (the library/Viber crate) were
// built as standalone windows whose module self-boots against fixed DOM ids
// defined in their own HTML entry (library.html). To fold such a surface into
// the shell WITHOUT editing its module, the shell injects that page's body
// markup into a keep-alive mount, then imports the module — which finds its ids
// via `document.getElementById` and mounts.
//
// The page markup is lifted from the source HTML imported `?raw`, so it can
// never drift from the real entry (they are edited together by the surface's
// owner). The page's own `<script>` is dropped: the shell imports the module
// itself, so leaving the inline script would boot it twice.

/**
 * Extract a single element's `outerHTML` from a raw HTML document string.
 * Throws if the selector matches nothing (a silent empty mount would look like
 * a blank surface). The parsed document's scripts are inert (DOMParser does not
 * execute them) and are excluded unless they sit inside the selected node.
 */
export function extractSurfaceMarkup(rawHtml: string, selector: string): string {
  const doc = new DOMParser().parseFromString(rawHtml, "text/html");
  const node = doc.querySelector(selector);
  if (!node) {
    throw new Error(`scaffolds: selector "${selector}" not found in raw HTML`);
  }
  // Defensive: strip any <script> that happens to live inside the node, so the
  // injected markup can never re-trigger a module boot.
  for (const script of Array.from(node.querySelectorAll("script"))) {
    script.remove();
  }
  return node.outerHTML;
}
