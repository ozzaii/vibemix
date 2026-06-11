# SPDX-License-Identifier: Apache-2.0
"""Taste plumbing on LibraryToolset.transition_slate (the Viber prep slate).

The live pill already pays for a consent-gated taste dimension: ``__main__``
loads ``app_data_dir()/taste_feedback.jsonl`` through
``intel.taste_model.load_taste_model`` and hands the role-pair scores to
``SuggestionService`` → ``TransitionScoringInput.taste_scores``. These tests
pin that Viber's ``transition_slate`` reads the SAME local store under the
SAME consent gate:

  * consent ON + feedback rows → the scoring input carries non-default taste
    scores for a known role pair, and the emitted candidate's taste component
    reflects them exactly (receipt honesty — the number is real, never
    fabricated).
  * consent OFF, or no feedback file, or a consent-read failure → byte-identical
    to the unwired behavior (``taste_scores=None`` → flat 0.50 component, and
    no rationale line ever mentions taste).
  * the store is read ONCE per toolset instance (one disk read per run).

Grounding (Cardinal Invariant #2): taste scores are role-pair keyed weights —
no track ids ride in, so the seen-set is provably untouched by the taste load.

No network; store/embedder/library fakes mirror test_setprep_tools.py. The
library fixture sets ``lib.tracks`` directly and never writes
``RekordboxLibrary.CACHE_PATH``, so no cache-path monkeypatch is needed.
"""

from __future__ import annotations

import numpy as np
import pytest

from vibemix.intel.feedback import append_feedback_event, parse_feedback_event
from vibemix.intel.taste_model import load_taste_model
from vibemix.library.rekordbox import CuePoint, RekordboxLibrary, TrackEntry
from vibemix.library.toolset import LibraryToolset

# --------------------------------------------------------------------------- #
# Fixtures — mirror test_setprep_tools.py fakes.
# --------------------------------------------------------------------------- #


def _track(tid: str, bpm: float = 124.0, key: str = "8A") -> TrackEntry:
    return TrackEntry(
        track_id=tid,
        title=f"Title {tid}",
        artist=f"Artist {tid}",
        album="A",
        bpm=bpm,
        key=key,
        duration_s=300.0,
        cues=(),
        filepath=f"/tmp/{tid}.mp3",
    )


class _FakeBackend:
    def __init__(self, ids, vectors):
        self._ids, self._vectors = ids, vectors

    def load_all(self):
        return self._ids, self._vectors


class _FakeStore:
    def __init__(self, ids, vectors, ranked, section_vectors=None):
        self._backend = _FakeBackend(ids, vectors)
        self._ranked = ranked  # list[(track_id, sim)]
        self.section_vectors = section_vectors or {}

    def search_centered(self, qvec, k=10):
        return self._ranked[:k]


@pytest.fixture
def library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    lib.tracks = {f"t{i:03d}": _track(f"t{i:03d}", bpm=124.0 + i) for i in range(3)}
    # Cue-anchored outgoing/incoming pair so best_source_section resolves an
    # outro→intro role pair — the exact key the synthetic taste rows train.
    lib.tracks["t000"] = TrackEntry(
        track_id="t000",
        title="Outgoing",
        artist="Artist",
        album="A",
        bpm=128.0,
        key="8A",
        duration_s=300.0,
        cues=(CuePoint(name="OUT", type="cue", start_s=240.0, end_s=None, number=5),),
        filepath="/tmp/t000.mp3",
    )
    lib.tracks["t001"] = TrackEntry(
        track_id="t001",
        title="Incoming",
        artist="Artist",
        album="A",
        bpm=128.0,
        key="9A",
        duration_s=300.0,
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
        filepath="/tmp/t001.mp3",
    )
    return lib


@pytest.fixture
def store() -> _FakeStore:
    ids = [f"t{i:03d}" for i in range(3)]
    vectors = np.eye(3, 8, dtype=np.float32)
    ranked = [(tid, 0.9 - 0.05 * i) for i, tid in enumerate(ids)]
    return _FakeStore(ids, vectors, ranked)


@pytest.fixture
def toolset(store, library) -> LibraryToolset:
    # embedder is unused on the ref-ids / no-text path.
    ts = LibraryToolset(embedder=None, store=store, library=library)
    ts.seen.update({"t000", "t001"})
    return ts


@pytest.fixture
def captured_scoring_inputs(monkeypatch) -> list:
    """Spy on the lazily-imported scorer, delegating to the real one."""
    from vibemix.intel import transition_scorer

    captured: list = []
    real = transition_scorer.score_transition_slate

    def _spy(scoring_input, **kwargs):
        captured.append(scoring_input)
        return real(scoring_input, **kwargs)

    monkeypatch.setattr(transition_scorer, "score_transition_slate", _spy)
    return captured


_SLATE_ARGS = {"source_track_id": "t000", "candidate_track_ids": ["t001"]}


def _feedback_event(event_id: str, session_id: str, label: str, role_pair: tuple[str, str]):
    return parse_feedback_event(
        {
            "event_id": event_id,
            "session_id": session_id,
            "surface": "prep_chat",
            "action": "transition_labeled",
            "label": label,
            "role_from": role_pair[0],
            "role_to": role_pair[1],
        }
    )


def _write_taste_rows(path) -> None:
    # ≥10 taste events across ≥2 sessions for one pair → a learned positive
    # weight (the same thresholds the live pill's model applies).
    for i in range(10):
        append_feedback_event(
            path,
            _feedback_event(f"evt_{i}", f"s{i % 3}", "would_play", ("outro", "intro")),
            profile_consent=True,
        )


def _wire_taste_env(monkeypatch, tmp_path, *, consent: bool) -> None:
    """Point the toolset's lazy consent + store seams at test doubles."""
    monkeypatch.setattr("vibemix.profile.load_consent", lambda: consent)
    monkeypatch.setattr("vibemix.runtime.config_store.app_data_dir", lambda: tmp_path)


# --------------------------------------------------------------------------- #
# Consent ON + rows on disk → real taste scores reach the scorer + receipts.
# --------------------------------------------------------------------------- #


def test_slate_carries_taste_scores_with_consent_on(
    toolset, captured_scoring_inputs, monkeypatch, tmp_path
):
    _wire_taste_env(monkeypatch, tmp_path, consent=True)
    _write_taste_rows(tmp_path / "taste_feedback.jsonl")
    expected = load_taste_model(
        tmp_path / "taste_feedback.jsonl", profile_consent=True
    ).taste_scores()
    assert expected[("outro", "intro")] > 0.60  # synthetic rows actually trained

    out = toolset.transition_slate(dict(_SLATE_ARGS))

    assert "error" not in out
    assert len(captured_scoring_inputs) == 1
    assert captured_scoring_inputs[0].taste_scores == expected
    # Receipt honesty: the emitted component IS the learned score, not a
    # fabricated number.
    candidate = out["candidates"][0]
    assert candidate["from_role"] == "outro"
    assert candidate["to_role"] == "intro"
    assert candidate["components"]["taste"] == pytest.approx(expected[("outro", "intro")])


def test_taste_load_never_touches_the_grounding_spine(toolset, monkeypatch, tmp_path):
    _wire_taste_env(monkeypatch, tmp_path, consent=True)
    _write_taste_rows(tmp_path / "taste_feedback.jsonl")
    seen_before = set(toolset.seen)

    out = toolset.transition_slate(dict(_SLATE_ARGS))

    assert "error" not in out
    assert toolset.seen == seen_before


# --------------------------------------------------------------------------- #
# Consent OFF / no file / consent-read failure → byte-identical flat behavior.
# --------------------------------------------------------------------------- #


def test_slate_taste_stays_flat_with_consent_off(
    toolset, captured_scoring_inputs, monkeypatch, tmp_path
):
    _wire_taste_env(monkeypatch, tmp_path, consent=False)
    # Rows exist on disk, but consent OFF must keep them out of scoring.
    _write_taste_rows(tmp_path / "taste_feedback.jsonl")

    out = toolset.transition_slate(dict(_SLATE_ARGS))

    assert "error" not in out
    assert captured_scoring_inputs[0].taste_scores is None
    assert out["candidates"][0]["components"]["taste"] == pytest.approx(0.50)


def test_slate_taste_stays_flat_without_feedback_file(
    toolset, captured_scoring_inputs, monkeypatch, tmp_path
):
    _wire_taste_env(monkeypatch, tmp_path, consent=True)

    out = toolset.transition_slate(dict(_SLATE_ARGS))

    assert "error" not in out
    assert captured_scoring_inputs[0].taste_scores is None
    candidate = out["candidates"][0]
    assert candidate["components"]["taste"] == pytest.approx(0.50)
    # Honesty: an empty model must never mint a taste rationale line.
    assert not any("taste" in reason.lower() for reason in candidate["reasons"])


def test_slate_degrades_to_flat_when_consent_read_fails(
    toolset, captured_scoring_inputs, monkeypatch, tmp_path
):
    def _boom() -> bool:
        raise OSError("state.json unreadable")

    monkeypatch.setattr("vibemix.profile.load_consent", _boom)
    monkeypatch.setattr("vibemix.runtime.config_store.app_data_dir", lambda: tmp_path)
    _write_taste_rows(tmp_path / "taste_feedback.jsonl")

    out = toolset.transition_slate(dict(_SLATE_ARGS))

    # Handlers return, never raise — and an unknown consent reads as withheld.
    assert "error" not in out
    assert captured_scoring_inputs[0].taste_scores is None
    assert out["candidates"][0]["components"]["taste"] == pytest.approx(0.50)


# --------------------------------------------------------------------------- #
# One disk read per run (per toolset instance).
# --------------------------------------------------------------------------- #


def test_taste_store_is_read_once_per_toolset_instance(toolset, monkeypatch, tmp_path):
    _wire_taste_env(monkeypatch, tmp_path, consent=True)
    _write_taste_rows(tmp_path / "taste_feedback.jsonl")

    from vibemix.intel import taste_model as taste_model_mod

    calls = {"n": 0}
    real = taste_model_mod.load_taste_model

    def _counting(path, **kwargs):
        calls["n"] += 1
        return real(path, **kwargs)

    monkeypatch.setattr(taste_model_mod, "load_taste_model", _counting)

    first = toolset.transition_slate(dict(_SLATE_ARGS))
    second = toolset.transition_slate(dict(_SLATE_ARGS))

    assert "error" not in first and "error" not in second
    assert calls["n"] == 1
