# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json

from scripts.eval import respan_sven_heartbeat_judge as judge


def _row(
    *,
    friend: int = 3,
    grounded: int = 3,
    earned: int = 3,
    move: int = 3,
    voice: int = 3,
    should_speak: bool = True,
) -> dict:
    return {
        "id": "fixture",
        "event": "MANUAL",
        "line": "Hold this for four bars, then move on the phrase.",
        "scores": {
            "friend_not_narrator": friend,
            "grounded_not_fabricated": grounded,
            "earned_not_constant": earned,
            "move_specific_not_spectrum": move,
            "voice_no_slop": voice,
            "should_speak": should_speak,
            "why": "fixture",
        },
    }


def test_quality_summary_passes_real_line_floor() -> None:
    summary = judge.quality_summary([_row()], min_judged=1, errors=0)

    assert summary["judged"] == 1
    assert summary["dim_means"]["grounded_not_fabricated"] == 3
    assert summary["failures"] == []


def test_quality_summary_fails_low_dimensions() -> None:
    summary = judge.quality_summary(
        [_row(friend=1, grounded=2, earned=1, voice=1)],
        min_judged=1,
        errors=0,
    )

    assert "mean friend_not_narrator 1.0 below 2" in summary["failures"]
    assert "mean grounded_not_fabricated 2.0 below 2.4" in summary["failures"]
    assert "mean earned_not_constant 1.0 below 2" in summary["failures"]
    assert "mean voice_no_slop 1.0 below 2" in summary["failures"]


def test_quality_summary_fails_should_not_have_spoken() -> None:
    summary = judge.quality_summary([_row(should_speak=False)], min_judged=1, errors=0)

    assert "should_NOT_have_spoken 1 > 0" in summary["failures"]


def test_quality_summary_fails_minimum_rows_and_errors() -> None:
    summary = judge.quality_summary([], min_judged=2, errors=1)

    assert "judged rows 0 below minimum 2" in summary["failures"]
    assert "judge errors 1 > 0" in summary["failures"]
    assert "no judged dim means" in summary["failures"]


def test_describe_bank_census_replay_silence_summary_passes_all_suppressed() -> None:
    kept, report = judge.describe_bank_census(
        [
            {"id": "0001_HEARTBEAT", "event": "HEARTBEAT", "line": "describe-bank"},
            {"id": "0002_PHASE", "event": "PHASE", "line": "more narration"},
            {"id": "0003_KICK_SWAP", "event": "KICK_SWAP", "line": "bare priority"},
        ]
    )
    summary = judge.census_silence_summary(report, min_rows=3)

    assert kept == []
    assert report["silenced_by_describe_bank_census"] == 3
    assert summary["pass"] is True
    assert summary["failures"] == []


def test_describe_bank_census_replay_silence_summary_fails_kept_rows() -> None:
    _kept, report = judge.describe_bank_census(
        [
            {
                "id": "0001_DROP",
                "event": "DROP",
                "line": "this priority event still needs a judge",
            },
        ]
    )
    summary = judge.census_silence_summary(report, min_rows=1)

    assert summary["pass"] is False
    assert "kept_for_judge 1 > 0" in summary["failures"]


def test_is_silenced_guard_substitution_detects_all_held_replies() -> None:
    # The live-claim guard replaces an unproven outcome claim with one of these
    # deterministic held replies AND leaves emit_corrected=False (the shipped
    # default) — so the runtime SILENCES them; they are never spoken. The recorded
    # response.txt still carries the substituted text, so the loader must not grade
    # them as spoken lines. Corpus-verified (2026-06-08): 140/144 such guard events
    # stripped, 0 organic. Import the canonical constants so the judge can never
    # drift out of sync with the runtime's held replies.
    from vibemix.state import deck_context as dc

    held = [
        dc.LIVE_TRANSITION_HELD_REPLY,
        dc.LIVE_CANDIDATE_HELD_REPLY,
        dc.LIVE_MOVE_EFFECT_HELD_REPLY,
        dc.LIVE_COACHING_ADVICE_HELD_REPLY,
        dc.LIVE_AUDIO_SOURCE_DETAIL_HELD_REPLY,
        dc.LIVE_TRACK_IDENTITY_HELD_REPLY,
        dc.LIVE_JUDGE_OVERPRAISE_HELD_REPLY,
        dc.LIVE_SPECTRAL_CLAIM_HELD_REPLY,
    ]
    assert judge.SILENCED_GUARD_SUBSTITUTIONS == frozenset(held)
    for reply in held:
        assert judge.is_silenced_guard_substitution(reply)
        assert judge.is_silenced_guard_substitution(f"  {reply}  ")  # whitespace-tolerant


def test_is_silenced_guard_substitution_passes_organic_line() -> None:
    assert not judge.is_silenced_guard_substitution(
        "Let it ride four bars, then snap it back on the phrase."
    )
    assert not judge.is_silenced_guard_substitution("")
    # A line that merely mentions a transition is still an organic spoken line.
    assert not judge.is_silenced_guard_substitution("That transition landed clean.")


def test_load_rows_skips_guard_silenced_held_reply(tmp_path) -> None:
    from vibemix.state import deck_context as dc

    inv = tmp_path / "invocations"

    def _mk(name: str, event: str, line: str) -> None:
        d = inv / name
        d.mkdir(parents=True)
        (d / "meta.json").write_text(json.dumps({"event": event}))
        (d / "response.txt").write_text(line)

    _mk("0001_PHASE", "PHASE", "Let it ride four bars, then snap it back.")  # organic → judged
    _mk("0002_PHASE", "PHASE", dc.LIVE_TRANSITION_HELD_REPLY)  # guard-silenced → skip
    _mk("0003_HEARTBEAT", "HEARTBEAT", "")  # already-silent → skip

    rows = judge.load_rows(tmp_path, set(), None)

    assert [r["line"] for r in rows] == ["Let it ride four bars, then snap it back."]


def test_load_rows_skips_wordless_citation_only_response(tmp_path) -> None:
    """Measured 2026-06-10 (baseline-cadence-midi-r2): the model answered with a
    bare citation atom plus a period. The runtime's TTS sanitizer now strips
    that to "" (the <empty> skip-TTS branch — never spoken), so the loader must
    count it as already-silent, exactly like the guard-substitution skip above:
    response.txt still records the raw text, but judging it as a spoken line
    scores a silence as friend-0 slop."""
    inv = tmp_path / "invocations"

    def _mk(name: str, event: str, line: str) -> None:
        d = inv / name
        d.mkdir(parents=True)
        (d / "meta.json").write_text(json.dumps({"event": event}))
        (d / "response.txt").write_text(line)

    _mk("0001_PHASE", "PHASE", "[energy:master_read=audio_peak_110_f3108ffa].")  # wordless → skip
    _mk("0002_PHASE", "PHASE", "Hold the low end open. [energy:master_read=audio_low_11_9b35751f]")

    rows = judge.load_rows(tmp_path, set(), None)

    assert [r["line"] for r in rows] == [
        "Hold the low end open. [energy:master_read=audio_low_11_9b35751f]"
    ]


def test_load_rows_skips_runtime_suppressed_turns(tmp_path) -> None:
    """The invocation dump is written even when the runtime SUPPRESSES the
    turn (slop / silence / stale / non_english) — response.txt keeps the
    original text, so a naive loader grades a silenced turn as a spoken line
    (2026-06-11 panel, instrument-honesty finding). meta['suppression'] is
    the runtime's own record of the decision; non-null counts as
    already-silent."""
    inv = tmp_path / "invocations"

    def _mk(name: str, event: str, line: str, suppression: str | None = None) -> None:
        d = inv / name
        d.mkdir(parents=True)
        meta = {"event": event}
        if suppression is not None:
            meta["suppression"] = suppression
        (d / "meta.json").write_text(json.dumps(meta))
        (d / "response.txt").write_text(line)

    _mk("0001_PHASE", "PHASE", "Hold the low end open for four bars.")
    _mk("0002_PHASE", "PHASE", "That drop was absolutely insane, fam!", suppression="slop")
    _mk("0003_PHASE", "PHASE", "Some stale line that never reached TTS.", suppression="stale")
    # A suppressed turn whose speculative HEAD already reached TTS was
    # partially heard — the instrument must never hide a heard line
    # (slop-audit required change, 2026-06-11).
    d = inv / "0004_PHASE"
    d.mkdir(parents=True)
    (d / "meta.json").write_text(
        json.dumps({"event": "PHASE", "suppression": "slop", "head_yielded": True})
    )
    (d / "response.txt").write_text("First sentence was heard. Then the slop arrived.")

    rows = judge.load_rows(tmp_path, set(), None)

    assert [r["line"] for r in rows] == [
        "Hold the low end open for four bars.",
        "First sentence was heard. Then the slop arrived.",
    ]


def test_probe_capture_status_reads_session_json(tmp_path) -> None:
    def _status(meta: dict | None) -> str:
        d = tmp_path / ("probe" + str(meta))
        d.mkdir()
        if meta is not None:
            (d / "session.json").write_text(json.dumps(meta))
        return judge.probe_capture_status(d)

    assert _status({"sven_probe_mode": True}) == "probe"
    assert _status({"sven_probe_mode": False}) == "shipped"
    assert _status({}) == "unknown"  # legacy recording, field absent
    assert _status(None) == "unknown"  # no session.json at all


def test_probe_caveat_loud_for_non_shipped() -> None:
    assert judge.probe_caveat("shipped") is None
    for status in ("probe", "unknown"):
        caveat = judge.probe_caveat(status)
        assert caveat is not None
        assert "NOT" in caveat  # loud: not the shipped spoken set
