// SPDX-License-Identifier: Apache-2.0
//
// Phase 97 / ONBOARD-04 — Headphone device picker on wizard step 2.
//
// Pins the picker surface: an additional DropdownDevice below the
// master-output picker. Users pick where tutor exemplar playback should
// route (default = system output). The wire shape is the EXISTING
// ipc.settings.set { field: 'learn.headphone_device_index' } envelope
// landed in P93 — this plan adds the picker UI, not the wire field.

import { describe, it, expect, afterEach, vi } from "vitest";
import {
  renderStep2,
  type Step2State,
  type Step2Callbacks,
} from "../../src/wizard/step2-output-device.js";

function makeState(over: Partial<Step2State> = {}): Step2State {
  return {
    blackHolePresent: false,
    blackHoleBannerPostClick: false,
    devices: [
      { id: "0", name: "MacBook Pro Speakers" },
      { id: "1", name: "AirPods Pro", isHeadphones: true },
      { id: "2", name: "BlackHole 2ch" },
    ],
    selectedDeviceId: "0",
    selectedHeadphoneDeviceIndex: null,
    ...over,
  };
}

function makeCallbacks(over: Partial<Step2Callbacks> = {}): Step2Callbacks {
  return {
    platform: "darwin",
    onContinue: vi.fn(),
    onSelectDevice: vi.fn(),
    onOpenInstall: vi.fn(),
    onRecheckBlackHole: vi.fn(),
    onBack: vi.fn(),
    onSelectHeadphoneDevice: vi.fn(),
    ...over,
  };
}

afterEach(() => {
  document.body.replaceChildren();
});

describe("wizard step 2 — headphone picker (ONBOARD-04)", () => {
  it("renders the headphone picker section when onSelectHeadphoneDevice is wired", () => {
    const rendered = renderStep2(makeState(), makeCallbacks());
    document.body.append(rendered);
    const section = rendered.querySelector<HTMLElement>(
      ".wizard-step__headphone-picker",
    );
    expect(section).not.toBeNull();
  });

  it("does NOT render the picker section when onSelectHeadphoneDevice is absent (back-compat)", () => {
    const rendered = renderStep2(
      makeState(),
      makeCallbacks({ onSelectHeadphoneDevice: undefined }),
    );
    document.body.append(rendered);
    const section = rendered.querySelector<HTMLElement>(
      ".wizard-step__headphone-picker",
    );
    expect(section).toBeNull();
  });

  it("carries the verbatim heading + helper copy (tone-disciplined lowercase)", () => {
    const rendered = renderStep2(makeState(), makeCallbacks());
    document.body.append(rendered);
    const heading = rendered.querySelector<HTMLElement>(
      ".wizard-step__headphone-picker__heading",
    );
    const helper = rendered.querySelector<HTMLElement>(
      ".wizard-step__headphone-picker__helper",
    );
    expect(heading?.textContent).toBe("tutor exemplar playback (headphones)");
    expect(helper?.textContent).toBe(
      "beginner lessons play short audio examples; pick where they should come out.",
    );
  });

  it("does not render the retired tone or fake window controls", () => {
    const rendered = renderStep2(makeState(), makeCallbacks());
    document.body.append(rendered);

    expect(rendered.querySelector(".cmp-audio-test")).toBeNull();
    expect(rendered.querySelector(".cmp-window-picker")).toBeNull();
    expect(rendered.textContent).not.toContain("1 kHz");
    expect(rendered.textContent).not.toContain("clean tone");
    expect(rendered.textContent).not.toContain("Pick a different window");
    expect(rendered.textContent).not.toContain("Chrome");
  });

  it("the default selection is the '[ system default ]' pseudo-option", () => {
    const rendered = renderStep2(
      makeState({ selectedHeadphoneDeviceIndex: null }),
      makeCallbacks(),
    );
    document.body.append(rendered);
    const section = rendered.querySelector<HTMLElement>(
      ".wizard-step__headphone-picker",
    );
    expect(section).not.toBeNull();
    // The DropdownDevice surfaces the current selected name in its head row.
    // When index is null, the picker shows "[ system default ]".
    const headName = section!.querySelector<HTMLElement>(
      ".cmp-dropdown-device__name",
    );
    expect(headName?.textContent).toBe("[ system default ]");
  });

  it("the system-default option lives at the top of the dropdown list (before any real device)", () => {
    const rendered = renderStep2(makeState(), makeCallbacks());
    document.body.append(rendered);
    const section = rendered.querySelector<HTMLElement>(
      ".wizard-step__headphone-picker",
    );
    expect(section).not.toBeNull();
    // Open the dropdown
    const head = section!.querySelector<HTMLElement>(
      ".cmp-dropdown-device__head",
    );
    head!.click();
    // First option in the panel should be "[ system default ]"
    const firstOption = section!.querySelector<HTMLElement>(
      ".cmp-dropdown-device__option",
    );
    expect(firstOption?.textContent).toContain("[ system default ]");
  });

  it("picking a real device fires onSelectHeadphoneDevice with the integer index", () => {
    const cb = makeCallbacks();
    const rendered = renderStep2(makeState(), cb);
    document.body.append(rendered);
    const section = rendered.querySelector<HTMLElement>(
      ".wizard-step__headphone-picker",
    );
    const head = section!.querySelector<HTMLElement>(
      ".cmp-dropdown-device__head",
    );
    head!.click();
    // Find the option for device id "1" (AirPods Pro)
    const airpodsOption = section!.querySelector<HTMLElement>(
      ".cmp-dropdown-device__option[data-id='1']",
    );
    expect(airpodsOption).not.toBeNull();
    airpodsOption!.click();
    expect(cb.onSelectHeadphoneDevice).toHaveBeenCalledTimes(1);
    expect(cb.onSelectHeadphoneDevice).toHaveBeenCalledWith(1);
  });

  it("picking the system-default option fires onSelectHeadphoneDevice with null", () => {
    const cb = makeCallbacks();
    const rendered = renderStep2(
      makeState({ selectedHeadphoneDeviceIndex: 1 }), // start on AirPods
      cb,
    );
    document.body.append(rendered);
    const section = rendered.querySelector<HTMLElement>(
      ".wizard-step__headphone-picker",
    );
    const head = section!.querySelector<HTMLElement>(
      ".cmp-dropdown-device__head",
    );
    head!.click();
    // Click "[ system default ]" option.
    const sysDefaultOption = section!.querySelector<HTMLElement>(
      ".cmp-dropdown-device__option[data-id='__system_default__']",
    );
    expect(sysDefaultOption).not.toBeNull();
    sysDefaultOption!.click();
    expect(cb.onSelectHeadphoneDevice).toHaveBeenCalledTimes(1);
    expect(cb.onSelectHeadphoneDevice).toHaveBeenCalledWith(null);
  });

  it("a non-null selectedHeadphoneDeviceIndex surfaces the matching device name in the head row", () => {
    const rendered = renderStep2(
      makeState({ selectedHeadphoneDeviceIndex: 1 }), // AirPods
      makeCallbacks(),
    );
    document.body.append(rendered);
    const section = rendered.querySelector<HTMLElement>(
      ".wizard-step__headphone-picker",
    );
    const headName = section!.querySelector<HTMLElement>(
      ".cmp-dropdown-device__name",
    );
    expect(headName?.textContent).toBe("AirPods Pro");
  });

  it("does NOT block the wizard Continue button when the output is selected", () => {
    // Continue arms on the real output-device selection. The picker is a
    // side-affordance, not a gate.
    const rendered = renderStep2(
      makeState({ selectedDeviceId: "0" }),
      makeCallbacks(),
    );
    document.body.append(rendered);
    // Find the Continue button — primary CTA with text "Continue".
    const buttons = Array.from(
      rendered.querySelectorAll<HTMLButtonElement>("button"),
    );
    const continueBtn = buttons.find((b) =>
      b.textContent?.includes("Continue"),
    );
    expect(continueBtn).not.toBeUndefined();
    // The button should be armed (not disabled).
    expect(continueBtn!.disabled).toBe(false);
  });

  it("keeps Continue disabled until an output device is selected", () => {
    const rendered = renderStep2(
      makeState({ selectedDeviceId: "" }),
      makeCallbacks(),
    );
    document.body.append(rendered);
    const buttons = Array.from(
      rendered.querySelectorAll<HTMLButtonElement>("button"),
    );
    const continueBtn = buttons.find((b) =>
      b.textContent?.includes("Continue"),
    );
    expect(continueBtn).not.toBeUndefined();
    expect(continueBtn!.disabled).toBe(true);
  });
});
