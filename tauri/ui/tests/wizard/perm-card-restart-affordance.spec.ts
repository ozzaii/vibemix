// SPDX-License-Identifier: Apache-2.0
//
// F6: after the user opens System Settings for screen recording, the sidecar
// needs a restart to re-read the process-cached macOS permission state.

import { afterEach, describe, expect, it, vi } from "vitest";
import { PermissionsCard } from "../../src/wizard/components/permissions-card.js";
import { renderStep1 } from "../../src/wizard/step1-permissions.js";

afterEach(() => {
  document.body.replaceChildren();
});

describe("PermissionsCard restart-to-apply affordance (F6)", () => {
  it("denied without awaitingRestart keeps the open-Settings readout", () => {
    const onOpenSettings = vi.fn();
    const onRestart = vi.fn();
    const card = PermissionsCard({
      kind: "screen-recording",
      state: "denied",
      onOpenSettings,
      onRestart,
    });
    document.body.append(card);
    const readout = card.querySelector<HTMLElement>(".cmp-perm-card__state-readout")!;
    expect(readout.textContent).toContain("DENIED · open Settings ↗");
    readout.click();
    expect(onOpenSettings).toHaveBeenCalledTimes(1);
    expect(onRestart).not.toHaveBeenCalled();
  });

  it("denied with awaitingRestart routes the click to onRestart", () => {
    const onOpenSettings = vi.fn();
    const onRestart = vi.fn();
    const card = PermissionsCard({
      kind: "screen-recording",
      state: "denied",
      awaitingRestart: true,
      onOpenSettings,
      onRestart,
    });
    document.body.append(card);
    const readout = card.querySelector<HTMLElement>(".cmp-perm-card__state-readout")!;
    expect(readout.textContent).toContain("GRANTED? RESTART TO APPLY ↻");
    readout.click();
    expect(onRestart).toHaveBeenCalledTimes(1);
    expect(onOpenSettings).not.toHaveBeenCalled();
  });
});

describe("renderStep1 screen-recording restart wiring (F6)", () => {
  it("surfaces restart once screenSettingsOpened is set", () => {
    const onRestartSidecar = vi.fn();
    const wrap = renderStep1(
      {
        screenRecording: "denied",
        microphone: "granted",
        screenSettingsOpened: true,
      },
      {
        platform: "darwin",
        onContinue: vi.fn(),
        onGrantScreen: vi.fn(),
        onGrantMic: vi.fn(),
        onOpenScreenSettings: vi.fn(),
        onOpenMicSettings: vi.fn(),
        onRestartSidecar,
        onBack: vi.fn(),
      },
    );
    document.body.append(wrap);
    const screenCard = wrap.querySelector<HTMLElement>(
      '.cmp-perm-card[data-kind="screen-recording"]',
    )!;
    const readout = screenCard.querySelector<HTMLElement>(
      ".cmp-perm-card__state-readout",
    )!;
    expect(readout.textContent).toContain("RESTART TO APPLY");
    readout.click();
    expect(onRestartSidecar).toHaveBeenCalledTimes(1);
  });

  it("keeps open-Settings before Settings was opened", () => {
    const wrap = renderStep1(
      { screenRecording: "denied", microphone: "granted" },
      {
        platform: "darwin",
        onContinue: vi.fn(),
        onGrantScreen: vi.fn(),
        onGrantMic: vi.fn(),
        onOpenScreenSettings: vi.fn(),
        onOpenMicSettings: vi.fn(),
        onBack: vi.fn(),
      },
    );
    document.body.append(wrap);
    const screenCard = wrap.querySelector<HTMLElement>(
      '.cmp-perm-card[data-kind="screen-recording"]',
    )!;
    expect(
      screenCard.querySelector(".cmp-perm-card__state-readout")!.textContent,
    ).toContain("DENIED · open Settings ↗");
  });
});
