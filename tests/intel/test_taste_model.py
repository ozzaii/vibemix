# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from vibemix.intel.feedback import append_feedback_event, parse_feedback_event
from vibemix.intel.taste_model import build_taste_model, load_taste_model


def _event(
    event_id: str,
    session_id: str,
    label: str,
    role_pair: tuple[str, str],
    *,
    risk_flags: tuple[str, ...] = (),
):
    return parse_feedback_event(
        {
            "event_id": event_id,
            "session_id": session_id,
            "surface": "prep_chat",
            "action": "transition_labeled",
            "label": label,
            "role_from": role_pair[0],
            "role_to": role_pair[1],
            "risk_flags": list(risk_flags),
        }
    )


def test_taste_model_is_neutral_at_cold_start() -> None:
    model = build_taste_model(
        tuple(_event(f"evt_{i}", "s1", "would_play", ("outro", "intro")) for i in range(3))
    )

    assert model.role_pair_weights == {}
    assert model.taste_score_for(("outro", "intro")) == 0.5


def test_taste_model_learns_positive_pair_after_enough_events_and_sessions() -> None:
    events = tuple(
        _event(f"evt_{i}", f"s{i % 3}", "would_play", ("outro", "groove")) for i in range(10)
    )

    model = build_taste_model(events)

    assert model.role_pair_weights[("outro", "groove")] > 0.0
    assert model.taste_score_for(("outro", "groove")) > 0.60


def test_single_session_negative_does_not_create_hard_constraint() -> None:
    events = tuple(_event(f"evt_{i}", "s1", "no", ("drop", "drop")) for i in range(10))

    model = build_taste_model(events)

    assert model.role_pair_weights == {}
    assert model.negative_constraints == ()


def test_repeated_negative_across_sessions_creates_constraint() -> None:
    events = tuple(_event(f"evt_{i}", f"s{i % 3}", "no", ("hook", "outro")) for i in range(10))

    model = build_taste_model(events)

    assert model.taste_score_for(("hook", "outro")) < 0.50
    assert model.negative_constraints


def test_technical_no_updates_risk_penalty_not_role_pair_taste() -> None:
    events = tuple(
        _event(
            f"evt_{i}",
            f"s{i % 3}",
            "technical_no",
            ("hook", "outro"),
            risk_flags=("vocal_clash",),
        )
        for i in range(12)
    )

    model = build_taste_model(events)

    assert model.role_pair_weights == {}
    assert model.risk_flag_penalties["vocal_clash"] < 0.0


def test_load_taste_model_reads_consent_gated_feedback_jsonl(tmp_path) -> None:
    path = tmp_path / "taste_feedback.jsonl"
    events = tuple(
        _event(f"evt_{i}", f"s{i % 3}", "played_next", ("outro", "intro")) for i in range(10)
    )
    for event in events:
        append_feedback_event(path, event, profile_consent=True)

    consented = load_taste_model(path, profile_consent=True)
    withheld = load_taste_model(path, profile_consent=False)

    assert consented.taste_score_for(("outro", "intro")) > 0.50
    assert withheld.taste_event_count == 0
    assert withheld.taste_score_for(("outro", "intro")) == 0.50
