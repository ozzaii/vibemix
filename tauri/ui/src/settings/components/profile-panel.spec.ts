/* profile-panel.spec.ts — Phase 32 / PROFILE-07.
 *
 * Vitest jsdom coverage for the Settings → Profile panel.
 *
 * Mocking strategy mirrors recording-row.spec.ts: `../../ipc/client.js` is
 * stubbed with hoisted per-test handles so each test can drive the pending
 * Promise. Covers three render states (consent-off, consent-on-no-profile,
 * consent-on-with-profile) + regenerate / delete / enable interaction paths.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

type ViewPayload = {
  profile: Record<string, unknown> | null;
  bytes: number;
  consent: boolean;
};
type RegeneratePayload = {
  ok: boolean;
  profile: Record<string, unknown> | null;
  error: string | null;
};
type DeletePayload = { ok: boolean; error: string | null };

let pendingView: ((p: { type: string; ts: string; payload: ViewPayload }) => void) | null = null;
let pendingRegen: ((p: { type: string; ts: string; payload: RegeneratePayload }) => void) | null = null;
let pendingDelete: ((p: { type: string; ts: string; payload: DeletePayload }) => void) | null = null;

const emitIpcMock = vi.fn(async (_t: string, _p: Record<string, unknown>) => undefined);

vi.mock("../../ipc/client.js", () => ({
  sendIpcRequest: vi.fn((requestType: string) => {
    if (requestType === "ipc.profile.view") {
      return new Promise((resolve) => {
        pendingView = resolve as typeof pendingView;
      });
    }
    if (requestType === "ipc.profile.regenerate") {
      return new Promise((resolve) => {
        pendingRegen = resolve as typeof pendingRegen;
      });
    }
    if (requestType === "ipc.profile.delete") {
      return new Promise((resolve) => {
        pendingDelete = resolve as typeof pendingDelete;
      });
    }
    return Promise.reject(new Error(`unexpected request: ${requestType}`));
  }),
  emitIpc: (t: string, p: Record<string, unknown>) => emitIpcMock(t, p),
}));

import { renderProfilePanel } from "./profile-panel.js";

beforeEach(() => {
  pendingView = null;
  pendingRegen = null;
  pendingDelete = null;
  emitIpcMock.mockClear();
});

afterEach(() => {
  document.body.replaceChildren();
  vi.clearAllMocks();
});

async function flush(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}

function resolveView(payload: ViewPayload): void {
  pendingView!({
    type: "ipc.profile.view_result",
    ts: "2026-05-15T00:00:00+00:00",
    payload,
  });
}

describe("profile-panel — initial render before view resolves", () => {
  it("shows consent-off empty state with enable affordance", async () => {
    const handle = renderProfilePanel();
    document.body.append(handle.element);
    // Before the view promise resolves, the panel renders the empty
    // (consent off) state synchronously.
    const led = handle.element.querySelector(
      ".vmx-profile-panel__consent-led",
    ) as HTMLElement;
    expect(led).toBeTruthy();
    expect(led.dataset.on).toBe("false");
    expect(led.textContent).toContain("consent off");
    expect(
      handle.element.querySelector('[data-testid="profile-panel-enable"]'),
    ).toBeTruthy();
    handle.dispose();
  });
});

describe("profile-panel — consent on, no profile yet", () => {
  it("shows empty state + regenerate button (no delete)", async () => {
    const handle = renderProfilePanel();
    document.body.append(handle.element);
    resolveView({ profile: null, bytes: 0, consent: true });
    await flush();

    expect(
      handle.element.querySelector(".vmx-profile-panel__empty")?.textContent,
    ).toContain("no profile yet");
    expect(
      handle.element.querySelector('[data-testid="profile-panel-regenerate"]'),
    ).toBeTruthy();
    expect(
      handle.element.querySelector('[data-testid="profile-panel-delete"]'),
    ).toBeFalsy();
    handle.dispose();
  });
});

describe("profile-panel — consent on, with profile", () => {
  it("renders key:value table + both action buttons + bytes counter", async () => {
    const handle = renderProfilePanel();
    document.body.append(handle.element);
    resolveView({
      profile: {
        preferred_genre: "hard_tek",
        avg_session_duration: 72,
        mix_style_tags: ["long_blends", "loud_drops"],
        tempo_preference_bin: "138-150",
        event_type_response_preferences: { PHASE: "sometimes" },
      },
      bytes: 234,
      consent: true,
    });
    await flush();

    const keys = handle.element.querySelectorAll(".vmx-profile-panel__key");
    expect(keys.length).toBe(5);
    expect(Array.from(keys).map((k) => k.textContent)).toEqual([
      "preferred_genre",
      "avg_session_duration",
      "mix_style_tags",
      "tempo_preference_bin",
      "event_type_response_preferences",
    ]);

    const bytes = handle.element.querySelector(".vmx-profile-panel__bytes");
    expect(bytes?.textContent).toContain("234 / 2048 bytes");

    expect(
      handle.element.querySelector('[data-testid="profile-panel-regenerate"]'),
    ).toBeTruthy();
    expect(
      handle.element.querySelector('[data-testid="profile-panel-delete"]'),
    ).toBeTruthy();
    handle.dispose();
  });
});

describe("profile-panel — enable affordance", () => {
  it("clicking enable fires ipc.profile.set_consent with consent=true", async () => {
    const handle = renderProfilePanel();
    document.body.append(handle.element);
    // Don't resolve the initial view — the enable button is in the
    // synchronous empty state.
    const btn = handle.element.querySelector(
      '[data-testid="profile-panel-enable"]',
    ) as HTMLButtonElement;
    btn.click();
    await flush();
    expect(emitIpcMock).toHaveBeenCalledWith("ipc.profile.set_consent", {
      consent: true,
    });
    handle.dispose();
  });
});

describe("profile-panel — regenerate insufficient evidence", () => {
  it("shows the keep-mixing status copy after insufficient_evidence reply", async () => {
    const handle = renderProfilePanel();
    document.body.append(handle.element);
    resolveView({ profile: null, bytes: 0, consent: true });
    await flush();

    const regen = handle.element.querySelector(
      '[data-testid="profile-panel-regenerate"]',
    ) as HTMLButtonElement;
    regen.click();
    await flush();
    expect(
      (handle.element.querySelector('[data-testid="profile-panel-status"]') as HTMLElement)
        .textContent,
    ).toBe("regenerating…");

    pendingRegen!({
      type: "ipc.profile.regenerate_result",
      ts: "2026-05-15T00:00:00+00:00",
      payload: { ok: false, profile: null, error: "insufficient_evidence" },
    });
    await flush();
    const status = handle.element.querySelector(
      '[data-testid="profile-panel-status"]',
    ) as HTMLElement;
    expect(status.textContent).toContain("keep mixing");
    expect(status.dataset.error).toBe("false");
    handle.dispose();
  });
});

describe("profile-panel — delete round-trip", () => {
  it("clicking delete posts ipc.profile.delete and refreshes view", async () => {
    const handle = renderProfilePanel();
    document.body.append(handle.element);
    resolveView({
      profile: {
        preferred_genre: "techno",
        avg_session_duration: 60,
        mix_style_tags: [],
        tempo_preference_bin: "128-138",
        event_type_response_preferences: {},
      },
      bytes: 180,
      consent: true,
    });
    await flush();

    const del = handle.element.querySelector(
      '[data-testid="profile-panel-delete"]',
    ) as HTMLButtonElement;
    del.click();
    await flush();
    // After ack, the panel re-fetches view; ack reply resolves first.
    pendingDelete!({
      type: "ipc.profile.delete_ack",
      ts: "2026-05-15T00:00:00+00:00",
      payload: { ok: true, error: null },
    });
    await flush();
    // Refresh kicks off a new view request — fulfil with the post-delete
    // empty state.
    resolveView({ profile: null, bytes: 0, consent: true });
    await flush();

    expect(
      handle.element.querySelector(".vmx-profile-panel__empty")?.textContent,
    ).toContain("no profile yet");
    handle.dispose();
  });
});
