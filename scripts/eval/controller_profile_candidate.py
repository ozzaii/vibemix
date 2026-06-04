#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build a clean-room MIDI profile candidate from source fact files.

This intentionally does not install the profile into ``src/vibemix/midi``. The
production profile package is owned by the MIDI lane; this eval script emits a
reviewable candidate + source audit from two inputs:

* manufacturer MIDI-message PDF text extracted with ``pdftotext -layout``;
* Mixxx controller XML used only as a factual cross-check for status/data bytes.

Only uncopyrightable hardware facts are extracted. No Mixxx XML/JS structure is
copied into the candidate.
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MANUFACTURER_URL = (
    "https://downloads.support.alphatheta.com/software_info/dj-controllers/"
    "DDJ-SB3/ddj-sb3_midi_message_list_e2.pdf"
)
MIXXX_URL = "https://raw.githubusercontent.com/mixxxdj/mixxx/main/res/controllers/Pioneer-DDJ-SB3.midi.xml"


@dataclass(frozen=True)
class CandidateFact:
    name: str
    midi_kind: str
    channel: int
    data1: int
    mixxx_group: str
    mixxx_description_terms: tuple[str, ...]
    pdf_anchor: str
    pdf_terms: tuple[str, ...]


FACTS: tuple[CandidateFact, ...] = (
    CandidateFact("vol_a", "cc", 0, 19, "[Channel1]", ("Channel fader Deck 1", "MSB"), "CH FADER", ("19", "13", "MSB", "1/2", "CC", "Bn")),
    CandidateFact("vol_b", "cc", 1, 19, "[Channel2]", ("Channel fader Deck 2", "MSB"), "CH FADER", ("19", "13", "MSB", "1/2", "CC", "Bn")),
    CandidateFact("eq_hi_a", "cc", 0, 7, "[Channel1]", ("High level Deck 1", "MSB"), "EQ HIGH", ("7", "07", "MSB", "1/2", "CC", "Bn")),
    CandidateFact("eq_hi_b", "cc", 1, 7, "[Channel2]", ("High level Deck 2", "MSB"), "EQ HIGH", ("7", "07", "MSB", "1/2", "CC", "Bn")),
    CandidateFact("eq_mid_a", "cc", 0, 11, "[Channel1]", ("Mid level Deck 1", "MSB"), "EQ MID", ("11", "0B", "MSB", "1/2", "CC", "Bn")),
    CandidateFact("eq_mid_b", "cc", 1, 11, "[Channel2]", ("Mid level Deck 2", "MSB"), "EQ MID", ("11", "0B", "MSB", "1/2", "CC", "Bn")),
    CandidateFact("eq_low_a", "cc", 0, 15, "[Channel1]", ("Low level Deck 1", "MSB"), "EQ LOW", ("15", "0F", "MSB", "1/2", "CC", "Bn")),
    CandidateFact("eq_low_b", "cc", 1, 15, "[Channel2]", ("Low level Deck 2", "MSB"), "EQ LOW", ("15", "0F", "MSB", "1/2", "CC", "Bn")),
    CandidateFact("tempo_a", "cc", 0, 0, "[Channel1]", ("Tempo slider Deck 1", "MSB"), "TEMPO", ("0", "00", "MSB", "1/2", "CC", "Bn")),
    CandidateFact("tempo_b", "cc", 1, 0, "[Channel2]", ("Tempo slider Deck 2", "MSB"), "TEMPO", ("0", "00", "MSB", "1/2", "CC", "Bn")),
    CandidateFact("jog_move_a", "cc", 0, 33, "[Channel1]", ("Jog ring Deck 1",), "JOG DIAL", ("CC", "33", "Bn", "21", "Difference count value")),
    CandidateFact("jog_move_b", "cc", 1, 33, "[Channel2]", ("Jog ring Deck 2",), "JOG DIAL", ("CC", "33", "Bn", "21", "Difference count value")),
    CandidateFact("filter_a", "cc", 6, 23, "[Channel1]", ("Filter Deck 1", "MSB"), "CH1 Filter", ("23", "17", "MSB", "7", "CC", "B6")),
    CandidateFact("filter_b", "cc", 6, 24, "[Channel2]", ("Filter Deck 2", "MSB"), "CH2 Filter", ("24", "18", "MSB", "7", "CC", "B6")),
    CandidateFact("xfader", "cc", 6, 31, "[Master]", ("Crossfader", "MSB"), "CROSSFADER", ("31", "1F", "MSB", "7", "CC", "B6")),
    CandidateFact("play_a", "note", 0, 11, "[Channel1]", ("Play/Pause Deck 1",), "PLAY/PAUSE", ("NOTE", "11", "9n", "0B")),
    CandidateFact("play_b", "note", 1, 11, "[Channel2]", ("Play/Pause Deck 2",), "PLAY/PAUSE", ("NOTE", "11", "9n", "0B")),
    CandidateFact("cue_a", "note", 0, 12, "[Channel1]", ("Cue Deck 1",), "CUE", ("NOTE", "12", "9n", "0C")),
    CandidateFact("cue_b", "note", 1, 12, "[Channel2]", ("Cue Deck 2",), "CUE", ("NOTE", "12", "9n", "0C")),
    CandidateFact("sync_a", "note", 0, 88, "[Channel1]", ("Sync Deck 1",), "SYNC", ("NOTE", "88", "9n", "58")),
    CandidateFact("sync_b", "note", 1, 88, "[Channel2]", ("Sync Deck 2",), "SYNC", ("NOTE", "88", "9n", "58")),
    CandidateFact("jog_a", "note", 0, 54, "[Channel1]", ("Jog touch (Vinyl Mode) Deck 1",), "touch", ("NOTE", "54", "9n", "36")),
    CandidateFact("jog_b", "note", 1, 54, "[Channel2]", ("Jog touch (Vinyl Mode) Deck 2",), "touch", ("NOTE", "54", "9n", "36")),
)


CONTROL_FIELDS: dict[str, tuple[str, str, str | None]] = {
    "vol_a": ("vol", "unipolar", "A"),
    "vol_b": ("vol", "unipolar", "B"),
    "eq_hi_a": ("eq_hi", "unipolar", "A"),
    "eq_hi_b": ("eq_hi", "unipolar", "B"),
    "eq_mid_a": ("eq_mid", "unipolar", "A"),
    "eq_mid_b": ("eq_mid", "unipolar", "B"),
    "eq_low_a": ("eq_low", "unipolar", "A"),
    "eq_low_b": ("eq_low", "unipolar", "B"),
    "tempo_a": ("tempo", "bipolar", "A"),
    "tempo_b": ("tempo", "bipolar", "B"),
    "jog_move_a": ("jog", "relative", "A"),
    "jog_move_b": ("jog", "relative", "B"),
    "filter_a": ("filter", "bipolar", "A"),
    "filter_b": ("filter", "bipolar", "B"),
    "xfader": ("xfader", "bipolar", None),
}


BUTTON_KINDS: dict[str, tuple[str, str]] = {
    "play_a": ("play", "A"),
    "play_b": ("play", "B"),
    "cue_a": ("cue", "A"),
    "cue_b": ("cue", "B"),
    "sync_a": ("sync", "A"),
    "sync_b": ("sync", "B"),
    "jog_a": ("jog_touch", "A"),
    "jog_b": ("jog_touch", "B"),
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().upper()


def _parse_int(text: str) -> int:
    return int(text, 16) if text.lower().startswith("0x") else int(text)


def _status_for(kind: str, channel: int) -> int:
    if kind == "cc":
        return 0xB0 + channel
    if kind == "note":
        return 0x90 + channel
    raise ValueError(f"unsupported kind: {kind}")


def _read_mixxx_controls(path: Path) -> list[dict[str, Any]]:
    root = ET.parse(path).getroot()
    rows: list[dict[str, Any]] = []
    for control in root.findall(".//control"):
        group = (control.findtext("group") or "").strip()
        description = (control.findtext("description") or "").strip()
        status = (control.findtext("status") or "").strip()
        midino = (control.findtext("midino") or "").strip()
        if not group or not status or not midino:
            continue
        rows.append(
            {
                "group": group,
                "description": description,
                "status": _parse_int(status),
                "data1": _parse_int(midino),
                "status_hex": f"0x{_parse_int(status):02X}",
                "data1_hex": f"0x{_parse_int(midino):02X}",
            }
        )
    return rows


def _mixxx_match(rows: list[dict[str, Any]], fact: CandidateFact) -> dict[str, Any]:
    expected_status = _status_for(fact.midi_kind, fact.channel)
    terms = tuple(_norm(term) for term in fact.mixxx_description_terms)
    for row in rows:
        if row["group"] != fact.mixxx_group:
            continue
        if row["status"] != expected_status or row["data1"] != fact.data1:
            continue
        description = _norm(row["description"])
        if all(term in description for term in terms):
            return {"matched": True, "row": row}
    return {
        "matched": False,
        "expected": {
            "group": fact.mixxx_group,
            "status_hex": f"0x{expected_status:02X}",
            "data1_hex": f"0x{fact.data1:02X}",
            "description_terms": fact.mixxx_description_terms,
        },
    }


def _pdf_window_match(pdf_text: str, fact: CandidateFact) -> dict[str, Any]:
    normalized = _norm(pdf_text)
    anchor = _norm(fact.pdf_anchor)
    pos = normalized.find(anchor)
    if pos < 0:
        return {"matched": False, "reason": f"anchor {fact.pdf_anchor!r} not found"}
    window = normalized[max(0, pos - 900) : pos + 1400]
    missing = [term for term in fact.pdf_terms if _norm(term) not in window]
    return {
        "matched": not missing,
        "anchor": fact.pdf_anchor,
        "missing_terms": missing,
        "window_start": max(0, pos - 900),
    }


def build_candidate() -> dict[str, Any]:
    controls: dict[str, Any] = {}
    buttons: dict[str, Any] = {}
    for fact in FACTS:
        if fact.midi_kind == "cc":
            field, axis, deck = CONTROL_FIELDS[fact.name]
            controls[fact.name] = {
                "kind": "cc",
                "channel": fact.channel,
                "cc": fact.data1,
                "axis": axis,
                "deck": deck,
                "field": field,
            }
        else:
            kind, deck = BUTTON_KINDS[fact.name]
            buttons[fact.name] = {
                "kind": kind,
                "channel": fact.channel,
                "note": fact.data1,
                "deck": deck,
            }
    return {
        "id": "pioneer_ddj_sb3",
        "display_name": "Pioneer DDJ-SB3",
        "port_name_hints": ["DDJ-SB3", "Pioneer DDJ-SB3"],
        "decks": ["A", "B"],
        "notes": (
            "Candidate generated by scripts/eval/controller_profile_candidate.py; "
            "NOT production-landed and NOT hardware-verified. MIDI bytes are clean-room "
            "facts from the official AlphaTheta/Pioneer DDJ-SB3 MIDI message list "
            "cross-checked against Mixxx Pioneer-DDJ-SB3.midi.xml. Current vibemix "
            "profile schema binds one CC per control, so 14-bit LSB companion CCs "
            "documented in the PDF (tempo/fader/EQ/filter/xfader) are intentionally "
            "omitted and MSB bytes are used, matching existing Pioneer profiles. "
            "Mode-dependent performance pads/hotcues are omitted from this core mix "
            "candidate. No Mixxx XML/JS source copied."
        ),
        "controls": controls,
        "buttons": buttons,
    }


def build_audit(manufacturer_text: Path, mixxx_xml: Path) -> dict[str, Any]:
    pdf_text = manufacturer_text.read_text(encoding="utf-8", errors="replace")
    mixxx_rows = _read_mixxx_controls(mixxx_xml)
    facts: dict[str, Any] = {}
    for fact in FACTS:
        pdf = _pdf_window_match(pdf_text, fact)
        mixxx = _mixxx_match(mixxx_rows, fact)
        facts[fact.name] = {
            "midi_kind": fact.midi_kind,
            "channel": fact.channel,
            "data1": fact.data1,
            "data1_hex": f"0x{fact.data1:02X}",
            "manufacturer_pdf": pdf,
            "mixxx_xml": mixxx,
            "cross_checked": bool(pdf.get("matched") and mixxx.get("matched")),
        }
    passed = [name for name, row in facts.items() if row["cross_checked"]]
    failed = [name for name, row in facts.items() if not row["cross_checked"]]
    return {
        "profile_id": "pioneer_ddj_sb3",
        "manufacturer_source": MANUFACTURER_URL,
        "mixxx_source": MIXXX_URL,
        "facts_total": len(facts),
        "facts_cross_checked": len(passed),
        "failed": failed,
        "schema_caveats": [
            "14-bit LSB bytes are documented by the manufacturer but omitted because the current profile schema binds one CC per semantic control.",
            "Performance pads are mode-dependent; they are omitted from this core candidate until runtime pad-bank state exists.",
            "Candidate is source-verified only; hardware sniff still required before marking verified.",
        ],
        "facts": facts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manufacturer-text", required=True, type=Path)
    parser.add_argument("--mixxx-xml", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    candidate = build_candidate()
    audit = build_audit(args.manufacturer_text, args.mixxx_xml)
    (args.out_dir / "candidate_profile.json").write_text(
        json.dumps(candidate, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    (args.out_dir / "source_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    summary = {
        "profile_id": audit["profile_id"],
        "facts_total": audit["facts_total"],
        "facts_cross_checked": audit["facts_cross_checked"],
        "failed": audit["failed"],
        "candidate_controls": len(candidate["controls"]),
        "candidate_buttons": len(candidate["buttons"]),
    }
    print(json.dumps(summary, indent=2))
    return 0 if not audit["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
