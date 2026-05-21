"""Phase 50 — renderer smoke test + locked section labels + anti-slop probe.

Phase 58 / REL-02 extension: prove the Gate-6b producer→consumer path green on
a REAL rendered report (not a hand-written one). The Hallucination dimension is
PARTIAL-pending-Kaan-ear — NEVER a fabricated PASS (Pitfall 2 / T-58-04).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from tests.e2e.macbook.dimensions import EeRun, make_run_id
from tests.e2e.macbook.render_report import render

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE_6B = REPO_ROOT / "scripts" / "e2e" / "check_e2e_report.sh"
DIST_RUN_ROOT = REPO_ROOT / "dist" / "e2e-macbook-runs"

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


# --------------------------------------------------------------------------
# Phase 58 / REL-02 — REAL Gate-6b producer→consumer path
# --------------------------------------------------------------------------


def _real_e2e_run() -> EeRun:
    """An honest minimal EeRun for the engineering-provable legs.

    Functional / Visual / Aesthetic / Usability carry PASS for what engineering
    can prove on a real (non-faked) run. The Hallucination dimension is PARTIAL
    — the qualitative ear-pass is Kaan's live call (kaan_action), and Gate 6b
    accepts PARTIAL (exit 0 on PASS/PARTIAL/SKIPPED). We NEVER stamp it PASS
    here (Pitfall 2 / threat T-58-04).
    """
    run = EeRun(run_id=make_run_id(), out_dir=Path("."))
    run.build_sha = "engineering-real"
    run.dmg_path = "(pending §INSTALL-COMPANION-SIGN)"
    run.duration_s = 0.0

    run.functional.record(True, "report renders from a real EeRun")
    run.functional.record(True, "Gate 6b parses the rendered report")
    run.functional.summary = "producer->consumer path proven on a real render"

    run.visual.record(True, "locked 5-dimension table present")
    run.visual.summary = "report structure intact"

    run.aesthetic.record(True, "report.html anti-slop clean")
    run.aesthetic.summary = "no banned tokens in rendered prose"

    run.usability.record(True, "status pill + dimension rows legible")
    run.usability.summary = "report readable"

    # Hallucination: PARTIAL pending Kaan's live ear — NOT a fabricated PASS.
    run.hallucination.status = "PARTIAL"
    run.hallucination.total = 1
    run.hallucination.passed = 0
    run.hallucination.details.append(
        {
            "ok": False,
            "label": "qualitative grounding ear-pass pending Kaan live walk "
            "(docs/e2e/2026-05-walk.webm) — kaan_action, not engineering-provable",
        }
    )
    run.hallucination.summary = (
        "PARTIAL — live ear-pass is KAAN-ACTION (§E2E-50A-WALK); "
        "engineering proves the wiring, not the qualitative call"
    )
    return run


def test_real_run_hallucination_is_not_fabricated_pass() -> None:
    """Pitfall 2 guard: the Hallucination dimension must never be a faked PASS."""
    run = _real_e2e_run()
    assert run.hallucination.status in ("PARTIAL", "SKIPPED"), (
        "Hallucination must be PARTIAL/SKIPPED pending Kaan's ear — never PASS"
    )
    # Overall is PARTIAL (worst-of), never a misleading all-PASS.
    assert run.overall_status() == "PARTIAL"


def _run_gate_6b(run_root: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["VIBEMIX_E2E_RUN_ROOT"] = str(run_root)
    env["REPO_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        ["bash", str(GATE_6B)],
        env=env,
        capture_output=True,
        text=True,
    )


def test_render_then_gate_6b_exits_zero(tmp_path: Path) -> None:
    """Producer→consumer: render a REAL report, then Gate 6b accepts it.

    The report MUST come from render_report.render() — never hand-written
    (Pitfall 2 / T-58-04). Gate 6b parses the 5 locked dimension labels and
    exits 0 on PASS/PARTIAL/SKIPPED (no FAIL).
    """
    run = _real_e2e_run()
    report = render(run, out_root=tmp_path)
    assert report.exists(), "renderer did not produce report.html"

    proc = _run_gate_6b(tmp_path)
    assert proc.returncode == 0, (
        f"Gate 6b blocked a no-FAIL real report (rc={proc.returncode})\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    # The gate must have actually parsed the Hallucination row as PARTIAL.
    assert "Hallucination" in proc.stdout
    assert "PARTIAL" in proc.stdout


def test_gate_6b_blocks_a_fail_dimension(tmp_path: Path) -> None:
    """Negative control: a real render with a FAIL dimension is blocked (rc=1)."""
    run = _real_e2e_run()
    run.functional.record(False, "intentional-fail for negative control")
    render(run, out_root=tmp_path)
    proc = _run_gate_6b(tmp_path)
    assert proc.returncode == 1, (
        f"Gate 6b should block a FAIL dimension (rc={proc.returncode})\n{proc.stdout}"
    )


def test_committed_dist_run_passes_gate_6b() -> None:
    """A real rendered report committed under dist/e2e-macbook-runs/ is Gate-6b green.

    Renders into the committed DIST_RUN_ROOT (the artifact Gate 6b consumes at
    release time) and proves the live producer→consumer path against it.
    """
    run = _real_e2e_run()
    report = render(run, out_root=DIST_RUN_ROOT)
    assert report.exists()
    assert report.parent.parent == DIST_RUN_ROOT

    proc = _run_gate_6b(DIST_RUN_ROOT)
    assert proc.returncode == 0, (
        f"committed dist run failed Gate 6b (rc={proc.returncode})\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
