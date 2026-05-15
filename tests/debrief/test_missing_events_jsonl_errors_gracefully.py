# SPDX-License-Identifier: Apache-2.0
"""Session-loader edge: EventsMissing raised when events.jsonl absent."""

from __future__ import annotations

from pathlib import Path

import pytest

from vibemix.debrief import EventsMissing, load_session
from vibemix.debrief.session_loader import InvalidSessionDir


def test_no_events_jsonl_raises_events_missing(tmp_path: Path):
    sess = tmp_path / "20260515-empty"
    sess.mkdir()
    with pytest.raises(EventsMissing) as ei:
        load_session(sess)
    assert ei.value.reason == "events_missing"


def test_non_existent_session_dir_raises_invalid_session_dir(tmp_path: Path):
    bogus = tmp_path / "does-not-exist"
    with pytest.raises(InvalidSessionDir) as ei:
        load_session(bogus)
    assert ei.value.reason == "invalid_session_dir"


def test_events_missing_exception_carries_session_dir(tmp_path: Path):
    sess = tmp_path / "session"
    sess.mkdir()
    try:
        load_session(sess)
    except EventsMissing as e:
        assert e.session_dir == sess
        return
    raise AssertionError("EventsMissing not raised")  # pragma: no cover
