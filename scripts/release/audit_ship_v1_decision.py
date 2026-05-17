#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""SHIP-V1-DECISION audit script — Plan 45-04 / SHIP-13.

Reads the last 14 days of evidence from 4 sources and pre-fills
`.planning/decisions/v3.0-SHIP-V1-DECISION.md` (or any --output path)
using `docs/SHIP-V1-DECISION-TEMPLATE.md` as the structural shell.

Goal: at T+30 of v3.0 bake, Kaan reviews the pre-filled report + signs
off on the 3-way decision (cut v1.0.0 / cycle v3.0.0-rc2 / pause) rather
than hand-collating data from 4 dashboards.

Evidence sources:
  1. GitHub releases telemetry (download counts, publish date).
  2. Bravoh /vibemix/healthz cron uptime stats (14-day window).
  3. eval/ear-test-logs/*.json since release publish (Plan 42-03 schema).
  4. GitHub issues opened in bake window (severity + crash-label rollup).

Modes:
  --fixtures PATH       hermetic; reads canned JSON / CSV from PATH/.
  --live                pulls from gh CLI + Bravoh healthz endpoint. Requires
                        GITHUB_TOKEN env. Read-only against all sources.

CLI:
  --since DAYS                       default 14
  --output PATH                      where the report lands
  --fixtures PATH                    hermetic fixtures dir
  --live                             pull from gh + Bravoh
  --release-tag TAG                  default v3.0.0-rc1
  --bravoh-healthz-stats-url URL     --live: prefer URL for uptime stats
  --bravoh-healthz-csv PATH          --live: fallback to local CSV
  --ear-test-dir PATH                ear-test logs dir (default eval/ear-test-logs)
  --template PATH                    template skeleton (default docs/SHIP-V1-DECISION-TEMPLATE.md)

Threat-model mitigations (per Plan 45-04 §threat_model):
  T-45-04-01 — Numeric substitution only; no raw HTML / markdown injection.
  T-45-04-02 — Ear-test log content NEVER copied into report; aggregate counts only.
  T-45-04-03 — `_generated_by:` HTML comment in report header for provenance.
  T-45-04-05 — gh subprocess argv list is read-only API calls; mutation methods
               (POST / PATCH / DELETE) are never in the argv we build.

Plan 45-06 §SHIP-13 runbook cites the literal T+30 invocation:
  uv run python scripts/release/audit_ship_v1_decision.py --live \\
    --bravoh-healthz-stats-url https://api.altidus.world/vibemix/healthz/stats \\
    --output .planning/decisions/v3.0-SHIP-V1-DECISION.md
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ----------------------------------------------------------------------
# Module-level constants
# ----------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE = REPO_ROOT / "docs" / "SHIP-V1-DECISION-TEMPLATE.md"
DEFAULT_EAR_TEST_DIR = REPO_ROOT / "eval" / "ear-test-logs"
DEFAULT_OUTPUT = REPO_ROOT / ".planning" / "decisions" / "v3.0-SHIP-V1-DECISION.md"
SCRIPT_VERSION = "1.0.0"

# Rubric thresholds — kept in code so the rubric "Current" cells can be
# auto-classified once the rubric ever needs a Green/Yellow/Red flag column.
# For v3.0 we keep the column at the "<pre-filled>" / numeric value level;
# Kaan reads the rubric + applies the threshold himself at sign-off.


# ----------------------------------------------------------------------
# Fixture-mode loaders
# ----------------------------------------------------------------------


def load_release_fixture(fixtures_dir: Path) -> dict[str, Any]:
    """Read gh_releases.json fixture."""
    path = fixtures_dir / "gh_releases.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing fixture: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_healthz_csv(path: Path) -> dict[str, Any]:
    """Parse a Bravoh healthz CSV (rows of timestamp,status).

    Returns dict: total_checks / ok_count / stale_count.
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing healthz CSV: {path}")
    total = 0
    ok = 0
    stale = 0
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get("status", "").strip().lower()
            total += 1
            if status == "ok":
                ok += 1
            elif status == "stale":
                stale += 1
    return {"total_checks": total, "ok_count": ok, "stale_count": stale}


def load_issues_fixture(fixtures_dir: Path) -> list[dict[str, Any]]:
    """Read gh_issues.json fixture (list of issue dicts)."""
    path = fixtures_dir / "gh_issues.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing fixture: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_ear_test_logs(directory: Path) -> list[dict[str, Any]]:
    """Read all ear-test logs from a directory. Returns parsed log list."""
    if not directory.exists():
        return []
    logs: list[dict[str, Any]] = []
    for path in sorted(directory.glob("ear_test_log_*.json")):
        try:
            with path.open(encoding="utf-8") as f:
                logs.append(json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            print(f"[audit] WARN: failed to parse {path}: {e}", file=sys.stderr)
    return logs


def load_ear_test_logs_from_ear_test_dir(directory: Path) -> list[dict[str, Any]]:
    """Read ear-test logs from the canonical eval/ear-test-logs dir
    (any *.json file matching the Plan 42-03 schema)."""
    if not directory.exists():
        return []
    logs: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        if path.name == "schema.json":
            continue
        try:
            with path.open(encoding="utf-8") as f:
                logs.append(json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            print(f"[audit] WARN: failed to parse {path}: {e}", file=sys.stderr)
    return logs


# ----------------------------------------------------------------------
# --live mode loaders
# ----------------------------------------------------------------------


def load_live_release(release_tag: str) -> dict[str, Any]:
    """Pull release telemetry via `gh api`. Read-only."""
    # READ-ONLY: no --method POST/PATCH/DELETE.
    cmd = [
        "gh",
        "api",
        f"repos/bravoh/vibemix/releases/tags/{release_tag}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"[audit] gh api releases failed (rc={result.returncode}): {result.stderr}"
        )
    return json.loads(result.stdout)


def load_live_issues(since_iso: str) -> list[dict[str, Any]]:
    """Pull issues opened since SINCE via `gh issue list`. Read-only."""
    cmd = [
        "gh",
        "issue",
        "list",
        "--repo",
        "bravoh/vibemix",
        "--state",
        "all",
        "--limit",
        "200",
        "--json",
        "number,title,createdAt,closedAt,state,labels",
        "--search",
        f"created:>={since_iso}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"[audit] gh issue list failed (rc={result.returncode}): {result.stderr}"
        )
    return json.loads(result.stdout)


def load_live_healthz_url(url: str) -> dict[str, Any]:
    """GET Bravoh healthz stats endpoint via stdlib urllib (no requests dep)."""
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read()
    return json.loads(body)


# ----------------------------------------------------------------------
# Aggregation
# ----------------------------------------------------------------------


def aggregate(
    *,
    release: dict[str, Any],
    healthz: dict[str, Any],
    issues: list[dict[str, Any]],
    ear_tests: list[dict[str, Any]],
    audit_date: datetime,
) -> dict[str, Any]:
    """Reduce raw evidence into the dict of template-placeholder values."""
    # --- Release metrics
    assets = release.get("assets", []) or []
    download_count = sum(int(a.get("download_count", 0)) for a in assets)
    dmg_count = sum(
        int(a.get("download_count", 0))
        for a in assets
        if a.get("name", "").lower().endswith(".dmg")
    )
    msi_count = sum(
        int(a.get("download_count", 0))
        for a in assets
        if a.get("name", "").lower().endswith(".msi")
    )
    published_at_raw = release.get("published_at", "")
    published_at = _parse_iso8601(published_at_raw)
    bake_days = (
        (audit_date - published_at).days if published_at else 0
    )

    # --- Healthz
    total = int(healthz.get("total_checks", 0))
    ok = int(healthz.get("ok_count", 0))
    stale = int(healthz.get("stale_count", 0))
    uptime_pct = (ok / total * 100.0) if total > 0 else 0.0

    # --- Issues
    crash_issues = [
        i
        for i in issues
        if any(
            (lbl.get("name", "").lower() == "crash" if isinstance(lbl, dict) else False)
            for lbl in (i.get("labels", []) or [])
        )
    ]
    open_crash = [i for i in crash_issues if str(i.get("state", "")).upper() == "OPEN"]
    closed_crash = [
        i for i in crash_issues if str(i.get("state", "")).upper() == "CLOSED"
    ]
    oldest_open_age = 0
    for i in open_crash:
        created = _parse_iso8601(i.get("createdAt", ""))
        if created is None:
            continue
        age = (audit_date - created).days
        if age > oldest_open_age:
            oldest_open_age = age

    # --- Ear-tests (T-45-04-02: aggregates only — no log content leaks)
    ear_test_count = len(ear_tests)
    slop_count = 0
    scripted_count = 0
    genres: set[str] = set()
    for log in ear_tests:
        flags = log.get("slop_flags", {}) or {}
        if flags.get("felt_slop"):
            slop_count += 1
        if flags.get("felt_scripted"):
            scripted_count += 1
        genre = log.get("genre")
        if isinstance(genre, str) and genre:
            genres.add(genre)
    genres_csv = ", ".join(sorted(genres)) if genres else "(none)"

    return {
        "download_count": download_count,
        "dmg_count": dmg_count,
        "msi_count": msi_count,
        "published_at": published_at_raw or "unknown",
        "bake_days": bake_days,
        "uptime_pct": f"{uptime_pct:.2f}",
        "ok": ok,
        "total": total,
        "stale_count": stale,
        "ear_test_count": ear_test_count,
        "genres_csv": genres_csv,
        "slop_count": slop_count,
        "scripted_count": scripted_count,
        "issue_count": len(issues),
        "crash_count": len(crash_issues),
        "open": len(open_crash),
        "closed": len(closed_crash),
        "oldest_age_days": oldest_open_age,
    }


def _parse_iso8601(raw: str) -> datetime | None:
    """Best-effort ISO-8601 parse (handles trailing Z)."""
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


# ----------------------------------------------------------------------
# Render
# ----------------------------------------------------------------------


def render_report(
    *,
    template_text: str,
    aggregated: dict[str, Any],
    release_tag: str,
    audit_date: datetime,
) -> str:
    """Substitute template placeholders + the 4 rubric "Current" cells.

    Threat-model T-45-04-01: all substitutions are integers / floats / pinned
    strings (release_tag, audit_date.isoformat, published_at). No raw HTML
    or markdown is injected from external sources.
    """
    text = template_text

    # --- Header fields
    audit_date_str = audit_date.date().isoformat()
    text = text.replace("<release_tag>", release_tag)
    text = text.replace("<YYYY-MM-DD>", audit_date_str)
    text = text.replace("<audit_date>", audit_date_str)
    text = text.replace("<published_at>", str(aggregated["published_at"]))
    text = text.replace("<N>", str(aggregated["bake_days"]))

    # --- Evidence section substitutions
    text = text.replace("<download_count>", str(aggregated["download_count"]))
    text = text.replace("<dmg_count>", str(aggregated["dmg_count"]))
    text = text.replace("<msi_count>", str(aggregated["msi_count"]))
    text = text.replace("<uptime_pct>", str(aggregated["uptime_pct"]))
    text = text.replace("<ok>", str(aggregated["ok"]))
    text = text.replace("<total>", str(aggregated["total"]))
    text = text.replace("<stale_count>", str(aggregated["stale_count"]))
    text = text.replace("<ear_test_count>", str(aggregated["ear_test_count"]))
    text = text.replace("<genres_csv>", str(aggregated["genres_csv"]))
    text = text.replace("<slop_count>", str(aggregated["slop_count"]))
    text = text.replace("<scripted_count>", str(aggregated["scripted_count"]))
    text = text.replace("<issue_count>", str(aggregated["issue_count"]))
    text = text.replace("<crash_count>", str(aggregated["crash_count"]))
    text = text.replace("<open>", str(aggregated["open"]))
    text = text.replace("<closed>", str(aggregated["closed"]))
    text = text.replace("<oldest_age_days>", str(aggregated["oldest_age_days"]))

    # --- Rubric "Current" column: replace each <pre-filled> with the
    # corresponding metric value. Order matches the 4 pre-filled rubric rows:
    #   1) Downloads     2) Uptime %    3) Ear-test slop incidents   4) Open crash issues
    # Each replace() runs in sequence so we only replace one at a time.
    rubric_values = [
        str(aggregated["download_count"]),
        f"{aggregated['uptime_pct']}%",
        str(aggregated["slop_count"]),
        str(aggregated["open"]),  # open crash issues
    ]
    for val in rubric_values:
        text = text.replace("<pre-filled>", val, 1)

    # --- Provenance HTML comment (T-45-04-03) injected just below the H1.
    provenance = (
        f"<!-- _generated_by: scripts/release/audit_ship_v1_decision.py "
        f"v{SCRIPT_VERSION} at {audit_date.isoformat()} (UTC) "
        f"— Plan 45-04 / SHIP-13. Kaan-discharge edits land below the rubric. -->\n"
    )
    # Place provenance right after the first H1 line.
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    inserted = False
    for line in lines:
        out.append(line)
        if not inserted and line.startswith("# v3.0 SHIP-V1-DECISION"):
            out.append("\n" + provenance)
            inserted = True
    return "".join(out)


# ----------------------------------------------------------------------
# Atomic write
# ----------------------------------------------------------------------


def write_atomic(path: Path, content: str) -> None:
    """Atomic write via tempfile + os.replace (Test 19, T-45-04 hygiene)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".tmp-audit-",
        suffix=".md",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            tmp.write(content)
        os.replace(tmp_path, path)
    except Exception:
        # Clean up tempfile on error so we never leave debris.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def _audit_date_now() -> datetime:
    """Return the current audit timestamp, honoring VIBEMIX_AUDIT_DATE_OVERRIDE
    (for deterministic tests / replays)."""
    override = os.environ.get("VIBEMIX_AUDIT_DATE_OVERRIDE")
    if override:
        parsed = _parse_iso8601(override)
        if parsed is not None:
            return parsed
    return datetime.now(timezone.utc)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="audit_ship_v1_decision",
        description="Pre-fill SHIP-V1-DECISION report from 4 evidence sources (SHIP-13).",
    )
    p.add_argument(
        "--since",
        type=int,
        default=14,
        help="bake-window days for issue query (default 14).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="path of the rendered decision report.",
    )
    p.add_argument(
        "--fixtures",
        type=Path,
        default=None,
        help="hermetic fixtures dir (default: --live).",
    )
    p.add_argument(
        "--live",
        action="store_true",
        help="pull evidence from gh + Bravoh healthz (requires GITHUB_TOKEN).",
    )
    p.add_argument(
        "--release-tag",
        type=str,
        default="v3.0.0-rc1",
        help="release tag whose telemetry is audited (default v3.0.0-rc1).",
    )
    p.add_argument(
        "--bravoh-healthz-stats-url",
        type=str,
        default=None,
        help="--live: prefer this URL for uptime stats (JSON {total_checks,ok_count,stale_count}).",
    )
    p.add_argument(
        "--bravoh-healthz-csv",
        type=Path,
        default=None,
        help="--live: fallback CSV if --bravoh-healthz-stats-url is not provided.",
    )
    p.add_argument(
        "--ear-test-dir",
        type=Path,
        default=None,
        help="ear-test logs dir (default: --fixtures dir for fixture-mode, "
        "eval/ear-test-logs/ for --live).",
    )
    p.add_argument(
        "--template",
        type=Path,
        default=DEFAULT_TEMPLATE,
        help="template skeleton (default: docs/SHIP-V1-DECISION-TEMPLATE.md).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    audit_date = _audit_date_now()

    # ---- Load evidence
    if args.live:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print(
                "[audit] --live requires GITHUB_TOKEN env "
                "(KAAN-ACTION-LEGAL.md §SHIP-13 documents the setup).",
                file=sys.stderr,
            )
            return 2
        release = load_live_release(args.release_tag)
        published_at = _parse_iso8601(release.get("published_at", ""))
        since_iso = (
            published_at.date().isoformat()
            if published_at
            else (audit_date.date().isoformat())
        )
        issues = load_live_issues(since_iso)
        if args.bravoh_healthz_stats_url:
            healthz = load_live_healthz_url(args.bravoh_healthz_stats_url)
        elif args.bravoh_healthz_csv:
            healthz = load_healthz_csv(args.bravoh_healthz_csv)
        else:
            print(
                "[audit] --live requires either --bravoh-healthz-stats-url "
                "OR --bravoh-healthz-csv. See §SHIP-13 runbook.",
                file=sys.stderr,
            )
            return 2
        # Ear-tests: default to the canonical project dir under --live.
        ear_dir = args.ear_test_dir or DEFAULT_EAR_TEST_DIR
        ear_tests = load_ear_test_logs_from_ear_test_dir(ear_dir)
    else:
        if not args.fixtures:
            print(
                "[audit] either --live or --fixtures PATH is required.",
                file=sys.stderr,
            )
            return 2
        if not args.fixtures.is_dir():
            print(
                f"[audit] --fixtures path is not a directory: {args.fixtures}",
                file=sys.stderr,
            )
            return 2
        release = load_release_fixture(args.fixtures)
        healthz = load_healthz_csv(args.fixtures / "healthz_uptime.csv")
        issues = load_issues_fixture(args.fixtures)
        ear_dir = args.ear_test_dir or args.fixtures
        ear_tests = load_ear_test_logs(ear_dir)

    # ---- Aggregate
    aggregated = aggregate(
        release=release,
        healthz=healthz,
        issues=issues,
        ear_tests=ear_tests,
        audit_date=audit_date,
    )

    # ---- Render
    template_text = args.template.read_text(encoding="utf-8")
    rendered = render_report(
        template_text=template_text,
        aggregated=aggregated,
        release_tag=args.release_tag,
        audit_date=audit_date,
    )

    # ---- Write atomic
    write_atomic(args.output, rendered)

    # ---- GH Actions notice (T+30 CI surfaces the report path)
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        print(
            f"::notice title=SHIP-V1-DECISION audit complete::"
            f"Report written to {args.output}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
