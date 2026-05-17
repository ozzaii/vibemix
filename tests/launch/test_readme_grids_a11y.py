# SPDX-License-Identifier: Apache-2.0
"""tests/launch/test_readme_grids_a11y.py — README grid a11y + cell-count gate.

LAUNCH-03 + LAUNCH-04 (Phase 44 Plan 44-02): asserts the live ``README.md``
DJ-software grid (6 cells) and Supported-controllers grid (10 cells) carry
non-empty alt-text on every ``<img>``, are slop-free in alt-text, and have
balanced cell counts. Catches drift like a missing ``alt=""``, a 7th
controller row, or a "powerful AI-powered" alt-text that slips through PR
review.

Three test layers:
- Module shape tests pin the public constants (cell counts, headings,
  blocklist subset).
- Happy-path test against the real README.
- Negative cases — synthetic READMEs in ``tmp_path`` that each violate one
  rule.

Pattern mirrors ``tests/launch/test_readme_hero_lock.py``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.launch.check_readme_grids_a11y import (
    CONTROLLERS_CELL_COUNT,
    CONTROLLERS_HEADING_FRAGMENT,
    DJ_SOFTWARE_CELL_COUNT,
    DJ_SOFTWARE_HEADING_FRAGMENT,
    _AI_SLOP_BLOCKLIST,
    check_readme,
    main,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "README.md"


# ---------------------------------------------------------------------------
# Module-level shape tests — pin the public surface of the checker.
# ---------------------------------------------------------------------------


def test_module_imports_cleanly() -> None:
    """Importing the checker exposes the public symbols used by CI."""
    assert callable(main)
    assert callable(check_readme)
    assert isinstance(DJ_SOFTWARE_HEADING_FRAGMENT, str)
    assert isinstance(CONTROLLERS_HEADING_FRAGMENT, str)
    assert isinstance(DJ_SOFTWARE_CELL_COUNT, int)
    assert isinstance(CONTROLLERS_CELL_COUNT, int)
    assert isinstance(_AI_SLOP_BLOCKLIST, tuple)


def test_locked_cell_counts() -> None:
    """Cell counts match CONTEXT §LAUNCH-03 + §LAUNCH-04 locked sets."""
    assert DJ_SOFTWARE_CELL_COUNT == 6
    assert CONTROLLERS_CELL_COUNT == 10


def test_heading_fragments_lowercase() -> None:
    """Heading fragments are lowercase — the script does case-insensitive
    matching, but pinning lowercase keeps the contract obvious to readers.
    """
    assert DJ_SOFTWARE_HEADING_FRAGMENT == DJ_SOFTWARE_HEADING_FRAGMENT.lower()
    assert CONTROLLERS_HEADING_FRAGMENT == CONTROLLERS_HEADING_FRAGMENT.lower()


def test_blocklist_pins_canonical_tokens() -> None:
    """Canonical slop tokens (subset) are present in the blocklist.

    Pinning a subset rather than the whole tuple keeps the test resilient
    to deliberate planner-approved adds/removes while still catching
    accidental removals of the load-bearing slop tokens.
    """
    canon = {
        "leverage",
        "synergize",
        "revolutionize",
        "AI-powered",
        "seamless",
        "powerful",
        "harness the power",
    }
    assert canon.issubset(set(_AI_SLOP_BLOCKLIST)), (
        f"blocklist drift: missing canonical tokens {canon - set(_AI_SLOP_BLOCKLIST)}"
    )


# ---------------------------------------------------------------------------
# Happy path — the live README must pass once both grids are in.
# ---------------------------------------------------------------------------


def test_real_readme_passes_a11y() -> None:
    """Live README.md passes all four gates on both grids.

    NOTE: RED at the start of Plan 44-02 — the DJ-software grid section
    doesn't exist yet. Goes GREEN after Task 2 ships the section + the 10
    canonical controllers replace the legacy table.
    """
    rc = check_readme(README, quiet=True)
    assert rc == 0, (
        "README grid a11y check failed — re-run "
        "`uv run python scripts/launch/check_readme_grids_a11y.py` "
        "for the failing-gate diagnostic"
    )


# ---------------------------------------------------------------------------
# Negative cases — each synthetic README violates one rule. Each builds on
# a valid baseline body that contains both well-formed grids, then breaks
# exactly one rule so the test isolates the gate under scrutiny.
# ---------------------------------------------------------------------------


def _make_valid_readme_body() -> str:
    """A minimal valid README body satisfying both grids — used as the
    starting point for each negative test."""
    dj_cells = "".join(
        f'<img src="docs/assets/dj-software/{slug}.svg" alt="{name} logo" width="200" />'
        for slug, name in (
            ("rekordbox", "rekordbox"),
            ("serato", "Serato"),
            ("traktor", "Traktor"),
            ("djay-pro", "djay Pro"),
            ("virtualdj", "VirtualDJ"),
            ("mixxx", "Mixxx"),
        )
    )
    ctl_cells = "".join(
        f'<img src="docs/assets/controllers/{slug}.svg" alt="{name}" width="200" />'
        for slug, name in (
            ("ddj-200", "Pioneer DDJ-200"),
            ("ddj-400", "Pioneer DDJ-400"),
            ("ddj-flx4", "Pioneer DDJ-FLX4"),
            ("ddj-rev1", "Pioneer DDJ-REV1"),
            ("kontrol-s2", "Native Instruments Traktor Kontrol S2"),
            ("kontrol-s4", "Native Instruments Traktor Kontrol S4"),
            ("mc-6000", "Denon DJ MC6000"),
            ("mc-7000", "Denon DJ MC7000"),
            ("mixtrack-platinum-fx", "Numark Mixtrack Platinum FX"),
            ("mixtrack-pro-fx", "Numark Mixtrack Pro FX"),
        )
    )
    return (
        "# vibemix\n\n"
        "## Works alongside whatever DJ app you already use\n\n"
        f"{dj_cells}\n\n"
        "## Supported controllers\n\n"
        f"{ctl_cells}\n\n"
        "## Install\n\nstuff\n"
    )


def test_valid_baseline_passes(tmp_path: Path) -> None:
    """Sanity check — the synthetic valid body itself passes all gates."""
    good = tmp_path / "README.md"
    good.write_text(_make_valid_readme_body(), encoding="utf-8")
    rc = check_readme(good, quiet=True)
    assert rc == 0


def test_negative_missing_alt(tmp_path: Path) -> None:
    """A README with one <img> missing alt= must fail."""
    bad = tmp_path / "README.md"
    body = _make_valid_readme_body().replace(
        'alt="rekordbox logo"',
        "",  # strip the alt attribute entirely
        1,
    )
    bad.write_text(body, encoding="utf-8")
    rc = check_readme(bad, quiet=True)
    assert rc != 0, "checker missed: <img> with no alt attribute"


def test_negative_empty_alt(tmp_path: Path) -> None:
    """A README with alt="" on a cell must fail."""
    bad = tmp_path / "README.md"
    body = _make_valid_readme_body().replace(
        'alt="Serato logo"',
        'alt=""',
        1,
    )
    bad.write_text(body, encoding="utf-8")
    rc = check_readme(bad, quiet=True)
    assert rc != 0, "checker missed: <img> with empty alt"


def test_negative_wrong_dj_cell_count(tmp_path: Path) -> None:
    """A DJ-software grid with 5 cells (one removed) must fail."""
    bad = tmp_path / "README.md"
    body = _make_valid_readme_body().replace(
        '<img src="docs/assets/dj-software/mixxx.svg" alt="Mixxx logo" width="200" />',
        "",
        1,
    )
    bad.write_text(body, encoding="utf-8")
    rc = check_readme(bad, quiet=True)
    assert rc != 0, "checker missed: DJ-software grid cell count != 6"


def test_negative_wrong_controller_cell_count(tmp_path: Path) -> None:
    """A controllers grid with 9 cells (one removed) must fail."""
    bad = tmp_path / "README.md"
    body = _make_valid_readme_body().replace(
        '<img src="docs/assets/controllers/mixtrack-pro-fx.svg" '
        'alt="Numark Mixtrack Pro FX" width="200" />',
        "",
        1,
    )
    bad.write_text(body, encoding="utf-8")
    rc = check_readme(bad, quiet=True)
    assert rc != 0, "checker missed: controllers grid cell count != 10"


def test_negative_slop_in_alt(tmp_path: Path) -> None:
    """A README with a slop token in alt-text must fail."""
    bad = tmp_path / "README.md"
    body = _make_valid_readme_body().replace(
        'alt="Pioneer DDJ-FLX4"',
        'alt="Pioneer DDJ-FLX4 powerful AI-powered controller"',
        1,
    )
    bad.write_text(body, encoding="utf-8")
    rc = check_readme(bad, quiet=True)
    assert rc != 0, "checker missed: slop token in alt-text"


def test_negative_missing_dj_software_section(tmp_path: Path) -> None:
    """A README missing the DJ-software H2 section entirely must fail."""
    bad = tmp_path / "README.md"
    body = _make_valid_readme_body().replace(
        "## Works alongside whatever DJ app you already use\n",
        "",
        1,
    )
    bad.write_text(body, encoding="utf-8")
    rc = check_readme(bad, quiet=True)
    assert rc != 0, "checker missed: DJ-software section absent"


def test_negative_missing_controllers_section(tmp_path: Path) -> None:
    """A README missing the controllers H2 section entirely must fail."""
    bad = tmp_path / "README.md"
    body = _make_valid_readme_body().replace(
        "## Supported controllers\n",
        "",
        1,
    )
    bad.write_text(body, encoding="utf-8")
    rc = check_readme(bad, quiet=True)
    assert rc != 0, "checker missed: controllers section absent"


# ---------------------------------------------------------------------------
# CLI entrypoint — subprocess smoke test.
# ---------------------------------------------------------------------------


def test_cli_entrypoint_runs(tmp_path: Path) -> None:
    """Invoking the script via subprocess against a synthetic valid
    README returns 0.

    We do NOT exercise the CLI against the live README here because the
    happy-path test above already covers that — and during TDD RED the
    live README's grids don't exist yet. A subprocess call against the
    synthetic valid body pins the CLI surface independently of phase
    state.
    """
    good = tmp_path / "README.md"
    good.write_text(_make_valid_readme_body(), encoding="utf-8")
    script = REPO_ROOT / "scripts" / "launch" / "check_readme_grids_a11y.py"
    result = subprocess.run(
        [sys.executable, str(script), "--readme", str(good), "--quiet"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"CLI exit {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )


def test_cli_missing_readme_fails(tmp_path: Path) -> None:
    """CLI returns non-zero when --readme points at a missing path."""
    script = REPO_ROOT / "scripts" / "launch" / "check_readme_grids_a11y.py"
    missing = tmp_path / "does-not-exist.md"
    result = subprocess.run(
        [sys.executable, str(script), "--readme", str(missing), "--quiet"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode != 0
