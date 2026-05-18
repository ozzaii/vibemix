"""OPP-03 anti-slop sibling-checker tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "audit" / "check_no_slop_opp.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("_check_no_slop_opp", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module()

AI_SLOP_BLOCKLIST = _mod.AI_SLOP_BLOCKLIST
DEFAULT_DIR = _mod.DEFAULT_DIR
scan_file = _mod.scan_file


def test_blocklist_is_nonempty_and_loaded():
    # The sibling MUST load the blocklist (from launch-side script or
    # the defensive fallback). Empty = misconfigured.
    assert isinstance(AI_SLOP_BLOCKLIST, tuple)
    assert len(AI_SLOP_BLOCKLIST) >= 10, f"expected >= 10 tokens, got {len(AI_SLOP_BLOCKLIST)}"


def test_real_scan_md_is_clean():
    # Plan 48-02's canonical scan must be slop-clean.
    for md in sorted(DEFAULT_DIR.glob("*.md")):
        errors = scan_file(md)
        assert errors == [], f"{md.name} has slop hits: {errors}"


def test_blocklist_token_triggers_failure(tmp_path: Path):
    token = AI_SLOP_BLOCKLIST[0]  # first token
    md = tmp_path / "synthetic.md"
    md.write_text(f"# title\nThis content includes the word {token} on purpose.\n")
    errors = scan_file(md)
    assert errors, f"token '{token}' must trigger scan_file failure"
    assert token in errors[0]


def test_deeply_phrase_triggers_failure(tmp_path: Path):
    md = tmp_path / "synthetic.md"
    md.write_text("This is deeply integrated content for test purposes.")
    errors = scan_file(md)
    assert errors, "\\bdeeply\\s+\\w+ must trigger gate"
    assert "deeply integrated" in errors[0].lower()


def test_clean_content_passes(tmp_path: Path):
    md = tmp_path / "clean.md"
    md.write_text("# Clean test fixture\n\nNo offending phrases here.\n")
    errors = scan_file(md)
    assert errors == [], f"clean content must not trigger gate, got: {errors}"
