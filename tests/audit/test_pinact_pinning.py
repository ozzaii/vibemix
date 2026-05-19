"""DEPS-07 — assert every `uses:` line in every .github/workflows/*.yml
is SHA-pinned (40-char hex) and not a floating tag ref.

Discharged 2026-05-19: `bash scripts/audit/run_pinact.sh --apply` ran
clean against every workflow except the `dtolnay/rust-toolchain@stable`
convention (a branch ref that resolves to rust-lang.org's stable channel
regardless of action SHA — listed in `.pinact.yaml::ignore_actions`).
"""

import re
from pathlib import Path

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


# Branch refs that intentionally bypass SHA-pinning (mirrors .pinact.yaml).
_IGNORE = {("dtolnay/rust-toolchain", "stable")}


def test_every_uses_is_sha_pinned():
    violations = []
    for wf, lineno, line in iter_uses_lines():
        if SHA_PIN_RE.match(line):
            continue
        m = TAG_REF_RE.match(line)
        if m and (m.group(1), m.group(2)) in _IGNORE:
            continue
        if m:
            violations.append(f"{wf.name}:{lineno}: {line.strip()}")
    if violations:
        raise AssertionError(
            "DEPS-07: floating tag refs found in workflows (run "
            "`bash scripts/audit/run_pinact.sh --apply`):\n  "
            + "\n  ".join(violations)
        )
