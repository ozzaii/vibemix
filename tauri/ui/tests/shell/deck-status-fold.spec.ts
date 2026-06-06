/**
 * @vitest-environment node
 *
 * F1: the folded SessionLayout status row must stay out of the shell deck.
 * jsdom cannot prove the visual overlap, so this guards the source contract
 * while live by-eye proof covers the actual stacked chrome.
 */

import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const UI_ROOT = resolve(__dirname, "../../");

function readUi(path: string): string {
  return readFileSync(resolve(UI_ROOT, path), "utf8");
}

describe("deck-fold status-row suppression", () => {
  it("suppresses the folded session status row under .surface--deck", () => {
    const shell = readUi("src/shell/shell.css");
    expect(shell).toContain(".surface--deck .vmx-statusrow { display: none; }");
    expect(shell).toContain(".surface--deck .vmx-titlebar { display: none; }");
    expect(shell).toContain(".surface--deck .vmx-modebar { display: none; }");
  });

  it("keeps the standalone SessionLayout status row intact", () => {
    const layout = readUi("src/session/SessionLayout.ts");
    expect(layout).toContain(".vmx-statusrow[hidden] { display: none; }");
    expect(layout).toContain("statusRow.hidden = true;");
  });
});
