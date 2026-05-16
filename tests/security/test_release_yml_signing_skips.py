# SPDX-License-Identifier: Apache-2.0
"""Phase 38 / DIST-15 + DIST-16 — release.yml empty-secret skip annotations.

Confirms that the Apple notarytool + SignPath legs of release.yml carry the
empty-secret skip pattern (CONTEXT §Apple notarytool wiring + §SignPath wiring).

The actual sign steps are gated on `SIGNING_AVAILABLE == 'true'`. Phase 38 adds
EXPLICIT annotation steps that fire on the inverse condition and emit
`::warning::` lines pointing at KAAN-ACTION-LEGAL.md.

These tests parse the workflow YAML and assert structure — no `act`/`gh`
execution required.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    import yaml  # PyYAML — listed as a test-time dep in conftest
except ImportError:  # pragma: no cover
    yaml = None


REPO_ROOT = Path(__file__).resolve().parents[2]
RELEASE_YML = REPO_ROOT / ".github/workflows/release.yml"


@pytest.fixture(scope="module")
def workflow_text() -> str:
    return RELEASE_YML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def workflow_yaml(workflow_text: str):
    if yaml is None:
        pytest.skip("PyYAML not installed")
    # The workflow has the GitHub Actions `on:` key which YAML coerces to True.
    return yaml.safe_load(workflow_text)


# ---------------------------------------------------------------------------
# 38-01 — Apple notarytool wiring annotation
# ---------------------------------------------------------------------------

def test_release_yml_apple_skip_step_exists(workflow_text: str):
    """The Apple-leg empty-secret annotation step must exist by name."""
    assert "SIGN — Apple notarytool wiring annotation (empty-secret skip)" in workflow_text


def test_release_yml_notarytool_invocation_present(workflow_text: str):
    """The actual notarytool invocation must still be wired (via sign_macos.sh)."""
    # sign_macos.sh is the canonical entrypoint; the comment header in release.yml
    # explicitly names notarytool.
    assert "notarytool" in workflow_text
    assert "scripts/dist/sign_macos.sh" in workflow_text


def test_release_yml_apple_sign_step_guarded_by_signing_available(workflow_yaml):
    """The SIGN+PACKAGE step on macOS MUST be guarded by SIGNING_AVAILABLE."""
    build_macos = workflow_yaml["jobs"]["build-macos"]
    steps = build_macos["steps"]
    sign_step = next(
        (s for s in steps if "SIGN + PACKAGE" in s.get("name", "")),
        None,
    )
    assert sign_step is not None, "SIGN + PACKAGE step not found"
    assert sign_step["if"] == "env.SIGNING_AVAILABLE == 'true' && env.DRY_RUN != 'true'"


def test_release_yml_skip_on_empty_apple_secret(workflow_yaml):
    """The Apple annotation step fires on the inverse condition."""
    build_macos = workflow_yaml["jobs"]["build-macos"]
    steps = build_macos["steps"]
    skip_step = next(
        (s for s in steps if "Apple notarytool wiring annotation" in s.get("name", "")),
        None,
    )
    assert skip_step is not None, "Apple notarytool wiring annotation step missing"
    assert skip_step["if"] == "env.SIGNING_AVAILABLE != 'true'"
    # The step must reference KAAN-ACTION-LEGAL.md so operators can find the runbook.
    assert "KAAN-ACTION-LEGAL.md" in skip_step["run"]
    assert "DIST-09" in skip_step["run"]


# ---------------------------------------------------------------------------
# 38-02 — SignPath wiring annotation (filled in by Plan 38-02)
# ---------------------------------------------------------------------------

def test_release_yml_signpath_skip_step_exists(workflow_text: str):
    assert "SIGN — SignPath wiring annotation (empty-secret skip)" in workflow_text


def test_release_yml_signpath_action_pinned_version(workflow_text: str):
    """The SignPath GH Action must be pinned to a version (not @main)."""
    m = re.search(
        r"uses:\s*signpath/github-action-submit-signing-request@(\S+)",
        workflow_text,
    )
    assert m is not None, "SignPath GH Action reference not found"
    version = m.group(1)
    assert version.startswith("v"), f"SignPath action not pinned to a vN.N.N tag: {version}"


def test_release_yml_signpath_sign_step_guarded_by_signing_available(workflow_yaml):
    build_windows = workflow_yaml["jobs"]["build-windows"]
    steps = build_windows["steps"]
    sign_step = next(
        (s for s in steps if "Submit signing request to SignPath" in s.get("name", "")),
        None,
    )
    assert sign_step is not None, "SignPath submission step missing"
    assert sign_step["if"] == "env.SIGNING_AVAILABLE == 'true' && env.DRY_RUN != 'true'"


def test_release_yml_skip_on_empty_signpath_secret(workflow_yaml):
    """The SignPath annotation step fires on the inverse condition."""
    build_windows = workflow_yaml["jobs"]["build-windows"]
    steps = build_windows["steps"]
    skip_step = next(
        (s for s in steps if "SignPath wiring annotation" in s.get("name", "")),
        None,
    )
    assert skip_step is not None, "SignPath wiring annotation step missing"
    assert skip_step["if"] == "env.SIGNING_AVAILABLE != 'true'"
    assert "KAAN-ACTION-LEGAL.md" in skip_step["run"]
    assert "DIST-11" in skip_step["run"]


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
