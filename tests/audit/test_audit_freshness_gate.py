"""DEPS-05 — assert the freshness gate script uses git log
(not mtime) and references all six lockfiles + both audit
artifacts."""

from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "audit" / "check_audit_freshness.sh"


def test_script_exists():
    assert SCRIPT.is_file(), f"missing {SCRIPT}"


def test_script_uses_git_log_not_mtime():
    src = SCRIPT.read_text()
    assert "git log -1 --format=%ct" in src, "must use git commit-time, not mtime"
    assert "stat -c %Y" not in src
    assert "find -mtime" not in src


def test_script_references_all_lockfiles():
    src = SCRIPT.read_text()
    for f in (
        "pyproject.toml", "uv.lock",
        "tauri/src-tauri/Cargo.toml", "tauri/src-tauri/Cargo.lock",
        "tauri/ui/package.json", "tauri/ui/package-lock.json",
    ):
        assert f in src, f"missing lockfile in script: {f}"


def test_script_references_both_audit_artifacts():
    src = SCRIPT.read_text()
    assert "docs/AUDIT.md" in src
    assert "scripts/audit/dep_ratings.yaml" in src
