"""Phase 50 — renderer smoke test + locked section labels + anti-slop probe."""

from __future__ import annotations

from pathlib import Path

from tests.e2e.macbook.dimensions import EeRun, make_run_id
from tests.e2e.macbook.render_report import render

LOCKED_SECTION_LABELS = ["Functional", "Visual", "Aesthetic", "Usability", "Hallucination"]

# Banned vocabulary (subset of canonical blocklist) — verifies template prose.
BANNED_TOKENS = [
    "deeply",
    "seamlessly",
    "effortlessly",
    "thoughtfully",
    "crafted",
    "curated",
    "unleashes",
    "empowers",
    "delight",
]


def _sample_run() -> EeRun:
    run = EeRun(run_id=make_run_id(), out_dir=Path("."))
    run.build_sha = "abcdef1"
    run.dmg_path = "/Applications/vibemix.app"
    run.duration_s = 12.4
    for dim in run.dimensions:
        dim.record(True, f"{dim.name.lower()}-check-1")
        dim.record(True, f"{dim.name.lower()}-check-2")
        dim.summary = "all green"
    return run


def test_render_writes_report_html(tmp_path: Path) -> None:
    run = _sample_run()
    path = render(run, out_root=tmp_path)
    assert path.exists(), "render did not produce report.html"
    assert path.name == "report.html"


def test_report_contains_all_locked_section_labels(tmp_path: Path) -> None:
    run = _sample_run()
    path = render(run, out_root=tmp_path)
    text = path.read_text(encoding="utf-8")
    for label in LOCKED_SECTION_LABELS:
        assert label in text, f"locked label '{label}' missing from report.html"


def test_report_status_pill_renders_overall(tmp_path: Path) -> None:
    run = _sample_run()
    path = render(run, out_root=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert 'class="pill PASS"' in text, "overall status pill not rendered"


def test_report_fail_dimension_propagates_to_overall(tmp_path: Path) -> None:
    run = _sample_run()
    run.functional.record(False, "intentional-fail")
    path = render(run, out_root=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert 'class="pill FAIL"' in text, "FAIL did not propagate to overall pill"


def test_report_no_banned_tokens(tmp_path: Path) -> None:
    run = _sample_run()
    path = render(run, out_root=tmp_path)
    text = path.read_text(encoding="utf-8").lower()
    for token in BANNED_TOKENS:
        assert token not in text, f"banned token '{token}' found in report.html"
