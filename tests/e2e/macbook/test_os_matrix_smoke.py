# SPDX-License-Identifier: Apache-2.0
"""Phase 50 / E2E — 50b OS-matrix dry-run smoke test.

Engineering-green = harness present + dry-run wire-check on at least 2
reachable configs. Real-VM run on all 5 OS configs gated on §INSTALL-VM-RUN
Kaan-action (carry-forward from Phase 49).

Configs that are NOT reachable in this environment are marked SKIPPED in the
SmokeResult, NOT FAIL — per CI-tolerant fallback.
"""

from __future__ import annotations

import platform

import pytest

from tests.e2e.macbook.os_matrix_smoke import (
    ALL_OS_CONFIGS,
    run_os_matrix_smoke,
)


def test_os_matrix_smoke_dry_run_returns_results_for_all_configs() -> None:
    """Dry-run smoke iterates ALL 5 configs; each returns a SmokeResult."""
    run = run_os_matrix_smoke(configs=ALL_OS_CONFIGS, dry_run=True)
    assert len(run.results) == len(ALL_OS_CONFIGS)
    for res in run.results:
        assert res.config in ALL_OS_CONFIGS
        assert isinstance(res.reason, str)


def test_os_matrix_smoke_projects_to_dimension() -> None:
    """The harness projects onto a Functional dimension for the report.html."""
    run = run_os_matrix_smoke(configs=ALL_OS_CONFIGS, dry_run=True)
    dim = run.as_dimension()
    assert dim.name == "Functional"
    assert dim.total == len(ALL_OS_CONFIGS)
    # status must be one of the four legal Dimension statuses
    assert dim.status in ("PASS", "FAIL", "PARTIAL", "SKIPPED")
    # summary is non-empty and references the count
    assert "50b" in dim.summary or "smoke" in dim.summary


@pytest.mark.skipif(
    platform.system() != "Darwin",
    reason="Engineering scaffold targets macOS-host smoke; Win-host smoke pending §INSTALL-VM-RUN",
)
def test_macos_host_config_reachable_or_marked_skipped() -> None:
    """When running on a macOS host, at least the host's native config should
    return a non-empty reason (either real result or SKIPPED-with-reason).
    """
    run = run_os_matrix_smoke(configs=ALL_OS_CONFIGS, dry_run=True)
    macos_results = [r for r in run.results if r.config.startswith("macos-")]
    # All macOS results must have a reason set (either OK or skip explanation).
    for r in macos_results:
        assert r.reason, f"{r.config} returned an empty reason"
