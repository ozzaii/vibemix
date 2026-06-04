# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_module():
    path = Path("scripts/eval/cue_landing_e2e.py")
    spec = importlib.util.spec_from_file_location("cue_landing_e2e", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_cue_landing_e2e_probe_proves_carriers_and_pill(tmp_path: Path) -> None:
    pytest.importorskip("mutagen")
    module = _load_module()

    proof = module.run_probe(tmp_path / "cue-proof")

    assert proof["schema"] == "cue_landing_e2e_v1"
    assert proof["status"] == "ok"
    assert proof["export_result"]["target"] == "all"
    assert proof["export_result"]["auto_cues"]["cues_added"] == 2
    assert proof["export_result"]["pill_cues_materialized"] == {"tracks": 1, "cues": 2}
    assert [row["carrier"] for row in proof["export_result"]["import_instructions"]] == [
        "rekordbox_xml",
        "m3u8",
        "markers2_tags",
    ]
    assert proof["outputs_exist"] == {
        "rekordbox": True,
        "m3u8": True,
        "markers2_tag_copy": True,
    }
    assert proof["rekordbox_snap"]["vm_cues"] == 2
    assert proof["rekordbox_snap"]["over_1ms"] == 0
    assert proof["rekordbox_snap"]["max_grid_error_ms"] < 1.0
    assert [row["beat_index"] for row in proof["rekordbox_snap"]["rows"]] == [32.0, 128.0]
    assert [row["start_s"] for row in proof["rekordbox_snap"]["rows"]] == [
        pytest.approx(15.608871),
        pytest.approx(62.060484),
    ]
    assert proof["export_result"]["auto_cues"]["snap_adjusted_count"] == 2
    assert proof["rekordbox_existing_grid_fixture"] == {
        "track_id": "dst",
        "inizio_s": 0.125,
        "bpm": 124.0,
        "purpose": "prove VM cues snap to a persisted Rekordbox grid, not just a BPM-only export grid",
    }
    assert proof["m3u8"]["contains_track_copy"] is True
    assert [cue["name"] for cue in proof["markers2_readback"]] == ["VM A IN", "VM D DROP"]
    assert [cue["index"] for cue in proof["markers2_readback"]] == [0, 3]
    assert [cue["position_ms"] for cue in proof["markers2_readback"]] == [15609, 62060]
    assert proof["pill"]["transition_present"] is True
    assert proof["pill"]["transition"]["target_deck"] == "B"
    assert proof["pill"]["transition"]["cue_slot"] == "A"
    assert proof["pill"]["transition"]["cue_source"] == "anlz"
    assert proof["pill"]["transition"]["to_start_s"] == pytest.approx(15.608871)
    assert proof["source_file_policy"]["mutated_user_audio"] is False
    assert (tmp_path / "cue-proof" / "proof.json").exists()
