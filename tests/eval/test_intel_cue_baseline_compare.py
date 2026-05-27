# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.intel_cue_baseline_compare import (
    DEFAULT_FIXTURE_DIR,
    compare_fixture_dir,
    diff_cue_snapshots,
    load_vibemix_proposals,
    main,
    parse_rekordbox_cues,
)


def test_parse_rekordbox_xml_normalizes_hot_slots() -> None:
    cues = parse_rekordbox_cues(
        DEFAULT_FIXTURE_DIR / "cue_baseline_after.xml",
        baseline="rekordbox_auto",
        snapshot_id="after",
    )

    assert [(cue.slot, cue.type, cue.start_s) for cue in cues] == [
        ("A", "hot_cue", 0.0),
        ("D", "hot_cue", 42.667),
        ("F", "hot_cue", 74.667),
    ]
    assert {cue.source_xml_snapshot_id for cue in cues} == {"after"}


def test_parse_rekordbox_xml_handles_memory_loop_and_hot_cue_range(tmp_path: Path) -> None:
    xml_path = tmp_path / "marks.xml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<DJ_PLAYLISTS Version="1.0.0">
  <COLLECTION Entries="1">
    <TRACK TrackID="track-x" Name="Fixture" Location="file:///private/demo.wav">
      <POSITION_MARK Name="Memory" Type="0" Start="1.500" Num="-1" />
      <POSITION_MARK Name="P" Type="0" Start="2.000" Num="15" />
      <POSITION_MARK Name="Out of range" Type="0" Start="3.000" Num="16" />
      <POSITION_MARK Name="Loop" Type="4" Start="8.000" End="16.000" Num="2" />
    </TRACK>
  </COLLECTION>
</DJ_PLAYLISTS>
""",
        encoding="utf-8",
    )

    cues = parse_rekordbox_cues(xml_path, baseline="rekordbox_auto")

    assert [(cue.label, cue.slot, cue.type, cue.end_s) for cue in cues] == [
        ("Memory", None, "memory_cue", None),
        ("P", "P", "hot_cue", None),
        ("Out of range", None, "hot_cue", None),
        ("Loop", "C", "loop", 16.0),
    ]


def test_diff_snapshots_detects_added_and_end_changes(tmp_path: Path) -> None:
    before_xml = tmp_path / "before.xml"
    after_xml = tmp_path / "after.xml"
    before_xml.write_text(
        """<DJ_PLAYLISTS><COLLECTION><TRACK TrackID="track-x">
<POSITION_MARK Name="Loop" Type="4" Start="8.000" End="12.000" Num="2" />
</TRACK></COLLECTION></DJ_PLAYLISTS>""",
        encoding="utf-8",
    )
    after_xml.write_text(
        """<DJ_PLAYLISTS><COLLECTION><TRACK TrackID="track-x">
<POSITION_MARK Name="A" Type="0" Start="0.000" Num="0" />
<POSITION_MARK Name="Loop" Type="4" Start="8.000" End="16.000" Num="2" />
</TRACK></COLLECTION></DJ_PLAYLISTS>""",
        encoding="utf-8",
    )

    diffs = diff_cue_snapshots(
        parse_rekordbox_cues(before_xml, baseline="dj"),
        parse_rekordbox_cues(after_xml, baseline="rekordbox_auto"),
    )

    assert [(diff.kind, diff.track_id, diff.slot) for diff in diffs] == [
        ("added", "track-x", "A"),
        ("changed", "track-x", "C"),
    ]


def test_load_vibemix_proposals_normalizes_fixture() -> None:
    cues = load_vibemix_proposals(DEFAULT_FIXTURE_DIR / "smart_cue_proposals.json")

    hard = [cue for cue in cues if cue.track_id == "fx-hard-001"]
    assert [(cue.slot, cue.label, cue.source_section_id) for cue in hard] == [
        ("A", "mix-in", "fx-hard-001#s000"),
        ("C", "breakdown", "fx-hard-001#s002"),
        ("D", "drop", "fx-hard-001#s003"),
        ("F", "mix-out", "fx-hard-001#s004"),
    ]
    assert all(cue.baseline == "vibemix" for cue in hard)


def test_compare_fixture_dir_emits_redacted_scorecard() -> None:
    result = compare_fixture_dir(DEFAULT_FIXTURE_DIR)

    assert result["schema"] == "intel_cue_baseline_compare_v1"
    assert result["valid"] is True
    assert result["privacy"] == {"local_paths_redacted": True}
    assert result["totals"] == {
        "tracks": 2,
        "baseline_cues": 3,
        "vibemix_cues": 7,
        "snapshot_added": 3,
        "snapshot_changed": 0,
        "snapshot_removed": 0,
    }
    assert result["distance_bands"] == {"exact": 3, "missing": 4}
    assert result["comparative_lift"] == {
        "vibemix_kept_and_baseline_missing": 4,
        "baseline_kept_and_vibemix_missing": 0,
        "both_kept_same_or_near": 3,
        "both_present_phrase_near": 0,
        "both_present_different": 0,
    }
    assert result["per_track"]["fx-hard-001"]["required_slots_filled"] == ["A", "D", "F"]
    assert "fixture://tracks" not in json.dumps(result)


def test_cli_json_uses_fixture_dir(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["--fixture-dir", str(DEFAULT_FIXTURE_DIR), "--json"]) == 0

    out = json.loads(capsys.readouterr().out)
    assert out["schema"] == "intel_cue_baseline_compare_v1"
    assert out["totals"]["snapshot_added"] == 3


def test_cli_requires_explicit_paths_together(capsys) -> None:  # type: ignore[no-untyped-def]
    try:
        main(["--before", str(DEFAULT_FIXTURE_DIR / "cue_baseline_before.xml")])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - argparse should always exit
        raise AssertionError("expected argparse to reject incomplete explicit paths")

    assert "must be provided together" in capsys.readouterr().err
