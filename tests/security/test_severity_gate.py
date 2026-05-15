# SPDX-License-Identifier: Apache-2.0
"""Phase 34 / SEC-02 — severity-gate matrix tests.

Pitfall P65 — LOW/MEDIUM must NOT fail the build; HIGH-direct MUST fail;
CRITICAL-anywhere MUST fail.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = REPO_ROOT / "scripts/dist/severity_gate.py"


@pytest.fixture(scope="module")
def gate_mod():
    spec = importlib.util.spec_from_file_location("severity_gate", GATE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["severity_gate"] = mod
    spec.loader.exec_module(mod)
    return mod


def _write(tmp_path: Path, name: str, payload) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Direct/transitive matrix
# ---------------------------------------------------------------------------

def test_high_on_direct_fails(gate_mod, tmp_path):
    direct = {"numpy"}
    payload = {"dependencies": [
        {"name": "numpy", "vulns": [{"id": "GHSA-foo", "severity": "HIGH"}]}
    ]}
    p = _write(tmp_path, "pa.json", payload)
    findings = gate_mod.parse_findings_payload(p, "pip-audit", direct)
    failing, _ = gate_mod.apply_gate(findings)
    assert len(failing) == 1
    assert failing[0].direct


def test_high_on_transitive_warns_only(gate_mod, tmp_path):
    direct: set[str] = set()  # numpy treated as transitive
    payload = {"dependencies": [
        {"name": "numpy", "vulns": [{"id": "GHSA-foo", "severity": "HIGH"}]}
    ]}
    p = _write(tmp_path, "pa.json", payload)
    findings = gate_mod.parse_findings_payload(p, "pip-audit", direct)
    failing, warnings = gate_mod.apply_gate(findings)
    assert failing == []
    # HIGH on transitive is neither fail nor warn (sits in policy mid-tier);
    # it is recorded silently. WARN_LEVELS are LOW/MEDIUM.
    assert warnings == []


def test_critical_on_transitive_fails(gate_mod, tmp_path):
    direct: set[str] = set()
    payload = {"dependencies": [
        {"name": "scipy", "vulns": [{"id": "GHSA-bar", "severity": "CRITICAL"}]}
    ]}
    p = _write(tmp_path, "pa.json", payload)
    findings = gate_mod.parse_findings_payload(p, "pip-audit", direct)
    failing, _ = gate_mod.apply_gate(findings)
    assert len(failing) == 1


def test_low_warns_not_fails(gate_mod, tmp_path):
    direct = {"numpy"}
    payload = {"dependencies": [
        {"name": "numpy", "vulns": [{"id": "GHSA-low", "severity": "LOW"}]}
    ]}
    p = _write(tmp_path, "pa.json", payload)
    findings = gate_mod.parse_findings_payload(p, "pip-audit", direct)
    failing, warnings = gate_mod.apply_gate(findings)
    assert failing == []
    assert len(warnings) == 1


def test_medium_warns_not_fails(gate_mod, tmp_path):
    direct = {"numpy"}
    payload = {"dependencies": [
        {"name": "numpy", "vulns": [{"id": "GHSA-med", "severity": "MEDIUM"}]}
    ]}
    p = _write(tmp_path, "pa.json", payload)
    findings = gate_mod.parse_findings_payload(p, "pip-audit", direct)
    failing, warnings = gate_mod.apply_gate(findings)
    assert failing == []
    assert len(warnings) == 1


def test_osv_moderate_normalises_to_medium(gate_mod, tmp_path):
    direct = {"sounddevice"}
    payload = {"results": [{
        "packages": [{
            "package": {"name": "sounddevice"},
            "vulnerabilities": [{
                "id": "GHSA-baz",
                "database_specific": {"severity": "MODERATE"},
            }],
        }],
    }]}
    p = _write(tmp_path, "osv.json", payload)
    findings = gate_mod.parse_findings_payload(p, "osv-scanner", direct)
    failing, warnings = gate_mod.apply_gate(findings)
    assert failing == []
    assert len(warnings) == 1
    assert warnings[0].severity == "MEDIUM"


def test_combined_no_dark_pattern(gate_mod, tmp_path):
    """A LOW + MEDIUM combo must NOT fail; the gate must surface them."""
    direct = {"numpy"}
    payload = {"dependencies": [
        {"name": "numpy", "vulns": [
            {"id": "GHSA-low", "severity": "LOW"},
            {"id": "GHSA-med", "severity": "MEDIUM"},
        ]}
    ]}
    p = _write(tmp_path, "pa.json", payload)
    findings = gate_mod.parse_findings_payload(p, "pip-audit", direct)
    failing, warnings = gate_mod.apply_gate(findings)
    assert failing == []
    assert len(warnings) == 2


def test_critical_direct_also_fails(gate_mod, tmp_path):
    direct = {"numpy"}
    payload = {"dependencies": [
        {"name": "numpy", "vulns": [{"id": "GHSA-crit", "severity": "CRITICAL"}]}
    ]}
    p = _write(tmp_path, "pa.json", payload)
    findings = gate_mod.parse_findings_payload(p, "pip-audit", direct)
    failing, _ = gate_mod.apply_gate(findings)
    assert len(failing) == 1


def test_no_findings_passes(gate_mod, tmp_path):
    direct = {"numpy"}
    payload = {"dependencies": [{"name": "numpy", "vulns": []}]}
    p = _write(tmp_path, "pa.json", payload)
    findings = gate_mod.parse_findings_payload(p, "pip-audit", direct)
    failing, warnings = gate_mod.apply_gate(findings)
    assert failing == []
    assert warnings == []


def test_direct_deps_extraction_from_pyproject(gate_mod, tmp_path):
    pp = tmp_path / "pyproject.toml"
    pp.write_text("""\
[project]
name = "x"
dependencies = ["numpy>=2", "scipy[full]==1.17", "mido"]
""", encoding="utf-8")
    direct = gate_mod._load_direct_deps(pp)
    assert direct == {"numpy", "scipy", "mido"}


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
