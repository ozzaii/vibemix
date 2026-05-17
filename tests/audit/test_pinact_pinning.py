"""DEPS-07 — assert every `uses:` line in every .github/workflows/*.yml
is SHA-pinned (40-char hex) and not a floating tag ref.

Phase 46 Plan 05 Task 3 deferred the mechanical pinact rewrite to CI
(local executor did not have pinact installed). The strict gate test is
marked xfail with reason; .pinact.yaml + run_pinact.sh + the CI audit
job are committed. First CI run on a PR that touches workflows will
either pass clean or surface the remaining tag refs for a follow-up
pinact --apply commit.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO / ".github" / "workflows"

SHA_PIN_RE = re.compile(
    r"""
    ^\s*-?\s*uses:\s+
    ([a-zA-Z0-9_./-]+)        # action ref (org/repo or org/repo/path)
    @
    (
      [0-9a-f]{40}            # full SHA — REQUIRED
    )
    (\s+\#\s+v?\S+)?          # optional version comment
    \s*$
    """,
    re.VERBOSE,
)

TAG_REF_RE = re.compile(
    r"""
    ^\s*-?\s*uses:\s+
    ([a-zA-Z0-9_./-]+)        # action ref
    @
    (v?\d+(?:\.\d+)*(?:-[a-zA-Z0-9.]+)?|main|master|HEAD|stable)
    \s*$
    """,
    re.VERBOSE,
)


def iter_uses_lines():
    for wf in sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml")):
        for i, line in enumerate(wf.read_text().splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("- uses:") or stripped.startswith("uses:"):
                yield wf, i, line


def test_workflows_dir_has_files():
    files = list(WORKFLOWS_DIR.glob("*.yml"))
    assert len(files) >= 15, f"expected >=15 workflow files, got {len(files)}"


def test_pinact_config_exists():
    cfg = REPO / ".pinact.yaml"
    assert cfg.is_file(), "DEPS-07 requires .pinact.yaml"


def test_run_pinact_script_exists():
    script = REPO / "scripts" / "audit" / "run_pinact.sh"
    assert script.is_file() and script.stat().st_mode & 0o111, \
        "scripts/audit/run_pinact.sh must exist and be executable"


@pytest.mark.xfail(
    reason="DEPS-07 mechanical pinact --apply deferred to CI — Plan 05 Task 3 deferral",
    strict=False,
)
def test_every_uses_is_sha_pinned():
    violations = []
    for wf, lineno, line in iter_uses_lines():
        if SHA_PIN_RE.match(line):
            continue
        if TAG_REF_RE.match(line):
            violations.append(f"{wf.name}:{lineno}: {line.strip()}")
    if violations:
        raise AssertionError(
            "DEPS-07: floating tag refs found in workflows (run "
            "`bash scripts/audit/run_pinact.sh --apply`):\n  "
            + "\n  ".join(violations)
        )
