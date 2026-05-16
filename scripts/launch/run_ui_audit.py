#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Phase 43 / Plan 43-01 — Tier-1 UI audit driver.

REQ-IDs: VIS-01

CONTEXT §VIS-01 — Visual Ship Lock locks four Tier-1 surfaces:

    session         → tauri/ui/src/session/        (SessionLayout.ts entry)
    mascot-overlay  → tauri/ui/src/overlay/  + tauri/ui/src/mascot/
    wizard          → tauri/ui/src/wizard/         (6-step onboarding)
    calibration     → tauri/ui/src/wizard/step1-permissions.ts
                      + tauri/ui/src/wizard/step2-output-device.ts

Audit-loop methodology (CONTEXT §VIS-01) — paired agents per surface:

    gsd-ui-checker   → BLOCK / FLAG / PASS verdicts on per-element states
    gsd-ui-auditor   → scored 6-pillar audit (hierarchy / contrast / motion /
                       typography / density / restraint)

The loop runs critique → execute until zero HIGH findings per surface.
Findings land in `.planning/phases/43-visual-ship-lock/UI-REVIEW-<surface>.md`.
Severity rubric: HIGH = blocks ship, MEDIUM = strongly-recommended-fix, LOW =
nice-to-have / deferred.

This script is the *markdown-skeleton + invariant-enforcement layer*, NOT a
runner. The paired audit agents themselves are invoked interactively from the
closure plans (43-02 / 43-03) via the Task tool; they append iteration rows
to the audit-loop log inside each UI-REVIEW-<surface>.md. The dry-run path
(default) writes the canonical skeleton without subprocessing anything — this
is the contract `tests/launch/test_ui_audit_driver.py` pins.

CLI:

    # List the 4 Tier-1 surfaces + owning closure plan + entry file.
    uv run python scripts/launch/run_ui_audit.py
    uv run python scripts/launch/run_ui_audit.py --list

    # Seed the markdown skeleton for one surface (dry-run is default).
    uv run python scripts/launch/run_ui_audit.py --surface session

    # Force-rewrite an existing seed (e.g. Plan 43-01 re-seed).
    uv run python scripts/launch/run_ui_audit.py --surface session --force-rewrite
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Sequence

# ---------------------------------------------------------------------------
# Tier-1 surface inventory — CONTEXT §VIS-01.
#
# The keys here MUST stay exactly as listed: tests assert the literal set
# {"session", "mascot-overlay", "wizard", "calibration"} and the closure
# plans (43-02 / 43-03) reference these filenames verbatim.
# ---------------------------------------------------------------------------
TIER1_SURFACES: Final[dict[str, dict[str, str]]] = {
    "session": {
        "dir": "tauri/ui/src/session/",
        "entry": "SessionLayout.ts",
        "owner_plan": "43-02",
    },
    "mascot-overlay": {
        "dir": "tauri/ui/src/overlay/ + tauri/ui/src/mascot/",
        "entry": "overlay-runtime.ts + renderer.ts",
        "owner_plan": "43-02",
    },
    "wizard": {
        "dir": "tauri/ui/src/wizard/",
        "entry": "onboarding-flow.ts",
        "owner_plan": "43-03",
    },
    "calibration": {
        "dir": "tauri/ui/src/wizard/",
        "entry": "step1-permissions.ts + step2-output-device.ts",
        "owner_plan": "43-03",
    },
}

# Default phase dir — Plan 43-01 lives under this exact slug. Tests override
# via --phase-dir to keep file-writes inside tmp_path.
DEFAULT_PHASE_DIR: Final[Path] = (
    Path(__file__).resolve().parents[2]
    / ".planning"
    / "phases"
    / "43-visual-ship-lock"
)

METHODOLOGY_BLOCK: Final[
    str
] = """> **Audit loop methodology** (CONTEXT §VIS-01):
>
> 1. `gsd-ui-checker` — emits BLOCK / FLAG / PASS verdicts on per-element
>    interaction states (hover / focus / active / disabled / drag).
> 2. `gsd-ui-auditor` — emits a scored 6-pillar audit:
>    hierarchy / contrast / motion / typography / density / restraint.
> 3. The pair runs critique → execute until **zero HIGH findings** per
>    Tier-1 surface. HIGH = blocks ship; MEDIUM = strongly-recommended-fix;
>    LOW = nice-to-have / deferred.
> 4. Each iteration MUST append a row to the *Audit Loop Log* below
>    (iteration / agent / verdict / files_changed / notes) so the
>    closure trail is reviewable end-to-end."""


# ---------------------------------------------------------------------------
# Skeleton writer
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _SkeletonSpec:
    surface: str
    entry: str
    owner_plan: str


def write_audit_skeleton(
    surface: str,
    phase_dir: Path,
    *,
    force_rewrite: bool = False,
) -> Path:
    """Write the canonical UI-REVIEW-<surface>.md skeleton.

    Returns the written path. If the target already exists and
    `force_rewrite=False`, appends an audit-loop log row noting the dry-run
    invocation rather than overwriting (idempotent per Plan 43-01).
    """
    if surface not in TIER1_SURFACES:
        raise ValueError(
            f"unknown surface {surface!r}; valid: "
            + ", ".join(sorted(TIER1_SURFACES.keys()))
        )

    meta = TIER1_SURFACES[surface]
    spec = _SkeletonSpec(
        surface=surface, entry=meta["entry"], owner_plan=meta["owner_plan"]
    )

    phase_dir.mkdir(parents=True, exist_ok=True)
    target = phase_dir / f"UI-REVIEW-{surface}.md"

    if target.exists() and not force_rewrite:
        # Idempotent: append a no-op audit-loop log row instead of
        # clobbering existing findings.
        with target.open("a", encoding="utf-8") as fh:
            fh.write(
                "\n<!-- dry-run touch "
                f"{_dt.datetime.now(_dt.timezone.utc).isoformat()} -->\n"
            )
        return target

    target.write_text(_render_skeleton(spec), encoding="utf-8")
    return target


def _render_skeleton(spec: _SkeletonSpec) -> str:
    today = _dt.date.today().isoformat()
    return f"""---
surface: {spec.surface}
entry: {spec.entry}
owner_plan: {spec.owner_plan}
seeded_by: 43-01
audited_at: {today}
status: skeleton
---

# UI Review — Surface: {spec.surface}

## Surface: {spec.surface}

**Entry:** `{spec.entry}`
**Owner closure plan:** {spec.owner_plan}

## Methodology

{METHODOLOGY_BLOCK}

## Findings

### HIGH findings

_None yet — Plan {spec.owner_plan} runs the first paired audit pass._

### MEDIUM findings

_None yet — Plan {spec.owner_plan} runs the first paired audit pass._

### LOW findings

_None yet — Plan {spec.owner_plan} runs the first paired audit pass._

## Audit Loop

### Audit Loop Log

| iteration | agent | verdict | files_changed | notes |
|-----------|-------|---------|---------------|-------|
| 0 | 43-01 (seed) | seeded | - | initial skeleton; closure plan {spec.owner_plan} runs iteration 1+ |
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_ui_audit",
        description=(
            "Phase 43 §VIS-01 Tier-1 UI audit driver. Writes the "
            "UI-REVIEW-<surface>.md skeleton; paired agents (gsd-ui-checker "
            "+ gsd-ui-auditor) run interactively from closure plans 43-02 / 43-03."
        ),
    )
    p.add_argument(
        "--surface",
        default=None,
        help=(
            "Tier-1 surface to seed. One of: "
            + ", ".join(sorted(TIER1_SURFACES.keys()))
        ),
    )
    p.add_argument(
        "--phase-dir",
        type=Path,
        default=DEFAULT_PHASE_DIR,
        help=(
            "Phase directory the skeleton is written to "
            f"(default: {DEFAULT_PHASE_DIR.relative_to(Path(__file__).resolve().parents[2])})"
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help=(
            "Write skeleton only; do NOT invoke gsd-ui-checker / "
            "gsd-ui-auditor agent processes (default). Kept as an explicit "
            "flag so closure plans can pass `--dry-run` for documentation."
        ),
    )
    p.add_argument(
        "--force-rewrite",
        action="store_true",
        default=False,
        help=(
            "If UI-REVIEW-<surface>.md already exists, overwrite it instead of "
            "appending a touch comment. Use sparingly — closure plans should not "
            "force-rewrite an audit that already carries iteration history."
        ),
    )
    p.add_argument(
        "--list",
        action="store_true",
        default=False,
        help="List the 4 Tier-1 surfaces with owning closure plan + entry file.",
    )
    return p


def _print_listing(stream) -> None:
    stream.write("Tier-1 surfaces (CONTEXT §VIS-01)\n")
    stream.write("=================================\n\n")
    for surface in sorted(TIER1_SURFACES.keys()):
        meta = TIER1_SURFACES[surface]
        stream.write(f"  {surface}\n")
        stream.write(f"    dir         : {meta['dir']}\n")
        stream.write(f"    entry       : {meta['entry']}\n")
        stream.write(f"    owner_plan  : {meta['owner_plan']}\n\n")
    stream.write(
        "Audit pairing: gsd-ui-checker (BLOCK/FLAG/PASS) "
        "+ gsd-ui-auditor (6-pillar score).\n"
    )


def _reject_unknown_surface(value: str) -> None:
    sys.stderr.write(
        f"error: unknown surface {value!r}\n"
        "valid surfaces:\n"
    )
    for s in sorted(TIER1_SURFACES.keys()):
        sys.stderr.write(f"  - {s}\n")
    raise SystemExit(2)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.surface is None or args.list:
        _print_listing(sys.stdout)
        return 0

    if args.surface not in TIER1_SURFACES:
        _reject_unknown_surface(args.surface)
        return 2  # unreachable — _reject_unknown_surface raises SystemExit

    written = write_audit_skeleton(
        args.surface,
        phase_dir=args.phase_dir,
        force_rewrite=args.force_rewrite,
    )
    sys.stdout.write(f"wrote {written}\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
