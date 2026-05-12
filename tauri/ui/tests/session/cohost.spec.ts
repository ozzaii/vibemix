/* Phase 13-03 — focused vitest spec for the cohost transcript header
 * after the 42×42 mascot placeholder drop (CONTEXT.md Open Q 2).
 *
 * Filed under tests/session/ rather than src/session/components/cohost.test.ts
 * (the plan's nominal path) because vitest.config.ts globs only on
 * `*.spec.ts` — co-locating under tests/ keeps the new assertions in the
 * default suite run instead of needing a special invocation.
 *
 * The shared component-suite (tests/session/components.spec.ts) also
 * pins the deletion under its renderCohostPanel block — this file adds
 * Phase-13-specific coverage that's easy to find by name. */

import { afterEach, describe, expect, it } from "vitest";

import {
  renderCohostPanel,
  type TranscriptLine,
} from "../../src/session/components/cohost.js";

function host(): HTMLElement {
  const div = document.createElement("div");
  document.body.append(div);
  return div;
}

afterEach(() => {
  document.body.replaceChildren();
});

describe("cohost transcript header — Phase 13 mascot drop", () => {
  it("renders no .vmx-cohost__mascot bubble in any status", () => {
    for (const status of ["LISTENING", "TALKING", "IDLE"] as const) {
      const panel = renderCohostPanel({
        status,
        transcript: [],
        latencyMs: null,
        grounded: false,
      });
      host().append(panel);
      expect(panel.querySelector(".vmx-cohost__mascot")).toBeNull();
    }
  });

  it("header keeps the AVERY name + status row only", () => {
    const panel = renderCohostPanel({
      status: "TALKING",
      transcript: [],
      latencyMs: null,
      grounded: true,
    });
    host().append(panel);
    const header = panel.querySelector<HTMLElement>(".vmx-cohost__header");
    expect(header).toBeTruthy();
    // Exactly one .vmx-cohost__meta child carrying AVERY + status, no
    // sibling mascot div.
    const metaChildren = header!.querySelectorAll(":scope > *");
    expect(metaChildren).toHaveLength(1);
    expect(metaChildren[0]?.classList.contains("vmx-cohost__meta")).toBe(true);
    expect(panel.querySelector(".vmx-cohost__name")?.textContent).toBe("AVERY");
    expect(
      panel.querySelector<HTMLElement>(".vmx-cohost__status")?.dataset.state,
    ).toBe("TALKING");
  });

  it("transcript still renders messages normally after the header reshape", () => {
    const transcript: TranscriptLine[] = [
      { role: "ai", text: "first", ts: "00:00:01" },
      { role: "ai", text: "second", ts: "00:00:02" },
    ];
    const panel = renderCohostPanel({
      status: "LISTENING",
      transcript,
      latencyMs: 320,
      grounded: true,
    });
    host().append(panel);
    expect(panel.querySelectorAll(".vmx-cohost__msg")).toHaveLength(2);
  });
});
