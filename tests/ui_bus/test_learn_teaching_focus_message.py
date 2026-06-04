# SPDX-License-Identifier: Apache-2.0
"""ipc.learn.teaching_focus + ipc.learn.control_rect envelope contracts.

These two envelopes drive the particle-organism focus mechanic — the mask
dissolves and streams to a taught control, then reforms on advance. They are
the visual-grounding twin of the citation-grounding reaction loop: the
organism animates ONLY on a real teaching event.
"""
from __future__ import annotations

import json

import pytest

from vibemix.ui_bus.learn_messages import LearnControlRect, LearnTeachingFocus
from vibemix.ui_bus.messages import _VALIDATOR


def test_teaching_focus_roundtrips_focus_with_band() -> None:
    env = LearnTeachingFocus.make(
        control_id="eq_low",
        deck="A",
        band="low",
        phase="focus",
    )
    wire = json.loads(env.to_json())

    assert wire["type"] == "ipc.learn.teaching_focus"
    assert wire["payload"] == {
        "control_id": "eq_low",
        "deck": "A",
        "band": "low",
        "phase": "focus",
    }
    _VALIDATOR.validate(wire)


def test_teaching_focus_roundtrips_reform_with_null_band() -> None:
    env = LearnTeachingFocus.make(
        control_id="play",
        deck="A",
        band=None,
        phase="reform",
    )
    wire = json.loads(env.to_json())

    assert wire["payload"]["band"] is None
    assert wire["payload"]["phase"] == "reform"
    _VALIDATOR.validate(wire)


def test_teaching_focus_accepts_master_section_empty_deck() -> None:
    env = LearnTeachingFocus.make(
        control_id="filter_fx",
        deck="",
        band=None,
        phase="focus",
    )
    wire = json.loads(env.to_json())

    assert wire["payload"]["deck"] == ""
    _VALIDATOR.validate(wire)


@pytest.mark.parametrize("band", ["low", "mid", "hi"])
def test_teaching_focus_all_eq_bands_validate(band: str) -> None:
    env = LearnTeachingFocus.make(
        control_id=f"eq_{band}",
        deck="B",
        band=band,
        phase="focus",
    )
    _VALIDATOR.validate(json.loads(env.to_json()))


def test_control_rect_roundtrips_screen_center() -> None:
    env = LearnControlRect.make(
        control_id="eq_low",
        deck="A",
        cx=120.5,
        cy=240.0,
    )
    wire = json.loads(env.to_json())

    assert wire["type"] == "ipc.learn.control_rect"
    assert wire["payload"] == {
        "control_id": "eq_low",
        "deck": "A",
        "cx": 120.5,
        "cy": 240.0,
    }
    _VALIDATOR.validate(wire)


def test_control_rect_coerces_int_coords_to_float() -> None:
    env = LearnControlRect.make(control_id="play", deck="", cx=10, cy=20)
    wire = json.loads(env.to_json())

    assert wire["payload"]["cx"] == 10.0
    assert wire["payload"]["cy"] == 20.0
    _VALIDATOR.validate(wire)
