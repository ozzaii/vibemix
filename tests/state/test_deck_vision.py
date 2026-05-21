# SPDX-License-Identifier: Apache-2.0
"""Tests for the Gemini-vision deck-read leg (Plan 59-05, DECK-02).

The vision deck-read is a SEPARATE structured-output Gemini call — NOT the
screenshot re-attached to the reaction turn. These tests use a MOCKED Gemini
client only; the default fast suite makes NO live Gemini call. The live path is
``eval/deck_vision/run_eval.py`` (opt-in), not these unit tests.

Coverage:
  * structured-JSON happy path → DeckTrack fields populated, source="screen_vision"
  * null / missing fields → unknown (confidence=0, harmonic fields None)
  * malformed / raising response → graceful unknown (NEVER raises into the poller)
  * cadence debounce blocks a too-soon second read
  * audio-only tier skip (no read attempted)
  * to_camelot normalization applied (musical / open-key → Camelot)
  * vision confidence is BELOW the XML floor (a misread badge is a silent error)
  * Gemini-only: no openai/anthropic import
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from vibemix.state.deck_vision import (
    VISION_CONF,
    DeckVisionReader,
)
from vibemix.state.deck_poller import VISION_CONF_FLOOR, XML_CONF_FLOOR


# ---------------------------------------------------------------------- #
# Mock Gemini client                                                      #
# ---------------------------------------------------------------------- #


class _FakeModels:
    """Mimics ``client.models`` — records the call + returns a canned response."""

    def __init__(self, *, text=None, exc=None):
        self._text = text
        self._exc = exc
        self.calls: list[dict] = []

    def generate_content(self, *, model, contents, config=None):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self._exc is not None:
            raise self._exc
        return SimpleNamespace(text=self._text)


class _FakeClient:
    def __init__(self, *, text=None, exc=None):
        self.models = _FakeModels(text=text, exc=exc)


_JPEG = b"\xff\xd8\xff\xe0fakejpeg\xff\xd9"


def _reader(client, **kw):
    # interval=0 by default so most tests don't trip the debounce gate.
    kw.setdefault("interval", 0.0)
    return DeckVisionReader(client=client, model="gemini-vision-test", **kw)


# ---------------------------------------------------------------------- #
# Happy path                                                              #
# ---------------------------------------------------------------------- #


def test_structured_json_happy_path_populates_decktracks():
    payload = json.dumps(
        {
            "decks": [
                {"side": "A", "title": "Strobe", "key": "8A", "bpm": 128},
                {"side": "B", "title": "Opus", "key": "Am", "bpm": 124},
            ]
        }
    )
    reader = _reader(_FakeClient(text=payload))
    decks = reader.read(_JPEG)

    assert set(decks) == {"A", "B"}
    a = decks["A"]
    assert a.title == "Strobe"
    assert a.camelot == "8A"
    assert a.bpm == 128.0
    assert a.source == "screen_vision"
    # "Am" (musical) normalizes to Camelot on deck B.
    assert decks["B"].camelot == "8A"
    assert decks["B"].title == "Opus"


def test_request_is_structured_output_not_free_text():
    payload = json.dumps({"decks": []})
    client = _FakeClient(text=payload)
    reader = _reader(client)
    reader.read(_JPEG)

    assert len(client.models.calls) == 1
    cfg = client.models.calls[0]["config"]
    # Structured output: a response_mime_type=application/json + response_schema
    # must be present (whichever config shape the impl uses).
    cfg_repr = repr(cfg)
    assert "application/json" in cfg_repr
    assert "response_schema" in cfg_repr or "responseSchema" in cfg_repr or hasattr(
        cfg, "response_schema"
    )


def test_screenshot_attached_as_image_jpeg_part():
    payload = json.dumps({"decks": []})
    client = _FakeClient(text=payload)
    reader = _reader(client)
    reader.read(_JPEG)
    contents = client.models.calls[0]["contents"]
    # The jpeg bytes must appear somewhere in the contents (inline image Part).
    assert "image/jpeg" in repr(contents)


# ---------------------------------------------------------------------- #
# Null-defensive parse                                                    #
# ---------------------------------------------------------------------- #


def test_null_fields_map_to_unknown_no_guess():
    payload = json.dumps(
        {"decks": [{"side": "A", "title": None, "key": None, "bpm": None}]}
    )
    reader = _reader(_FakeClient(text=payload))
    decks = reader.read(_JPEG)
    a = decks["A"]
    assert a.title is None
    assert a.key is None
    assert a.camelot is None
    assert a.bpm == 0.0
    assert a.confidence == 0.0  # null field → confidence=0 / unknown


def test_missing_fields_map_to_unknown():
    payload = json.dumps({"decks": [{"side": "A"}]})
    reader = _reader(_FakeClient(text=payload))
    decks = reader.read(_JPEG)
    a = decks["A"]
    assert a.title is None
    assert a.camelot is None
    assert a.confidence == 0.0


def test_unparseable_key_normalizes_to_none():
    payload = json.dumps(
        {"decks": [{"side": "A", "title": "X", "key": "ZZZ-not-a-key", "bpm": 120}]}
    )
    reader = _reader(_FakeClient(text=payload))
    decks = reader.read(_JPEG)
    # title present → deck resolved, but a junk key degrades to None (no guess).
    assert decks["A"].camelot is None


# ---------------------------------------------------------------------- #
# Graceful degradation                                                    #
# ---------------------------------------------------------------------- #


def test_raising_client_returns_graceful_unknown_no_raise():
    reader = _reader(_FakeClient(exc=RuntimeError("network down")))
    decks = reader.read(_JPEG)  # must NOT raise
    assert decks == {}


def test_malformed_json_returns_graceful_unknown():
    reader = _reader(_FakeClient(text="not json at all {{{"))
    decks = reader.read(_JPEG)
    assert decks == {}


def test_empty_response_returns_graceful_unknown():
    reader = _reader(_FakeClient(text=""))
    decks = reader.read(_JPEG)
    assert decks == {}


def test_decks_not_a_list_returns_graceful_unknown():
    reader = _reader(_FakeClient(text=json.dumps({"decks": "garbage"})))
    decks = reader.read(_JPEG)
    assert decks == {}


# ---------------------------------------------------------------------- #
# Cadence debounce + audio-only skip                                      #
# ---------------------------------------------------------------------- #


def test_cadence_debounce_blocks_too_soon_second_read():
    payload = json.dumps({"decks": [{"side": "A", "title": "T", "key": "8A", "bpm": 128}]})
    client = _FakeClient(text=payload)
    reader = _reader(client, interval=10.0)

    first = reader.read(_JPEG)
    assert first["A"].title == "T"
    assert len(client.models.calls) == 1

    # Second read within the interval → debounced (returns last result, no new call).
    second = reader.read(_JPEG)
    assert len(client.models.calls) == 1  # NO second Gemini call
    assert "A" in second  # last-known returned, not an error


def test_audio_only_tier_skips_vision_entirely():
    payload = json.dumps({"decks": [{"side": "A", "title": "T", "key": "8A", "bpm": 128}]})
    client = _FakeClient(text=payload)
    reader = _reader(client)
    decks = reader.read(_JPEG, audio_only=True)
    assert decks == {}
    assert len(client.models.calls) == 0  # never called the model


# ---------------------------------------------------------------------- #
# Confidence: vision strictly below XML                                   #
# ---------------------------------------------------------------------- #


def test_vision_confidence_below_xml_floor():
    # A misread badge is a silent error — vision must carry LOWER confidence than
    # an XML-matched key so it can never out-cite the pre-analyzed tag.
    assert VISION_CONF < XML_CONF_FLOOR
    # And it lands at-or-below the gating floor consumed by the poller.
    assert VISION_CONF <= VISION_CONF_FLOOR


def test_resolved_deck_carries_vision_conf_constant():
    payload = json.dumps({"decks": [{"side": "A", "title": "T", "key": "8A", "bpm": 128}]})
    reader = _reader(_FakeClient(text=payload))
    decks = reader.read(_JPEG)
    assert decks["A"].confidence == VISION_CONF


# ---------------------------------------------------------------------- #
# Gemini-only                                                             #
# ---------------------------------------------------------------------- #


def test_no_foreign_provider_import():
    import pathlib

    src = pathlib.Path("src/vibemix/state/deck_vision.py").read_text().lower()
    assert "openai" not in src
    assert "anthropic" not in src
