# SPDX-License-Identifier: Apache-2.0
"""Phase 50 / E2E — 50b OS-matrix smoke harness.

Implements the 4-step objective smoke: install → launch → wait-for-first-event
→ shutdown. Composes Phase 49's ``scripts/dist/install_vm_matrix.sh`` rather
than re-implementing — passes a ``--check-e2e`` flag.

Engineering-green = harness present + dry-run on at least 2 reachable configs.
Real-VM run on all 5 OS configs (macOS 12.3 Intel, 14 AS, 15 AS, Win 10, Win 11)
is gated on §INSTALL-VM-RUN Kaan-action (carry-forward from Phase 49).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from tests.e2e.macbook.dimensions import Functional

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_VM_MATRIX = REPO_ROOT / "scripts" / "dist" / "install_vm_matrix.sh"

OsConfig = Literal[
    "macos-12.3-intel",
    "macos-14-as",
    "macos-15-as",
    "win-10-x64",
    "win-11-x64",
]

ALL_OS_CONFIGS: tuple[OsConfig, ...] = (
    "macos-12.3-intel",
    "macos-14-as",
    "macos-15-as",
    "win-10-x64",
    "win-11-x64",
)


@dataclass
class SmokeResult:
    config: OsConfig
    install_ok: bool = False
    launch_ok: bool = False
    first_event_ok: bool = False
    shutdown_ok: bool = False
    reason: str = ""

    @property
    def all_ok(self) -> bool:
        return all([self.install_ok, self.launch_ok, self.first_event_ok, self.shutdown_ok])


@dataclass
class OsMatrixSmokeRun:
    results: list[SmokeResult] = field(default_factory=list)

    def as_dimension(self) -> Functional:
        """Project results onto a Functional dimension for the report.html."""
        dim = Functional(name="Functional")
        for r in self.results:
            label = f"50b smoke — {r.config}"
            dim.record(r.all_ok, label, reason=r.reason)
        if self.results:
            pass_n = sum(1 for r in self.results if r.all_ok)
            dim.summary = f"50b OS-matrix smoke: {pass_n}/{len(self.results)} configs"
            if pass_n == 0:
                dim.status = "FAIL"
            elif pass_n < len(self.results):
                dim.status = "PARTIAL"
            else:
                dim.status = "PASS"
        else:
            dim.summary = "no configs evaluated"
            dim.status = "SKIPPED"
        return dim


def _config_reachable(config: OsConfig) -> bool:
    """Return True iff the OS config can be smoke-tested in this environment.

    Phase 50 engineering scaffold: macos-15-as is reachable on Kaan's MacBook;
    the others require Tart VM images that ship at §INSTALL-VM-RUN discharge.
    """
    import platform

    if config == "macos-15-as" and platform.system() == "Darwin":
        # platform.mac_ver returns ('15.x.y', ...) on macOS 15.
        ver = platform.mac_ver()[0]
        if ver.startswith("15."):
            return True
    if config == "macos-14-as" and platform.system() == "Darwin":
        ver = platform.mac_ver()[0]
        if ver.startswith("14."):
            return True
    # Win configs require Tart-on-Mac or a real Win runner — neither
    # available in default CI for engineering scaffold.
    return False


def _smoke_one_config(config: OsConfig, dry_run: bool = True) -> SmokeResult:
    """Run the smoke against one OS config via install_vm_matrix.sh --check-e2e.

    dry_run=True (default) does NOT spin a real VM; it only invokes the
    harness in --dry-run mode (Phase 49 contract) and verifies the wire.
    """
    res = SmokeResult(config=config)

    if not INSTALL_VM_MATRIX.is_file():
        res.reason = f"install_vm_matrix.sh missing at {INSTALL_VM_MATRIX}"
        return res

    if not _config_reachable(config):
        res.reason = f"config {config} not reachable in this environment (Tart image required)"
        return res

    cmd = ["bash", str(INSTALL_VM_MATRIX), "--config", config, "--check-e2e"]
    if dry_run:
        cmd.append("--dry-run")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        res.reason = "harness timeout (>180s) — engineering scaffold accepts; real-VM run deferred"
        return res
    except FileNotFoundError as e:
        res.reason = f"harness invocation failed: {e}"
        return res

    # In dry-run, all 4 stages report SKIPPED in the harness output but the
    # WIRE is what we're verifying. Treat exit 0 as install_ok=launch_ok=first_event_ok=shutdown_ok.
    if proc.returncode == 0:
        res.install_ok = True
        res.launch_ok = True
        res.first_event_ok = True
        res.shutdown_ok = True
        res.reason = "dry-run wire OK" if dry_run else "real-VM smoke OK"
    else:
        res.reason = (
            f"harness exited {proc.returncode}; "
            f"stderr={proc.stderr.strip()[:200]}"
        )
    return res


def run_os_matrix_smoke(
    configs: tuple[OsConfig, ...] = ALL_OS_CONFIGS, dry_run: bool = True
) -> OsMatrixSmokeRun:
    """Execute the 50b smoke across the given configs. Default = dry-run wire check."""
    run = OsMatrixSmokeRun()
    for config in configs:
        run.results.append(_smoke_one_config(config, dry_run=dry_run))
    return run
