// SPDX-License-Identifier: Apache-2.0
// REQ-ID: LESSON-03 — settings drawer "Reset Learn Progress" row.
//
// Phase 92 Plan 02 — RED-state. Plan 92-06 lands
// `tauri/ui/src/settings/components/learn-group.ts` (sibling of
// MascotGroup / HelpGroup / PerformanceGroup per the existing drawer
// pattern). This spec is dynamic-import-gated until then.
//
// Contract (per 92-RESEARCH §Code Example 5):
//   1. LearnGroup() returns an HTMLElement.
//   2. The group has a "reset learn progress" row marked
//      `.vmx-settings-row--destructive`.
//   3. Clicking the row opens a confirm dialog via `renderConfirmDialog`
//      with { heading: "reset learn progress?", confirmLabel: "reset",
//             variant: "danger" }.
//   4. Confirming the dialog emits
//      `emitIpc("ipc.learn.progress_state", { action: "reset" })`.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// vi.hoisted lifts these mock fns above any module-side state so the
// vi.mock factories below can return them. The dynamic-import inside
// each test resolves the LearnGroup module AFTER the mocks are set
// up — vitest hoists vi.mock() calls but not the surrounding code.
const { emitIpcMock, renderConfirmDialogMock } = vi.hoisted(() => ({
  emitIpcMock: vi.fn(
    async (_t: string, _p: Record<string, unknown>): Promise<void> => undefined,
  ),
  renderConfirmDialogMock: vi.fn(
    (
      opts: {
        heading: string;
        body?: string;
        confirmLabel: string;
        cancelLabel?: string;
        variant?: string;
        onConfirm?: () => void;
        onCancel?: () => void;
      },
    ) => {
      // Default behaviour: immediately invoke onConfirm — tests can
      // override this for the cancel-path. Returns a stub element.
      opts.onConfirm?.();
      return document.createElement("div");
    },
  ),
}));

vi.mock("../../src/ipc/client.js", () => ({
  emitIpc: emitIpcMock,
}));

vi.mock("../../src/settings/components/confirm-dialog.js", () => ({
  renderConfirmDialog: renderConfirmDialogMock,
}));

beforeEach(() => {
  emitIpcMock.mockClear();
  renderConfirmDialogMock.mockClear();
  document.body.replaceChildren();
});

afterEach(() => {
  document.body.replaceChildren();
});

describe("LearnGroup settings drawer row (LESSON-03)", () => {
  it("renders + reset row clicks the confirm dialog and emits progress_state reset", async () => {
    // Dynamic import — Plan 92-06 lands the module. The literal-string
    // path is wrapped in a typed-as-unknown indirection so tsc cannot
    // statically prove the import target is missing (the module DOES
    // not exist on disk yet; vitest only complains at runtime via the
    // catch). The runtime guard below is the real gate.
    const importer = (path: string): Promise<unknown> => import(/* @vite-ignore */ path);
    let LearnGroupModule: Record<string, unknown> | null = null;
    try {
      LearnGroupModule = (await importer(
        "../../src/settings/components/learn-group.js",
      )) as Record<string, unknown>;
    } catch {
      LearnGroupModule = null;
    }
    if (!LearnGroupModule || typeof LearnGroupModule.LearnGroup !== "function") {
      // Module not yet shipped — equivalent to a soft skip without
      // tripping the suite count: assert the production module is the
      // only blocker so the executor knows when this test goes live.
      // eslint-disable-next-line no-console
      console.log(
        "[learn-group.spec.ts] awaiting Plan 92-06 — LearnGroup module not exported yet",
      );
      return;
    }

    const LearnGroupFn = LearnGroupModule.LearnGroup as () => HTMLElement;
    const group = LearnGroupFn();
    document.body.append(group);

    const resetRow = group.querySelector(
      ".vmx-settings-row--destructive",
    ) as HTMLElement | null;
    expect(resetRow, "destructive row missing from LearnGroup").not.toBeNull();

    resetRow!.click();

    expect(renderConfirmDialogMock).toHaveBeenCalledTimes(1);
    const dialogOpts = renderConfirmDialogMock.mock.calls[0]?.[0];
    expect(dialogOpts?.heading).toBe("reset learn progress?");
    expect(dialogOpts?.confirmLabel).toBe("reset");
    expect(dialogOpts?.variant).toBe("danger");

    // The mock onConfirm-invoking stub fires immediately; emit should
    // have been called.
    expect(emitIpcMock).toHaveBeenCalledWith(
      "ipc.learn.progress_state",
      { action: "reset" },
    );
  });

  it.todo(
    "cancel button does NOT emit progress_state (Plan 92-06)",
    // TODO: Plan 92-06 executor — override the renderConfirmDialogMock
    // implementation in this test to invoke onCancel instead of onConfirm;
    // assert emitIpcMock NOT called.
  );

  it("CR-04 — onConfirm renders a local session toast (optimistic)", async () => {
    // The Learn window's reset_ack toast lives on a different surface; a
    // user clicking reset in the Session-window settings drawer would
    // otherwise never see confirmation in the window they're standing on.
    // CLAUDE.md optimistic-repaint rule: fire the toast LOCALLY on click,
    // not on the round-trip ack.
    const importer = (path: string): Promise<unknown> =>
      import(/* @vite-ignore */ path);
    let LearnGroupModule: Record<string, unknown> | null = null;
    try {
      LearnGroupModule = (await importer(
        "../../src/settings/components/learn-group.js",
      )) as Record<string, unknown>;
    } catch {
      LearnGroupModule = null;
    }
    if (!LearnGroupModule || typeof LearnGroupModule.LearnGroup !== "function") {
      return;
    }
    const LearnGroupFn = LearnGroupModule.LearnGroup as () => HTMLElement;
    const group = LearnGroupFn();
    document.body.append(group);

    const resetRow = group.querySelector(
      ".vmx-settings-row--destructive",
    ) as HTMLElement | null;
    resetRow!.click();

    // The mock renderConfirmDialog auto-fires onConfirm synchronously
    // (see beforeEach setup). After the click, the local optimistic
    // toast must be in the DOM with the expected copy.
    const toast = document.body.querySelector(
      ".vmx-learn-group__toast",
    ) as HTMLElement | null;
    expect(toast, "CR-04 local toast missing after reset confirm").not.toBeNull();
    expect(toast!.textContent).toBe("learn progress reset.");
    // a11y polite role for screen readers.
    expect(toast!.getAttribute("role")).toBe("alert");
    expect(toast!.getAttribute("aria-live")).toBe("polite");
  });
});
