# SPDX-License-Identifier: Apache-2.0
"""4-site schema-mirror lock for the `[judge:]` evidence source (the Vibe Judge).

Mirrors the [recall:] / [exemplar:] / [cue:] precedents EXACTLY. The Judge's
deterministic move-quality verdict is voiced by the co-host as a grounded
`[judge:<verdict_id>]` atom; the source MUST appear at every site or a fabricated
`[judge:<id>]` rides through un-validated (the silent-poisoning hole the
multi-site lock-step contract exists to prevent). `judge` is RETRIEVAL/narration-
time (like recall/exemplar/cue), so it stays OUT of memory/ingest.py — asymmetry
is intentional.
"""
from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent


def test_site_1_evidence_sources_frozenset_contains_judge() -> None:
    from vibemix.state.evidence_registry import EVIDENCE_SOURCES
    assert "judge" in EVIDENCE_SOURCES


def test_site_2_source_alt_regex_includes_judge() -> None:
    from vibemix.state.evidence_registry import _SOURCE_ALT
    assert "judge" in _SOURCE_ALT.split("|")


def test_site_2b_evidence_citation_re_matches_judge_atom() -> None:
    from vibemix.state.evidence_registry import (
        EVIDENCE_CITATION_RE,
        parse_citations,
    )
    assert EVIDENCE_CITATION_RE.fullmatch("[judge:transition@128.4]") is not None
    # Inner colon survives (mirrors recall/exemplar/cue precedent)
    assert EVIDENCE_CITATION_RE.fullmatch("[judge:8A>9A@128.4]") is not None
    assert parse_citations("[judge:transition@128.4]") == [("judge", "transition@128.4")]


def test_site_3_citation_grammar_block_documents_judge() -> None:
    from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK
    assert "[judge:<verdict_id>]" in CITATION_GRAMMAR_BLOCK


def test_site_4_dj_cohost_citation_strip_allows_judge() -> None:
    source_path = _REPO / "src" / "vibemix" / "agent" / "dj_cohost.py"
    text = source_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r'if source not in\s*\(\s*"ev"\s*,\s*"mix"\s*,\s*"midi"\s*,\s*"key"\s*,'
        r'\s*"recall"\s*,\s*"exemplar"\s*,\s*"cue"\s*,\s*"judge"',
        re.MULTILINE,
    )
    assert pattern.search(text) is not None


def test_evidence_registry_writes_and_reads_judge_source() -> None:
    from vibemix.state.evidence_registry import EvidenceRegistry
    reg = EvidenceRegistry()
    reg.write(source="judge", key="transition@128.4", t_session=128.4)
    assert reg.snapshot()["judge"]["transition@128.4"] == (128.4,)


def test_judge_stays_out_of_memory_ingest_alternation() -> None:
    # Asymmetry (intentional): ingest-time extractor must NOT whitelist judge.
    source_path = _REPO / "src" / "vibemix" / "memory" / "ingest.py"
    text = source_path.read_text(encoding="utf-8")
    assert "judge" not in re.search(r'_SOURCE_ALT\s*=\s*"([^"]+)"', text).group(1).split("|")
