"""Phase 50 — pytest fixtures for the e2e MacBook harness.

Includes the session-autouse ``_privacy_guard`` fixture that asserts the
harness never writes to off-limits paths per memory
``feedback_privacy_scope_narrow``: ~/.hermes/, ~/hermes-rig/logs/, ~/.lmstudio/.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.e2e.macbook.audio_loopback_fixture import audio_loopback_recorder  # noqa: F401
from tests.e2e.macbook.dimensions import EeRun, make_run_id
from tests.e2e.macbook.render_report import render

# Off-limits paths from memory ``feedback_privacy_scope_narrow``. Paths can be
# overridden in tests via env var; production resolves to the user home.
_OFF_LIMITS_ENV = "VIBEMIX_E2E_OFF_LIMITS_ROOTS"
_DEFAULT_OFF_LIMITS = (
    "~/.hermes",
    "~/hermes-rig/logs",
    "~/.lmstudio",
)


def _resolved_off_limits_roots() -> list[Path]:
    """Resolve off-limits roots, honoring the test override env."""
    raw = os.environ.get(_OFF_LIMITS_ENV)
    if raw:
        return [Path(p).expanduser() for p in raw.split(os.pathsep) if p]
    return [Path(p).expanduser() for p in _DEFAULT_OFF_LIMITS]


def _snapshot(roots: list[Path]) -> dict[str, tuple[int, float]]:
    """Snapshot (file_count, max_mtime) per root. Missing dirs map to (0, 0).

    File count is the load-bearing field — the harness's contract is to never
    *create* files under off-limits roots. mtime is recorded for diagnostics
    only (background processes can touch existing files and shouldn't
    false-positive the gate).
    """
    out: dict[str, tuple[int, float]] = {}
    for root in roots:
        if not root.exists():
            out[str(root)] = (0, 0.0)
            continue
        max_mtime = 0.0
        count = 0
        try:
            for p in root.rglob("*"):
                try:
                    if p.is_file():
                        count += 1
                        m = p.stat().st_mtime
                        if m > max_mtime:
                            max_mtime = m
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
            pass
        out[str(root)] = (count, max_mtime)
    return out


@pytest.fixture(scope="session", autouse=True)
def _privacy_guard() -> None:
    """Assert the harness writes ZERO files into off-limits paths.

    Snapshots (file count, max mtime) per root pre-session; re-snapshots
    post-session; asserts no delta. Per memory ``feedback_privacy_scope_narrow``.

    Absent directories are treated as zero baseline (no error).
    """
    roots = _resolved_off_limits_roots()
    before = _snapshot(roots)
    yield
    after = _snapshot(roots)
    drift = []
    for root, (count, mtime) in after.items():
        b_count, _b_mtime = before.get(root, (0, 0.0))
        # Only file-count growth signals a harness write. mtime growth alone
        # can be caused by unrelated background processes (e.g., LM Studio
        # running on a dev machine) and would false-positive. The harness's
        # contract is: never *create* files under off-limits roots.
        if count > b_count:
            drift.append(
                f"{root}: before_count={b_count} after_count={count} "
                f"(harness created {count - b_count} new file(s))"
            )
    assert not drift, (
        "E2E harness wrote to off-limits path(s) — violates privacy invariant "
        f"(memory feedback_privacy_scope_narrow):\n  " + "\n  ".join(drift)
    )


@pytest.fixture
def e2e_run(tmp_path) -> EeRun:
    """Yield an EeRun bound to a tmp output dir; render report.html on teardown.

    Tests can record assertions into ``run.functional``, ``run.visual``, etc.
    The fixture renders the report.html on teardown into ``tmp_path``.
    """
    run = EeRun(run_id=make_run_id(), out_dir=tmp_path)
    yield run
    render(run, out_root=tmp_path)
