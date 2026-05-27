# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from vibemix.intel.feedback import parse_feedback_event
from vibemix.intel.profile_projection import profile_projection_privacy_errors, project_profile
from vibemix.intel.taste_model import build_taste_model


def test_profile_projection_is_empty_without_consent() -> None:
    model = build_taste_model(())

    profile = project_profile(model, consent=False)

    assert profile["consent"] is False
    assert profile["transition_style_tags"] == ()


def test_profile_projection_emits_allowlisted_tags_only() -> None:
    events = tuple(
        parse_feedback_event(
            {
                "event_id": f"evt_{i}",
                "session_id": f"s{i % 3}",
                "surface": "prep_chat",
                "action": "transition_labeled",
                "label": "would_play",
                "role_from": "outro",
                "role_to": "groove",
            }
        )
        for i in range(10)
    )
    model = build_taste_model(events)

    profile = project_profile(model, consent=True)

    assert "long_phrase_blends" in profile["transition_style_tags"]
    assert profile_projection_privacy_errors(profile) == ()


def test_profile_projection_privacy_rejects_action_ids() -> None:
    assert profile_projection_privacy_errors(
        {
            "schema": "intel_profile_projection_v1",
            "transition_style_tags": ("tr_001",),
        }
    ) == ("private_or_action_id_present", "unknown_transition_style_tag")
