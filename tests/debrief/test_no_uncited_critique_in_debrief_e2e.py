# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF-07 HARD GATE — end-to-end.

Runs `debrief.main.run` against a fixture session with mocked Gemini
client and asserts the persisted ``session_debrief.json`` contains
ZERO uncited sentences in any advice text field. This is THE gate;
its failure blocks the phase release.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vibemix.debrief import run
from vibemix.debrief.drills import Drill, Drills
from vibemix.debrief.stripper import assert_all_cited


def _build_full_session(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "recordings"
    root.mkdir()
    sess = root / "20260515-e2e"
    sess.mkdir()

    events = [
        {"t": 0.0, "kind": "session_start"},
        {"t": 100.0, "kind": "event", "type": "TRACK_CHANGE", "track": "A"},
        {"t": 100.5, "kind": "ai_text", "text": "Strong opener [ev:TRACK_CHANGE@100.000]."},
        {"t": 300.0, "kind": "event", "type": "MIX_MOVE"},
        {"t": 300.5, "kind": "ai_text", "text": "Sweep landed clean [ev:MIX_MOVE@300.000]."},
        {"t": 600.0, "kind": "event", "type": "HEARTBEAT"},
    ]
    (sess / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events), encoding="utf-8"
    )
    (sess / "evidence_registry.json").write_text(
        json.dumps(
            {
                "ev": {
                    "TRACK_CHANGE": [100.0],
                    "MIX_MOVE": [300.0],
                    "HEARTBEAT": [600.0],
                }
            }
        ),
        encoding="utf-8",
    )
    wav = sess / "voice.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00" * 48000)
    return root, sess


def _make_mock_client_with_uncited_sentences_in_tldr():
    """Mock Gemini returns mixed cited/uncited text — stripper must drop the
    uncited before the orchestrator persists."""
    client = MagicMock()

    # Drills response — all valid, citations resolve.
    drills_response = SimpleNamespace(
        parsed=Drills(
            drills=[
                Drill(
                    situation=f"S{i}",
                    behavior=f"Behavior {i} [ev:MIX_MOVE@05:00]",
                    impact=f"Impact {i} [ev:TRACK_CHANGE@01:40]",
                    action_recommended=f"Action {i} [ev:HEARTBEAT@10:00]",
                    citation="[ev:MIX_MOVE@05:00]",
                )
                for i in range(3)
            ]
        ),
        text="",
    )

    # TLDR text response — sprinkled with uncited filler sentences.
    tldr_text_response = SimpleNamespace(
        text=(
            "Track opened strong [ev:TRACK_CHANGE@01:40]. "
            "Random filler one. "
            "The mix landed clean [ev:MIX_MOVE@05:00]. "
            "Random filler two. "
            "Closing groove felt warm [ev:HEARTBEAT@10:00]."
        )
    )

    # TTS response — produce real PCM so PyAV can encode.
    pcm = b"\x00\x00" * 24000
    inline = SimpleNamespace(inline_data=SimpleNamespace(data=pcm))
    tts_response = SimpleNamespace(
        candidates=[SimpleNamespace(content=SimpleNamespace(parts=[inline]))]
    )

    client.models.generate_content.side_effect = [
        drills_response,
        tldr_text_response,
        tts_response,
    ]
    return client


def test_no_uncited_critique_in_persisted_debrief(tmp_path: Path):
    """THE HARD GATE.

    After full pipeline, every advice-field sentence in the persisted
    session_debrief.json carries at least one citation.
    """
    root, sess = _build_full_session(tmp_path)
    client = _make_mock_client_with_uncited_sentences_in_tldr()

    state = run(sess, client=client, recordings_root=root, serve=False)
    assert state["cache_hit"] is False

    debrief_path = sess / "session_debrief.json"
    assert debrief_path.exists()
    debrief = json.loads(debrief_path.read_text(encoding="utf-8"))

    # Hard gate: every drill's behavior/impact/action_recommended is fully cited.
    for d in debrief["drills"]:
        assert_all_cited(d["behavior"])
        assert_all_cited(d["impact"])
        assert_all_cited(d["action_recommended"])


def test_e2e_with_zero_cited_events_raises_typed_error(tmp_path: Path):
    """When the evidence_registry is empty + Gemini returns all-uncited TLDR
    text, the orchestrator surfaces a typed error and does not write a
    partial debrief."""
    from vibemix.debrief.tldr import DebriefGenerationError

    root = tmp_path / "recordings"
    root.mkdir()
    sess = root / "20260515-allbad"
    sess.mkdir()
    (sess / "events.jsonl").write_text(
        "\n".join(
            json.dumps(e) for e in [
                {"t": 0.0, "kind": "session_start"},
                {"t": 600.0, "kind": "event", "type": "HEARTBEAT"},
            ]
        ),
        encoding="utf-8",
    )
    # Empty evidence_registry on purpose.
    (sess / "evidence_registry.json").write_text(
        json.dumps({"ev": {"HEARTBEAT": [600.0]}}), encoding="utf-8"
    )
    wav = sess / "voice.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00" * 24000)

    from vibemix.debrief.drills import DrillsGenerationError

    client = MagicMock()
    # Drill citations all bogus → after retries raise DrillsGenerationError.
    bad_drill = Drill(
        situation="S", behavior="B [ev:BOGUS@01:00]", impact="I [ev:BOGUS@01:00]",
        action_recommended="A [ev:BOGUS@01:00]",
        citation="[ev:BOGUS@01:00]",  # not in snapshot
    )
    drills_response = SimpleNamespace(
        parsed=Drills(drills=[bad_drill, bad_drill, bad_drill]),
        text="",
    )
    client.models.generate_content.return_value = drills_response

    with pytest.raises(DrillsGenerationError):
        run(sess, client=client, recordings_root=root, serve=False)

    # No partial debrief on disk.
    assert not (sess / "session_debrief.json").exists()
    assert not (sess / "debrief_tldr.mp3").exists()
