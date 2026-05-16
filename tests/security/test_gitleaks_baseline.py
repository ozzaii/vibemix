# SPDX-License-Identifier: Apache-2.0
"""Phase 34 / SEC-01 — gitleaks baseline discipline.

Pitfall P64 — broad allowlists fail the entire signal of the scanner.
This test enforces:

  1. Every entry in ``.secrets.baseline`` has a non-empty ``comment``.
  2. Every entry's ``secret`` field matches the AIza-fixture pattern
     (``AIza[A-Za-z0-9-_]{15,30}-TEST-FIXTURE-DO-NOT-USE``).
  3. The committed ``.gitleaks.toml`` does NOT contain a broad allowlist
     (no ``regex = '''.*'''`` or single-dot regexes).
  4. Every ``allowlist.regexes`` entry has a ``paths`` restriction.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE = REPO_ROOT / ".secrets.baseline"
CONFIG = REPO_ROOT / ".gitleaks.toml"

AIZA_FIXTURE_RE = re.compile(r"^AIza[0-9A-Za-z\-_]{15,30}-TEST-FIXTURE-DO-NOT-USE$")
BROAD_RE_PATTERNS = {"'''.*'''", "'.*'", '".*"', "'''.+'''"}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_baseline_entries(text: str) -> list[dict[str, str]]:
    """Hand parser — no `tomllib` dependency on Py3.10. We use stdlib only."""
    try:
        import tomllib  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover — py<3.11
        import tomli as tomllib  # type: ignore[no-redef]
    data = tomllib.loads(text)
    return data.get("findings", [])


def test_baseline_file_exists() -> None:
    assert BASELINE.exists(), ".secrets.baseline must be committed"
    assert CONFIG.exists(), ".gitleaks.toml must be committed"


def test_every_baseline_entry_has_comment() -> None:
    entries = _parse_baseline_entries(_read(BASELINE))
    assert entries, "baseline must declare at least the AIza fixture entry"
    for i, entry in enumerate(entries):
        comment = entry.get("comment", "").strip()
        assert comment, f"baseline entry #{i} missing comment: {entry!r}"
        # Comment must be substantive — > 20 chars to discourage `# ok`.
        assert len(comment) >= 20, f"baseline entry #{i} comment too thin"


def test_baseline_secrets_are_aiza_fixtures() -> None:
    entries = _parse_baseline_entries(_read(BASELINE))
    for entry in entries:
        secret = entry.get("secret", "")
        assert AIZA_FIXTURE_RE.match(secret), (
            f"baseline secret {secret!r} is not an AIza-fixture pattern; "
            "real keys must never be allowlisted (Pitfall P64)"
        )


def test_baseline_paths_are_bounded() -> None:
    """Each entry references a fixture path that exists or is in tests/."""
    entries = _parse_baseline_entries(_read(BASELINE))
    for entry in entries:
        file = entry.get("file", "")
        assert file, f"baseline entry missing file: {entry!r}"
        # Must live under tests/ or scripts/ — never src/ or top-level config.
        assert file.startswith(("tests/", "scripts/")), (
            f"baseline file {file!r} must live under tests/ or scripts/ "
            "to keep the allowlist surgical (Pitfall P64)"
        )


def test_gitleaks_config_no_broad_allowlist() -> None:
    cfg = _read(CONFIG)
    # Walk every regex line; reject the broad patterns.
    for line in cfg.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "regex" in stripped and "=" in stripped:
            value = stripped.split("=", 1)[1].strip()
            for broad in BROAD_RE_PATTERNS:
                assert value != broad, (
                    f"broad allowlist pattern {broad!r} forbidden — "
                    "use AIza-fixture-shaped regex only (Pitfall P64)"
                )


def test_gitleaks_allowlist_regex_has_paths_constraint() -> None:
    """Every allowlist regex must be bound to a paths list."""
    cfg = _read(CONFIG)
    # Crude but adequate: ensure the `[[allowlist.regexes]]` section block
    # below contains both `regex =` and `paths =` lines.
    in_block = False
    saw_regex = False
    saw_paths = False
    for line in cfg.splitlines():
        stripped = line.strip()
        if stripped.startswith("[[allowlist.regexes]]"):
            if in_block:
                assert saw_regex and saw_paths, (
                    "allowlist.regexes entry without paths constraint (P64)"
                )
            in_block = True
            saw_regex = False
            saw_paths = False
            continue
        if in_block and stripped.startswith("[") and stripped.endswith("]"):
            assert saw_regex and saw_paths, (
                "allowlist.regexes entry without paths constraint (P64)"
            )
            in_block = False
        if in_block:
            if stripped.startswith("regex"):
                saw_regex = True
            elif stripped.startswith("paths"):
                saw_paths = True
    if in_block:
        assert saw_regex and saw_paths, (
            "trailing allowlist.regexes entry without paths constraint (P64)"
        )


def test_fixture_file_exists() -> None:
    fixture = REPO_ROOT / "tests/security/fixtures/aiza_placeholder.txt"
    assert fixture.exists()
    assert "TEST-FIXTURE-DO-NOT-USE" in fixture.read_text()


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
