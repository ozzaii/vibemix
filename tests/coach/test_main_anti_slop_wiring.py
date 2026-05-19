# SPDX-License-Identifier: Apache-2.0
"""Plan 20-05 — source-grep assertions over `src/vibemix/__main__.py` that
lock the Phase 20 anti-slop runtime wiring contract.

We use AST-level / source-grep inspection — mirrors `test_smoke_07/08` from
`tests/test_main_smoke.py` (Plan 19-05 wiring assertions). Three reasons we
can't drive `main()` end-to-end and assert on the agent kwargs at runtime:

1. The pre-existing baseline carries 3 failing smoke tests (`smoke_03/04/05`)
   that prevent main() teardown from running cleanly — locking wiring at the
   AST level keeps the contract pinned even when the live-runtime harness is
   broken.
2. The wired path actually fires inside ``DJCoHostAgent.__init__`` /
   ``coach_loop`` only when the corresponding kwargs are non-None — a unit
   test that drives main() to teardown would re-trigger every Phase 19-05
   teardown bug. AST grep is the surgical contract.
3. The 33 unit + 7 integration tests in `tests/agent/test_dj_cohost_*` already
   verify the wired-path BEHAVIOR. This file's job is to verify the WIRING
   at the __main__.py call site.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def main_src() -> str:
    """Read ``src/vibemix/__main__.py`` exactly once per test module."""
    return Path("src/vibemix/__main__.py").read_text()


# ---------------------------------------------------------------------------
# Task 20-05-01 — linter + tracker + registry imports & construction
# ---------------------------------------------------------------------------


def test_wire01_imports_citation_linter_and_stripped_rate_tracker(
    main_src: str,
) -> None:
    """W01: __main__.py imports CitationLinter AND StrippedRateTracker from
    vibemix.coach."""
    assert "CitationLinter" in main_src, "CitationLinter import missing"
    assert "StrippedRateTracker" in main_src, "StrippedRateTracker import missing"
    # Both should be on a single coach-import line OR two separate lines.
    assert (
        "from vibemix.coach import" in main_src
        or "from vibemix.coach " in main_src
    ), "Expected `from vibemix.coach import` style import"


def test_wire02_imports_evidence_registry(main_src: str) -> None:
    """W02: __main__.py imports EvidenceRegistry from vibemix.state — required
    so the linter has a non-None snapshot to validate against (otherwise
    linter strips every response with reason='no_citations')."""
    assert "EvidenceRegistry" in main_src, "EvidenceRegistry import missing"


def test_wire03_constructs_citation_linter(main_src: str) -> None:
    """W03: __main__.py constructs CitationLinter() at startup."""
    assert "CitationLinter()" in main_src, "CitationLinter() not instantiated"


def test_wire04_constructs_stripped_rate_tracker(main_src: str) -> None:
    """W04: __main__.py constructs StrippedRateTracker() (either no-args or
    kwarg form — the constants module supplies the defaults)."""
    assert re.search(
        r"StrippedRateTracker\s*\(", main_src
    ), "StrippedRateTracker() not instantiated"


def test_wire05_constructs_evidence_registry(main_src: str) -> None:
    """W05: __main__.py constructs EvidenceRegistry() at startup so
    state_refresh_loop + EventDetector can write observations + the
    agent's snapshot is non-empty."""
    assert "EvidenceRegistry()" in main_src, "EvidenceRegistry() not instantiated"


# ---------------------------------------------------------------------------
# Task 20-05-01 — DJCoHostAgent kwargs
# ---------------------------------------------------------------------------


def test_wire06_dj_cohost_agent_receives_citation_linter_kwarg(
    main_src: str,
) -> None:
    """W06: DJCoHostAgent(...) call contains citation_linter= kwarg."""
    assert "citation_linter=" in main_src, (
        "DJCoHostAgent must receive citation_linter= kwarg"
    )


def test_wire07_dj_cohost_agent_receives_stripped_rate_tracker_kwarg(
    main_src: str,
) -> None:
    """W07: DJCoHostAgent(...) call contains stripped_rate_tracker= kwarg."""
    assert "stripped_rate_tracker=" in main_src, (
        "DJCoHostAgent must receive stripped_rate_tracker= kwarg"
    )


def test_wire08_ack_bank_retired_from_main(main_src: str) -> None:
    """W08: The placeholder ack-bank surface (pre-recorded "yeah/oh/nice"
    OPUS clips) was retired alongside the cohost_v3/v4 POC reference. No
    AckBank construction, import, or kwarg threading must remain in
    main()."""
    assert "AckBank" not in main_src, (
        "AckBank reference leaked back into __main__.py — the placeholder "
        "ack-bank surface is retired (English clips fought the Turkish "
        "persona + anti-slop thesis)"
    )
    assert "ack_bank=" not in main_src, (
        "ack_bank=... kwarg leaked back into __main__.py wiring"
    )


def test_wire09_dj_cohost_agent_receives_playback_kwarg(main_src: str) -> None:
    """W09: DJCoHostAgent(...) call contains playback=playback kwarg.

    `playback=playback` appears twice in the file (BufferRegistry
    constructor + DJCoHostAgent constructor). Pre-ack-bank-retirement
    coach_loop also got the same instance; coach_loop no longer needs
    it, so two occurrences is the new minimum.
    """
    assert main_src.count("playback=playback") >= 2, (
        "playback=playback must appear in DJCoHostAgent(...) "
        "in ADDITION to BufferRegistry(...)"
    )


def test_wire10_dj_cohost_agent_receives_evidence_registry_kwarg(
    main_src: str,
) -> None:
    """W10: DJCoHostAgent(...) call contains evidence_registry=... kwarg.
    Without this the agent's per-turn snapshot would be None and every
    response would strip with reason='no_citations'."""
    assert "evidence_registry=" in main_src, (
        "DJCoHostAgent must receive evidence_registry= kwarg"
    )


def test_wire11_state_refresh_loop_receives_evidence_registry(
    main_src: str,
) -> None:
    """W11: state_refresh_loop(...) call contains
    evidence_registry=evidence_registry — required so the registry actually
    gets observations written into it. Without this, the registry is empty
    and the linter strips everything."""
    # state_refresh_loop kwarg shows up in the asyncio.create_task call.
    # We check that evidence_registry appears within ~600 chars of
    # "state_refresh_loop(" to disambiguate from the agent kwarg usage.
    idx = main_src.find("state_refresh_loop(")
    assert idx != -1, "state_refresh_loop(...) call missing"
    window = main_src[idx : idx + 600]
    assert "evidence_registry=evidence_registry" in window, (
        "state_refresh_loop must be invoked with evidence_registry=evidence_registry"
    )


# ---------------------------------------------------------------------------
# Task 20-05-01 — VIBEMIX_ANTI_SLOP env flag
# ---------------------------------------------------------------------------


def test_wire12_env_var_vibemix_anti_slop_read(main_src: str) -> None:
    """W12: __main__.py reads VIBEMIX_ANTI_SLOP env var with normalization."""
    assert "VIBEMIX_ANTI_SLOP" in main_src, "VIBEMIX_ANTI_SLOP env var not read"
    # Normalization pattern — at least `.strip().lower()` somewhere in the read.
    # Use a forgiving regex so a chain like `os.environ.get("VIBEMIX_ANTI_SLOP", "on").strip().lower()`
    # passes.
    assert ".strip().lower()" in main_src, (
        "VIBEMIX_ANTI_SLOP must be normalized via .strip().lower()"
    )


def test_wire13_anti_slop_disabled_path_passes_none_kwargs(main_src: str) -> None:
    """W13: When VIBEMIX_ANTI_SLOP is off, the linter primitives are None.
    Source contains a conditional `if anti_slop_enabled else None` pattern
    OR equivalent — verifies the disable branch exists at the construction
    site, not just a conditional banner print."""
    # Accept any of: `if anti_slop_enabled else None`,
    # `CitationLinter() if anti_slop_enabled else None`,
    # or a multi-line `if/else` block that assigns None.
    pattern = re.compile(
        r"CitationLinter\(\)\s+if\s+anti_slop_enabled\s+else\s+None"
    )
    assert pattern.search(main_src), (
        "CitationLinter must be conditionally constructed: "
        "`CitationLinter() if anti_slop_enabled else None`"
    )


def test_wire14_anti_slop_banner_printed(main_src: str) -> None:
    """W14: A startup banner reports the anti-slop dispatch decision so
    Kaan sees on/off in the terminal at boot."""
    # The exact banner text is implementation detail — check for the
    # "-> anti-slop:" prefix which matches the existing v4-style banner
    # convention (`-> tts:`, `-> brain:`, `-> cache:`).
    assert "-> anti-slop:" in main_src, "Anti-slop boot banner missing"


# ---------------------------------------------------------------------------
# Task 20-05-01 — construction order (linter created BEFORE agent)
# ---------------------------------------------------------------------------


def test_wire15_linter_primitives_constructed_before_agent(main_src: str) -> None:
    """W15: CitationLinter / StrippedRateTracker / EvidenceRegistry are
    constructed BEFORE the DJCoHostAgent(...) call site. Required so the
    agent receives instantiated objects, not None."""
    linter_idx = main_src.find("CitationLinter()")
    tracker_idx = main_src.find("StrippedRateTracker(")
    registry_idx = main_src.find("EvidenceRegistry()")
    agent_idx = main_src.find("DJCoHostAgent(")
    assert linter_idx != -1 and tracker_idx != -1 and registry_idx != -1, (
        "Linter primitives not all constructed"
    )
    assert agent_idx != -1, "DJCoHostAgent(...) call missing"
    assert linter_idx < agent_idx, "CitationLinter() must precede DJCoHostAgent("
    assert tracker_idx < agent_idx, "StrippedRateTracker() must precede DJCoHostAgent("
    assert registry_idx < agent_idx, "EvidenceRegistry() must precede DJCoHostAgent("
