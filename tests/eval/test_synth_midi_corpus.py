# SPDX-License-Identifier: Apache-2.0
"""Pins for scripts/eval/synth_midi_corpus.py — the replay-corpus tape minter.

The spec path is how sparse, landmark-timed tapes get minted per corpus; the
legacy no-spec path must keep emitting the exact 112321 tape (its density is
itself a measured reference point in the 2026-06-09 bench history).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "eval" / "synth_midi_corpus.py"
_spec = importlib.util.spec_from_file_location("synth_midi_corpus", _SCRIPT)
assert _spec is not None and _spec.loader is not None
smc = importlib.util.module_from_spec(_spec)
sys.modules["synth_midi_corpus"] = smc
_spec.loader.exec_module(smc)


def test_legacy_tape_unchanged() -> None:
    rows = smc.build_move_script()
    assert len(rows) == 139  # the measured 112321 tape — a bench reference point
    assert rows == sorted(rows, key=lambda r: r["ts"])


def test_spec_rows_sorted_and_bounded() -> None:
    spec = {
        "tracks": [[0.0, "A - One", 100.0]],
        "moves": [
            {"kind": "eq_kill", "t": 30.0, "deck": "A", "band": "low", "hold": 4.0, "depth": 6},
            {"kind": "transition", "t": 60.0, "dur": 10.0, "from_deck": "A", "to_deck": "B", "bass_swap": True},
        ],
    }
    rows = smc.build_move_script_from_spec(spec)
    assert rows == sorted(rows, key=lambda r: r["ts"])
    assert all(0 <= r["data2"] <= 127 for r in rows)
    assert all(r["type"] == "cc" for r in rows)


def test_transition_touches_both_decks_and_xfader() -> None:
    spec = {
        "tracks": [],
        "moves": [
            {"kind": "transition", "t": 50.0, "dur": 12.0, "from_deck": "A", "to_deck": "B", "bass_swap": True}
        ],
    }
    rows = smc.build_move_script_from_spec(spec)
    move_rows = [r for r in rows if r["ts"] >= 50.0]
    channels = {(r["channel"], r["data1"]) for r in move_rows}
    assert (smc._CH_DECK_A, smc._CC_VOL) in channels
    assert (smc._CH_DECK_B, smc._CC_VOL) in channels
    assert (smc._CH_MIXER, smc._CC_XFADER) in channels
    # bass swap rides both decks' low EQ
    assert (smc._CH_DECK_A, smc._CC_EQ_LOW) in channels
    assert (smc._CH_DECK_B, smc._CC_EQ_LOW) in channels


def test_eq_kill_restores_to_center() -> None:
    spec = {
        "tracks": [],
        "moves": [{"kind": "eq_kill", "t": 10.0, "deck": "A", "band": "low", "hold": 3.0, "depth": 8}],
    }
    rows = smc.build_move_script_from_spec(spec)
    eq_rows = [r for r in rows if r["data1"] == smc._CC_EQ_LOW and r["channel"] == smc._CH_DECK_A]
    assert eq_rows[-1]["data2"] == 64
    assert min(r["data2"] for r in eq_rows) == 8


def test_unknown_move_kind_fails_loud() -> None:
    with pytest.raises(SystemExit, match="unknown move kind"):
        smc.build_move_script_from_spec({"tracks": [], "moves": [{"kind": "scratch", "t": 1.0}]})


def test_nowplaying_from_spec_tracks() -> None:
    rows = smc.build_nowplaying_script([(0.0, "X - Y", 90.0), (90.0, "Z - W", 60.0)])
    assert [r["title"] for r in rows] == ["X - Y", "Z - W"]
    assert rows[1]["ts"] == 90.0
