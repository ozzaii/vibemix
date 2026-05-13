"""OSS hygiene gate — Phase 19 Plan 19-02.

Ensures the required hygiene files exist with the required sections,
issue templates are valid YAML, and the NOTICE file is current.
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[2]


REQUIRED_FILES = [
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "NOTICE",
    "TRADEMARKS.md",
    "LICENSE",
]

REQUIRED_ISSUE_TEMPLATES = [
    "bug_report.yml",
    "feature_request.yml",
    "new_controller.yml",
    "config.yml",
]


@pytest.mark.parametrize("filename", REQUIRED_FILES)
def test_hygiene_file_exists(filename: str) -> None:
    path = REPO_ROOT / filename
    assert path.exists(), f"{filename} missing — required by Phase 19 GH-13/14"
    assert path.stat().st_size > 100, f"{filename} suspiciously small"


def test_contributing_mentions_dco() -> None:
    text = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "DCO" in text or "Developer Certificate of Origin" in text
    assert "git commit -s" in text or "Signed-off-by" in text


def test_security_has_contact() -> None:
    text = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "security@bravoh.com" in text
    assert "90 day" in text.lower() or "90-day" in text.lower() or "90 days" in text


def test_trademarks_lists_third_parties() -> None:
    text = (REPO_ROOT / "TRADEMARKS.md").read_text(encoding="utf-8")
    for vendor in ["Pioneer", "Numark", "Hercules", "Apple", "Microsoft", "Google"]:
        assert vendor in text, f"TRADEMARKS.md missing {vendor}"


def test_code_of_conduct_references_covenant() -> None:
    text = (REPO_ROOT / "CODE_OF_CONDUCT.md").read_text(encoding="utf-8")
    assert "Contributor Covenant" in text
    assert "ozai@bravoh.com" in text


@pytest.mark.parametrize("template", REQUIRED_ISSUE_TEMPLATES)
def test_issue_template_exists(template: str) -> None:
    path = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / template
    assert path.exists(), f".github/ISSUE_TEMPLATE/{template} missing"


@pytest.mark.skipif(yaml is None, reason="pyyaml not installed")
@pytest.mark.parametrize("template", REQUIRED_ISSUE_TEMPLATES)
def test_issue_template_parses(template: str) -> None:
    path = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / template
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
    assert isinstance(parsed, dict), f"{template} did not parse as a YAML mapping"


def test_pr_template_exists() -> None:
    path = REPO_ROOT / ".github" / "pull_request_template.md"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "DCO" in text or "Signed-off-by" in text or "git commit -s" in text


def test_notice_passes_gen_notice_check() -> None:
    import subprocess

    result = subprocess.run(
        ["python3", "-m", "scripts.dist.gen_notice", "--check"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, (
        f"gen_notice --check failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
