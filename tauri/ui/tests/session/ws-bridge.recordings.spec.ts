/* Phase 15 Plan 05 Task 1 — ws-bridge recordings.usage subscriber tests.
 *
 * Asserts the `applyRecordingsUsage` payload applier (subscribed to
 * `ipc.recordings.usage` pushes in `initSessionBridge`) writes the
 * `usage` sub-field of the SettingsUIState `recordings` slice — and
 * leaves the `sessions` array + `loading` + `error` untouched per
 * UI-SPEC §State Management (avoids list-flicker mid-interaction).
 *
 * The bridge owns the only write path for `recordings.usage` — the
 * drawer's `recordings.list` request handles session-array updates on
 * drawer open. Both flow through the same `recordings` slice.
 */

import { beforeEach, describe, expect, it } from "vitest";

import { applyRecordingsUsage } from "../../src/session/ws-bridge.js";
import {
  _resetSettingsUIStateForTests,
  getSettingsUIState,
  setRecordingsSlice,
} from "../../src/settings/state.js";

beforeEach(() => {
  _resetSettingsUIStateForTests();
});

describe("applyRecordingsUsage", () => {
  it("writes sessions + bytes_total into the recordings.usage sub-slice", () => {
    applyRecordingsUsage({ sessions: 12, bytes_total: 3_656_838_349 });
    const ui = getSettingsUIState();
    expect(ui.recordings.usage.sessions).toBe(12);
    expect(ui.recordings.usage.bytes_total).toBe(3_656_838_349);
  });

  it("leaves the sessions array untouched (no list re-fetch on push)", () => {
    setRecordingsSlice({
      sessions: [
        {
          session_dir: "20260513-210410",
          started_at_iso: "2026-05-13T21:04:10+02:00",
          duration_s: 1800,
          event_count: 22,
          bytes_total: 1_500_000,
          crashed: false,
        },
      ],
    });
    applyRecordingsUsage({ sessions: 1, bytes_total: 1_500_000 });
    const ui = getSettingsUIState();
    expect(ui.recordings.sessions.length).toBe(1);
    expect(ui.recordings.sessions[0]!.session_dir).toBe("20260513-210410");
  });

  it("leaves loading + error fields untouched", () => {
    setRecordingsSlice({ loading: true, error: "previous error" });
    applyRecordingsUsage({ sessions: 5, bytes_total: 12_345 });
    const ui = getSettingsUIState();
    expect(ui.recordings.loading).toBe(true);
    expect(ui.recordings.error).toBe("previous error");
    expect(ui.recordings.usage).toEqual({ sessions: 5, bytes_total: 12_345 });
  });

  it("zero-sessions push (empty recordings dir) writes 0 / 0", () => {
    applyRecordingsUsage({ sessions: 0, bytes_total: 0 });
    const ui = getSettingsUIState();
    expect(ui.recordings.usage).toEqual({ sessions: 0, bytes_total: 0 });
  });
});

describe("RecordingsSlice default", () => {
  it("starts at empty sessions + zero usage + loading=false + error=null", () => {
    const ui = getSettingsUIState();
    expect(ui.recordings.sessions).toEqual([]);
    expect(ui.recordings.usage).toEqual({ sessions: 0, bytes_total: 0 });
    expect(ui.recordings.loading).toBe(false);
    expect(ui.recordings.error).toBeNull();
  });
});
