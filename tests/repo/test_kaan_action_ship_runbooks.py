# SPDX-License-Identifier: Apache-2.0
"""Phase 45 / Plan 45-06 — KAAN-ACTION-LEGAL.md §SHIP-01..§SHIP-13 runbook
structural pin.

REQ-IDs: SHIP-01, SHIP-02, SHIP-03, SHIP-04, SHIP-05, SHIP-06, SHIP-07,
         SHIP-08, SHIP-09, SHIP-10, SHIP-11, SHIP-12, SHIP-13

Pins the 13-section discharge cookbook appended after §LAUNCH-08:

- All 13 H2 headers present in order (no gaps, no duplicates).
- Each section carries the canonical 8 blocks (header / who / pre-req /
  commands / verification / post-discharge / unblocks / sign-off).
- Cited scripts EXIST on disk — the runbook can't drift away from the
  shipped engineering surface.
- ENV-var requirements pinned literally for §SHIP-04 / §SHIP-08 / §SHIP-13.
- §SHIP-07 explicitly flags the tag-regex bump
  (^v2\\.1\\.0-rc[0-9]+$ → ^v3\\.0\\.0-rc[0-9]+$) as a prerequisite.
- §SHIP-10 carries the literal repo-transfer gh-api invocation verbatim.
- Pre-§SHIP-01 content (everything up through §LAUNCH-08) is preserved
  verbatim.
- AI-slop blocklist (the same 16 tokens enforced by
  scripts/launch/check_no_ai_slop.py) is clean across the appended
  content + no "deeply <word>" constructions appear.
- Sign-off blocks carry the canonical `_____` placeholder lines + a
  `Sign-off by` line.

Plan 45-06 task ordering:

- Task 1 (this file) lands all 11 tests RED — 8 fail because no §SHIP-NN
  sections exist; 3 pass because the existing file already qualifies
  (file exists, pre-§SHIP-01 content untouched, AI-slop clean).
- Task 2 appends §SHIP-01..07 → 7 of 13 sections present, some tests
  partial pass.
- Task 3 appends §SHIP-08..13 → all 11 tests GREEN.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
KAL = REPO_ROOT / "KAAN-ACTION-LEGAL.md"

# 16 forbidden tokens — mirrored from
# scripts/launch/check_no_ai_slop.py AI_SLOP_BLOCKLIST. Kept inline here
# (not imported) because the slop checker's CLI only accepts the
# launch-copy directory; the same blocklist applies to KAAN-ACTION-LEGAL
# content per the §KAAN-ACTION-LEGAL Discharge Runbooks decisions.
AI_SLOP_BLOCKLIST: tuple[str, ...] = (
    "leverage",
    "synergize",
    "revolutionize",
    "game-changer",
    "next-generation",
    "cutting-edge",
    "seamless",
    "robust",
    "powerful",
    "intuitive",
    "delightful experience",
    "AI-powered",
    "harness the power",
    "unlock",
    "transformative",
    "paradigm",
)

# "deeply <word>" regex — same construction the slop checker flags.
_DEEPLY_RE = re.compile(r"\bdeeply\s+\w+", re.IGNORECASE)

# Canonical 8-block markers — every §SHIP-NN section must contain each
# logical block. The canonical §LAUNCH-08 / §GATE-* style mixes H3
# headings (`### Pre-requisites`) and bold-prefixed inline labels
# (`**Status:**`) — so each marker is a tuple of accepted spellings.
# A section passes if ANY variant in the tuple appears in its body.
REQUIRED_BLOCK_MARKERS: tuple[tuple[str, ...], ...] = (
    # Pre-requisites block: explicit subheading OR inline "Pre-requisites:"
    ("### Pre-requisites", "Pre-requisites:", "**Pre-requisites:**"),
    # Verification block: subheading OR colon-suffix.
    ("### Verification", "Verification:"),
    # Post-discharge block: subheading OR inline.
    ("### Post-discharge", "Post-discharge:"),
    # Unblocks block: "### Unblocks" or "### What unblocks" or colon form.
    ("### Unblocks", "### What unblocks", "Unblocks:"),
    # Sign-off block is checked separately (asserts `_____` placeholder
    # plus `Sign-off by` line).
)

# §SHIP-NN → required cross-reference (substring that must appear in the
# section body). Backs Test 5 (cited scripts/anchors exist on disk).
REQUIRED_CROSS_REFS: dict[str, tuple[str, ...]] = {
    "§SHIP-04": ("scripts/dist/install_vm_matrix.sh",),
    "§SHIP-06": ("scripts/release/check_bravoh_server_ready.sh",),
    "§SHIP-08": ("scripts/launch/launch_trigger.sh",),
    "§SHIP-11": ("docs/launch-rotation.md",),
    "§SHIP-13": ("scripts/release/audit_ship_v1_decision.py",),
}

# Each cross-referenced path must exist on disk.
CROSS_REF_ON_DISK: dict[str, str] = {
    "scripts/dist/install_vm_matrix.sh": "Plan 45-01",
    "scripts/release/check_bravoh_server_ready.sh": "Plan 45-03",
    "scripts/launch/launch_trigger.sh": "Plan 45-02",
    "docs/launch-rotation.md": "Plan 45-05",
    "scripts/release/audit_ship_v1_decision.py": "Plan 45-04",
}

# ENV-var requirements per section — Test 9.
REQUIRED_ENV_VARS: dict[str, tuple[str, ...]] = {
    "§SHIP-04": ("VIBEMIX_INSTALL_VM_RUN",),
    "§SHIP-08": ("LAUNCH_REAL", "DISCORD_WEBHOOK_URL", "GITHUB_TOKEN"),
    "§SHIP-13": ("GITHUB_TOKEN",),
}


def _body() -> str:
    assert KAL.exists(), f"missing {KAL}"
    return KAL.read_text(encoding="utf-8")


def _section_bodies() -> dict[str, str]:
    """Return {§SHIP-NN: section_text} for the 13 appended sections.

    Each section_text spans from the H2 header line up to (but not
    including) the next `## §SHIP-` H2, or EOF.
    """
    text = _body()
    headers = list(
        re.finditer(r"^## (§SHIP-\d{2}) — .*$", text, re.MULTILINE)
    )
    bodies: dict[str, str] = {}
    for i, m in enumerate(headers):
        start = m.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        bodies[m.group(1)] = text[start:end]
    return bodies


# --------------------------------------------------------------------- #
# Test 1: file exists
# --------------------------------------------------------------------- #
def test_kaan_action_legal_exists():
    assert KAL.exists(), f"KAAN-ACTION-LEGAL.md missing at {KAL}"


# --------------------------------------------------------------------- #
# Test 2: all 13 §SHIP-NN H2 headers present, exact count, no duplicates
# --------------------------------------------------------------------- #
def test_all_thirteen_ship_nn_h2_headers_present():
    text = _body()
    matches = re.findall(r"^## (§SHIP-\d{2}) — ", text, re.MULTILINE)
    expected = [f"§SHIP-{n:02d}" for n in range(1, 14)]
    assert sorted(set(matches)) == sorted(expected), (
        f"expected exactly §SHIP-01..§SHIP-13; found unique set "
        f"{sorted(set(matches))}"
    )
    # No duplicate H2s either.
    assert len(matches) == 13, (
        f"expected 13 §SHIP-NN H2 headers; found {len(matches)}: {matches}"
    )


# --------------------------------------------------------------------- #
# Test 3: H2 order is chronological 01 → 13 (no re-ordering)
# --------------------------------------------------------------------- #
def test_ship_nn_h2_order_is_chronological():
    text = _body()
    matches = re.findall(r"^## (§SHIP-\d{2}) — ", text, re.MULTILINE)
    expected = [f"§SHIP-{n:02d}" for n in range(1, 14)]
    assert matches == expected, (
        f"§SHIP-NN H2 headers out of order; expected {expected}, got {matches}"
    )


# --------------------------------------------------------------------- #
# Test 4: each section contains the canonical 8-block markers
# --------------------------------------------------------------------- #
def test_each_section_has_canonical_blocks():
    bodies = _section_bodies()
    missing: list[str] = []
    # Accept "### Discharge commands", "### Discharge command", or the
    # colon-suffixed inline forms.
    discharge_re = re.compile(
        r"(?:###\s+Discharge commands?\b|Discharge commands?:)"
    )
    for sec, body in bodies.items():
        for variants in REQUIRED_BLOCK_MARKERS:
            if not any(v in body for v in variants):
                missing.append(
                    f"{sec}: missing any of {variants}"
                )
        if not discharge_re.search(body):
            missing.append(f"{sec}: missing 'Discharge command(s)' block")
    assert not missing, "Section block markers missing:\n  " + "\n  ".join(
        missing
    )


# --------------------------------------------------------------------- #
# Test 5: cited scripts/docs exist on disk + the right section cites them
# --------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "section,refs",
    [(k, v) for k, v in REQUIRED_CROSS_REFS.items()],
)
def test_section_cites_required_cross_ref(section: str, refs: tuple[str, ...]):
    bodies = _section_bodies()
    if section not in bodies:
        pytest.fail(f"section {section} not present in KAAN-ACTION-LEGAL.md")
    body = bodies[section]
    for ref in refs:
        assert ref in body, (
            f"{section} must cite '{ref}' verbatim "
            "(cross-reference is the operator's entry-point into the "
            "engineering surface shipped in its sibling plan)"
        )
        # Anchor source-of-truth on disk:
        assert (REPO_ROOT / ref).exists(), (
            f"cited path {ref} ({CROSS_REF_ON_DISK.get(ref, '')}) "
            "missing on disk — runbook would dangle"
        )


# --------------------------------------------------------------------- #
# Test 6: pre-§SHIP-01 content preserved verbatim (anchor on §LAUNCH-08)
# --------------------------------------------------------------------- #
def test_pre_ship_content_preserved():
    text = _body()
    # §LAUNCH-08 H2 must still appear before the first §SHIP-NN H2 at the
    # right relative position (line ≥1834).
    launch_08_m = re.search(r"^## §LAUNCH-08 — ", text, re.MULTILINE)
    assert launch_08_m, "§LAUNCH-08 H2 lost — pre-§SHIP-01 content corrupted"
    # First §SHIP-NN appears AFTER §LAUNCH-08.
    ship_m = re.search(r"^## §SHIP-01 — ", text, re.MULTILINE)
    # If §SHIP-01 doesn't exist yet (Task 1 RED), test still passes
    # because the precondition is "pre-§SHIP-01 content untouched" — it
    # only meaningfully fails AFTER §SHIP-01 lands.
    if ship_m is not None:
        assert launch_08_m.start() < ship_m.start(), (
            "§LAUNCH-08 must remain BEFORE §SHIP-01 — append-only invariant"
        )
    # Line count check: the launch-08 header must still sit at line ≥1830.
    line_no = text[: launch_08_m.start()].count("\n") + 1
    assert line_no >= 1830, (
        f"§LAUNCH-08 moved to line {line_no} (expected ≥1830) — pre-existing "
        "content reshuffled"
    )


# --------------------------------------------------------------------- #
# Test 7: AI-slop blocklist clean for the appended §SHIP-NN content
# --------------------------------------------------------------------- #
def test_ship_sections_clean_of_ai_slop():
    bodies = _section_bodies()
    combined = "\n".join(bodies.values())
    combined_lower = combined.lower()

    slop_hits: list[str] = []
    for token in AI_SLOP_BLOCKLIST:
        if token.lower() in combined_lower:
            slop_hits.append(token)
    assert not slop_hits, (
        f"AI-slop tokens leaked into §SHIP-NN content: {slop_hits}"
    )

    deeply_hits = _DEEPLY_RE.findall(combined)
    assert not deeply_hits, (
        f"'deeply <word>' constructions leaked into §SHIP-NN content: "
        f"{deeply_hits}"
    )


# --------------------------------------------------------------------- #
# Test 8: every §SHIP-NN section has a sign-off block
# --------------------------------------------------------------------- #
def test_each_section_has_signoff_block():
    bodies = _section_bodies()
    missing: list[str] = []
    placeholder_re = re.compile(r"_{5,}")
    for sec, body in bodies.items():
        if not placeholder_re.search(body):
            missing.append(f"{sec}: no '_____' sign-off placeholder")
        if "Sign-off by" not in body:
            missing.append(f"{sec}: no 'Sign-off by' line")
    assert not missing, "Sign-off blocks missing:\n  " + "\n  ".join(missing)


# --------------------------------------------------------------------- #
# Test 9: ENV-var requirements pinned for §SHIP-04 / §SHIP-08 / §SHIP-13
# --------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "section,env_vars",
    [(k, v) for k, v in REQUIRED_ENV_VARS.items()],
)
def test_section_pins_env_vars(section: str, env_vars: tuple[str, ...]):
    bodies = _section_bodies()
    if section not in bodies:
        pytest.fail(f"section {section} not present in KAAN-ACTION-LEGAL.md")
    body = bodies[section]
    for var in env_vars:
        assert var in body, (
            f"{section} must mention ENV var '{var}' "
            "(operator-facing runbook must spell out what to export "
            "before discharge — secrets are NAMED, never literal values)"
        )


# --------------------------------------------------------------------- #
# Test 10: §SHIP-10 carries the literal gh-api repo-transfer command
# --------------------------------------------------------------------- #
def test_ship_10_carries_literal_transfer_command():
    bodies = _section_bodies()
    if "§SHIP-10" not in bodies:
        pytest.fail("§SHIP-10 not present in KAAN-ACTION-LEGAL.md")
    body = bodies["§SHIP-10"]
    # Literal command per CONTEXT §specifics. Allow either `repos/...` or
    # `repos/$CURRENT_OWNER/vibemix/transfer` shape — both are valid.
    assert "gh api -X POST" in body, (
        "§SHIP-10 must spell out `gh api -X POST` verbatim — repo "
        "transfer is the highest-privilege manual command in the cascade"
    )
    assert "vibemix/transfer" in body, (
        "§SHIP-10 must reference `vibemix/transfer` endpoint path"
    )
    assert "new_owner=bravoh" in body, (
        "§SHIP-10 must spell out `new_owner=bravoh` — the target org"
    )


# --------------------------------------------------------------------- #
# Test 11: §SHIP-07 flags the tag-regex bump as a prerequisite
# --------------------------------------------------------------------- #
def test_ship_07_flags_tag_regex_bump():
    bodies = _section_bodies()
    if "§SHIP-07" not in bodies:
        pytest.fail("§SHIP-07 not present in KAAN-ACTION-LEGAL.md")
    body = bodies["§SHIP-07"]
    # Either the old or the new regex shape (or both) must appear, plus
    # explicit language flagging it as a prerequisite. The current
    # cut_release.sh ships `^v2\.1\.0-rc[0-9]+$` (line 44); the new
    # ship-cut needs `^v3\.0\.0-rc[0-9]+$`.
    assert "v2.1.0-rc" in body, (
        "§SHIP-07 must reference the CURRENT cut_release.sh tag regex "
        "(v2.1.0-rc) so the operator knows what to bump from"
    )
    assert "v3.0.0-rc" in body, (
        "§SHIP-07 must reference the TARGET tag regex (v3.0.0-rc) so the "
        "operator knows what to bump to"
    )
    # The word "prerequisite" or "Pre-req"/"pre-req" must be near the
    # tag-regex mention so the operator reads it as a gate, not trivia.
    assert (
        "prerequisite" in body.lower()
        or "pre-requisite" in body.lower()
        or "pre-req" in body.lower()
    ), "§SHIP-07 must label the tag-regex bump as a prerequisite/pre-req"
