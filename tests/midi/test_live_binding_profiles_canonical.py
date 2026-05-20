# SPDX-License-Identifier: Apache-2.0
"""Phase 53 BRINGUP-03 — pin the live binding/decode path as canonical on
``midi/profiles/`` and document-and-pin the dual-map resolution.

THE DUAL-MAP QUESTION (resolved here):
    There are TWO controller-map registries in ``src/vibemix/midi``:

    1. ``midi/profiles/*.json`` + ``load_profile`` / ``list_profiles`` /
       ``find_mapping`` — this is the CANONICAL path the LIVE session uses.
       ``MidiMacOS().controller_state`` is built from
       ``load_profile("pioneer_ddj_flx4")``; the hot-plug watcher resolves
       ports via ``find_mapping`` / ``find_mapping_or_generic``; the listener
       binds + decodes through the ``ControllerProfile`` loaded from here.

    2. ``midi/controllers/*.json`` + ``MidiMapLoader`` (``map_loader.py``) — a
       SEPARATE, semantically-richer per-SKU map registry that is
       CURRENTLY UNWIRED: NOTHING under ``src/vibemix`` imports it at runtime
       (only its own module + the schema reference it). It is valid code kept
       for a future multi-controller path; it is NOT the live decode source.

    Resolution (locked for Phase 53): profiles/ is canonical for live binding +
    decode. controllers/+MidiMapLoader stays as a separate, unwired registry —
    we do NOT switch the live path to it, and we do NOT delete it. This module
    PINS that invariant so the live path can't silently migrate to controllers/
    and so MidiMapLoader can't silently acquire a live-runtime importer.
"""

from __future__ import annotations

import pathlib
import re
from types import SimpleNamespace

from vibemix.midi import list_profiles, load_profile
from vibemix.midi.registry import find_mapping


# ---------- (a) find_mapping resolves FLX4 on profiles/ ----------


def test_find_mapping_resolves_flx4_to_pioneer_profile():
    profile = find_mapping("DDJ-FLX4 USB MIDI")
    assert profile is not None
    assert profile.id == "pioneer_ddj_flx4"


def test_find_mapping_resolves_on_second_hint():
    """The FLX4 profile carries two port-name hints (``DDJ-FLX4`` and
    ``FLX4``); a firmware revision exposing only ``FLX4 ...`` must still bind."""
    profile = find_mapping("My FLX4 Controller")
    assert profile is not None
    assert profile.id == "pioneer_ddj_flx4"


def test_find_mapping_result_is_a_listed_profile():
    """Whatever find_mapping returns must be a profile that list_profiles
    enumerates — i.e. it comes from profiles/, not some out-of-band source."""
    profile = find_mapping("DDJ-FLX4 USB MIDI")
    assert profile is not None
    assert profile.id in list_profiles()


# ---------- (b) MidiMacOS live state binds the profiles/ FLX4 + decodes ----------


def test_midi_macos_controller_state_binds_flx4_profile():
    """The live session's ControllerState (MidiMacOS().controller_state) is
    bound to the profiles/ FLX4 profile — the strongest pin that the live
    decode path is canonical on profiles/."""
    from vibemix.platform import MidiMacOS

    macos = MidiMacOS()
    assert macos.controller_state._profile.id == "pioneer_ddj_flx4"
    snap = macos.controller_state.deck_snapshot()
    assert set(snap.keys()) == {"A", "B", "xfader", "connected"}


def test_midi_macos_controller_state_decodes_known_flx4_cc():
    """A known FLX4 CC (ch0/cc19 = vol_a) decodes correctly through the live
    ControllerState — proving the binding came from profiles/ and the decode
    works end-to-end against the live state object."""
    from vibemix.platform import MidiMacOS

    macos = MidiMacOS()
    cs = macos.controller_state
    cs.handle_msg(SimpleNamespace(type="control_change", channel=0, control=19, value=110))
    assert cs.deck_snapshot()["A"]["vol"] == 110


def test_flx4_state_from_profiles_decodes_without_map_loader():
    """A ControllerState built directly from load_profile('pioneer_ddj_flx4')
    decodes a known FLX4 CC — and this whole flow never imports MidiMapLoader,
    proving the live decode does not depend on the controllers/ registry."""
    from vibemix.midi.state import ControllerState

    profile = load_profile("pioneer_ddj_flx4")
    assert profile is not None
    cs = ControllerState(profile=profile)
    cs.handle_msg(SimpleNamespace(type="control_change", channel=0, control=19, value=64))
    assert cs.deck_snapshot()["A"]["vol"] == 64


# ---------- (c) controllers/ + MidiMapLoader is documented-unwired ----------


def test_map_loader_is_valid_code_but_not_the_live_source():
    """MidiMapLoader imports + constructs fine (it is valid, maintained code) —
    but importing it is a deliberate, explicit act. The point of this test is
    to assert it is NOT silently the live decode source: it is in a different
    module from the live binding path and is not re-exported from vibemix.midi.
    """
    from vibemix.midi.map_loader import MidiMapLoader

    assert MidiMapLoader is not None
    # MidiMapLoader is NOT re-exported from the package __init__ (the live
    # surface) — the only public live-binding helpers there are load_profile /
    # find_mapping / find_mapping_or_generic.
    import vibemix.midi as midi_pkg

    assert "MidiMapLoader" not in getattr(midi_pkg, "__all__", [])
    assert not hasattr(midi_pkg, "MidiMapLoader")


def test_no_live_runtime_consumer_imports_map_loader():
    """Source-level invariant: NO module under src/vibemix imports map_loader /
    MidiMapLoader except map_loader.py itself. This pins the dual-map
    resolution — the live path cannot silently migrate to the controllers/
    registry, and MidiMapLoader cannot silently acquire a live consumer.

    A re-export from midi/__init__.py would be tolerated (it is still not a
    live consumer), but today there is none — so the only allowed file is
    map_loader.py.
    """
    here = pathlib.Path(__file__).resolve()
    # tests/midi/test_*.py -> repo root is parents[2]
    repo_root = here.parents[2]
    src_root = repo_root / "src" / "vibemix"
    assert src_root.is_dir(), f"src/vibemix not found at {src_root}"

    pattern = re.compile(r"\bmap_loader\b|\bMidiMapLoader\b")
    allowed = {"map_loader.py"}
    offenders: list[str] = []
    for py in src_root.rglob("*.py"):
        if py.name in allowed:
            continue
        text = py.read_text(encoding="utf-8")
        if pattern.search(text):
            offenders.append(str(py.relative_to(repo_root)))

    assert offenders == [], (
        "map_loader/MidiMapLoader has acquired a live-runtime importer — the "
        "dual-map resolution is violated. profiles/ must stay canonical for "
        f"live binding/decode. Offending files: {offenders}"
    )
