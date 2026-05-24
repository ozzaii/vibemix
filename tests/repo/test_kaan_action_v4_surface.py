# SPDX-License-Identifier: Apache-2.0
"""Phase 58 / Plan 58-03 — KAAN-ACTION-LEGAL.md §SHIP-V4 completeness pin.

REQ-ID: REL-03

Pins the ONE consolidated v4.0 ship surface appended after §SHIP-13 so the
canonical cookbook cannot silently drift away from STATE's open carry-forward
items. Mirrors the structural-pin style of
``tests/repo/test_kaan_action_ship_runbooks.py``.

Asserts:

- The "§SHIP-V4" consolidated section exists (single H2).
- It names EVERY open carry-forward token — Apple (DIST-09), SignPath
  (DIST-11 + INSTALL-COMPANION-SIGN, shared cert), the §E2E-50A-WALK + its
  ``2026-05-walk.webm`` artifact, the 54+55 HUMAN-UAT ear-passes,
  §INSTALL-VM-RUN, §VIS-04 / §VIS-05, §SHIP-CONTACT-VBAUDIO, DEPS-08.
- It cross-references the existing §SHIP-CUT runbook (the literal token
  appears) — does NOT re-write the 9-step sequence.
- It states the public-tag Kaan-confirm (``v0.1.0-rc1`` recommended) and the
  Gate-5b Bravoh precondition (``healthz``).
- The appended copy is anti-slop clean — the AI_SLOP_BLOCKLIST is imported
  from the canonical ``scripts/launch/check_no_ai_slop.py`` (no banned token,
  no ``deeply <word>`` construction).
- It carries a canonical sign-off block (``_____`` placeholder + ``Sign-off
  by`` line).
- The P46 hard rule holds: the section contains no POST/PUT to apple/signpath.

The OPEN_ITEM_TOKENS list is hard-coded to the CURRENT open-item set so that
adding a new open item to STATE without reflecting it here fails this test —
the drift guard.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
KAL = REPO_ROOT / "KAAN-ACTION-LEGAL.md"


def _load_blocklist() -> tuple[str, ...]:
    """Import AI_SLOP_BLOCKLIST from the canonical slop checker.

    Loaded via importlib (the script lives outside the import path) so the
    test stays pinned to the SAME blocklist the launch-copy gate enforces —
    not a hand-copied duplicate that could drift.
    """
    checker = REPO_ROOT / "scripts" / "launch" / "check_no_ai_slop.py"
    assert checker.exists(), f"missing canonical slop checker at {checker}"
    spec = importlib.util.spec_from_file_location("_kal_slop_checker", checker)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    blocklist = getattr(mod, "AI_SLOP_BLOCKLIST")
    assert isinstance(blocklist, tuple) and blocklist
    return blocklist


AI_SLOP_BLOCKLIST: tuple[str, ...] = _load_blocklist()
_DEEPLY_RE = re.compile(r"\bdeeply\s+\w+", re.IGNORECASE)

# Every open carry-forward + the v4.0 ear-pass + the §E2E walk that MUST be
# named in the consolidated surface. Hard-coded = drift guard: a new STATE
# open item without a token here fails the test.
OPEN_ITEM_TOKENS: tuple[str, ...] = (
    "DIST-09",                 # Apple Dev Program Agreement (Francesco)
    "DIST-11",                 # SignPath OSS cert (Windows binary)
    "INSTALL-COMPANION-SIGN",  # SignPath companion signing — SAME shared cert
    "E2E-50A-WALK",            # the real-Mac end-to-end walk (REL-02)
    "2026-05-walk.webm",       # the walk artifact (Gate 6b feed)
    "54-HUMAN-UAT",            # hype ear-pass (Gate 2b feed)
    "55-HUMAN-UAT",            # coach ear-pass (Gate 2b feed)
    "INSTALL-VM-RUN",          # Tart VM 5-OS matrix (carry-forward)
    "VIS-04",                  # Mixamo retargets (parallel asset-discharge)
    "VIS-05",                  # legacy_prep_* retargets (parallel)
    "SHIP-CONTACT-VBAUDIO",    # VB-Audio email (ship-optimization)
    "DEPS-08",                 # livekit-plugins-openai cull (tech-debt)
)


def _body() -> str:
    assert KAL.exists(), f"KAAN-ACTION-LEGAL.md missing at {KAL}"
    return KAL.read_text(encoding="utf-8")


def _ship_v4_section() -> str:
    """Return the §SHIP-V4 section text (H2 → next H2 or EOF)."""
    text = _body()
    m = re.search(
        r"^## §SHIP-V4 — .*?(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert m is not None, "§SHIP-V4 consolidated section not found"
    return m.group(0)


# --------------------------------------------------------------------- #
# Test 1: the consolidated §SHIP-V4 section exists exactly once
# --------------------------------------------------------------------- #
def test_ship_v4_section_exists_once():
    text = _body()
    matches = re.findall(r"^## (§SHIP-V4) — ", text, re.MULTILINE)
    assert matches == ["§SHIP-V4"], (
        f"expected exactly one §SHIP-V4 H2 header; found {matches}"
    )


# --------------------------------------------------------------------- #
# Test 2: every open carry-forward token appears (drift guard)
# --------------------------------------------------------------------- #
def test_lists_every_open_carry_forward():
    sec = _ship_v4_section()
    missing = [tok for tok in OPEN_ITEM_TOKENS if tok not in sec]
    assert not missing, (
        "§SHIP-V4 must name every open carry-forward; missing: "
        f"{missing} (drift away from STATE — add the item to the surface)"
    )


# --------------------------------------------------------------------- #
# Test 3: cross-references the existing §SHIP-CUT runbook (no re-write)
# --------------------------------------------------------------------- #
def test_cross_references_ship_cut():
    sec = _ship_v4_section()
    assert "SHIP-CUT" in sec, (
        "§SHIP-V4 must cross-reference the existing §SHIP-CUT runbook so the "
        "operator's one-button entry point stays single-source"
    )
    # And the ORIGINAL §SHIP-V4 body must NOT duplicate the 9-step sequence
    # verbatim — a light guard: the literal `gh release create` belongs to
    # §SHIP-CUT, not the original cluster body.
    #
    # Exception (Plan 69-05): the appended `### v7.0 OSS-04 autonomous-mode
    # route` sub-section DELIBERATELY pre-stages the verbatim `gh release
    # create v0.1.0-rc1 ...` invocation captured from cut_release.sh stdout,
    # per Phase 69 CONTEXT.md OSS-04 decision. That pre-staging is the entire
    # point of the sub-section — when both external signatures land, no
    # engineering discovery step is left. The guard below scopes the
    # anti-duplication assertion to the original §SHIP-V4 body (up to the
    # v7.0 OSS-04 sub-section); the sub-section itself is regression-pinned
    # by tests/repo/test_ship_v4_section_exists.py (Plan 69-05).
    pre_v7_body = sec.split("### v7.0 OSS-04 autonomous-mode route", 1)[0]
    assert "gh release create" not in pre_v7_body, (
        "§SHIP-V4 original body must point at §SHIP-CUT, not re-type its "
        "publish command (the v7.0 OSS-04 sub-section is the documented "
        "exception — see Plan 69-05)"
    )


# --------------------------------------------------------------------- #
# Test 4: public-tag confirm + Gate-5b Bravoh precondition stated
# --------------------------------------------------------------------- #
def test_states_public_tag_confirm_and_gate_5b():
    sec = _ship_v4_section()
    assert "v0.1.0-rc1" in sec, (
        "§SHIP-V4 must surface the recommended public tag v0.1.0-rc1"
    )
    assert "v4.0.0-rc1" in sec, (
        "§SHIP-V4 must surface the v4.0.0-rc1 one-line override option"
    )
    assert "healthz" in sec, (
        "§SHIP-V4 must state the Gate-5b Bravoh /vibemix/healthz precondition"
    )
    assert "check_bravoh_server_ready.sh" in sec, (
        "§SHIP-V4 must point at the Gate-5b verifier script"
    )


# --------------------------------------------------------------------- #
# Test 5: appended copy is anti-slop clean (canonical blocklist)
# --------------------------------------------------------------------- #
def test_ship_v4_clean_of_ai_slop():
    sec = _ship_v4_section()
    low = sec.lower()
    slop_hits = [tok for tok in AI_SLOP_BLOCKLIST if tok.lower() in low]
    assert not slop_hits, (
        f"AI-slop tokens leaked into §SHIP-V4: {slop_hits}"
    )
    deeply_hits = _DEEPLY_RE.findall(sec)
    assert not deeply_hits, (
        f"'deeply <word>' constructions leaked into §SHIP-V4: {deeply_hits}"
    )


# --------------------------------------------------------------------- #
# Test 6: the section carries a canonical sign-off block
# --------------------------------------------------------------------- #
def test_ship_v4_has_signoff_block():
    sec = _ship_v4_section()
    assert re.search(r"_{5,}", sec), (
        "§SHIP-V4 missing the '_____' sign-off placeholder lines"
    )
    assert "Sign-off by" in sec, (
        "§SHIP-V4 missing the 'Sign-off by' line"
    )


# --------------------------------------------------------------------- #
# Test 7: P46 hard rule — no POST/PUT to apple/signpath in the surface
# --------------------------------------------------------------------- #
def test_ship_v4_no_external_signing_post():
    sec = _ship_v4_section().lower()
    # No curl/gh POST/PUT to apple.com or signpath.{io,org}.
    for endpoint in ("apple.com", "signpath.io", "signpath.org"):
        if endpoint in sec:
            window_re = re.compile(
                r"(?:-x\s*(?:post|put)|curl[^\n]*\b(?:post|put)\b)[^\n]*"
                + re.escape(endpoint)
            )
            assert not window_re.search(sec), (
                f"§SHIP-V4 must not POST/PUT to {endpoint} (P46 hard rule)"
            )
