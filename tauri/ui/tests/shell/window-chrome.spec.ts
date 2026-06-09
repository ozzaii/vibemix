/**
 * @vitest-environment node
 *
 * Main-window chrome contract. The shipped app should use native macOS
 * decorations with an overlay titlebar so the shell keeps its slim drag chrome
 * while the OS supplies the rounded frame and traffic lights.
 */

import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const UI_ROOT = resolve(__dirname, "../../");

function readUi(path: string): string {
  return readFileSync(resolve(UI_ROOT, path), "utf8");
}

describe("main window chrome", () => {
  it("uses native decorations with the overlay titlebar + native window material", () => {
    const conf = readUi("../src-tauri/tauri.conf.json5");
    expect(conf).toContain('"label": "main"');
    expect(conf).toContain('"decorations": true');
    expect(conf).toContain('"hiddenTitle": true');
    expect(conf).toContain('"titleBarStyle": "Overlay"');
    // Transparent webview so the native window material (macOS NSVisualEffectView
    // "Sidebar" vibrancy / Windows Mica, applied in main.rs) shows through the
    // chrome + sidebar glass; the opaque .shell-main content stage hides it.
    expect(conf).toContain('"transparent": true');
    const main = readUi("../src-tauri/src/main.rs");
    expect(main).toContain("apply_main_native_material");
    expect(main).toContain("NSVisualEffectMaterial::Sidebar");
    // The vibrancy transparency is scoped to the live Tauri runtime so plain
    // Vite/browser dev keeps its opaque scene (no white bleed through the glass).
    const shell = readUi("src/shell/shell.css");
    expect(shell).toContain('html[data-runtime="tauri"]');
  });

  it("reserves the native traffic-light gutter in shell chrome", () => {
    const shell = readUi("src/shell/shell.css");
    const tokens = readUi("src/tokens.css");
    expect(shell).toContain(".shell-chrome .traffic-spacer");
    expect(shell).toContain("width: 72px");
    expect(tokens).toContain("overlay titlebar");
  });

  it("spends native material and seats the accelerator keycaps on the rows", () => {
    const shell = readUi("src/shell/shell.css");
    const chromeBlock = shell.match(/\.shell-chrome \{[\s\S]*?\n\}/)?.[0] ?? "";
    const sidebarBlock = shell.match(/\.shell-sidebar \{[\s\S]*?\n\}/)?.[0] ?? "";
    expect(shell).toContain("-webkit-backdrop-filter: blur(24px) saturate(1.16)");
    expect(shell).toContain("box-shadow:\n    var(--bevel-raised)");
    expect(sidebarBlock).not.toContain("border-right: 1px solid var(--border-default)");
    expect(chromeBlock).not.toContain("border-bottom: 1px solid var(--border-subtle)");
    // Pink-mock 1:1 (fable pass 2026-06-10): the accelerator is a machined
    // keycap ALWAYS seated on the row — gradient face + top specular — not a
    // hover-reveal pill. Active row tints the cap brand.
    const kbdBlock = shell.match(/\.sb-nav-item \.sb-kbd \{[\s\S]*?\n\}/)?.[0] ?? "";
    expect(kbdBlock).toContain("linear-gradient(180deg, var(--void-12) 0%, var(--void-8) 100%)");
    expect(kbdBlock).not.toContain("font-size: 0");
    expect(shell).toContain('.sb-nav-item[aria-current="true"] .sb-kbd');
  });
});
