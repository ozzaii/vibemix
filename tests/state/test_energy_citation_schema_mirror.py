# SPDX-License-Identifier: Apache-2.0
"""Schema-mirror lock for the `[energy:]` evidence source (master-mix energy read).

Mirrors the [recall:] / [exemplar:] / [cue:] / [judge:] precedents EXACTLY.
The energy-read receipt (runtime/energy_read_voice.py) registers
``("energy", "master_read=<id>_<digest>", t)`` at receipt-build time and
instructs the model to copy ``[energy:<read_id>]`` verbatim; the source MUST
appear at every lock-step site or the atom parses to zero citations — invisible
to the CitationLinter AND unstripped by the TTS sanitizer, so Chatterbox would
speak the raw bracket aloud (the silent-poisoning hole, found by the 2026-06-09
receipt-wire slop audit). ``energy`` is narration-time (like recall/exemplar/
cue/judge), so it stays OUT of memory/ingest.py — asymmetry is intentional.
Unlike judge, ``energy`` also stays OUT of the dj_cohost chip allow-list:
its body carries no DJ-action verb worth a chip (same class as aud/track/screen).
"""
from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent


def test_site_1_evidence_sources_frozenset_contains_energy() -> None:
    from vibemix.state.evidence_registry import EVIDENCE_SOURCES
    assert "energy" in EVIDENCE_SOURCES


def test_site_2_source_alt_regex_includes_energy() -> None:
    from vibemix.state.evidence_registry import _SOURCE_ALT
    assert "energy" in _SOURCE_ALT.split("|")


def test_site_2b_evidence_citation_re_matches_energy_atom() -> None:
    from vibemix.state.evidence_registry import (
        EVIDENCE_CITATION_RE,
        parse_citations,
    )
    assert (
        EVIDENCE_CITATION_RE.fullmatch("[energy:master_read=audio_groove_12_ab12cd34]")
        is not None
    )
    # The risk-flag form survives too (energy_risk=<flag>)
    assert EVIDENCE_CITATION_RE.fullmatch("[energy:energy_risk=key_clash]") is not None
    assert parse_citations("[energy:master_read=audio_groove_12_ab12cd34]") == [
        ("energy", "master_read=audio_groove_12_ab12cd34")
    ]


def test_site_3_citation_grammar_block_documents_energy() -> None:
    from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK
    assert "[energy:<read_id>]" in CITATION_GRAMMAR_BLOCK


def test_site_4_energy_stays_out_of_chip_allow_list() -> None:
    # Intentional: no DJ-action verb in a master_read body — no chip (same
    # class as aud/track/screen). Linter + TTS strip still cover the atom.
    source_path = _REPO / "src" / "vibemix" / "agent" / "dj_cohost.py"
    text = source_path.read_text(encoding="utf-8")
    match = re.search(r"if source not in\s*\(([^)]+)\)\s*:", text)
    assert match is not None
    allow_list = [item.strip().strip('"') for item in match.group(1).split(",") if item.strip()]
    assert "energy" not in allow_list


def test_site_5_tts_sanitizer_strips_energy_atom() -> None:
    # THE motivating hole: pre-fix, the energy bracket rode through to
    # Chatterbox and was spoken aloud.
    from vibemix.agent.tts_sanitizer import strip_citations_for_tts
    spoken = strip_citations_for_tts(
        "Hold the groove steady. [energy:master_read=audio_groove_12_ab12cd34]"
    )
    assert "[" not in spoken and "]" not in spoken
    assert "Hold the groove steady." in spoken


def test_evidence_registry_writes_and_reads_energy_source() -> None:
    from vibemix.state.evidence_registry import EvidenceRegistry
    reg = EvidenceRegistry()
    reg.write(source="energy", key="master_read=audio_groove_12_ab12cd34", t_session=48.0)
    assert reg.snapshot()["energy"]["master_read=audio_groove_12_ab12cd34"] == (48.0,)


def test_energy_stays_out_of_memory_ingest_alternation() -> None:
    # Asymmetry (intentional): ingest-time extractor must NOT whitelist energy.
    source_path = _REPO / "src" / "vibemix" / "memory" / "ingest.py"
    text = source_path.read_text(encoding="utf-8")
    assert "energy" not in re.search(r'_SOURCE_ALT\s*=\s*"([^"]+)"', text).group(1).split("|")
