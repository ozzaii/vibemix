"""DEPS-09 — assert the 4 dep-health badges are present in README.md
with the expected shield URLs + GitHub workflow links."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
README = REPO / "README.md"

REQUIRED_BADGE_LABELS = (
    "uv%20lock",
    "cargo-deny",
    "npm-audit",
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
