# SPDX-License-Identifier: Apache-2.0
"""Prepared-pool awareness for Course 3 lessons."""
from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState
from vibemix.library.prepared_pool import (
    PreparedPool,
    PreparedPoolTrack,
    build_prepared_pool_prompt,
    load_latest_prepared_pool,
    next_track_id_after,
)
from vibemix.state.evidence_registry import EvidenceRegistry


def _write_pool(
    path: Path,
    *,
    name: str,
    created_at: float,
    track_count: int = 5,
) -> None:
    rows = [
        {
            "track_id": f"t{i}",
            "title": f"Track {i}",
            "artist": f"Artist {i}",
            "bpm": 124 + i,
            "key": "8A",
            "filepath": f"/tmp/t{i}.wav",
        }
        for i in range(1, track_count + 1)
    ]
    path.write_text(
        json.dumps(
            {
                "name": name,
                "created_at": created_at,
                "track_count": track_count,
                "dropped_ids": [],
                "tracks": rows,
            }
        ),
        encoding="utf-8",
    )


def _tutor_payloads(ipc: MagicMock) -> list[dict]:
    return [
        call.args[0]["payload"]
        for call in ipc.emit.call_args_list
        if call.args and call.args[0].get("type") == "ipc.learn.tutor_speak"
    ]


def _runtime(
    *,
    loader,
    registry: EvidenceRegistry | None = None,
) -> tuple[LessonRuntime, MagicMock]:
    ipc = MagicMock(name="ipc_router")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=LearnProgress(),
        evidence_registry=registry,
        prepared_pool_loader=loader,
    )
    return runtime, ipc


def test_load_latest_prepared_pool_ignores_corrupt_and_undersized(
    tmp_path: Path,
) -> None:
    """Only real five-track pool artifacts can drive L3.02 copy."""
    _write_pool(tmp_path / "old.json", name="Old Pool", created_at=10.0)
    _write_pool(tmp_path / "small.json", name="Small Pool", created_at=30.0, track_count=3)
    (tmp_path / "broken.json").write_text("{not-json", encoding="utf-8")
    _write_pool(tmp_path / "new.json", name="New Pool", created_at=20.0)

    pool = load_latest_prepared_pool(playlists_dir=tmp_path)

    assert pool is not None
    assert pool.name == "New Pool"
    assert pool.track_count == 5
    assert pool.tracks[0].display_name() == "Artist 1 - Track 1"


def test_load_latest_prepared_pool_uses_mtime_when_created_at_missing(
    tmp_path: Path,
) -> None:
    """Legacy/handwritten playlist JSON still gets a deterministic order."""
    _write_pool(tmp_path / "old.json", name="Old", created_at=10.0)
    missing_created = tmp_path / "missing-created.json"
    _write_pool(missing_created, name="Missing Created", created_at=1.0)
    raw = json.loads(missing_created.read_text(encoding="utf-8"))
    raw.pop("created_at")
    missing_created.write_text(json.dumps(raw), encoding="utf-8")
    os.utime(missing_created, (50.0, 50.0))

    pool = load_latest_prepared_pool(playlists_dir=tmp_path)

    assert pool is not None
    assert pool.name == "Missing Created"


def test_prepared_pool_prompt_is_specific_and_bounded() -> None:
    pool = PreparedPool(
        name="A" * 120,
        created_at=1.0,
        json_path=Path("pool.json"),
        tracks=(
            PreparedPoolTrack("t1", title="First " + "X" * 100, artist="A"),
            PreparedPoolTrack("t2", title="Second", artist="B"),
            PreparedPoolTrack("t3"),
            PreparedPoolTrack("t4"),
            PreparedPoolTrack("t5"),
        ),
    )

    text = build_prepared_pool_prompt(pool)

    assert len(text) <= 260
    assert text.startswith("latest saved pool:")
    assert "start with A - First" in text
    assert "load B - Second on the other deck." in text


def test_next_track_id_after_returns_following_pool_row() -> None:
    pool = PreparedPool(
        name="Plan",
        created_at=1.0,
        json_path=Path("pool.json"),
        tracks=(
            PreparedPoolTrack("t1"),
            PreparedPoolTrack("t2"),
            PreparedPoolTrack("t3"),
        ),
    )

    assert next_track_id_after(pool, "t1") == "t2"
    assert next_track_id_after(pool, "t3") is None
    assert next_track_id_after(pool, "missing") is None


def test_l302_emits_prepared_pool_prompt_with_grounded_track_citation() -> None:
    pool = PreparedPool(
        name="Peak Practice",
        created_at=1.0,
        json_path=Path("pool.json"),
        tracks=(
            PreparedPoolTrack("t1", title="Open", artist="One"),
            PreparedPoolTrack("t2", title="Second", artist="Two"),
            PreparedPoolTrack("t3"),
            PreparedPoolTrack("t4"),
            PreparedPoolTrack("t5"),
        ),
    )
    registry = EvidenceRegistry()
    registry.register_library(SimpleNamespace(tracks={"t1": None}))
    runtime, ipc = _runtime(loader=lambda: pool, registry=registry)

    runtime.send(
        "load",
        lesson_id="L3.02",
        course_id="course_3_play_mode",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    payloads = _tutor_payloads(ipc)
    assert payloads[0]["text"] == (
        "open a prepared five-track pool from build-a-set or your own queue. "
        "play track one."
    )
    assert payloads[1]["text"] == (
        "latest saved pool: Peak Practice, 5 tracks. "
        "start with One - Open; load Two - Second on the other deck."
    )
    assert payloads[1]["tts_marker"] == "L302.prepared_pool"
    assert payloads[1]["citations"] == ["[track:t1]"]


def test_l302_stays_on_fixture_copy_when_no_prepared_pool() -> None:
    runtime, ipc = _runtime(loader=lambda: None)

    runtime.send(
        "load",
        lesson_id="L3.02",
        course_id="course_3_play_mode",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    texts = [payload["text"] for payload in _tutor_payloads(ipc)]
    assert texts == [
        "open a prepared five-track pool from build-a-set or your own queue. "
        "play track one."
    ]


def test_l302_omits_track_citation_when_registry_does_not_resolve() -> None:
    pool = PreparedPool(
        name="Ungrounded",
        created_at=1.0,
        json_path=Path("pool.json"),
        tracks=(
            PreparedPoolTrack("not registered", title="Open", artist="One"),
            PreparedPoolTrack("t2", title="Second", artist="Two"),
            PreparedPoolTrack("t3"),
            PreparedPoolTrack("t4"),
            PreparedPoolTrack("t5"),
        ),
    )
    runtime, ipc = _runtime(loader=lambda: pool, registry=EvidenceRegistry())

    runtime.send(
        "load",
        lesson_id="L3.02",
        course_id="course_3_play_mode",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    assert _tutor_payloads(ipc)[1]["citations"] == []
