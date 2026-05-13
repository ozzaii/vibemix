/* Phase 15 Plan 04 Task 2 — recording-browser.ts vitest jsdom coverage.
 *
 * Covers UI-SPEC §Component Contracts (renderRecordingBrowser) + §Disk
 * usage line + §Empty state + §Virtualization. The 8 tests below are the
 * verbatim acceptance set declared in 15-04-PLAN.md §Task 2 §behavior.
 *
 * Vitest env: jsdom (routed via vitest.config.ts environmentMatchGlobs).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@tauri-apps/api/core", () => ({
  convertFileSrc: (path: string): string => `asset://localhost${path}`,
}));

vi.mock("../../ipc/client.js", () => ({
  // The browser doesn't fire IPC itself — but recording-row.ts does on expand.
  // For browser-level tests we never expand a row, so this is a no-op stub.
  sendIpcRequest: vi.fn(
    () => new Promise(() => { /* never resolves — no row is expanded in these tests */ }),
  ),
}));

import { renderRecordingBrowser } from "./recording-browser.js";
import type { RecordingSummary } from "./recording-row.js";

function fakeSession(i: number): RecordingSummary {
  // Pad to 4 chars so the ISO timestamp slot stays valid.
  const dd = String(13 - (i % 12)).padStart(2, "0");
  const hh = String(12 + (i % 8)).padStart(2, "0");
  const mm = String(i % 60).padStart(2, "0");
  return {
    session_dir: `2026051${dd}-${hh}${mm}10`,
    started_at_iso: `2026-05-${dd}T${hh}:${mm}:10+02:00`,
    duration_s: 1800 + i * 60,
    event_count: 20 + i,
    bytes_total: 1_000_000 + i * 100_000,
    crashed: false,
  };
}

// Controllable IntersectionObserver stub for Test 4.
type IOCallback = (entries: Array<{ isIntersecting: boolean }>) => void;

class FakeIntersectionObserver {
  static instances: FakeIntersectionObserver[] = [];
  callback: IOCallback;
  observed: Element[] = [];
  constructor(cb: IOCallback) {
    this.callback = cb;
    FakeIntersectionObserver.instances.push(this);
  }
  observe(el: Element): void {
    this.observed.push(el);
  }
  unobserve(_el: Element): void { /* no-op */ }
  disconnect(): void {
    this.observed = [];
  }
  /** Test-only — simulate the sentinel scrolling into view. */
  trigger(): void {
    this.callback([{ isIntersecting: true }]);
  }
}

beforeEach(() => {
  FakeIntersectionObserver.instances = [];
  vi.stubGlobal("IntersectionObserver", FakeIntersectionObserver);
  // jsdom matchMedia stub for the in-row prefers-reduced-motion query.
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onchange: null,
    }),
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.replaceChildren();
  vi.clearAllMocks();
});

describe("recording-browser — Test 1: empty state + zero usage", () => {
  it("renders disk usage line + verbatim empty state copy", () => {
    const { root } = renderRecordingBrowser({
      initialSessions: [],
      initialUsage: { sessions: 0, bytes_total: 0 },
      onReplay: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(root);

    const usage = root.querySelector<HTMLElement>(".vmx-rec-browser__usage");
    expect(usage?.textContent).toBe("RECORDINGS · 0 SESSIONS · 0 MB USED");

    const empty = root.querySelector<HTMLElement>(".vmx-rec-browser__empty");
    expect(empty?.textContent).toBe(
      "No recordings yet. Sessions appear here after they end.",
    );
    expect(empty?.getAttribute("role")).toBe("status");
  });
});

describe("recording-browser — Test 2: setUsage formatting", () => {
  it("formats GB with one decimal for >=1024^3 bytes", () => {
    const handle = renderRecordingBrowser({
      initialSessions: [],
      initialUsage: { sessions: 0, bytes_total: 0 },
      onReplay: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    handle.setUsage({ sessions: 12, bytes_total: 3_656_838_349 });
    const usage = handle.root.querySelector<HTMLElement>(
      ".vmx-rec-browser__usage",
    );
    expect(usage?.textContent).toBe("RECORDINGS · 12 SESSIONS · 3.4 GB USED");
  });

  it("formats integer MB for <1GB bytes", () => {
    const handle = renderRecordingBrowser({
      initialSessions: [],
      initialUsage: { sessions: 0, bytes_total: 0 },
      onReplay: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    handle.setUsage({ sessions: 4, bytes_total: 524_288_000 });
    const usage = handle.root.querySelector<HTMLElement>(
      ".vmx-rec-browser__usage",
    );
    expect(usage?.textContent).toBe("RECORDINGS · 4 SESSIONS · 500 MB USED");
  });

  it("renders LOADING sentinel for bytes_total === -1", () => {
    const handle = renderRecordingBrowser({
      initialSessions: [],
      initialUsage: { sessions: 0, bytes_total: 0 },
      onReplay: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    handle.setUsage({ sessions: 0, bytes_total: -1 });
    const usage = handle.root.querySelector<HTMLElement>(
      ".vmx-rec-browser__usage",
    );
    expect(usage?.textContent).toBe("RECORDINGS · LOADING…");
  });

  it("renders UNAVAILABLE sentinel for bytes_total === -2", () => {
    const handle = renderRecordingBrowser({
      initialSessions: [],
      initialUsage: { sessions: 0, bytes_total: 0 },
      onReplay: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    handle.setUsage({ sessions: 0, bytes_total: -2 });
    const usage = handle.root.querySelector<HTMLElement>(
      ".vmx-rec-browser__usage",
    );
    expect(usage?.textContent).toBe("RECORDINGS · UNAVAILABLE");
  });
});

describe("recording-browser — Test 3: setSessions populates row list + clears empty state", () => {
  it("renders 3 row roots when given 3 summaries", () => {
    const handle = renderRecordingBrowser({
      initialSessions: [],
      initialUsage: { sessions: 0, bytes_total: 0 },
      onReplay: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    handle.setSessions([fakeSession(0), fakeSession(1), fakeSession(2)]);

    const rows = handle.root.querySelectorAll(".vmx-rec-row");
    expect(rows.length).toBe(3);

    const empty = handle.root.querySelector(".vmx-rec-browser__empty");
    expect(empty).toBeNull();
  });
});

describe("recording-browser — Test 4: virtualization above 50 rows", () => {
  it("renders only the first chunk + sentinel for 51 sessions", () => {
    const handle = renderRecordingBrowser({
      initialSessions: [],
      initialUsage: { sessions: 0, bytes_total: 0 },
      onReplay: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    const sessions = Array.from({ length: 51 }, (_, i) => fakeSession(i));
    handle.setSessions(sessions);

    // Initial mount: 12 rows + sentinel — NOT all 51.
    const rowsAfterMount = handle.root.querySelectorAll(".vmx-rec-row");
    expect(rowsAfterMount.length).toBe(12);
    const sentinel = handle.root.querySelector(".vmx-rec-browser__sentinel");
    expect(sentinel).not.toBeNull();

    // Trigger the IntersectionObserver to mount the next chunk.
    expect(FakeIntersectionObserver.instances.length).toBe(1);
    FakeIntersectionObserver.instances[0]!.trigger();
    expect(handle.root.querySelectorAll(".vmx-rec-row").length).toBe(24);
  });
});

describe("recording-browser — Test 5: at-threshold full mount", () => {
  it("renders all 50 rows immediately + no IntersectionObserver", () => {
    const handle = renderRecordingBrowser({
      initialSessions: [],
      initialUsage: { sessions: 0, bytes_total: 0 },
      onReplay: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    const sessions = Array.from({ length: 50 }, (_, i) => fakeSession(i));
    handle.setSessions(sessions);

    expect(handle.root.querySelectorAll(".vmx-rec-row").length).toBe(50);
    expect(handle.root.querySelector(".vmx-rec-browser__sentinel")).toBeNull();
    expect(FakeIntersectionObserver.instances.length).toBe(0);
  });
});

describe("recording-browser — Test 6: delete button opens confirm dialog (danger)", () => {
  it("clicking a row's delete button mounts a confirm dialog on document.body", () => {
    const handle = renderRecordingBrowser({
      initialSessions: [],
      initialUsage: { sessions: 0, bytes_total: 0 },
      onReplay: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    handle.setSessions([fakeSession(0)]);

    const deleteBtn = handle.root.querySelector<HTMLButtonElement>(
      '.vmx-rec-row__btn[data-kind="delete"]',
    );
    expect(deleteBtn).not.toBeNull();
    deleteBtn!.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    // confirmDialog mounts a backdrop on document.body.
    const dialog = document.body.querySelector<HTMLElement>(
      ".vmx-confirm__dialog",
    );
    expect(dialog).not.toBeNull();
    expect(dialog?.dataset.variant).toBe("danger");

    const heading = dialog!.querySelector<HTMLElement>(".vmx-confirm__heading");
    // Heading uses the formatted "YYYY-MM-DD HH:MM" timestamp.
    expect(heading?.textContent ?? "").toMatch(/Delete session 2026-05-\d\d \d\d:\d\d\?/);

    const body = dialog!.querySelector<HTMLElement>(".vmx-confirm__body");
    expect(body?.textContent).toBe("This cannot be undone.");
  });
});

describe("recording-browser — Test 7: confirming delete fires onDelete", () => {
  it("clicking CONFIRM calls onDelete(session_dir, timestamp)", () => {
    const onDelete = vi.fn();
    const handle = renderRecordingBrowser({
      initialSessions: [],
      initialUsage: { sessions: 0, bytes_total: 0 },
      onReplay: vi.fn(),
      onDelete,
    });
    document.body.append(handle.root);

    const session = fakeSession(0);
    handle.setSessions([session]);

    const deleteBtn = handle.root.querySelector<HTMLButtonElement>(
      '.vmx-rec-row__btn[data-kind="delete"]',
    );
    deleteBtn!.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    const confirmBtn = document.body.querySelector<HTMLButtonElement>(
      '.vmx-confirm__btn[data-kind="confirm"]',
    );
    expect(confirmBtn).not.toBeNull();
    confirmBtn!.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    expect(onDelete).toHaveBeenCalledTimes(1);
    const [calledSessionDir, calledTimestamp] = onDelete.mock.calls[0]!;
    expect(calledSessionDir).toBe(session.session_dir);
    expect(typeof calledTimestamp).toBe("string");
    expect(calledTimestamp).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/);
  });
});

describe("recording-browser — Test 8: cancelling delete tears down the dialog", () => {
  it("clicking CANCEL removes the dialog and does NOT fire onDelete", () => {
    const onDelete = vi.fn();
    const handle = renderRecordingBrowser({
      initialSessions: [],
      initialUsage: { sessions: 0, bytes_total: 0 },
      onReplay: vi.fn(),
      onDelete,
    });
    document.body.append(handle.root);

    handle.setSessions([fakeSession(0)]);

    const deleteBtn = handle.root.querySelector<HTMLButtonElement>(
      '.vmx-rec-row__btn[data-kind="delete"]',
    );
    deleteBtn!.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    let dialog = document.body.querySelector<HTMLElement>(".vmx-confirm__dialog");
    expect(dialog).not.toBeNull();

    const cancelBtn = document.body.querySelector<HTMLButtonElement>(
      '.vmx-confirm__btn[data-kind="cancel"]',
    );
    cancelBtn!.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    dialog = document.body.querySelector<HTMLElement>(".vmx-confirm__dialog");
    expect(dialog).toBeNull();
    expect(onDelete).not.toHaveBeenCalled();
  });
});
