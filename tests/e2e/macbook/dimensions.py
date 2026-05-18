"""Phase 50 — five-dimension structured results for e2e report.html.

Each dimension records its own pass/fail count + summary. Overall status is
the worst-of across dimensions (FAIL > PARTIAL > SKIPPED > PASS).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

DimensionStatus = Literal["PASS", "FAIL", "PARTIAL", "SKIPPED"]

_STATUS_RANK = {"FAIL": 3, "PARTIAL": 2, "SKIPPED": 1, "PASS": 0}


@dataclass
class Dimension:
    """One row in the report.html dimension table."""

    name: str
    status: DimensionStatus = "PASS"
    total: int = 0
    passed: int = 0
    summary: str = ""
    details: list[dict] = field(default_factory=list)

    def record(self, ok: bool, label: str, **meta) -> None:
        """Record one assertion. Updates total/passed + appends to details."""
        self.total += 1
        if ok:
            self.passed += 1
        self.details.append({"ok": ok, "label": label, **meta})
        if not ok and self.status == "PASS":
            self.status = "FAIL"


@dataclass
class Functional(Dimension):
    name: str = "Functional"


@dataclass
class Visual(Dimension):
    name: str = "Visual"


@dataclass
class Aesthetic(Dimension):
    name: str = "Aesthetic"


@dataclass
class Usability(Dimension):
    name: str = "Usability"


@dataclass
class Hallucination(Dimension):
    name: str = "Hallucination"


@dataclass
class EeRun:
    """Top-level e2e run container; one per CI invocation or local walk."""

    run_id: str
    out_dir: Path
    build_sha: str = ""
    dmg_path: str = ""
    duration_s: float = 0.0
    functional: Functional = field(default_factory=Functional)
    visual: Visual = field(default_factory=Visual)
    aesthetic: Aesthetic = field(default_factory=Aesthetic)
    usability: Usability = field(default_factory=Usability)
    hallucination: Hallucination = field(default_factory=Hallucination)
    privacy_ok: bool = True
    anti_slop_ok: bool = True

    @property
    def dimensions(self) -> list[Dimension]:
        return [
            self.functional,
            self.visual,
            self.aesthetic,
            self.usability,
            self.hallucination,
        ]

    def overall_status(self) -> DimensionStatus:
        return compute_overall_status([d.status for d in self.dimensions])


def compute_overall_status(statuses: list[DimensionStatus]) -> DimensionStatus:
    """Worst-of across dimensions. FAIL > PARTIAL > SKIPPED > PASS."""
    if not statuses:
        return "SKIPPED"
    worst = max(statuses, key=lambda s: _STATUS_RANK.get(s, 0))
    return worst


def make_run_id(now: datetime | None = None) -> str:
    """UTC stamp format: %Y-%m-%dT%H-%M-%SZ (colon-free for filesystem use)."""
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H-%M-%SZ")
