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
  it("mounts the lesson runner before the Earned wall", () => {
    const app = readUi("src/shell/app.ts");
    expect(app).toContain("mount.append(lessonHost, wallHost)");
    expect(app.indexOf("mountLearnWindow(lessonHost)")).toBeLessThan(
      app.indexOf("mountSkillWall(wallHost)"),
    );
  });

  it("constrains Learn to the shell stage instead of the viewport", () => {
    const css = readUi("src/shell/shell.css");
    const learn = readUi("src/learn/learn-window.ts");
    const shell = readUi("src/shell/DesktopShell.ts");
    expect(shell).toContain("host.dataset.surface = model.activeSurface");
    expect(learn).toContain("interface StatusTickPayload");
    expect(learn).toContain("payload?:");
    expect(learn).toContain("function statusTickMidiCount");
    expect(learn).toContain("detail?.payload?.midi");
    expect(learn).toContain('"ipc.status.tick"');
    expect(learn).toContain("ready to practice");
    expect(learn).toContain("controller detected");
    expect(learn).toContain("dataset.readiness = readiness");
    expect(learn).toContain('status.setMirrorStatus(nextMidiSeen ? "midi" : "screen")');
    expect(readUi("src/learn/components/status-bar.ts")).toContain('case "midi":');
    expect(readUi("src/learn/components/status-bar.ts")).toContain("controller detected");
    expect(learn).toContain("practice deck ready");
    const wsClient = readUi("src/learn/ws-client.ts");
    expect(wsClient).toContain('const STATUS_TICK_TYPE = "ipc.status.tick"');
    expect(wsClient).toContain("subscribeIpc<StatusTickEnvelope>");
    expect(wsClient).toContain("dispatchStatusTickEnvelope");
    expect(wsClient).toContain("new CustomEvent(STATUS_TICK_TYPE");
    expect(css).toContain(
      '.surface[data-surface="learn"].surface--mounted .surface-mount',
    );
    expect(css).toContain("grid-template-rows: minmax(0, 1fr) auto");
    expect(css).toContain(
      '.surface[data-surface="learn"].surface--mounted .learn-lesson-host #learn-root',
    );
    expect(css).toContain("height: 100%");
    expect(css).toContain("padding-bottom: calc(var(--sp-5) + 24px)");
    expect(css).toContain("#learn-root.lesson-mode");
    expect(css).toContain("grid-template-rows: 56px minmax(0, 1fr) auto minmax(112px, auto)");
    expect(css).toContain(".surface--mounted .learn-titlebar { display: none; }");
    expect(css).toContain(".learn-lesson-host #learn-status-bar");
    expect(css).toContain("display: none");
    expect(css).toContain(".learn-lesson-host .learn-booth-panel");
    expect(css).toContain(".learn-booth-brief");
    expect(css).toContain("position: absolute");
    expect(css).toContain("top: var(--sp-5)");
    expect(css).toContain("bottom: auto");
    expect(css).toContain('[data-readiness="midi"]');
    expect(css).toContain(".learn-lesson-host .learn-footer");
    expect(css).toContain(".learn-earned-wall:has(.skill-wall__empty)");
    expect(css).toContain('#shell-root[data-surface="learn"]');
    expect(css).toContain("--panel-w: 228px");
    expect(css).toContain("grid-template-areas:");
    expect(css).toContain('"kicker primary secondary"');
    expect(css).toContain('"brief primary secondary"');
    expect(css).toContain('"pulse primary secondary"');
    expect(css).toContain("justify-content: stretch");
  });

  it("keeps Earned as compact context in the folded surface", () => {
    const css = readUi("src/shell/shell.css");
    expect(css).toContain(".learn-earned-wall .skill-wall__head");
    expect(css).toContain("display: none");
    expect(css).toContain("grid-template-columns: repeat(3, minmax(0, 1fr))");
    expect(css).toContain(".learn-earned-wall .skill-wall__remains");
    expect(css).toContain(
      '.surface[data-surface="learn"].surface--mounted .learn-booth-earned',
    );
  });
});
