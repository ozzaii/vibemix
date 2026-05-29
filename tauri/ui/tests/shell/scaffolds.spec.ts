/**
 * @vitest-environment jsdom
 *
 * The scaffold extractor lifts a standalone surface's body markup out of its
 * own HTML entry (imported `?raw`, so it never drifts from the source page) so
 * the shell can inject it into a keep-alive mount and let the surface's module
 * self-boot against its own fixed ids. Crucially it must drop the page's module
 * `<script>`, or importing the module AND leaving the script would double-boot.
 */

import { describe, expect, it } from "vitest";

import { extractSurfaceMarkup } from "../../src/shell/scaffolds.js";

const RAW = `<!DOCTYPE html><html><head><title>x</title></head><body data-mode="chat">
  <div id="app">
    <div class="vmx-lib-app" data-wire="library.shell">
      <button id="vmx-lib-runbtn">go</button>
    </div>
  </div>
  <script type="module" src="/src/library/index.ts"></script>
</body></html>`;

describe("extractSurfaceMarkup", () => {
  it("returns the selected node's outerHTML", () => {
    const m = extractSurfaceMarkup(RAW, ".vmx-lib-app");
    expect(m).toContain('class="vmx-lib-app"');
    expect(m).toContain('id="vmx-lib-runbtn"');
  });

  it("drops the page's module script so importing the module is the single boot", () => {
    const m = extractSurfaceMarkup(RAW, ".vmx-lib-app");
    expect(m).not.toContain("<script");
    expect(m).not.toContain("/src/library/index.ts");
  });

  it("throws a clear error when the selector is absent", () => {
    expect(() => extractSurfaceMarkup(RAW, ".does-not-exist")).toThrow(/does-not-exist/);
  });
});
