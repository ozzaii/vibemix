# SPDX-License-Identifier: Apache-2.0
"""Pins for the keyless auto-crate set-prep path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pytest

import vibemix.library.create_playlist as cp_mod
from vibemix.library import energy as energy_mod
from vibemix.library import toolset as tool_mod
from vibemix.library.auto_crate import AutoCrateResult, build_auto_crate
from vibemix.library.energy import EnergyScore
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry
from vibemix.library.toolset import LibraryToolset


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
    def __init__(self, ids: list[str], vectors: np.ndarray) -> None:
        self._ids = ids
        self._vectors = vectors

    def load_all(self):
        return self._ids, self._vectors


class _FakeStore:
    def __init__(self, ids: list[str], vectors: np.ndarray) -> None:
        self._backend = _FakeBackend(ids, vectors)
        self._ranked = [(tid, 0.95 - 0.05 * i) for i, tid in enumerate(ids)]

    def search_centered(self, qvec, k=10):
        return self._ranked[:k]


@pytest.fixture
def library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    keys = ["8A", "9A", "8B", "7A", "8A", "9B"]
    lib.tracks = {f"t{i:03d}": _track(f"t{i:03d}", bpm=124.0 + i, key=keys[i]) for i in range(6)}
    return lib


@pytest.fixture
def toolset(library) -> LibraryToolset:
    ids = list(library.tracks)
    vectors = np.eye(len(ids), 8, dtype=np.float32)
    return LibraryToolset(embedder=None, store=_FakeStore(ids, vectors), library=library)


@pytest.fixture(autouse=True)
def deterministic_writes(monkeypatch, tmp_path):
    monkeypatch.setattr(
        energy_mod,
        "score_energy_cached",
        lambda *a, **k: EnergyScore(score=70.0, breakdown={}),
    )

    def create_playlist_tmp(library, name, track_ids):
        return cp_mod.create_playlist(library, name, track_ids, out_dir=tmp_path / "playlists")

    monkeypatch.setattr(tool_mod, "create_playlist", create_playlist_tmp)


def test_auto_crate_builds_grounded_playlist_and_export(toolset, tmp_path):
    result = build_auto_crate(
        ref_track_ids=["t000"],
        curve="opener",
        n_slots=3,
        k=6,
        name="Fast Hardgroove",
        export="both",
        out_path=str(tmp_path / "fast.xml"),
        toolset=toolset,
    )

    assert result.stop_reason == "exported"
    assert len(result.track_ids) == 3
    assert set(result.track_ids).issubset(toolset.seen)
    assert result.playlist is not None
    assert Path(result.playlist["m3u_path"]).exists()
    assert Path(result.playlist["json_path"]).exists()
    assert result.export_path == str(tmp_path / "fast.xml")
    assert result.export_outputs == {
        "rekordbox": str(tmp_path / "fast.xml"),
        "m3u8": str(tmp_path / "fast.m3u8"),
    }
    assert Path(result.export_path).exists()
    assert Path(result.export_outputs["m3u8"]).exists()
    assert [row["name"] for row in result.tool_trace] == [
        "discover_pool",
        "sequence_set",
        "transition_slate",
        "transition_slate",
        "create_playlist",
        "export_set",
    ]
    assert "min_dur=120.0s" in result.tool_trace[0]["summary"]
    assert any("O7:" in gate for gate in result.owner_gates)
    assert any("O10:" in gate for gate in result.owner_gates)


def test_auto_crate_preserves_all_carrier_export_receipt(toolset, tmp_path, monkeypatch):
    original_dispatch = toolset.dispatch

    def dispatch(name, args):
        if name != "export_set":
            return original_dispatch(name, args)
        assert args["target"] == "all"
        assert args["tag_write_granted"] is True
        out_xml = tmp_path / "all.xml"
        out_m3u8 = tmp_path / "all.m3u8"
        out_xml.write_text("<DJ_PLAYLISTS/>", encoding="utf-8")
        out_m3u8.write_text("#EXTM3U\n", encoding="utf-8")
        return {
            "exported": True,
            "target": "all",
            "path": str(out_xml),
            "outputs": {"rekordbox": str(out_xml), "m3u8": str(out_m3u8)},
            "tag_receipts": [
                {
                    "carrier": "markers2_tags",
                    "compatible_apps": ["Serato", "Mixxx"],
                    "tagged": 2,
                    "cues_total": 6,
                    "skipped": 0,
                    "files": ["/tmp/a.mp3", "/tmp/b.mp3"],
                    "skipped_tracks": [],
                }
            ],
            "import_instructions": [
                {
                    "app": "Rekordbox",
                    "carrier": "rekordbox_xml",
                    "path": str(out_xml),
                    "writes_audio_tags": False,
                    "instruction": "Import XML",
                },
                {
                    "app": "Serato, Mixxx",
                    "carrier": "markers2_tags",
                    "files": ["/tmp/a.mp3", "/tmp/b.mp3"],
                    "writes_audio_tags": True,
                    "instruction": "Reload files",
                },
            ],
            "auto_cues": {"enabled": True, "tracks_cued": 2, "cues_added": 6},
        }

    monkeypatch.setattr(toolset, "dispatch", dispatch)

    result = build_auto_crate(
        ref_track_ids=["t000"],
        curve="opener",
        n_slots=3,
        k=6,
        name="All Carriers",
        export="all",
        tag_write_granted=True,
        out_path=str(tmp_path / "all.xml"),
        toolset=toolset,
    )

    assert result.stop_reason == "exported"
    assert result.export_outputs == {
        "rekordbox": str(tmp_path / "all.xml"),
        "m3u8": str(tmp_path / "all.m3u8"),
    }
    assert result.export_tag_receipts[0]["carrier"] == "markers2_tags"
    assert result.export_tag_receipts[0]["compatible_apps"] == ["Serato", "Mixxx"]
    assert result.export_import_instructions[0]["carrier"] == "rekordbox_xml"
    assert result.export_import_instructions[1]["carrier"] == "markers2_tags"
    assert result.to_dict()["export_import_instructions"][1]["files"] == [
        "/tmp/a.mp3",
        "/tmp/b.mp3",
    ]
    assert result.export_auto_cues == {"enabled": True, "tracks_cued": 2, "cues_added": 6}


def test_auto_crate_allows_explicit_short_tool_override(toolset):
    result = build_auto_crate(
        ref_track_ids=["t000"],
        curve="opener",
        n_slots=3,
        k=6,
        name="Short Tools",
        min_duration_s=0.0,
        toolset=toolset,
    )

    assert result.stop_reason == "created"
    assert "min_dur=0.0s" in result.tool_trace[0]["summary"]


def test_auto_crate_requires_query_or_refs(toolset):
    result = build_auto_crate(toolset=toolset)

    assert result.stop_reason == "no_intent"
    assert result.tool_trace == []
    assert "query and/or" in (result.error or "")


def test_rationale_is_grounded_only(toolset):
    result = build_auto_crate(
        ref_track_ids=["t000"],
        curve="opener",
        n_slots=3,
        k=6,
        name="dark massive banger",
        toolset=toolset,
    )

    rationale = result.rationale.lower()
    assert "energy fit error" in rationale
    assert "average coherence" in rationale
    assert "lower is better" in rationale
    for invented_adjective in ("dark", "massive", "banger"):
        assert invented_adjective not in rationale
    assert "fit 70/100" not in rationale


def test_transition_receipts_fail_soft(toolset, monkeypatch):
    monkeypatch.setattr(
        toolset,
        "transition_slate",
        lambda args: {"error": "transition model unavailable"},
    )

    result = build_auto_crate(
        ref_track_ids=["t000"],
        curve="opener",
        n_slots=3,
        k=6,
        name="Transitions Optional",
        toolset=toolset,
    )

    assert result.stop_reason == "created"
    assert result.transition_receipts
    assert all(row["error"] == "transition model unavailable" for row in result.transition_receipts)
    assert "Transition receipts resolved 0/2" in result.rationale


def test_cli_auto_crate_passes_refs_and_args(monkeypatch, capsys):
    import vibemix.__main__ as main_mod
    import vibemix.library.auto_crate as auto_mod

    seen: dict[str, object] = {}

    def fake_build_auto_crate(**kwargs):
        seen.update(kwargs)
        return AutoCrateResult(
            name="CLI Fast",
            stop_reason="exported",
            curve=kwargs["curve"],
            n_slots=kwargs["n_slots"],
            ref_track_ids=kwargs["ref_track_ids"],
            track_ids=["t001"],
            playlist={"m3u_path": "/tmp/cli.m3u8", "json_path": "/tmp/cli.json"},
            export_path="/tmp/cli.xml",
        )

    monkeypatch.setattr(auto_mod, "build_auto_crate", fake_build_auto_crate)

    rc = main_mod._cmd_library_auto_crate(
        argparse.Namespace(
            query=None,
            ref_track_ids=["t000"],
            ref_track_ids_csv="t001, t002",
            curve="peak_time",
            n_slots=4,
            k=12,
            name="CLI Fast",
            export="both",
            out_path="/tmp/cli.xml",
            bpm_min=124.0,
            bpm_max=130.0,
            min_duration_s=None,
            max_duration_s=None,
            novelty=0.25,
            json=True,
        )
    )

    captured = capsys.readouterr()
    assert rc == 0
    assert seen["ref_track_ids"] == ["t000", "t001", "t002"]
    assert seen["curve"] == "peak_time"
    assert seen["export"] == "both"
    assert seen["novelty"] == 0.25
    assert json.loads(captured.out)["stop_reason"] == "exported"
    assert "auto-crate 'CLI Fast'" in captured.err


def test_cli_auto_crate_write_tags_defaults_to_all_carriers(monkeypatch, capsys):
    import vibemix.__main__ as main_mod
    import vibemix.library.auto_crate as auto_mod

    seen: dict[str, object] = {}

    def fake_build_auto_crate(**kwargs):
        seen.update(kwargs)
        return AutoCrateResult(
            name="CLI All",
            stop_reason="exported",
            curve=kwargs["curve"],
            n_slots=kwargs["n_slots"],
            ref_track_ids=kwargs["ref_track_ids"],
            track_ids=["t001"],
            playlist={"m3u_path": "/tmp/all.m3u8", "json_path": "/tmp/all.json"},
            export_path="/tmp/all.xml",
            export_outputs={"rekordbox": "/tmp/all.xml", "m3u8": "/tmp/all.m3u8"},
            export_import_instructions=[
                {"carrier": "rekordbox_xml", "path": "/tmp/all.xml"},
                {"carrier": "m3u8", "path": "/tmp/all.m3u8"},
                {"carrier": "markers2_tags", "files": ["/tmp/a.mp3"]},
            ],
        )

    monkeypatch.setattr(auto_mod, "build_auto_crate", fake_build_auto_crate)

    rc = main_mod._cmd_library_auto_crate(
        argparse.Namespace(
            query="fast export",
            ref_track_ids=[],
            ref_track_ids_csv=None,
            curve="opener",
            n_slots=3,
            k=12,
            name="CLI All",
            export=None,
            out_path=None,
            bpm_min=None,
            bpm_max=None,
            min_duration_s=None,
            max_duration_s=None,
            novelty=None,
            write_tags=True,
            json=True,
        )
    )

    captured = capsys.readouterr()
    assert rc == 0
    assert seen["export"] == "all"
    assert seen["tag_write_granted"] is True
    payload = json.loads(captured.out)
    assert [row["carrier"] for row in payload["export_import_instructions"]] == [
        "rekordbox_xml",
        "m3u8",
        "markers2_tags",
    ]
