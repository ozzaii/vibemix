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
  it("uses native decorations with the macOS overlay titlebar", () => {
    const conf = readUi("../src-tauri/tauri.conf.json5");
    expect(conf).toContain('"label": "main"');
    expect(conf).toContain('"decorations": true');
    expect(conf).toContain('"hiddenTitle": true');
    expect(conf).toContain('"titleBarStyle": "Overlay"');
    expect(conf).toContain('"transparent": false');
  });

  it("reserves the native traffic-light gutter in shell chrome", () => {
    const shell = readUi("src/shell/shell.css");
    const tokens = readUi("src/tokens.css");
    expect(shell).toContain(".shell-chrome .traffic-spacer");
    expect(shell).toContain("width: 72px");
    expect(tokens).toContain("overlay titlebar");
  });

  it("spends native material and demotes sidebar accelerator digits at rest", () => {
    const shell = readUi("src/shell/shell.css");
    const chromeBlock = shell.match(/\.shell-chrome \{[\s\S]*?\n\}/)?.[0] ?? "";
    const sidebarBlock = shell.match(/\.shell-sidebar \{[\s\S]*?\n\}/)?.[0] ?? "";
    expect(shell).toContain("-webkit-backdrop-filter: blur(24px) saturate(1.16)");
    expect(shell).toContain("box-shadow:\n    var(--bevel-raised)");
    expect(sidebarBlock).not.toContain("border-right: 1px solid var(--border-default)");
    expect(chromeBlock).not.toContain("border-bottom: 1px solid var(--border-subtle)");
    expect(shell).toContain(".sb-nav-item .sb-kbd::before");
    expect(shell).toContain(".sb-nav-item:hover .sb-kbd");
    expect(shell).toContain(".sb-nav-item:focus-visible .sb-kbd");
  });
});
