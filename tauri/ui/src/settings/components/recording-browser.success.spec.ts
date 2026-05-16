/* Phase 15 Plan 01 Task 3 — vitest ROADMAP success-criteria gates.
 *
 * Three cases that wedge the SHIPPED columns of the audit table in
 * tests/recording/test_phase15_success_criteria.py into vitest CI:
 *
 *   Test E — disk-usage line is the SINGLE error/loading channel for the
 *            recordings surface (covers ROADMAP §1 chronological list +
 *            sentinel-aware status display + UI-SPEC §State Management
 *            no-list-refetch invariant).
 *   Test F — chronological newest-first ordering is preserved as-given
 *            (covers ROADMAP §1 — UI trusts wire order from the sidecar's
 *            recordings_index.py:296 sort).
 *   Test G — single-row playback discipline (covers ROADMAP §2 — UI-SPEC
 *            §Row replay claims "Single-row guarantee: only one row is
 *            open at a time"). EXPECTED-FAIL: the shipped recording-browser.ts
 *            onToggle handler (lines 362-378) only flips the clicked row;
 *            there is NO close-others discipline. The gap is documented in
 *            15-01-SUMMARY.md for closure in Plan 15-04.
 *
 * Mocks mirror recording-browser.spec.ts exactly so the success gates run
 * in the same jsdom environment with the same FakeIntersectionObserver +
 * convertFileSrc + sendIpcRequest contracts.
 *
 * Vitest env: jsdom (routed via vitest.config.ts environmentMatchGlobs).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@tauri-apps/api/core", () => ({
  convertFileSrc: (path: string): string => `asset://localhost${path}`,
}));

vi.mock("../../ipc/client.js", () => ({
  // Test G mounts <audio> + transcript on row expand. The transcript fetch
  // never resolves so the test asserts purely on the mounted <audio> count
  // (events.jsonl rendering is irrelevant to the playback-discipline gate).
  sendIpcRequest: vi.fn(
    () => new Promise(() => { /* never resolves — playback discipline only */ }),
  ),
}));

import { renderRecordingBrowser } from "./recording-browser.js";
import type { RecordingSummary } from "./recording-row.js";

function fakeSession(opts: { isoDay: string; sessionDir: string }): RecordingSummary {
  return {
    session_dir: opts.sessionDir,
    started_at_iso: `${opts.isoDay}T21:04:10+02:00`,
    duration_s: 1800,
    event_count: 20,
    bytes_total: 1_000_000,
    crashed: false,
  };
}

class FakeIntersectionObserver {
  static instances: FakeIntersectionObserver[] = [];
  callback: (entries: Array<{ isIntersecting: boolean }>) => void;
  observed: Element[] = [];
  constructor(cb: (entries: Array<{ isIntersecting: boolean }>) => void) {
    this.callback = cb;
    FakeIntersectionObserver.instances.push(this);
  }
  observe(el: Element): void { this.observed.push(el); }
  unobserve(_el: Element): void { /* no-op */ }
  disconnect(): void { this.observed = []; }
}

beforeEach(() => {
  FakeIntersectionObserver.instances = [];
  vi.stubGlobal("IntersectionObserver", FakeIntersectionObserver);
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

// ===========================================================================
// Test E — disk-usage line is the single status channel; sentinel-aware
//
// Defends ROADMAP §1 list semantics + UI-SPEC §Sentinel + §State Management:
//
//   * On UNAVAILABLE (-2 sentinel), the disk-usage line carries the failure
//     signal — the empty-state body STILL renders ("No recordings yet…")
//     because the list area is its own channel (no inline banner).
//   * On a successful setUsage push, ONLY the usage line updates — the
//     list area is NOT refetched (UI-SPEC §State Management mandates that
//     ipc.recordings.usage updates do not trigger setSessions).
// ===========================================================================

describe("recording-browser success-criteria — Test E: disk-usage line is the single status channel", () => {
  it("renders UNAVAILABLE sentinel with empty-state body still visible; setUsage push doesn't refetch the list", () => {
    const onReplay = vi.fn();
    const onDelete = vi.fn();
    const handle = renderRecordingBrowser({
      initialSessions: [],
      initialUsage: { sessions: 0, bytes_total: -2 },
      onReplay,
      onDelete,
    });
    document.body.append(handle.root);

    // 1. UNAVAILABLE sentinel renders verbatim copy from UI-SPEC.
    const usage = handle.root.querySelector<HTMLElement>(
      ".vmx-rec-browser__usage",
    );
    expect(usage?.textContent).toBe("RECORDINGS · UNAVAILABLE");

    // 2. Empty-state body STILL renders (single-channel discipline — the
    //    list area is independent of the disk-usage error sentinel).
    const empty = handle.root.querySelector<HTMLElement>(
      ".vmx-rec-browser__empty",
    );
    expect(empty?.textContent).toBe(
      "No recordings yet. Sessions appear here after they end.",
    );

    // 3. Push a successful usage update — usage line updates, list does NOT
    //    refetch (UI-SPEC §State Management: ipc.recordings.usage updates
    //    never trigger setSessions; the disk-usage line is the ONLY surface
    //    that mutates).
    handle.setUsage({ sessions: 5, bytes_total: 524_288_000 });
    expect(usage?.textContent).toBe(
      "RECORDINGS · 5 SESSIONS · 500 MB USED",
    );

    // 4. Empty-state body is STILL the same node — no row mount happened
    //    as a side-effect of the usage push.
    const stillEmpty = handle.root.querySelector<HTMLElement>(
      ".vmx-rec-browser__empty",
    );
    expect(stillEmpty).toBe(empty);
    const rowsAfter = handle.root.querySelectorAll(".vmx-rec-row");
    expect(rowsAfter.length).toBe(0);
  });
});

// ===========================================================================
// Test F — chronological newest-first ordering preserved AS-GIVEN
//
// Defends ROADMAP §1 ("chronologically-ordered list"). The browser does NOT
// re-sort — it trusts the wire order from recordings_index.py:296 which
// is the canonical sort. Asserts both directions: when given [newer, older]
// the first row is newer; when given [older, newer] the first row is older
// (no client-side sort masking a sidecar bug).
// ===========================================================================

describe("recording-browser success-criteria — Test F: newest-first chronological order is preserved as-given", () => {
  it("renders rows in the order received without client-side re-sort", () => {
    const handle = renderRecordingBrowser({
      initialSessions: [],
      initialUsage: { sessions: 0, bytes_total: 0 },
      onReplay: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    const older = fakeSession({ isoDay: "2026-05-13", sessionDir: "20260513-210410" });
    const newer = fakeSession({ isoDay: "2026-05-14", sessionDir: "20260514-210410" });

    // Wire order = newest-first (as the sidecar would emit).
    handle.setSessions([newer, older]);
    let tsCells = handle.root.querySelectorAll<HTMLElement>(".vmx-rec-row__ts");
    expect(tsCells.length).toBe(2);
    expect(tsCells[0]!.textContent).toBe("2026-05-14 21:04");
    expect(tsCells[1]!.textContent).toBe("2026-05-13 21:04");

    // Reverse the wire order — the browser must render in the new received
    // order, NOT silently re-sort. (If the browser secretly sorted, this
    // would produce the same first cell as before — proving the trust-the-
    // wire contract is the only line of defense.)
    handle.setSessions([older, newer]);
    tsCells = handle.root.querySelectorAll<HTMLElement>(".vmx-rec-row__ts");
    expect(tsCells.length).toBe(2);
    expect(tsCells[0]!.textContent).toBe("2026-05-13 21:04");
    expect(tsCells[1]!.textContent).toBe("2026-05-14 21:04");
  });
});

// ===========================================================================
// Test G — single-row playback discipline (EXPECTED-FAIL — gap for Plan 15-04)
//
// UI-SPEC §Row replay claims: "Single-row guarantee: only one row is open
// at a time". The CURRENT implementation in recording-browser.ts:362-378
// does NOT enforce this — onToggle for row N only flips row N's expanded
// state; there is no iteration over rowHandles to setExpanded(false) on
// the other rows.
//
// This test is `it.fails(...)` so the gap is captured in CI without
// blocking the build. Plan 15-04 closes the gap by adding a "close-others"
// step inside the onToggle closure (see 15-01-SUMMARY.md §Found Gaps).
//
// When 15-04 lands the close-others fix, flip `it.fails` → `it` and the
// gate becomes a regression detector.
// ===========================================================================

describe("recording-browser success-criteria — Test G: single-row playback discipline", () => {
  it.fails(
    "GAP — opening a second row should tear down the first row's <audio> (UI-SPEC §Row replay)",
    () => {
      const handle = renderRecordingBrowser({
        initialSessions: [],
        initialUsage: { sessions: 0, bytes_total: 0 },
        onReplay: vi.fn(),
        onDelete: vi.fn(),
      });
      document.body.append(handle.root);

      handle.setSessions([
        fakeSession({ isoDay: "2026-05-14", sessionDir: "20260514-210410" }),
        fakeSession({ isoDay: "2026-05-13", sessionDir: "20260513-210410" }),
        fakeSession({ isoDay: "2026-05-12", sessionDir: "20260512-210410" }),
      ]);
      const rows = handle.root.querySelectorAll<HTMLElement>(".vmx-rec-row");
      expect(rows.length).toBe(3);

      // Click row[0]'s body (the meta cell triggers onToggle per the row
      // contract — Test 7 of recording-row.spec.ts).
      const meta0 = rows[0]!.querySelector<HTMLElement>(".vmx-rec-row__meta");
      meta0!.dispatchEvent(new MouseEvent("click", { bubbles: true }));

      // After row[0] open: exactly one <audio> mounted.
      let audios = document.querySelectorAll("audio");
      expect(audios.length).toBe(1);
      expect(rows[0]!.dataset.open).toBe("true");

      // Click row[1]'s body — the contract says row[0]'s <audio> should be
      // torn down (single-row guarantee). The current shipped code does NOT
      // enforce this — both rows end up with an <audio> mounted.
      const meta1 = rows[1]!.querySelector<HTMLElement>(".vmx-rec-row__meta");
      meta1!.dispatchEvent(new MouseEvent("click", { bubbles: true }));

      audios = document.querySelectorAll("audio");
      // EXPECTED at contract: 1. ACTUAL on shipped code: 2 — this assertion
      // FAILS, which is what `it.fails(...)` expects (the test passes
      // overall when the inner expectation fails).
      expect(audios.length).toBe(1);
    },
  );
});
