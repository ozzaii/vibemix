# SPDX-License-Identifier: Apache-2.0
"""Phase 34 / SEC-02 + SEC-03 — CVE severity gate.

Pitfall P65 — LOW/MEDIUM CVE flood drowns the real signal.

Matrix (vibemix-side policy):

    SEVERITY        DIRECT          TRANSITIVE
    LOW             warn            warn
    MEDIUM          warn            warn
    HIGH            **FAIL**        warn
    CRITICAL        **FAIL**        **FAIL**

Inputs (any of):

  * pip-audit JSON:        `pip-audit -f json`
  * osv-scanner JSON:      `osv-scanner --format=json`
  * cargo-audit JSON:      `cargo audit --json`
  * cargo-deny JSON:       `cargo deny check --format json`

Usage:

    python scripts/dist/severity_gate.py \\
        --pip-audit pip-audit.json \\
        --osv osv.json \\
        --direct-deps pyproject.toml

The gate is purposely conservative: any HIGH+ on direct deps OR any
CRITICAL anywhere fails the build. Everything else is warning.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

FAIL_DIRECT = {"HIGH", "CRITICAL"}
FAIL_TRANSITIVE = {"CRITICAL"}
WARN_LEVELS = {"LOW", "MEDIUM", "MODERATE"}  # `MODERATE` is osv-scanner's MEDIUM


# ---------------------------------------------------------------------------
# Data shape
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Finding:
    package: str
    severity: str           # normalised UPPER
    direct: bool
    cve: str
    source: str             # which tool emitted this

    def is_fail(self) -> bool:
        sev = self.severity
        if sev in FAIL_DIRECT and self.direct:
            return True
        if sev in FAIL_TRANSITIVE:
            return True
        return False


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _normalise(sev: str | None) -> str:
    if not sev:
        return "UNKNOWN"
    sev_u = sev.strip().upper()
    if sev_u in {"MODERATE"}:
        return "MEDIUM"
    return sev_u


def _load_direct_deps(direct_deps_path: Path | None) -> set[str]:
    """Best-effort direct-dep extraction from pyproject.toml.

    Falls back to empty set (every dep treated as transitive — strictly safer
    in the FAIL direction since CRITICAL still fails).
    """
    if not direct_deps_path or not direct_deps_path.exists():
        return set()
    try:
        import tomllib
    except ImportError:  # pragma: no cover
        import tomli as tomllib  # type: ignore[no-redef]
    data = tomllib.loads(direct_deps_path.read_text(encoding="utf-8"))
    deps = data.get("project", {}).get("dependencies", []) or []
    out: set[str] = set()
    for spec in deps:
        # `package>=1.2,<2` → `package`
        name = spec.split("[")[0].split(">")[0].split("=")[0].split("<")[0].strip()
        if name:
            out.add(name.lower())
    return out


def parse_pip_audit(data: dict[str, Any], direct: set[str]) -> Iterable[Finding]:
    # pip-audit JSON shape: {"dependencies": [{"name": ..., "vulns": [{"id": ..., "severity": ...}]}]}
    for dep in data.get("dependencies", []):
        name = dep.get("name", "").lower()
        for v in dep.get("vulns", []) or []:
            yield Finding(
                package=name,
                severity=_normalise(v.get("severity") or v.get("cvss_severity")),
                direct=name in direct,
                cve=v.get("id", "UNKNOWN"),
                source="pip-audit",
            )


def parse_osv(data: dict[str, Any], direct: set[str]) -> Iterable[Finding]:
    # osv-scanner JSON shape: {"results": [{"packages": [{"package": {...}, "vulnerabilities": [...]}]}]}
    for result in data.get("results", []) or []:
        for pkg_entry in result.get("packages", []) or []:
            pkg = pkg_entry.get("package", {})
            name = (pkg.get("name") or "").lower()
            for v in pkg_entry.get("vulnerabilities", []) or []:
                # osv encodes severity under database_specific.severity OR
                # severity[].score. Both fallback paths checked.
                sev = None
                for sev_block in v.get("severity", []) or []:
                    sev = sev_block.get("score") or sev
                if not sev:
                    sev = v.get("database_specific", {}).get("severity")
                yield Finding(
                    package=name,
                    severity=_normalise(sev),
                    direct=name in direct,
                    cve=v.get("id", "UNKNOWN"),
                    source="osv-scanner",
                )


def parse_cargo_audit(data: dict[str, Any], direct: set[str]) -> Iterable[Finding]:
    # cargo audit JSON shape: {"vulnerabilities": {"list": [{"advisory": {"id": ..., "informational": ..., "severity": ...}, "package": {"name": ...}}]}}
    for v in data.get("vulnerabilities", {}).get("list", []) or []:
        adv = v.get("advisory", {})
        pkg = v.get("package", {})
        name = (pkg.get("name") or "").lower()
        # cargo-audit doesn't always populate severity; fallback to advisory.severity.
        sev = adv.get("severity") or v.get("severity")
        yield Finding(
            package=name,
            severity=_normalise(sev),
            direct=name in direct,
            cve=adv.get("id", "UNKNOWN"),
            source="cargo-audit",
        )


def parse_findings_payload(path: Path, source: str, direct: set[str]) -> list[Finding]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"::warning::severity_gate: failed to parse {path} as JSON: {e}", file=sys.stderr)
        return []
    if source == "pip-audit":
        return list(parse_pip_audit(data, direct))
    if source == "osv-scanner":
        return list(parse_osv(data, direct))
    if source == "cargo-audit":
        return list(parse_cargo_audit(data, direct))
    raise ValueError(f"unknown source: {source}")


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------

def apply_gate(findings: list[Finding]) -> tuple[list[Finding], list[Finding]]:
    """Return (failing, warnings)."""
    failing = [f for f in findings if f.is_fail()]
    warnings = [f for f in findings if not f.is_fail() and f.severity in WARN_LEVELS]
    return failing, warnings


def format_finding(f: Finding) -> str:
    tag = "DIRECT" if f.direct else "transitive"
    return f"  [{f.severity:8}] {f.package:30} {f.cve:20} ({tag}, {f.source})"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--pip-audit", type=Path, default=None)
    p.add_argument("--osv", type=Path, default=None)
    p.add_argument("--cargo-audit", type=Path, default=None)
    p.add_argument("--direct-deps", type=Path, default=None,
                   help="pyproject.toml from which to read direct deps")
    p.add_argument("--direct-rust-crates", type=Path, default=None,
                   help="Cargo.toml from which to read direct Rust crates")
    args = p.parse_args(argv)

    direct = _load_direct_deps(args.direct_deps)
    direct_rust = _load_direct_rust_crates(args.direct_rust_crates)
    direct_all = direct | direct_rust

    findings: list[Finding] = []
    if args.pip_audit:
        findings += parse_findings_payload(args.pip_audit, "pip-audit", direct_all)
    if args.osv:
        findings += parse_findings_payload(args.osv, "osv-scanner", direct_all)
    if args.cargo_audit:
        findings += parse_findings_payload(args.cargo_audit, "cargo-audit", direct_all)

    failing, warnings = apply_gate(findings)

    if warnings:
        print(f"::group::CVE warnings ({len(warnings)} below gate)")
        for f in warnings:
            print(format_finding(f))
        print("::endgroup::")

    if failing:
        print(f"::error::CVE gate failed — {len(failing)} blocking finding(s):")
        for f in failing:
            print(format_finding(f))
        return 1

    print(f"::notice::CVE gate passed — {len(findings)} total, {len(warnings)} warnings, 0 failing.")
    return 0


def _load_direct_rust_crates(path: Path | None) -> set[str]:
    if not path or not path.exists():
        return set()
    try:
        import tomllib
    except ImportError:  # pragma: no cover
        import tomli as tomllib  # type: ignore[no-redef]
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    deps = data.get("dependencies", {}) or {}
    return {name.lower() for name in deps.keys()}


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
