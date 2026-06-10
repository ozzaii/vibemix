"""DEPS-09 — assert the dep-health badges are present in README.md
with the expected shield URLs + GitHub workflow links.

The 2026-06-04 README de-slop (23bd6c0e) deliberately consolidated the
original 4-badge block to 2: the per-job cargo-deny / npm-audit badges
were dropped because all three dep jobs run in the SAME dep-audit.yml
workflow — the surviving "uv lock" badge's shields.io workflow-status URL
already goes red when cargo-deny or npm-audit fails. The jobs themselves
are unchanged (DEPS-01/02/03 in .github/workflows/dep-audit.yml)."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
README = REPO / "README.md"

REQUIRED_BADGE_LABELS = (
    "uv%20lock",
    "CycloneDX",
)

REQUIRED_WORKFLOW_LINKS = (
    "dep-audit.yml",
    "sbom.yml",
)


def test_readme_exists():
    assert README.is_file(), f"missing {README}"


def test_all_required_badge_labels_present():
    text = README.read_text()
    missing = [label for label in REQUIRED_BADGE_LABELS if label not in text]
    assert not missing, f"missing dep-health badge labels: {missing}"


def test_badges_link_to_workflow_files():
    text = README.read_text()
    missing = [w for w in REQUIRED_WORKFLOW_LINKS if w not in text]
    assert not missing, f"missing workflow file links: {missing}"


def test_badge_block_uses_shields_io_actions_endpoint():
    text = README.read_text()
    m = re.search(r"img\.shields\.io/github/actions/workflow/status", text)
    assert m is not None, "DEPS-09: badge URLs must use the shields.io actions/workflow endpoint"
