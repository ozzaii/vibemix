# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    path = Path("scripts/eval/controller_profile_candidate.py")
    spec = importlib.util.spec_from_file_location("controller_profile_candidate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ddj_sb3_candidate_shape_and_source_audit(tmp_path):
    module = _load_module()
    pdf = tmp_path / "manufacturer.txt"
    pdf.write_text(
        """
        PLAY/PAUSE press 1/2 NOTE 11 B-1 9n 0B
        CUE press 1/2 NOTE 12 C0 9n 0C
        SYNC press 1/2 NOTE 88 E6 9n 58
        JOG DIAL rotate Wheel side 1/2 CC 33 - Bn 21 Difference count value
        touch 1/2 NOTE 54 F#3 9n 36
        TEMPO slide 0 00 MSB 1/2 CC - Bn 32 20 LSB
        TRIM rotate 4 04 MSB 1/2 CC - Bn 36 24 LSB
        EQ HIGH rotate 7 07 MSB 1/2 CC - Bn 39 27 LSB
        EQ MID rotate 11 0B MSB 1/2 CC - Bn 43 2B LSB
        EQ LOW rotate 15 0F MSB 1/2 CC - Bn 47 2F LSB
        CH1 Filter 7 CC 23 17 MSB B6 55 37 LSB
        CH2 Filter 7 CC 24 18 MSB B6 56 38 LSB
        CH FADER slide 19 13 MSB 1/2 CC - Bn 51 33 LSB
        CROSSFADER slide 31 1F MSB 7 CC - B6 63 3F LSB
        """,
        encoding="utf-8",
    )
    xml = tmp_path / "mixxx.xml"
    xml.write_text(
        """<?xml version="1.0"?>
        <MixxxControllerPreset><controller><controls>
          <control><group>[Channel1]</group><description>Channel fader Deck 1 (MSB)</description><status>0xB0</status><midino>0x13</midino></control>
          <control><group>[Channel2]</group><description>Channel fader Deck 2 (MSB)</description><status>0xB1</status><midino>0x13</midino></control>
          <control><group>[Channel1]</group><description>High level Deck 1 (MSB)</description><status>0xB0</status><midino>0x07</midino></control>
          <control><group>[Channel2]</group><description>High level Deck 2 (MSB)</description><status>0xB1</status><midino>0x07</midino></control>
          <control><group>[Channel1]</group><description>Mid level Deck 1 (MSB)</description><status>0xB0</status><midino>0x0B</midino></control>
          <control><group>[Channel2]</group><description>Mid level Deck 2 (MSB)</description><status>0xB1</status><midino>0x0B</midino></control>
          <control><group>[Channel1]</group><description>Low level Deck 1 (MSB)</description><status>0xB0</status><midino>0x0F</midino></control>
          <control><group>[Channel2]</group><description>Low level Deck 2 (MSB)</description><status>0xB1</status><midino>0x0F</midino></control>
          <control><group>[Channel1]</group><description>Tempo slider Deck 1 (MSB)</description><status>0xB0</status><midino>0x00</midino></control>
          <control><group>[Channel2]</group><description>Tempo slider Deck 2 (MSB)</description><status>0xB1</status><midino>0x00</midino></control>
          <control><group>[Channel1]</group><description>Jog ring Deck 1</description><status>0xB0</status><midino>0x21</midino></control>
          <control><group>[Channel2]</group><description>Jog ring Deck 2</description><status>0xB1</status><midino>0x21</midino></control>
          <control><group>[Channel1]</group><description>Filter Deck 1 (MSB)</description><status>0xB6</status><midino>0x17</midino></control>
          <control><group>[Channel2]</group><description>Filter Deck 2 (MSB)</description><status>0xB6</status><midino>0x18</midino></control>
          <control><group>[Master]</group><description>Crossfader (MSB)</description><status>0xB6</status><midino>0x1F</midino></control>
          <control><group>[Channel1]</group><description>Play/Pause Deck 1</description><status>0x90</status><midino>0x0B</midino></control>
          <control><group>[Channel2]</group><description>Play/Pause Deck 2</description><status>0x91</status><midino>0x0B</midino></control>
          <control><group>[Channel1]</group><description>Cue Deck 1</description><status>0x90</status><midino>0x0C</midino></control>
          <control><group>[Channel2]</group><description>Cue Deck 2</description><status>0x91</status><midino>0x0C</midino></control>
          <control><group>[Channel1]</group><description>Sync Deck 1</description><status>0x90</status><midino>0x58</midino></control>
          <control><group>[Channel2]</group><description>Sync Deck 2</description><status>0x91</status><midino>0x58</midino></control>
          <control><group>[Channel1]</group><description>Jog touch (Vinyl Mode) Deck 1</description><status>0x90</status><midino>0x36</midino></control>
          <control><group>[Channel2]</group><description>Jog touch (Vinyl Mode) Deck 2</description><status>0x91</status><midino>0x36</midino></control>
        </controls></controller></MixxxControllerPreset>""",
        encoding="utf-8",
    )

    profile = module.build_candidate()
    assert profile["id"] == "pioneer_ddj_sb3"
    assert len(profile["controls"]) == 15
    assert len(profile["buttons"]) == 8
    assert profile["controls"]["filter_b"]["channel"] == 6
    assert profile["buttons"]["sync_a"]["note"] == 88

    audit = module.build_audit(pdf, xml)
    assert audit["facts_total"] == 23
    assert audit["facts_cross_checked"] == 23
    assert audit["failed"] == []
