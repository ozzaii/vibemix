# SPDX-License-Identifier: Apache-2.0
"""Phase 48 / OPP-03 — Opportunity-scan auto-Red enforcement validator.

Three gates, single CI surface:

1. **md<->yaml parity gate** — every DEP-OPP-NN id in
   ``docs/dep-opportunities/<YYYY-MM>-scan.md`` must appear in
   ``scripts/audit/dep_ratings.yaml::opportunity_evaluations`` and
   vice versa.

2. **Auto-Red constraint gate** — every candidate whose ``candidate``
   field matches one of the :data:`CONSTRAINT_VIOLATORS` substrings
   (case-insensitive) MUST carry a ``rating`` of either
   ``red-constraint`` or ``red-risk``. The scan markdown author MUST
   explicitly mark these Red — the validator does NOT auto-correct;
   it FAILS so the author fixes the row.

3. **ADR-existence gate** — every ``green-adopt`` row MUST carry a
   non-empty ``adr_sidecar`` that resolves to an existing file under
   ``.planning/decisions/``.

Run from repo root::

    uv run python scripts/audit/scan_opportunities.py
    uv run python scripts/audit/scan_opportunities.py --scan docs/dep-opportunities/2026-05-scan.md
    uv run python scripts/audit/scan_opportunities.py --quiet

Exit 0 = all gates pass. Exit 1 = at least one gate failed.

Schema for opportunity_evaluations entries lives in
``scripts/audit/dep_ratings_schema.json`` ``$defs.opportunity_entry``.
Schema validation is performed implicitly by Plan 48-01's
``tests/audit/test_opportunity_evaluations_schema.py``; this script
does NOT re-validate against jsonschema (separation of concerns: this
enforces the OPP-03 contract; the schema test enforces shape).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCAN = REPO_ROOT / "docs" / "dep-opportunities" / "2026-05-scan.md"
YAML_FILE = REPO_ROOT / "scripts" / "audit" / "dep_ratings.yaml"
DECISIONS_DIR = REPO_ROOT / ".planning" / "decisions"

# CONTEXT.md Decision 8 — auto-Red set. Case-insensitive substring match
# against opportunity_entry.candidate. If a row's candidate contains one
# of these substrings, its rating MUST be red-constraint or red-risk.
CONSTRAINT_VIOLATORS: tuple[str, ...] = (
    "CLAP",
    "LAION-CLAP",
    "MERT",
    "OpenL3",
    "OpenAI direct",
    "Anthropic API direct",
    "Demucs",
    "Spleeter",
    "Ableton Link",
    "DAW API",
    "Linux-only",
    "ProDJ Link",
    "cdj-link-py",
    "Dante Via",
    "Loopback Audio",
    "Soundflower",
    "Auto-Rig Pro",
)

ALLOWED_RED_RATINGS: frozenset[str] = frozenset({"red-constraint", "red-risk"})

DEP_OPP_ID_RE = re.compile(r"DEP-OPP-\d{2}")


def _load_yaml() -> dict:
    return yaml.safe_load(YAML_FILE.read_text())


def _md_ids(scan_path: Path) -> set[str]:
    return set(DEP_OPP_ID_RE.findall(scan_path.read_text()))


def _yaml_ids(yaml_data: dict) -> set[str]:
    return {row["id"] for row in yaml_data.get("opportunity_evaluations", [])}


def gate_md_yaml_parity(scan_path: Path, yaml_data: dict, errors: list[str]) -> None:
    md_only = _md_ids(scan_path) - _yaml_ids(yaml_data)
    yaml_only = _yaml_ids(yaml_data) - _md_ids(scan_path)
    if md_only:
        errors.append(
            f"[parity] {len(md_only)} id(s) in scan markdown but NOT in yaml: "
            f"{sorted(md_only)}"
        )
    if yaml_only:
        errors.append(
            f"[parity] {len(yaml_only)} id(s) in yaml but NOT in scan markdown: "
            f"{sorted(yaml_only)}"
        )


def gate_auto_red(yaml_data: dict, errors: list[str]) -> None:
    for row in yaml_data.get("opportunity_evaluations", []):
        cand_lower = row["candidate"].lower()
        for violator in CONSTRAINT_VIOLATORS:
            if violator.lower() in cand_lower:
                if row["rating"] not in ALLOWED_RED_RATINGS:
                    errors.append(
                        f"[auto-red] {row['id']} candidate '{row['candidate']}' "
                        f"matches violator '{violator}' but rating is "
                        f"'{row['rating']}' — MUST be red-constraint or red-risk"
                    )


def gate_adr_existence(yaml_data: dict, errors: list[str]) -> None:
    for row in yaml_data.get("opportunity_evaluations", []):
        if row["rating"] != "green-adopt":
            continue
        adr_path = row.get("adr_sidecar", "")
        if not adr_path:
            errors.append(
                f"[adr] {row['id']} is green-adopt but adr_sidecar is empty"
            )
            continue
        full = REPO_ROOT / adr_path
        if not full.is_file():
            errors.append(
                f"[adr] {row['id']} adr_sidecar='{adr_path}' does not exist on disk"
            )


def run_gates(scan_path: Path, quiet: bool = False) -> int:
    if not scan_path.is_file():
        print(f"error: scan file not found: {scan_path}", file=sys.stderr)
        return 1
    if not YAML_FILE.is_file():
        print(f"error: yaml file not found: {YAML_FILE}", file=sys.stderr)
        return 1

    yaml_data = _load_yaml()
    if "opportunity_evaluations" not in yaml_data:
        print(
            f"error: yaml missing opportunity_evaluations block: {YAML_FILE}",
            file=sys.stderr,
        )
        return 1

    errors: list[str] = []
    gate_md_yaml_parity(scan_path, yaml_data, errors)
    gate_auto_red(yaml_data, errors)
    gate_adr_existence(yaml_data, errors)

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        print(
            f"\n{len(errors)} gate failure(s) — fix the rows above and re-run",
            file=sys.stderr,
        )
        return 1

    if not quiet:
        n = len(yaml_data["opportunity_evaluations"])
        print(f"opp-scan gates passed: {n} rows, scan={scan_path.name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 48 / OPP-03 opportunity-scan validator"
    )
    parser.add_argument(
        "--scan",
        type=Path,
        default=DEFAULT_SCAN,
        help=f"path to scan markdown (default: {DEFAULT_SCAN.relative_to(REPO_ROOT)})",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    return run_gates(args.scan, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
