"""DEPS-02 / DEPS-03 static policy test — asserts cargo-deny license
allowlist + GPL ban list + dep-audit workflow shape. Pure static
analysis; no cargo or npm execution."""

import tomllib
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
DENY_TOML = REPO / "tauri" / "src-tauri" / "deny.toml"
DEP_AUDIT_YML = REPO / ".github" / "workflows" / "dep-audit.yml"

REQUIRED_ALLOW = {
    "Apache-2.0",
    "Apache-2.0 WITH LLVM-exception",
    "MIT",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "Unicode-DFS-2016",
    "MPL-2.0",
}
REQUIRED_DENY = {
    "GPL-2.0-only",
    "GPL-2.0-or-later",
    "GPL-3.0-only",
    "GPL-3.0-or-later",
    "AGPL-3.0-only",
    "AGPL-3.0-or-later",
    "LGPL-3.0-only",
    "LGPL-3.0-or-later",
}


def _load_deny():
    return tomllib.loads(DENY_TOML.read_text())


def test_deny_toml_exists():
    assert DENY_TOML.is_file(), f"missing {DENY_TOML}"


def test_license_allowlist_contains_required():
    d = _load_deny()
    allow = set(d["licenses"]["allow"])
    missing = REQUIRED_ALLOW - allow
    assert not missing, f"allowlist missing entries: {missing}"


def test_license_deny_contains_gpl_family():
    d = _load_deny()
    deny = set(d["licenses"].get("deny", []))
    missing = REQUIRED_DENY - deny
    assert not missing, f"deny list missing GPL family: {missing}"


def test_dep_audit_workflow_has_three_jobs():
    d = yaml.safe_load(DEP_AUDIT_YML.read_text())
    jobs = set(d["jobs"].keys())
    assert jobs == {"uv-regen-diff", "cargo-deny", "npm-audit-pr-comment"}, \
        f"unexpected job set: {jobs}"


def test_npm_audit_job_has_pr_comment_permission():
    d = yaml.safe_load(DEP_AUDIT_YML.read_text())
    perms = d["jobs"]["npm-audit-pr-comment"]["permissions"]
    assert perms["pull-requests"] == "write", \
        "npm-audit-pr-comment job must have pull-requests:write"


def test_cargo_deny_job_uses_pinned_version():
    # cargo-deny version drift can change policy enforcement semantics.
    # Pin to 0.16.1 (the lowest version with [licenses].deny support
    # plus stable advisory schema v2).
    d = yaml.safe_load(DEP_AUDIT_YML.read_text())
    steps = d["jobs"]["cargo-deny"]["steps"]
    install_step = next((s for s in steps if "Install cargo-deny" in s.get("name", "")), None)
    assert install_step is not None, "missing cargo-deny install step"
    assert "0.16.1" in install_step["run"], "cargo-deny must be pinned to 0.16.1"
