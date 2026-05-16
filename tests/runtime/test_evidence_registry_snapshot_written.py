# SPDX-License-Identifier: Apache-2.0
"""Plan 29-00 Task 2 Part A — EvidenceRegistry snapshot per session.

`VoiceRecorder.close()` MUST serialize the linked EvidenceRegistry snapshot to
``<session_dir>/evidence_registry.json`` before clearing the registry, using
the atomic tmp+rename pattern.

The snapshot is the runtime-of-truth document the debrief sidecar (Plan 29-02)
will read back at replay time. Without it, citation-tooltip resolution in
Plan 29-05 has no anchor and fabricates citations — closes the central
hallucination gate (DEBRIEF-07).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibemix.audio.recorder import VoiceRecorder
from vibemix.state.evidence_registry import EvidenceRegistry


def _make_registry_with_events() -> EvidenceRegistry:
    reg = EvidenceRegistry()
    reg.write("ev", "track_change", 1.5)
    reg.write("aud", "rms_jump_3.5", 2.0)
    reg.write("midi", "fader_a_85pct", 4.2)
    return reg


def test_snapshot_written_on_close(tmp_path: Path) -> None:
    reg = _make_registry_with_events()
    rec = VoiceRecorder(root=tmp_path, evidence_registry=reg)
    session_dir = rec.session_dir
    rec.close()

    snap_path = session_dir / "evidence_registry.json"
    assert snap_path.exists(), "evidence_registry.json must be written on close()"
    data = json.loads(snap_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    # Three sources written: ev, aud, midi
    assert {"ev", "aud", "midi"}.issubset(data.keys()), (
        f"expected ev/aud/midi sources in snapshot, got {list(data.keys())!r}"
    )
    assert "track_change" in data["ev"]
    # Timestamps are serialized as a list (tuples → JSON arrays)
    assert data["ev"]["track_change"] == [1.5]


def test_snapshot_idempotent_double_close(tmp_path: Path) -> None:
    reg = _make_registry_with_events()
    rec = VoiceRecorder(root=tmp_path, evidence_registry=reg)
    rec.close()
    # Second close must not crash
    rec.close()
    snap_path = rec.session_dir / "evidence_registry.json"
    assert snap_path.exists()


def test_snapshot_atomic_no_tmp_leftover(tmp_path: Path) -> None:
    """tmp+rename pattern must not leave the .tmp file behind on success."""
    reg = _make_registry_with_events()
    rec = VoiceRecorder(root=tmp_path, evidence_registry=reg)
    rec.close()
    tmp_path_leftover = rec.session_dir / "evidence_registry.json.tmp"
    assert not tmp_path_leftover.exists(), (
        ".tmp staging file must be renamed away on successful write"
    )


def test_snapshot_no_registry_no_file(tmp_path: Path) -> None:
    """If no evidence_registry passed (zero-arg construction), no snapshot file."""
    rec = VoiceRecorder(root=tmp_path)  # backward-compat: no registry
    rec.close()
    snap_path = rec.session_dir / "evidence_registry.json"
    assert not snap_path.exists(), (
        "VoiceRecorder() without registry kwarg must not write snapshot"
    )
