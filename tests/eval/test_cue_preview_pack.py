# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "eval" / "cue_preview_pack.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("cue_preview_pack", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_preview_pack_slices_vm_cues_from_three_seconds_before(tmp_path: Path) -> None:
    module = _load_module()
    audio = tmp_path / "track file.mp3"
    audio.write_bytes(b"fake audio")
    xml = tmp_path / "set.xml"
    xml.write_text(
        f"""<?xml version='1.0' encoding='utf-8'?>
<DJ_PLAYLISTS Version="1.0.0">
  <COLLECTION Entries="1">
    <TRACK Location="file://localhost/{audio}" Name="Cue Track" Artist="DJ Test">
      <POSITION_MARK Name="MY DJ CUE" Type="0" Start="8.000" Num="1" />
      <POSITION_MARK Name="VM A IN" Type="0" Start="15.500" Num="0" />
      <POSITION_MARK Name="VM D DROP" Type="0" Start="61.900" Num="3" />
    </TRACK>
  </COLLECTION>
</DJ_PLAYLISTS>
""",
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def fake_runner(cmd, **kwargs):
        calls.append(list(cmd))
        Path(cmd[-1]).write_bytes(b"wav")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    manifest = module.create_preview_pack(
        xml,
        out_dir=tmp_path / "previews",
        pre_roll_s=3.0,
        duration_s=8.0,
        runner=fake_runner,
    )

    assert manifest["ok"] is True
    assert manifest["cue_count"] == 2
    assert manifest["written"] == 2
    assert [row["cue_name"] for row in manifest["previews"]] == ["VM A IN", "VM D DROP"]
    assert [row["slot"] for row in manifest["previews"]] == ["0", "3"]
    assert [row["preview_start_s"] for row in manifest["previews"]] == [12.5, 58.9]
    assert manifest["previews"][0]["source_audio"] == str(audio)
    assert all(Path(row["output"]).exists() for row in manifest["previews"])
    assert calls[0][calls[0].index("-ss") + 1] == "12.500"
    assert calls[0][calls[0].index("-t") + 1] == "8.000"
    assert (tmp_path / "previews" / "manifest.json").exists()


def test_parse_vm_cues_clamps_pre_roll_at_zero(tmp_path: Path) -> None:
    module = _load_module()
    audio = tmp_path / "track.mp3"
    audio.write_bytes(b"fake audio")
    xml = tmp_path / "set.xml"
    xml.write_text(
        f"""<DJ_PLAYLISTS>
  <COLLECTION>
    <TRACK Location="file://localhost/{audio}" Name="Tiny Intro">
      <POSITION_MARK Name="VM A IN" Type="0" Start="1.250" Num="0" />
    </TRACK>
  </COLLECTION>
</DJ_PLAYLISTS>
""",
        encoding="utf-8",
    )

    rows = module.parse_vm_cues(xml, pre_roll_s=3.0, out_dir=tmp_path / "previews")

    assert len(rows) == 1
    assert rows[0].preview_start_s == 0.0
    assert rows[0].cue_start_s == 1.25
