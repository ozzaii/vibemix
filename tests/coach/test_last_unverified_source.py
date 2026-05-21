# SPDX-License-Identifier: Apache-2.0
"""Plan 55-03 Task 2 — pins StrippedRateTracker.last_unverified() as the REAL
source for SessionCitationPayload.last_unverified_response.

The holder is fed by an optional keyword-only kwarg on record():
``record(stripped, *, unverified_text=None)``. When unverified_text is
provided (on a STRIP or a BYPASS — both surface text the user did/did-not
hear), it overwrites self._last_unverified ("most-recent" semantics). A clean
emit (record(False) with no text) leaves it untouched. The default None keeps
every existing record(bool) call site byte-identical — the rolling-rate +
cumulative-slop counters work whether or not text is passed.

This REPLACES the hardcoded ``last_unverified_response = None`` in
__main__.py's _citation_telemetry() (closed in Task 4).
"""

from __future__ import annotations

from vibemix.coach import StrippedRateTracker


# ---------------------------------------------------------------------------
# Cold-start + clean emit — None
# ---------------------------------------------------------------------------


def test_last_unverified_cold_start_is_none() -> None:
    """A fresh tracker.last_unverified() is None (nothing stripped yet)."""
    tracker = StrippedRateTracker()
    assert tracker.last_unverified() is None


def test_clean_record_does_not_set_last_unverified() -> None:
    """record(False) with no text (a clean emit) leaves last_unverified() None."""
    tracker = StrippedRateTracker()
    tracker.record(False)
    assert tracker.last_unverified() is None


# ---------------------------------------------------------------------------
# Strip / bypass with text — surfaces the unverified text
# ---------------------------------------------------------------------------


def test_strip_with_text_sets_last_unverified() -> None:
    """record(True, unverified_text=...) surfaces the stripped text."""
    tracker = StrippedRateTracker()
    tracker.record(True, unverified_text="ghost line [ev:GHOST@9.9]")
    assert tracker.last_unverified() == "ghost line [ev:GHOST@9.9]"


def test_bypass_with_text_sets_last_unverified() -> None:
    """record(False, unverified_text=...) also surfaces text.

    A bypass means the user HEARD an unverified line — the diagnostics
    surface must reflect it, so bypass text sets the holder too.
    """
    tracker = StrippedRateTracker()
    tracker.record(False, unverified_text="bypassed line [ev:GHOST@9.9]")
    assert tracker.last_unverified() == "bypassed line [ev:GHOST@9.9]"


def test_last_unverified_most_recent_overwrites() -> None:
    """A later unverified emission overwrites — most-recent semantics."""
    tracker = StrippedRateTracker()
    tracker.record(True, unverified_text="older")
    assert tracker.last_unverified() == "older"
    tracker.record(True, unverified_text="newer")
    assert tracker.last_unverified() == "newer"


def test_clean_emit_between_strips_does_not_clear() -> None:
    """A clean record(False) after a strip leaves the last unverified text intact.

    The holder is "most recent UNVERIFIED" — a clean turn does not erase it.
    """
    tracker = StrippedRateTracker()
    tracker.record(True, unverified_text="ghost")
    tracker.record(False)  # clean, no text — must not clear
    assert tracker.last_unverified() == "ghost"


# ---------------------------------------------------------------------------
# Backward-compat — record(bool) without the kwarg never sets the holder
# ---------------------------------------------------------------------------


def test_record_without_kwarg_does_not_set_last_unverified() -> None:
    """record(True) / record(False) without unverified_text leave it None.

    Pins the default-None contract that keeps every existing record(bool)
    call site byte-identical.
    """
    tracker = StrippedRateTracker()
    tracker.record(True)
    tracker.record(False)
    tracker.record(True)
    assert tracker.last_unverified() is None


def test_record_without_kwarg_still_drives_rate_and_slop() -> None:
    """The optional kwarg does not perturb rate()/slop_ratio() — they still
    work whether or not text is passed."""
    t = [100.0]
    tracker = StrippedRateTracker(time_fn=lambda: t[0])
    tracker.record(True, unverified_text="x")
    tracker.record(False)
    # 1 stripped / 2 total — both signals move regardless of the text kwarg.
    assert tracker.slop_ratio() == 0.5
    assert tracker.rate() == 0.5
