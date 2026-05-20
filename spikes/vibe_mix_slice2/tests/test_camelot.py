# SPDX-License-Identifier: Apache-2.0
import pytest

from spikes.vibe_mix_slice2.camelot import are_compatible, parse_camelot


@pytest.mark.parametrize(
    "key,expected",
    [
        ("8A", "8A"), ("12b", "12B"), (" 1A ", "1A"),
        ("Am", "8A"), ("A", "11B"), ("C", "8B"), ("Cm", "5A"),
        ("F#m", "11A"), ("Gbm", "11A"), ("Bbm", "3A"), ("A#m", "3A"),
        ("Ab", "4B"), ("G#", "4B"), ("Dm", "7A"), ("Em", "9A"),
        ("13A", None), ("H", None), ("", None), (None, None), ("xyz", None),
    ],
)
def test_parse_camelot(key, expected):
    assert parse_camelot(key) == expected


def test_enharmonic_equivalents_match():
    assert parse_camelot("F#m") == parse_camelot("Gbm")
    assert parse_camelot("Ab") == parse_camelot("G#")


def test_compatible_identical():
    assert are_compatible("8A", "8A")


def test_compatible_wheel_adjacent_same_letter():
    assert are_compatible("8A", "7A")
    assert are_compatible("8A", "9A")
    assert are_compatible("12A", "1A")  # wheel wraps
    assert not are_compatible("8A", "10A")  # two steps = clash


def test_compatible_relative_major_minor():
    assert are_compatible("8A", "8B")   # Am <-> C
    assert are_compatible("Am", "C")


def test_incompatible_when_either_unknown():
    # Never claim an in-key mix we cannot prove.
    assert not are_compatible("8A", None)
    assert not are_compatible("garbage", "8A")


def test_different_letter_different_number_incompatible():
    assert not are_compatible("8A", "9B")
