# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace


class _FakeReport:
    embedded = 1
    skipped_cached = 0
    failed = 0
    total = 1
    cue_agreement_tracks = 1
    cue_agreement_scored = 1
    cue_agreement_weak_labels = 2
    cue_agreement_score_sum = 0.75

    def as_dict(self) -> dict[str, object]:
        return {
            "embedded": self.embedded,
            "skipped_cached": self.skipped_cached,
            "failed": self.failed,
            "total": self.total,
            "cue_agreement": {
                "tracks": self.cue_agreement_tracks,
                "scored": self.cue_agreement_scored,
                "weak_labels": self.cue_agreement_weak_labels,
                "mean_score": self.cue_agreement_score_sum,
            },
        }


class _FakeSource:
    name = "rekordbox"

    def __init__(
        self,
        xml_path: str | None = None,
        nml_path: str | None = None,
    ) -> None:
        self.xml_path = xml_path
        self.nml_path = nml_path
        self.resolved_path = Path(xml_path or nml_path or "/fixture/collection.xml")

    def detect(self) -> bool:
        return True

    def default_paths(self) -> list[Path]:
        return [Path("/fixture/collection.xml")]


class _FakeTraktorSource(_FakeSource):
    name = "traktor"

    def default_paths(self) -> list[Path]:
        return [Path("/fixture/collection.nml")]


class _FakeStore:
    closed = False

    def close(self) -> None:
        self.closed = True


class _FakeClapEngine:
    backend = "fake-clap"


def _patch_ingest_dependencies(monkeypatch, *, anlz_builder, captured):
    import vibemix.library.anlz_ingest as anlz_mod
    import vibemix.library.clap_engine as clap_mod
    import vibemix.library.ingest as ingest_mod
    import vibemix.library.sources.rekordbox as source_mod
    import vibemix.library.sources.traktor as traktor_source_mod
    import vibemix.library.store as store_mod

    monkeypatch.setattr(source_mod, "RekordboxSource", _FakeSource)
    monkeypatch.setattr(traktor_source_mod, "TraktorSource", _FakeTraktorSource)
    monkeypatch.setattr(clap_mod, "ClapEngine", _FakeClapEngine)
    monkeypatch.setattr(store_mod, "open_store", lambda: _FakeStore())
    monkeypatch.setattr(anlz_mod, "build_anlz_index", anlz_builder)

    def _fake_ingest_source(source, embedder, store, **kwargs):
        captured["source"] = source
        captured["embedder"] = embedder
        captured["store"] = store
        captured["kwargs"] = kwargs
        return _FakeReport()

    monkeypatch.setattr(ingest_mod, "ingest_source", _fake_ingest_source)


def test_library_ingest_cli_builds_and_passes_anlz_index(monkeypatch, capsys) -> None:
    import vibemix.__main__ as main_mod

    fake_index = SimpleNamespace(by_basename={"a.wav": (object(),), "b.wav": (object(),)})
    captured = {}
    _patch_ingest_dependencies(
        monkeypatch,
        anlz_builder=lambda: fake_index,
        captured=captured,
    )

    code = main_mod._cmd_library_ingest(argparse.Namespace(path="collection.xml", json=True))

    assert code == 0
    assert captured["kwargs"]["persist_library"] is True
    assert captured["kwargs"]["anlz_index"] is fake_index

    out = capsys.readouterr()
    assert json.loads(out.out)["embedded"] == 1
    assert "ANLZ structure index=2 tracks" in out.err


def test_library_ingest_cli_falls_back_when_anlz_index_fails(monkeypatch, capsys) -> None:
    import vibemix.__main__ as main_mod

    captured = {}

    def _raise_anlz() -> object:
        raise RuntimeError("fixture boom")

    _patch_ingest_dependencies(
        monkeypatch,
        anlz_builder=_raise_anlz,
        captured=captured,
    )

    code = main_mod._cmd_library_ingest(argparse.Namespace(path="collection.xml", json=False))

    assert code == 0
    assert captured["kwargs"]["anlz_index"] is None
    assert "ANLZ structure index unavailable (fixture boom)" in capsys.readouterr().err


def test_library_ingest_cli_can_enable_cue_agreement_calibration(
    monkeypatch, capsys
) -> None:
    import vibemix.__main__ as main_mod

    captured = {}
    _patch_ingest_dependencies(
        monkeypatch,
        anlz_builder=lambda: SimpleNamespace(by_basename={}),
        captured=captured,
    )

    code = main_mod._cmd_library_ingest(
        argparse.Namespace(path="collection.xml", json=False, calibrate_cues=True)
    )

    assert code == 0
    assert captured["kwargs"]["cue_agreement_calibration"] is True

    out = capsys.readouterr()
    assert "cue-agreement calibration=on (telemetry only)" in out.err
    assert "-> cue agreement: tracks=1 scored=1 weak_labels=2 mean_score=0.75" in out.out


def test_library_ingest_cli_can_select_traktor_source(monkeypatch, capsys) -> None:
    import vibemix.__main__ as main_mod

    captured = {}
    _patch_ingest_dependencies(
        monkeypatch,
        anlz_builder=lambda: SimpleNamespace(by_basename={"should-not": (object(),)}),
        captured=captured,
    )

    code = main_mod._cmd_library_ingest(
        argparse.Namespace(
            path="collection.nml",
            source="traktor",
            json=True,
            calibrate_cues=False,
        )
    )

    assert code == 0
    assert isinstance(captured["source"], _FakeTraktorSource)
    assert captured["source"].nml_path == "collection.nml"
    assert captured["kwargs"]["anlz_index"] is None

    out = capsys.readouterr()
    assert json.loads(out.out)["embedded"] == 1
    assert "source=traktor" in out.err
    assert "ANLZ structure index skipped for source=traktor" in out.err
