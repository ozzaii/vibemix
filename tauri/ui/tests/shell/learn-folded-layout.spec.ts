/**
 * @vitest-environment node
 *
 * Folded Learn layout contract. The shipped app embeds Learn inside the shell
 * stage; it must not behave like a full standalone window there. The product
 * regression this covers: Learn opened as a cluttered Earned wall with the
 * actual practice action floating near the bottom of the whole screen.
 */

import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = resolve(__dirname, "../../");

function readUi(path: string): string {
  return readFileSync(resolve(ROOT, path), "utf8");
}

describe("folded Learn shell layout", () => {
  it("mounts the coming-soon tease without booting the lesson runner", () => {
    const app = readUi("src/shell/app.ts");
    expect(app).toContain("mountLearnTease(mount)");
    expect(app).toContain("Teaching that earns its place.");
    expect(app).not.toContain("mountLearnWindow");
    expect(app).not.toContain("mountSkillWall");
    expect(app).not.toContain("../learn/learn-window.js");
    expect(app).not.toContain("../learn/SkillWall.js");
  });

  it("keeps the Learn nav entry accessible as a parked launch surface", () => {
    const surfaces = readUi("src/shell/surfaces.ts");
    expect(surfaces).toContain('id: "learn"');
    expect(surfaces).toContain('kbd: "3"');
    expect(surfaces).toContain('label: "Learn"');
  });

  it("styles the parked Learn tease as a folded shell surface", () => {
    const css = readUi("src/shell/shell.css");
    const shell = readUi("src/shell/DesktopShell.ts");
    expect(shell).toContain("host.dataset.surface = model.activeSurface");
    expect(css).toContain(".surface-mount:has(.learn-tease)");
    expect(css).toContain(".learn-tease__plate");
    expect(css).toContain(".learn-tease__proof");
    expect(css).toContain(".learn-tease__led");
  });

  it("guards the legacy session mode path from opening standalone Learn", () => {
    const renderLoop = readUi("src/session/render-loop.ts");
    expect(renderLoop).toContain('if (mode === "learn") return Promise.resolve("learn-tease")');
    expect(renderLoop).not.toContain('invoke("open_learn_window")');
  });

  it("guards Debrief referrals from opening standalone Learn", () => {
    const debrief = readUi("src/debrief/debrief-window.ts");
    expect(debrief).not.toContain("open_learn_lesson_window");
    expect(debrief).not.toContain("open_learn_window");
    expect(debrief).not.toContain("learn-referral-click");
  });
});
