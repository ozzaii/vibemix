# SPDX-License-Identifier: Apache-2.0
"""Phase 34 / SEC-03 — Rust CVE workflow shape.

Smoke test that the cargo-deny config + workflow files are present and
contain the load-bearing fields. We don't run `cargo audit` here (no Rust
toolchain in pytest path); the workflow itself executes it in CI.
"""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DENY_TOML = REPO_ROOT / "tauri/src-tauri/deny.toml"
WORKFLOW = REPO_ROOT / ".github/workflows/rust-cve.yml"


def test_deny_toml_exists():
    assert DENY_TOML.exists()


def test_deny_toml_has_advisories_section():
    txt = DENY_TOML.read_text(encoding="utf-8")
    assert "[advisories]" in txt
    assert "yanked" in txt


def test_deny_toml_denies_unknown_sources():
    txt = DENY_TOML.read_text(encoding="utf-8")
    assert 'unknown-registry = "deny"' in txt
    assert 'unknown-git = "deny"' in txt


def test_deny_toml_allows_apache_and_mit():
    txt = DENY_TOML.read_text(encoding="utf-8")
    assert '"Apache-2.0"' in txt
    assert '"MIT"' in txt


def test_rust_cve_workflow_invokes_severity_gate():
    txt = WORKFLOW.read_text(encoding="utf-8")
    assert "severity_gate.py" in txt
    assert "--cargo-audit" in txt


def test_rust_cve_workflow_pins_versions():
    txt = WORKFLOW.read_text(encoding="utf-8")
    assert "cargo-audit --version 0.20.1" in txt
    assert "cargo-deny --version 0.16.2" in txt


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
