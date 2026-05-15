/* Phase 28 Plan 07 Task 3 — staleness banner vitest specs.
 *
 * Mocks ipc/client.ts subscribeIpc + emitIpc to drive nudge messages and
 * assert button → emit + DOM visibility behaviour.
 *
 * Vitest env: jsdom (covered by tests/**\/*.spec.ts glob).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const subscribers = new Map<string, (msg: unknown) => void>();
const emitted: { type: string; payload: Record<string, unknown> }[] = [];

vi.mock("../../src/ipc/client.js", () => ({
  subscribeIpc: vi.fn(
    async (type: string, cb: (msg: unknown) => void) => {
      subscribers.set(type, cb);
      return () => subscribers.delete(type);
    },
  ),
  emitIpc: vi.fn(async (type: string, payload: Record<string, unknown>) => {
    emitted.push({ type, payload });
  }),
}));

import { renderStalenessBanner } from "../../src/settings/components/staleness-banner.js";

beforeEach(() => {
  subscribers.clear();
  emitted.length = 0;
  document.body.replaceChildren();
});

afterEach(() => {
  document.body.replaceChildren();
});

async function _flushMicrotasks(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

describe("staleness-banner — appears on nudge with age text", () => {
  it("removes hidden class and shows age count after staleness_nudge", async () => {
    const handle = renderStalenessBanner();
    document.body.append(handle.element);
    expect(handle.element.classList.contains("hidden")).toBe(true);

    // Wait for the async subscribeIpc to resolve and register the cb.
    await _flushMicrotasks();
    const cb = subscribers.get("ipc.library.staleness_nudge");
    expect(cb).toBeDefined();

    cb!({
      type: "ipc.library.staleness_nudge",
      ts: "2026-05-15T12:00:00Z",
      payload: { age_days: 45, snoozed_until_ts: null, schema_version: "1" },
    });

    expect(handle.element.classList.contains("hidden")).toBe(false);
    const ageEl = handle.element.querySelector(".vmx-staleness-age");
    expect(ageEl?.textContent).toContain("45");
  });
});

describe("staleness-banner — dismiss hides + emits action", () => {
  it("hides banner on dismiss + emits ipc.library.staleness_action dismiss", async () => {
    const handle = renderStalenessBanner();
    document.body.append(handle.element);
    await _flushMicrotasks();

    const cb = subscribers.get("ipc.library.staleness_nudge")!;
    cb({
      type: "ipc.library.staleness_nudge",
      ts: "2026-05-15T12:00:00Z",
      payload: { age_days: 45, snoozed_until_ts: null, schema_version: "1" },
    });

    const dismissBtn = handle.element.querySelector(
      ".vmx-staleness-dismiss",
    ) as HTMLButtonElement;
    dismissBtn.click();

    expect(handle.element.classList.contains("hidden")).toBe(true);
    expect(emitted).toContainEqual({
      type: "ipc.library.staleness_action",
      payload: { action: "dismiss", schema_version: "1" },
    });
  });
});

describe("staleness-banner — snooze emits 7d action + hides", () => {
  it("emits ipc.library.staleness_action snooze_7d on snooze click", async () => {
    const handle = renderStalenessBanner();
    document.body.append(handle.element);
    await _flushMicrotasks();

    const cb = subscribers.get("ipc.library.staleness_nudge")!;
    cb({
      type: "ipc.library.staleness_nudge",
      ts: "2026-05-15T12:00:00Z",
      payload: { age_days: 60, snoozed_until_ts: null, schema_version: "1" },
    });

    const snoozeBtn = handle.element.querySelector(
      ".vmx-staleness-snooze",
    ) as HTMLButtonElement;
    snoozeBtn.click();

    expect(handle.element.classList.contains("hidden")).toBe(true);
    expect(emitted).toContainEqual({
      type: "ipc.library.staleness_action",
      payload: { action: "snooze_7d", schema_version: "1" },
    });
  });
});

describe("staleness-banner — no show without nudge", () => {
  it("stays hidden when no message is dispatched", async () => {
    const handle = renderStalenessBanner();
    document.body.append(handle.element);
    await _flushMicrotasks();

    expect(handle.element.classList.contains("hidden")).toBe(true);
  });
});

describe("staleness-banner — singular 'day' for age=1", () => {
  it("formats 1 day without 's'", async () => {
    const handle = renderStalenessBanner();
    document.body.append(handle.element);
    await _flushMicrotasks();

    const cb = subscribers.get("ipc.library.staleness_nudge")!;
    cb({
      type: "ipc.library.staleness_nudge",
      ts: "2026-05-15T12:00:00Z",
      payload: { age_days: 1, snoozed_until_ts: null, schema_version: "1" },
    });

    const ageEl = handle.element.querySelector(".vmx-staleness-age");
    expect(ageEl?.textContent).toBe("1 day");
  });
});
