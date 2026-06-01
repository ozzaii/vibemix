# SPDX-License-Identifier: Apache-2.0
"""Static checks for bundled notices and clean-room reference attribution."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
NOTICE = REPO_ROOT / "NOTICE"
NOTICE_MD = REPO_ROOT / "NOTICE.md"
THIRD_PARTY = REPO_ROOT / "THIRD_PARTY_LICENSES.md"

CLEAN_ROOM_REFERENCES = (
    "src/vibemix/audio/cues.py",
    "src/vibemix/audio/grid.py",
    "src/vibemix/audio/miniplayer.py",
    "src/vibemix/audio/xfade.py",
    "src/vibemix/learn/beatmatch_judge.py",
    "src/vibemix/state/transition_clock.py",
)


def test_clean_room_mixxx_references_are_documented() -> None:
    text = THIRD_PARTY.read_text(encoding="utf-8")

    assert "Mixxx" in text
    assert "GPLv2 or later" in text
    assert "No Mixxx source files are bundled" in text
    assert "linked, or redistributed" in text
    for source_path in CLEAN_ROOM_REFERENCES:
        assert source_path in text


def test_notices_point_to_clean_room_reference_map() -> None:
    notice_text = NOTICE.read_text(encoding="utf-8")
    asset_notice_text = NOTICE_MD.read_text(encoding="utf-8")

    assert "THIRD_PARTY_LICENSES.md" in notice_text
    assert "THIRD_PARTY_LICENSES.md" in asset_notice_text
    assert "No Mixxx source files are bundled" in notice_text
    assert "no Mixxx source is" in asset_notice_text
