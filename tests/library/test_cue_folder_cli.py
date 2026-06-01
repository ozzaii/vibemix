# SPDX-License-Identifier: Apache-2.0
"""CLI wiring for ``vibemix library cue``.

The cue engine itself is tested in ``test_cue_folder.py``. These tests only pin
argparse/handler behavior and monkeypatch the engine so they need no real audio,
ONNX model, Rekordbox, Mixxx, or Serato install.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vibemix import __main__ as main_mod
from vibemix.library import cue_folder as cue_folder_mod
from vibemix.library.cue_folder import CueExportReport


def _args(tmp_path: Path, **overrides: object) -> argparse.Namespace:
    data = {
        "path": str(tmp_path),
        "out": str(tmp_path / "set.m3u8"),
        "export": "m3u8",
        "name": "vibemix cues",
        "max_cues": 4,
        "json": True,
    }
    data.update(overrides)
    return argparse.Namespace(**data)


def test_cmd_library_cue_exports_folder_json(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    def fake_export(folder, out, *, export, name, max_cues, on_progress):
        assert Path(folder) == tmp_path
        assert out == str(tmp_path / "set.m3u8")
        assert export == "m3u8"
        assert name == "vibemix cues"
        assert max_cues == 4
        on_progress(1, 1, "track.mp3")
        return CueExportReport(
            tracks_cued=1,
            cues_total=2,
            skipped=0,
            outputs={"m3u8": str(tmp_path / "set.m3u8")},
        )

    monkeypatch.setattr(cue_folder_mod, "export_cued_folder", fake_export)

    rc = main_mod._cmd_library_cue(_args(tmp_path))

    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["ok"] is True
    assert payload["tracks_cued"] == 1
    assert payload["outputs"] == {"m3u8": str(tmp_path / "set.m3u8")}
    assert captured.err == ""


def test_cmd_library_cue_rejects_missing_folder(capsys) -> None:
    rc = main_mod._cmd_library_cue(
        argparse.Namespace(
            path="/tmp/vibemix-missing-cue-folder",
            out="x.xml",
            export="rekordbox",
            name="vibemix cues",
            max_cues=8,
            json=True,
        )
    )

    assert rc == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["ok"] is False
    assert "not a directory" in payload["error"]


def test_library_cue_subparser_exists() -> None:
    parser = argparse.ArgumentParser()
    main_mod._build_library_subparsers(parser)

    args = parser.parse_args(
        ["cue", "/tmp/music", "--export", "both", "--out", "cues.xml", "--json"]
    )

    assert args.func is main_mod._cmd_library_cue
    assert args.path == "/tmp/music"
    assert args.export == "both"
    assert args.out == "cues.xml"
    assert args.json is True
