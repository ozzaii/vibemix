# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from vibemix.intel.feedback import (
    append_feedback_event,
    feedback_event_to_row,
    feedback_privacy_errors,
    load_feedback_events,
    parse_feedback_event,
    persistable_events,
)


def test_parse_feedback_event_preserves_structured_fields() -> None:
    event = parse_feedback_event(
        {
            "event_id": "evt_001",
            "session_id": "s1",
            "surface": "live_pill",
            "action": "accepted",
            "label": "would_play",
            "role_from": "outro",
            "role_to": "intro",
            "risk_flags": ["tempo_bridge"],
        }
    )

    assert event.role_pair == ("outro", "intro")
    assert event.risk_flags == ("tempo_bridge",)


def test_consent_off_prevents_persistence() -> None:
    event = parse_feedback_event(
        {
            "event_id": "evt_001",
            "session_id": "s1",
            "surface": "prep_chat",
            "action": "transition_labeled",
            "label": "would_play",
        }
    )

    assert persistable_events((event,), profile_consent=False) == ()
    assert persistable_events((event,), profile_consent=True) == (event,)


def test_feedback_privacy_catches_paths_and_vectors() -> None:
    event = parse_feedback_event(
        {
            "event_id": "evt_001",
            "session_id": "s1",
            "surface": "prep_chat",
            "action": "transition_labeled",
            "label": "would_play",
            "local_path": "/Users/ozai/Music/private.wav",
        }
    )

    assert feedback_privacy_errors((event,)) == ("evt_001:private_payload_present",)


def test_load_feedback_events_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(
        json.dumps(
            {
                "event_id": "evt_001",
                "session_id": "s1",
                "surface": "prep_chat",
                "action": "transition_labeled",
                "label": "maybe",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert len(load_feedback_events(path)) == 1


def test_append_feedback_event_writes_jsonl_only_with_consent(tmp_path: Path) -> None:
    event = parse_feedback_event(
        {
            "event_id": "evt_choice_001",
            "session_id": "s1",
            "surface": "live_next_pill",
            "action": "transition_labeled",
            "label": "played_next",
            "role_from": "outro",
            "role_to": "groove",
            "candidate_id": "tr_002",
            "risk_flags": ["tempo_bridge"],
            "score": 0.84,
            "selected_track_id": "b",
        }
    )
    path = tmp_path / "taste_feedback.jsonl"

    assert append_feedback_event(path, event, profile_consent=False) is False
    assert not path.exists()
    assert append_feedback_event(path, event, profile_consent=True) is True

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows == [feedback_event_to_row(event, profile_consent=True)]
    assert load_feedback_events(path)[0].label == "played_next"
