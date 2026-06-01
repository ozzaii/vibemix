# SPDX-License-Identifier: Apache-2.0
"""Plan 58-04 Task 2 — the ABSOLUTE hard guard (T-58-08 / Pitfall 4 / P46).

``cut_release.sh`` is PRE-FLIGHT ONLY. The literal ``gh release create`` must
appear ONLY inside the printed ``cat <<EOF ... EOF`` heredoc (so Kaan can copy
it) and must NEVER be reachable as an executed command line — including under
the new ``--dry-run`` mode. This is the load-bearing safety property: an
autonomous agent must never publish.

Static-analysis pin; mirrors the read-script + ``_echo_lines`` approach of
``tests/repo/test_cut_release_invokes_check_gate.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CUT_RELEASE = REPO_ROOT / "scripts" / "launch" / "cut_release.sh"


def _read_script() -> str:
    assert CUT_RELEASE.is_file(), f"cut_release.sh missing: {CUT_RELEASE}"
    return CUT_RELEASE.read_text(encoding="utf-8")


def _lines(text: str) -> list[str]:
    return text.splitlines()


def _heredoc_line_span(lines: list[str]) -> tuple[int, int]:
    """Return the (start, end) line indices of the printed `cat <<EOF` heredoc
    body (exclusive of the `cat <<EOF` / `EOF` delimiter lines)."""
    start = end = -1
    for i, ln in enumerate(lines):
        s = ln.strip()
        if start == -1 and s.startswith("cat <<EOF"):
            start = i
        elif start != -1 and s == "EOF":
            end = i
            break
    assert start != -1, "expected a `cat <<EOF` heredoc in cut_release.sh"
    assert end != -1, "expected a closing `EOF` for the heredoc"
    return start, end


# ---------------------------------------------------------------------------
# gh release create lives ONLY inside the printed heredoc
# ---------------------------------------------------------------------------


def test_gh_release_create_only_inside_heredoc():
    """Every NON-comment `gh release create` must sit inside the printed
    heredoc. Comment lines (the HARD GUARD doc block) are allowed anywhere."""
    lines = _lines(_read_script())
    start, end = _heredoc_line_span(lines)
    body_occurrences = []
    for i, ln in enumerate(lines):
        if "gh release create" not in ln:
            continue
        if ln.strip().startswith("#"):
            continue  # documentation comment — never executed
        body_occurrences.append(i)
        assert start < i < end, (
            f"`gh release create` on line {i + 1} is OUTSIDE the printed "
            f"heredoc (lines {start + 1}..{end + 1}) — it must NEVER be a "
            "reachable executed command (T-58-08 / P46)."
        )
    assert body_occurrences, (
        "expected the printed `gh release create` example inside the heredoc"
    )


def test_gh_release_create_never_an_executed_command_line():
    """No line may invoke gh release create as a real command: a bare
    `gh release create ...` (or `$(...)`/backtick/`bash -c` wrapping it) that
    is NOT the heredoc body line."""
    lines = _lines(_read_script())
    start, end = _heredoc_line_span(lines)
    for i, ln in enumerate(lines):
        if "gh release create" not in ln:
            continue
        if start < i < end:
            continue  # heredoc body — printed, not executed
        s = ln.strip()
        # Anything outside the heredoc that mentions the publish is forbidden,
        # unless it is a comment line documenting the guard.
        assert s.startswith("#"), (
            f"line {i + 1} references `gh release create` outside the heredoc "
            f"and is not a comment: {s!r}"
        )


def test_no_dry_run_branch_invokes_publish():
    """The --dry-run path must not add any code that runs the publish."""
    text = _read_script()
    # The only DRY_RUN-guarded blocks must be the gate stubs + banner — none
    # may contain `gh release create`.
    assert "DRY_RUN" in text, "expected the --dry-run guard variable"
    # Crude but effective: every `gh release create` occurrence is already
    # pinned to the heredoc above; assert no `gh ` command appears in a
    # DRY_RUN conditional body by checking no `gh release create` sits on a
    # line whose nearest preceding `if`/`elif` mentions DRY_RUN.
    lines = _lines(text)
    pending_dry = False
    for ln in lines:
        s = ln.strip()
        if re.match(r"(if|elif)\b.*DRY_RUN", s):
            pending_dry = True
        elif s == "fi":
            pending_dry = False
        if pending_dry and "gh release create" in s and not s.startswith("#"):
            raise AssertionError(
                "a DRY_RUN-guarded branch invokes `gh release create` — "
                "the hard guard must hold even under --dry-run"
            )


def test_script_documents_hard_guard():
    text = _read_script()
    assert "HARD GUARD" in text, (
        "cut_release.sh must keep the HARD GUARD documentation block"
    )
    assert "--dry-run" in text, (
        "the HARD GUARD note must cover --dry-run explicitly"
    )
