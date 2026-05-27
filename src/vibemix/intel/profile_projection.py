# SPDX-License-Identifier: Apache-2.0
"""Prompt-safe projection of deterministic taste aggregates."""

from __future__ import annotations

import json
import re
from typing import Any

from vibemix.intel.taste_model import TasteModel

ALLOWED_TRANSITION_STYLE_TAGS: frozenset[str] = frozenset(
    {
        "long_phrase_blends",
        "energy_lifts",
        "energy_holds",
        "vocal_avoidant",
        "tooly_intros",
        "breakdown_resets",
    }
)


def project_profile(model: TasteModel, *, consent: bool) -> dict[str, Any]:
    if not consent:
        return {
            "schema": "intel_profile_projection_v1",
            "consent": False,
            "transition_style_tags": (),
            "suggestion_cadence": "quiet",
        }
    tags: list[str] = []
    if _weight(model, ("outro", "intro")) > 0.05 or _weight(model, ("outro", "groove")) > 0.05:
        tags.append("long_phrase_blends")
    if _weight(model, ("breakdown", "drop")) > 0.05 or _weight(model, ("build", "drop")) > 0.05:
        tags.append("energy_lifts")
    if _weight(model, ("drop", "drop")) < -0.05:
        tags.append("energy_holds")
    if model.risk_flag_penalties.get("vocal_clash", 0.0) < -0.05:
        tags.append("vocal_avoidant")
    if _weight(model, ("outro", "groove")) > 0.05:
        tags.append("tooly_intros")
    if _weight(model, ("breakdown", "build")) > 0.05:
        tags.append("breakdown_resets")
    return {
        "schema": "intel_profile_projection_v1",
        "consent": True,
        "transition_style_tags": tuple(tag for tag in tags if tag in ALLOWED_TRANSITION_STYLE_TAGS),
        "suggestion_cadence": "balanced" if model.taste_event_count >= 10 else "quiet",
    }


def profile_projection_privacy_errors(profile: dict[str, Any]) -> tuple[str, ...]:
    text = json.dumps(profile, sort_keys=True)
    errors: list[str] = []
    if re.search(r"\b(?:tr|fx)[_-][a-z0-9_-]+\b", text):
        errors.append("private_or_action_id_present")
    if re.search(r"#s\d{3}\b", text):
        errors.append("section_id_present")
    if any(token in text for token in ("/Users/", "/Volumes/", "file://", "raw_vector")):
        errors.append("private_payload_present")
    unknown_tags = set(profile.get("transition_style_tags") or ()) - ALLOWED_TRANSITION_STYLE_TAGS
    if unknown_tags:
        errors.append("unknown_transition_style_tag")
    return tuple(errors)


def _weight(model: TasteModel, role_pair: tuple[str, str]) -> float:
    return model.role_pair_weights.get(role_pair, 0.0)


__all__ = [
    "ALLOWED_TRANSITION_STYLE_TAGS",
    "profile_projection_privacy_errors",
    "project_profile",
]
