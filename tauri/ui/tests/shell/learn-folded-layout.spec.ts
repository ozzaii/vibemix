/**
 * @vitest-environment node
 *
 * Folded Learn layout contract. The shipped app embeds Learn inside the shell
 * stage as the Wreck Room booth; it must not behave like a full standalone
 * window there. Two product regressions this covers: (1) Learn opening as the
 * cluttered standalone Earned wall with the practice action floating near the
 * bottom of the whole screen, and (2) the pre-redesign "coming soon" tease
 * shipping as the Learn surface (the parked plate is retired; the booth is
 * the front door).
 */

import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = resolve(__dirname, "../../");

function readUi(path: string): string {
  return readFileSync(resolve(ROOT, path), "utf8");
}

describe("folded Learn shell layout", () => {
  it("mounts the Wreck Room booth without booting the standalone lesson window", () => {
    const app = readUi("src/shell/app.ts");
    expect(app).toContain("mountWreckBooth(mount)");
    expect(app).not.toContain("mountLearnTease");
    expect(app).not.toContain("mountLearnWindow");
    expect(app).not.toContain("mountSkillWall");
    expect(app).not.toContain("../learn/learn-window.js");
    expect(app).not.toContain("../learn/SkillWall.js");
  });

  it("keeps the booth on lean components, never the full learn-window chrome", () => {
    const booth = readUi("src/learn/booth/wreck-booth.ts");
    expect(booth).not.toContain("learn-window");
    expect(booth).not.toContain("SkillWall");
    expect(booth).toContain('"ipc.learn.ack"');
    // round start/stop ride the existing ack wire; no new envelope types
    expect(booth).toContain("wreck_round");
    expect(booth).toContain("wreck_stop");
  });

  it("keeps the Learn nav entry accessible", () => {
    const surfaces = readUi("src/shell/surfaces.ts");
    expect(surfaces).toContain('id: "learn"');
    expect(surfaces).toContain('kbd: "3"');
    expect(surfaces).toContain('label: "Learn"');
  });

  it("styles the booth as a full-bleed folded shell surface", () => {
    const css = readUi("src/shell/shell.css");
    const shell = readUi("src/shell/DesktopShell.ts");
    expect(shell).toContain("host.dataset.surface = model.activeSurface");
    expect(css).toContain(".surface-mount:has(.wreck-booth)");
    expect(css).not.toContain("learn-tease");
  });

  it("guards the legacy session mode path from opening standalone Learn", () => {
    const renderLoop = readUi("src/session/render-loop.ts");
    expect(renderLoop).not.toContain('invoke("open_learn_window")');
  });

  it("guards Debrief referrals from opening standalone Learn", () => {
    const debrief = readUi("src/debrief/debrief-window.ts");
    expect(debrief).not.toContain("open_learn_lesson_window");
    expect(debrief).not.toContain("open_learn_window");
    expect(debrief).not.toContain("learn-referral-click");
  });
});
