# SPDX-License-Identifier: Apache-2.0
"""One Mind S5 — debrief → profile write-back tests.

Pins the contract that keeps the persona-shaping profile safe:
  1. Consent-gated (no consent → no write).
  2. Best-effort (a builder/save failure never raises — the debrief must not
     crash on the write-back).
  3. Uses the STRUCTURED events + evidence path (the proven build_profile), and
     skips when there is no signal to learn from.
"""

from __future__ import annotations

from vibemix.debrief.profile_writeback import write_back_profile


def _consent_on() -> bool:
    return True


def _consent_off() -> bool:
    return False


def test_s5_consent_off_writes_nothing() -> None:
    saved: list = []
    wrote = write_back_profile(
        [{"type": "TRACK_CHANGE"}],
        {"event": {"TRACK_CHANGE": [1.0, 2.0]}},
        consent_loader=_consent_off,
        prior_loader=lambda: None,
        builder=lambda *a, **k: {"preferred_genre": "techno"},
        saver=saved.append,
    )
    assert wrote is False
    assert saved == []  # consent gate fires before the builder


def test_s5_consent_on_builds_and_saves() -> None:
    saved: list = []
    seen_args: dict = {}

    def _builder(prior, events, evidence, *, consent):
        seen_args.update(prior=prior, events=events, evidence=evidence, consent=consent)
        return {"preferred_genre": "techno"}

    wrote = write_back_profile(
        [{"type": "MIX_MOVE"}],
        {"event": {"MIX_MOVE": [1.0, 2.0, 3.0]}},
        consent_loader=_consent_on,
        prior_loader=lambda: {"preferred_genre": "house"},
        builder=_builder,
        saver=saved.append,
    )
    assert wrote is True
    assert saved == [{"preferred_genre": "techno"}]
    # Structured session signal is forwarded to the builder (closes the
    # session_events=[] gap; the evidence snapshot is grounded, not drill prose).
    assert seen_args["events"] == [{"type": "MIX_MOVE"}]
    assert seen_args["evidence"] == {"event": {"MIX_MOVE": [1.0, 2.0, 3.0]}}
    assert seen_args["consent"] is True


def test_s5_nothing_to_learn_skips() -> None:
    saved: list = []
    wrote = write_back_profile(
        [],
        {},
        consent_loader=_consent_on,
        prior_loader=lambda: None,  # no prior + no signal → skip
        builder=lambda *a, **k: {"x": 1},
        saver=saved.append,
    )
    assert wrote is False
    assert saved == []


def test_s5_builder_none_writes_nothing() -> None:
    saved: list = []
    wrote = write_back_profile(
        [],
        {"event": {"TRACK_CHANGE": [1.0, 2.0]}},
        consent_loader=_consent_on,
        prior_loader=lambda: {"preferred_genre": "house"},
        builder=lambda *a, **k: None,  # insufficient evidence per builder
        saver=saved.append,
    )
    assert wrote is False
    assert saved == []


def test_s5_builder_exception_is_swallowed() -> None:
    saved: list = []

    def _boom(*a, **k):
        raise RuntimeError("builder blew up")

    wrote = write_back_profile(
        [],
        {"event": {"TRACK_CHANGE": [1.0, 2.0]}},
        consent_loader=_consent_on,
        prior_loader=lambda: {"preferred_genre": "house"},
        builder=_boom,
        saver=saved.append,
    )
    assert wrote is False  # never raises — the debrief must not crash
    assert saved == []


def test_s5_save_exception_is_swallowed() -> None:
    def _boom_save(_profile):
        raise OSError("disk full")

    wrote = write_back_profile(
        [],
        {"event": {"TRACK_CHANGE": [1.0, 2.0]}},
        consent_loader=_consent_on,
        prior_loader=lambda: {"preferred_genre": "house"},
        builder=lambda *a, **k: {"preferred_genre": "techno"},
        saver=_boom_save,
    )
    assert wrote is False  # save failure is contained
