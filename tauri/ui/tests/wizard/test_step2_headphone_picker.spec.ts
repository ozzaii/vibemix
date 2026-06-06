// SPDX-License-Identifier: Apache-2.0
//
// Session 2 activation cleanup: Learn is parked for launch, so Step 2 keeps
// only the primary output-device picker. The old tutorial headphone picker
// must stay gone.

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  renderStep2,
  type Step2Callbacks,
  type Step2State,
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
    ...over,
  };
}

afterEach(() => {
  document.body.replaceChildren();
});

describe("wizard step 2 - retired lesson headphone picker", () => {
  it("does not render the Learn-only headphone picker", () => {
    const rendered = renderStep2(makeState(), makeCallbacks());
    document.body.append(rendered);

    expect(rendered.querySelector(".wizard-step__headphone-picker")).toBeNull();
    expect(rendered.textContent).not.toContain("tutor exemplar playback");
    expect(rendered.textContent).not.toContain("[ system default ]");
    expect(rendered.textContent).not.toContain("beginner lessons play");
  });

  it("keeps the primary output device picker and Continue gate", () => {
    const cb = makeCallbacks();
    const rendered = renderStep2(makeState({ selectedDeviceId: "" }), cb);
    document.body.append(rendered);

    expect(rendered.textContent).toContain("OUTPUT DEVICE");
    expect(rendered.querySelector(".cmp-dropdown-device")).not.toBeNull();
    const continueButton = Array.from(rendered.querySelectorAll("button")).find((button) =>
      (button.textContent ?? "").toLowerCase().includes("continue"),
    );
    expect(continueButton).toBeDefined();
    expect(continueButton!.disabled).toBe(true);
  });

  it("selecting the primary output device still fires onSelectDevice", () => {
    const cb = makeCallbacks();
    const rendered = renderStep2(makeState({ selectedDeviceId: "0" }), cb);
    document.body.append(rendered);

    rendered.querySelector<HTMLElement>(".cmp-dropdown-device__head")?.click();
    document
      .querySelector<HTMLElement>(".cmp-dropdown-device__option[data-id='1']")
      ?.click();

    expect(cb.onSelectDevice).toHaveBeenCalledWith("1");
  });
});
