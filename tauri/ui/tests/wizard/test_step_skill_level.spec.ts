// SPDX-License-Identifier: Apache-2.0
//
// Quick 260529-ifq — Skill-level wizard step (position 4, after controller).
//
// Pins the new onboarding surface: a 3-option radio card (beginner /
// intermediate / pro) that mirrors the telemetry-consent pattern. On Continue
// the router emits ipc.wizard.set_skill (covered by the Python handler test);
// this spec pins the render + selection + non-blocking Continue behavior.

import { describe, it, expect, afterEach, vi } from "vitest";
import {
  renderStepSkillLevel,
  type SkillLevelState,
  type SkillLevelCallbacks,
} from "../../src/wizard/step-skill-level.js";

function makeState(over: Partial<SkillLevelState> = {}): SkillLevelState {
  return { skill: "intermediate", ...over };
}

function makeCallbacks(
  over: Partial<SkillLevelCallbacks> = {},
): SkillLevelCallbacks {
  return { onContinue: vi.fn(), onSelect: vi.fn(), onBack: vi.fn(), ...over };
}

afterEach(() => {
  document.body.replaceChildren();
});

describe("wizard step — skill level", () => {
  it("renders the verbatim heading 'STEP 4 / 6 · SKILL'", () => {
    const r = renderStepSkillLevel(makeState(), makeCallbacks());
    document.body.append(r);
    expect(r.querySelector(".wizard-step__heading")?.textContent).toContain(
      "STEP 4 / 6 · SKILL",
    );
  });

  it("renders the verbatim lowercase subtitle", () => {
    const r = renderStepSkillLevel(makeState(), makeCallbacks());
    document.body.append(r);
    expect(r.querySelector(".wizard-step__subtitle")?.textContent).toBe(
      "let vibemix learn your level. coaching matches where you are.",
    );
  });

  it("renders three equal-prominence options", () => {
    const r = renderStepSkillLevel(makeState(), makeCallbacks());
    document.body.append(r);
    expect(r.querySelectorAll(".vmx-skill-level__radio-row")).toHaveLength(3);
  });

  it("pre-selects intermediate by default (data-default + data-selected)", () => {
    const r = renderStepSkillLevel(makeState(), makeCallbacks());
    document.body.append(r);
    const row = r.querySelector<HTMLElement>(
      '.vmx-skill-level__radio-row[data-value="intermediate"]',
    );
    expect(row?.dataset.default).toBe("true");
    expect(row?.dataset.selected).toBe("true");
  });

  it("reflects a non-default selection in data-selected", () => {
    const r = renderStepSkillLevel(makeState({ skill: "pro" }), makeCallbacks());
    document.body.append(r);
    expect(
      r
        .querySelector<HTMLElement>(
          '.vmx-skill-level__radio-row[data-value="pro"]',
        )
        ?.dataset.selected,
    ).toBe("true");
    expect(
      r
        .querySelector<HTMLElement>(
          '.vmx-skill-level__radio-row[data-value="intermediate"]',
        )
        ?.dataset.selected,
    ).toBe("false");
  });

  it("picking 'pro' fires onSelect('pro')", () => {
    const cb = makeCallbacks();
    const r = renderStepSkillLevel(makeState(), cb);
    document.body.append(r);
    r.querySelector<HTMLInputElement>(
      '.vmx-skill-level__radio-row[data-value="pro"] input',
    )!.click();
    expect(cb.onSelect).toHaveBeenCalledTimes(1);
    expect(cb.onSelect).toHaveBeenCalledWith("pro");
  });

  it("Continue is always armed and fires onContinue (non-blocking)", () => {
    const cb = makeCallbacks();
    const r = renderStepSkillLevel(makeState(), cb);
    document.body.append(r);
    const continueBtn = Array.from(
      r.querySelectorAll<HTMLButtonElement>("button"),
    ).find((b) => b.textContent?.includes("Continue"));
    expect(continueBtn).toBeTruthy();
    expect(continueBtn!.disabled).toBe(false);
    continueBtn!.click();
    expect(cb.onContinue).toHaveBeenCalledTimes(1);
  });

  it("Back fires onBack when provided", () => {
    const cb = makeCallbacks();
    const r = renderStepSkillLevel(makeState(), cb);
    document.body.append(r);
    const backBtn = Array.from(
      r.querySelectorAll<HTMLButtonElement>("button"),
    ).find((b) => b.textContent?.includes("Back"));
    backBtn!.click();
    expect(cb.onBack).toHaveBeenCalledTimes(1);
  });
});
