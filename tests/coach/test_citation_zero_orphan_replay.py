# SPDX-License-Identifier: Apache-2.0
"""LIVE-04 zero-orphan replay against the real fixture.

This module pins the EXISTING airtight emission contract with REAL primitives
(no mocks, no network): build an EvidenceRegistry from the real session trace
``tests/fixtures/hype_trace_genre1.jsonl`` (writing ``ev:<TYPE>@t`` for every
event line + a few ``track:<id>`` entries via ``register_library`` on a
duck-typed library), then assert that for the set of citations a grounded
reply emits against that registry, ``CitationLinter.check(...).valid`` is True
AND every parsed atom resolves via ``EvidenceRegistry.has(...)`` — i.e. ZERO
orphans across the replayed corpus.

An ORPHAN is a citation atom emitted by the model that does NOT resolve to a
real EvidenceRegistry entry within the mode tolerance. "Zero orphans" means
every atom a grounded reply emits resolves; a hallucinated id is provably an
orphan (Task 2 in this file). Together these prove the linter strips orphans
BEFORE they reach the ear.

NO source is modified — ``citation_linter.py`` + ``evidence_registry.py`` +
``debrief/stripper.py`` are the airtight grounding gate per 55-RESEARCH Q0;
the telemetry leak is closed separately in Plan 55-03. The detector, linter,
and registry are untouched; this file ADDS replay regressions only.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from vibemix.coach.citation_linter import CitationLinter
from vibemix.coach.constants import LIVE_TOLERANCE_S
from vibemix.state.evidence_registry import EvidenceRegistry, parse_citations

# The real session trace captured on Kaan's Mac (genre 1). Resolved relative
# to this test file so the test is location-independent.
_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "hype_trace_genre1.jsonl"
)

# A few slug-form track ids registered on the duck-typed library. The fixture's
# real ``track`` field holds full titles with spaces (e.g. "A$AP ROCKY - ...")
# which the citation grammar rejects (body charset is ``[^\s,\]]+``). Gemini
# emits the spaceless slug form at the citation boundary, so we register the
# canonical id form a ``[track:<id>]`` citation actually uses.
_REGISTERED_TRACK_IDS = ("54830", "12345")


def _build_registry_from_fixture() -> EvidenceRegistry:
    """Build a REAL EvidenceRegistry from the real fixture event lines.

    For every JSONL line with ``kind == "event"`` write
    ``reg.write("ev", line["type"], float(line["t"]))`` — the ``t`` is
    session-relative seconds. Then register a couple of track ids via
    ``register_library`` on a tiny duck-typed object (any object with a
    ``.tracks`` mapping works — no full RekordboxLibrary needed).
    """
    reg = EvidenceRegistry()
    with _FIXTURE.open() as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            line = json.loads(raw)
            if line.get("kind") != "event":
                continue
            reg.write("ev", line["type"], float(line["t"]))
    # Duck-typed library: register_library only needs a ``.tracks`` mapping.
    lib = SimpleNamespace(tracks={tid: object() for tid in _REGISTERED_TRACK_IDS})
    reg.register_library(lib)
    return reg


def _fixture_events() -> list[tuple[str, float]]:
    """Return [(type, t), ...] for every event line in the fixture."""
    out: list[tuple[str, float]] = []
    with _FIXTURE.open() as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            line = json.loads(raw)
            if line.get("kind") != "event":
                continue
            out.append((line["type"], float(line["t"])))
    return out


def _atom_resolves(
    reg: EvidenceRegistry,
    source: str,
    body: str,
    snapshot: dict,
    tol: float = LIVE_TOLERANCE_S,
) -> bool:
    """Resolve a single parsed (source, body) atom against the registry.

    Time-keyed sources (ev/aud/midi) decompose the body into ``key`` + float
    ``t`` and call ``reg.has(source, key, t, tol)``. Existence-only sources
    just check key presence in the snapshot — mirrors the linter's own dispatch.
    """
    if source in ("ev", "aud", "midi"):
        if "@" not in body:
            return False
        key, _, t_str = body.partition("@")
        try:
            t_target = float(t_str)
        except ValueError:
            return False
        return reg.has(source, key, t_target, tol)
    # Existence-only sources.
    return body in snapshot.get(source, {})


# =========================================================================== #
# Task 1 — zero-orphan replay: every grounded citation resolves               #
# =========================================================================== #


def test_registry_built_from_real_fixture_events() -> None:
    """The registry is seeded from the REAL fixture event lines.

    Every ``ev:<TYPE>@t`` from the fixture lands in the registry, and the
    duck-typed track ids register. This pins that the replay corpus is built
    from real session data, not a hand-rolled snapshot.
    """
    reg = _build_registry_from_fixture()
    snap = reg.snapshot()

    events = _fixture_events()
    assert events, "fixture must contain event lines"

    # Every fixture event type is present as an ev:<TYPE> source key.
    fixture_types = {etype for etype, _ in events}
    assert fixture_types == set(snap.get("ev", {})), (
        "registry ev keys must mirror the fixture event types exactly"
    )

    # Every registered track id is an existence-only entry under track.
    for tid in _REGISTERED_TRACK_IDS:
        assert tid in snap.get("track", {}), f"track id {tid} must be registered"


def test_grounded_replies_are_valid_against_real_registry() -> None:
    """Grounded replies citing REAL fixture events + registered track ids are
    valid: check(...).valid is True, reason 'valid'.

    The cited @t is taken verbatim from the fixture so it resolves at exactly
    0.0s offset — the strongest possible grounding.
    """
    reg = _build_registry_from_fixture()
    snap = reg.snapshot()
    linter = CitationLinter()

    events = _fixture_events()
    # Pick a real PHASE event and a real MIX_MOVE event from the fixture.
    phase_t = next(t for etype, t in events if etype == "PHASE")
    mix_t = next(t for etype, t in events if etype == "MIX_MOVE")

    grounded_replies = [
        f"Phase shifted hard [ev:PHASE@{phase_t}]",
        f"That filter sweep was clean [ev:MIX_MOVE@{mix_t}]",
        "Reckon that was a banger [track:54830]",
        # Multi-citation: a real event + a registered track id together.
        f"Big moment, love it [ev:PHASE@{phase_t},track:54830]",
    ]

    for reply in grounded_replies:
        result = linter.check(reply, snap, mode="live")
        assert result.valid is True, f"grounded reply must pass: {reply!r}"
        assert result.reason == "valid", f"reason must be 'valid' for {reply!r}"


def test_zero_orphans_across_grounded_replies() -> None:
    """The orphan count across the grounded replies is 0.

    For every (source, body) atom parsed from the grounded replies, assert it
    resolves via ``reg.has(...)`` (time-keyed) or key-presence (existence-only).
    The orphan count — atoms that do NOT resolve — must be exactly 0.
    """
    reg = _build_registry_from_fixture()
    snap = reg.snapshot()

    events = _fixture_events()
    phase_t = next(t for etype, t in events if etype == "PHASE")
    mix_t = next(t for etype, t in events if etype == "MIX_MOVE")

    grounded_replies = [
        f"Phase shifted hard [ev:PHASE@{phase_t}]",
        f"That filter sweep was clean [ev:MIX_MOVE@{mix_t}]",
        "Reckon that was a banger [track:54830]",
        f"Big moment, love it [ev:PHASE@{phase_t},track:54830]",
    ]

    total_atoms = 0
    orphans: list[tuple[str, str]] = []
    for reply in grounded_replies:
        for source, body in parse_citations(reply):
            total_atoms += 1
            if not _atom_resolves(reg, source, body, snap):
                orphans.append((source, body))

    assert total_atoms > 0, "the replies must contain citation atoms to replay"
    assert orphans == [], f"expected zero orphans, found: {orphans}"


# =========================================================================== #
# Task 2 — hallucination-strip: injected non-existent citation is stripped     #
# against a NON-empty real registry (stronger than the empty-registry hype     #
# proof in tests/state/test_hype_anti_slop.py — here real evidence EXISTS but  #
# the fabricated citation still never reaches the ear).                        #
# =========================================================================== #


def test_hallucinated_time_keyed_citation_is_stripped() -> None:
    """An injected time-keyed orphan ([ev:GHOST_EVENT@999.9]) is stripped on
    the NON-empty real registry: valid False, reason 'invalid_atoms', and the
    orphan atom surfaces in LintResult.missing.

    GHOST_EVENT is not a fixture event type and 999.9s is beyond every real
    observation — a deliberately-hallucinated citation. The strip proves an
    orphan never reaches the ear even when the registry holds real evidence.
    """
    reg = _build_registry_from_fixture()
    snap = reg.snapshot()
    linter = CitationLinter()

    result = linter.check("Massive ghost drop [ev:GHOST_EVENT@999.9]", snap, mode="live")
    assert result.valid is False
    assert result.reason == "invalid_atoms"
    assert ("ev", "GHOST_EVENT@999.9") in result.missing


def test_hallucinated_track_citation_is_stripped() -> None:
    """An injected existence-only orphan ([track:NONEXISTENT_ID]) is stripped:
    valid False, reason 'invalid_atoms', the orphan in .missing.

    NONEXISTENT_ID was never registered via register_library — a fabricated
    track reference is provably stripped on the real registry.
    """
    reg = _build_registry_from_fixture()
    snap = reg.snapshot()
    linter = CitationLinter()

    result = linter.check("Reckon that was [track:NONEXISTENT_ID]", snap, mode="live")
    assert result.valid is False
    assert result.reason == "invalid_atoms"
    assert ("track", "NONEXISTENT_ID") in result.missing


def test_mixed_reply_one_hallucinated_atom_strips_whole_reply() -> None:
    """Response-level binary strip: a reply with one REAL atom + one
    hallucinated atom is INVALID as a whole (a single bad atom strips the
    entire utterance). The hallucinated atom is in .missing; the real one
    is NOT — orphans never reach the ear, and the valid atom is still
    surfaced as grounded for telemetry.
    """
    reg = _build_registry_from_fixture()
    snap = reg.snapshot()
    linter = CitationLinter()

    phase_t = next(t for etype, t in _fixture_events() if etype == "PHASE")
    reply = f"Real phase shift [ev:PHASE@{phase_t}] then a ghost [ev:GHOST_EVENT@999.9]"

    result = linter.check(reply, snap, mode="live")
    assert result.valid is False, "one bad atom must strip the WHOLE reply"
    assert result.reason == "invalid_atoms"
    assert ("ev", "GHOST_EVENT@999.9") in result.missing
    assert ("ev", f"PHASE@{phase_t}") not in result.missing


def test_strip_holds_on_nonempty_registry_not_just_empty() -> None:
    """Documents the contract: this proves the airtight strip on a NON-empty
    real registry. test_hype_anti_slop.py strips against an EMPTY registry;
    here real evidence EXISTS (the fixture corpus), yet the hallucinated
    citation is still stripped — the harder, more realistic case.
    """
    reg = _build_registry_from_fixture()
    snap = reg.snapshot()
    # The registry genuinely holds real observations (non-empty).
    assert len(reg) > 0, "this proof requires a NON-empty real registry"
    assert snap.get("ev"), "real ev observations must exist in the snapshot"

    # Yet a fabricated citation is still stripped.
    result = CitationLinter().check(
        "Fabricated banger [ev:GHOST_EVENT@999.9]", snap, mode="live"
    )
    assert result.valid is False
    assert ("ev", "GHOST_EVENT@999.9") in result.missing
