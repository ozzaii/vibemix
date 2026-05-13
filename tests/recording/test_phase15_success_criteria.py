# SPDX-License-Identifier: Apache-2.0
"""Phase 15 Plan 01 — ROADMAP success-criteria gates (audit + test).

This file is the TEST-side wedge for Phase 15's four ROADMAP success criteria.
It locks the surface-as-shipped against regression and documents the gaps that
Plans 15-02 / 15-03 / 15-04 will close.

NEVER edit ``recordings_index.py`` / ``config_store.py`` / ``__main__.py`` /
``runtime/settings.py`` to make these tests pass. They are read-only gates;
any failure here is either a regression (fix the source in a NEW plan) or a
real GAP (closure tracked in the table below — fix in 15-02/03/04).

----------------------------------------------------------------------
Audit Table — Phase 15 ROADMAP Success Criteria → Shipped Artifact → Status
----------------------------------------------------------------------

| # | ROADMAP success criterion | Shipped artifact (path:line) | Status   | Closure plan |
|---|---------------------------|------------------------------|----------|--------------|
| 1 | Settings → Recordings list — chronological roster of past sessions, reveal-in-Finder per row | `tauri/ui/src/settings/components/recording-browser.ts` (renderRecordingBrowser) + `recording-row.ts` (date + duration cells); newest-first sort enforced in `src/vibemix/runtime/recordings_index.py:296` (`summaries.sort(..., reverse=True)`) | PARTIAL | reveal-in-Finder icon → 15-04 |
| 2 | Per-row replay — voice.wav inline, input.wav opens in OS default app | inline `<audio controls>` for voice.wav via `convertFileSrc(asset://...)` in `recording-row.ts` (lazy-mount + collapse-teardown of decoder); native scrubber accent-color amber | PARTIAL | open-input.wav-externally icon → 15-04 |
| 3 | Delete with confirm pattern | SHIPPED via alternate pattern (impeccable Wave 5.A 2026-05-14): optimistic-remove + 4s undo toast in `recording-browser.ts` (~lines 332-360) replaces the modal confirm flow declared in CONTEXT.md. Locked by `recording-browser.spec.ts` Tests 6/7/8. The undo toast IS the confirm — see UI-SPEC §"Delete Flow" + §"Row delete (no modal)". | SHIPPED | n/a |
| 4 | Retention auto-prune 7d default + every 6h + events.jsonl logging | boot sweep at `src/vibemix/__main__.py:332` + session-close sweep at `src/vibemix/__main__.py:523` + settings-change sweep at `src/vibemix/runtime/settings.py:284-312`; default 7d declared in `config_store.ConfigStore.retention_days = 7` + retention-slider; ∞ sentinel short-circuit in `recordings_index.py:482-483` | PARTIAL | (a) periodic every-6h sweep loop → 15-02; (b) events.jsonl `retention_pruned` line → 15-02 |

----------------------------------------------------------------------
Gap Evidence (verbatim grep output, executed 2026-05-14)
----------------------------------------------------------------------

  $ grep -rn 'retention_pruned' src/vibemix/
  → no matches → GAP confirmed: retention_pruned events.jsonl line absent

  $ grep -rn '21600\\|hours=6\\|sweep_loop\\|sweep_task' src/vibemix/
  → no matches → GAP confirmed: periodic 6h sweep loop absent

  $ grep -rn 'reveal_in_os\\|open_external\\|recording.reveal' src/vibemix/ tauri/
  → no matches → GAP confirmed: reveal-in-OS / open-input.wav IPC absent

----------------------------------------------------------------------
Found Gaps → Closure Plan Pointers
----------------------------------------------------------------------

  * GAP A — periodic 6h sweep loop (`asyncio.create_task` w/ `await asyncio.sleep(21600)`) → addressed by **Plan 15-02**
  * GAP B — `events.jsonl` `{"event":"retention_pruned","count":N,"bytes":M,...}` log line → addressed by **Plan 15-02**
  * GAP C — reveal-in-OS sidecar IPC + UI icon → addressed by **Plan 15-03** (sidecar) and **Plan 15-04** (UI)
  * GAP D — open-input.wav-in-default-app sidecar IPC + UI icon → addressed by **Plan 15-04**

----------------------------------------------------------------------
Pre-existing Test Status (clean checkout, executed 2026-05-14)
----------------------------------------------------------------------

  $ pytest tests/recording/test_recordings_index.py tests/recording/test_retention_sweep.py tests/ui_bus/test_recordings_messages.py
  → 46 passed in 0.60s  (16 + 7 + 23 cases)

  $ npm run test -- --run \\
        src/settings/components/recording-browser.spec.ts \\
        src/settings/components/recording-row.spec.ts \\
        tests/session/ws-bridge.recordings.spec.ts
  → 34 tests passed (8 + 14 + 5 + extras)

Baseline is GREEN before any new test is added. The four pytest cases below
defend the SHIPPED columns of the audit table; the GAPS are tracked above for
closure in Plans 15-02 / 15-03 / 15-04.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from vibemix.runtime.config_store import ConfigStore
from vibemix.runtime.recordings_index import run_retention_sweep


# ---------------------------------------------------------------------------
# Local helpers — minimal session-dir factory.
#
# tests/recording/conftest.py exposes ``make_fake_session`` but it stamps
# session.json with the wall-clock ``datetime.now()`` (not a frozen value),
# which would defeat Tests A and C below — both depend on the dir name and
# the sweep's ``now`` argument being deterministic so the cutoff math is
# exact. We build dirs by hand instead, matching the schema-shape regex
# ``^\d{8}-\d{6}$`` enforced in recordings_index.py:78.
# ---------------------------------------------------------------------------


def _plant_session(root: Path, name: str) -> Path:
    """Create ``root/<name>`` with a ``voice.wav`` placeholder so rmtree has work."""
    session_dir = root / name
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "voice.wav").write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")  # 16 bytes
    return session_dir


# ===========================================================================
# Test A — default 7d retention prunes one >7d-old dir, keeps one ≤7d-old dir
#
# Defends ROADMAP success-criterion #4 ("default 7d") at the function
# boundary. The cutoff math is ``now - timedelta(days=retention_days)``
# (recordings_index.py:489); a session_start strictly older than cutoff is
# eligible. Frozen now=2026-05-14 12:00:00, retention_days=7 ⇒
# cutoff=2026-05-07 12:00:00. The 2026-01-01 dir is older → pruned. The
# 2026-05-13 dir is newer → kept.
# ===========================================================================


def test_default_retention_7d_prunes_old_session(tmp_path: Path) -> None:
    root = tmp_path / "recordings"
    root.mkdir()
    old = _plant_session(root, "20260101-120000")
    fresh = _plant_session(root, "20260513-120000")

    deleted = run_retention_sweep(
        root,
        retention_days=7,
        now=datetime(2026, 5, 14, 12, 0, 0),
    )

    assert deleted == ["20260101-120000"], (
        f"expected only the >7d-old dir to be pruned, got {deleted!r}"
    )
    assert not old.exists(), "old session dir must be removed from disk"
    assert fresh.exists(), "≤7d-old session dir must remain on disk"


# ===========================================================================
# Test B — ∞ sentinel (retention_days=36500) short-circuits BEFORE scandir
#
# Defends recordings_index.py:482-483 (``if retention_days >= 36500: return [];``)
# and the threat-register T-15-01-03 disposition: an attacker setting
# retention_days=36500 cannot trigger expensive scandir. Mock os.scandir to
# raise so any call would fail loud — assert the sentinel returns [] without
# the mock ever firing.
# ===========================================================================


def test_infinite_sentinel_36500_short_circuits_without_scan(
    tmp_path: Path,
) -> None:
    root = tmp_path / "recordings"
    root.mkdir()
    # Plant a session that WOULD be eligible for prune at retention_days=0 —
    # confirming the short-circuit fires BEFORE the scan loop.
    _plant_session(root, "20200101-000000")

    fake_scandir = MagicMock(side_effect=AssertionError("scandir must not be called"))
    with patch("vibemix.runtime.recordings_index.os.scandir", fake_scandir):
        deleted = run_retention_sweep(root, retention_days=36500)

    assert deleted == [], f"sentinel must return []; got {deleted!r}"
    fake_scandir.assert_not_called()


# ===========================================================================
# Test C — live-session dir excluded from sweep (T-15-03-06 threat-register)
#
# Defends recordings_index.py:476-481 docstring claim. The live session dir
# is created at started_at = now(); its dir name parses to a time strictly
# >= now - epsilon. With cutoff = now - retention_days (any positive
# retention), session_start >= cutoff so the ``continue`` branch
# (recordings_index.py:508) skips it. Even at retention_days=0 (cutoff=now),
# the dir name parses to "now - 1 second", which is strictly < cutoff — but
# the contract is that the active dir's started_at is at most epsilon
# behind the call's ``now`` argument. We model this by passing
# ``now = session_dir_time + 1 second``, so cutoff=session_dir_time+1s and
# session_start=session_dir_time → session_start < cutoff. We assert the
# sweep DOES NOT delete it because the dir was created AFTER the call's
# semantic "now" (the active session's started_at must be > cutoff for
# any sensible retention_days). Operationally: retention_days >= 1 day is
# the only configurable value (the slider's lowest stop is 1d, never 0d) —
# so the active session's started_at = wall-clock now is ALWAYS >>
# cutoff = now - 1day. Test C codifies this with retention_days=1.
# ===========================================================================


def test_live_session_dir_excluded_from_sweep(tmp_path: Path) -> None:
    root = tmp_path / "recordings"
    root.mkdir()
    # Frozen "now" = 2026-05-14 12:00:00. Active session started 30s ago.
    frozen_now = datetime(2026, 5, 14, 12, 0, 0)
    active_started = frozen_now - timedelta(seconds=30)
    active_name = active_started.strftime("%Y%m%d-%H%M%S")
    active_dir = _plant_session(root, active_name)

    deleted = run_retention_sweep(
        root,
        retention_days=1,  # cutoff = frozen_now - 1d → active session is way fresher
        now=frozen_now,
    )

    assert deleted == [], (
        f"live (active) session dir must NOT be pruned; got {deleted!r}"
    )
    assert active_dir.exists(), "active session dir must remain on disk"


# ===========================================================================
# Test D — default ConfigStore.retention_days == 7
#
# Defends ROADMAP success-criterion #4 "default 7d" at the config-store
# boundary. config_store.py:153 declares ``retention_days: int = 7``; this
# test catches a silent drift to e.g. 14 or 30 in a future refactor.
# ===========================================================================


def test_default_retention_days_is_7_in_config_store() -> None:
    cs = ConfigStore()
    assert cs.retention_days == 7, (
        f"ROADMAP §4 mandates default retention=7d; got {cs.retention_days!r} — "
        "if this changed intentionally, update the ROADMAP success criteria FIRST."
    )


# Implicit verification: no source files were modified by these tests.
# The 4 tests above exercise pure-read behavior of recordings_index +
# config_store; any failure is either a real regression (fix in a NEW plan)
# or a documentation drift between source and the audit table above.
