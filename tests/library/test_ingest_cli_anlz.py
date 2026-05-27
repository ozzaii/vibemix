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

    def as_dict(self) -> dict[str, int]:
        return {
            "embedded": self.embedded,
            "skipped_cached": self.skipped_cached,
            "failed": self.failed,
            "total": self.total,
        }


class _FakeSource:
    name = "rekordbox"

    def __init__(self, xml_path: str | None = None) -> None:
        self.xml_path = xml_path
        self.resolved_path = Path(xml_path or "/fixture/collection.xml")

    def detect(self) -> bool:
        return True

    def default_paths(self) -> list[Path]:
        return [Path("/fixture/collection.xml")]


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
    import vibemix.library.store as store_mod

    monkeypatch.setattr(source_mod, "RekordboxSource", _FakeSource)
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
