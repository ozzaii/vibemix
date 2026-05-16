# SPDX-License-Identifier: Apache-2.0
"""Phase 41 Plan 41-06 / LAT-09 — scaffold sanity tests for the Gemini
3.1 Flash Live music spike.

What this guards:

1. Spike framework cannot be deleted by accident (template + script +
   harness all required).
2. Spike model literal ``gemini-3.1-flash-live-preview`` must NOT leak
   from spikes/ into src/vibemix/ — the Plan 41-01 grep gate scopes to
   src/vibemix/ so the literal is allowed in spikes/ but redundant
   pytest assertion catches it earlier in the dev loop.
3. The Kaan-action discharge runbook stays aligned with the spike script
   entry point (operator wouldn't be able to follow stale steps).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]

VERDICT_TEMPLATE = REPO_ROOT / "spikes" / "gemini-3-1-flash-live-music.md"
RECORDING_HARNESS = REPO_ROOT / "spikes" / "scripts" / "recording_harness.py"
SPIKE_RUNNER = REPO_ROOT / "spikes" / "scripts" / "run_live_spike.py"
KAAN_ACTION_PROXY = REPO_ROOT / ".planning" / "KAAN-ACTION-PROXY.md"

# Required H2 section headers in the verdict template (per Plan 41-06
# must_haves: Setup / Measurements / Anti-Hallucination Behavior /
# Session Cap Workaround Status / Verdict / Rationale).
REQUIRED_SECTIONS: tuple[str, ...] = (
    "## Setup",
    "## Measurements",
    "## Anti-Hallucination Behavior",
    "## Session Cap Workaround Status",
    "## Verdict",
    "## Rationale",
)

# Spike model literal — present in spikes/, banned in src/vibemix/.
LIVE_MODEL_LITERAL = "gemini-3.1-flash-live-preview"


# ---------------------------------------------------------------------------
# Scaffold existence + structure
# ---------------------------------------------------------------------------


def test_verdict_template_exists_with_all_sections() -> None:
    """All 6 H2 sections present in the verdict template."""
    assert VERDICT_TEMPLATE.exists(), (
        f"missing verdict template: {VERDICT_TEMPLATE}"
    )
    text = VERDICT_TEMPLATE.read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        assert section in text, (
            f"verdict template missing required H2 section: {section!r}"
        )


def test_verdict_template_status_starts_engineering_scaffolded() -> None:
    """Status field must be ``engineering-scaffolded`` until the discharge
    flow runs and Kaan flips it to ``verdict-written``."""
    text = VERDICT_TEMPLATE.read_text(encoding="utf-8")
    assert "**Status:** engineering-scaffolded" in text, (
        "verdict template must declare Status: engineering-scaffolded at scaffold time"
    )


# ---------------------------------------------------------------------------
# Importability
# ---------------------------------------------------------------------------


def test_recording_harness_module_importable() -> None:
    """``import spikes.scripts.recording_harness`` succeeds and exposes
    the ``RecordingHarness`` class."""
    import spikes.scripts.recording_harness as mod

    assert hasattr(mod, "RecordingHarness")
    assert callable(mod.RecordingHarness)


def test_run_live_spike_module_importable() -> None:
    """The spike entry point imports cleanly and carries the live model
    literal as a module-level constant."""
    import spikes.scripts.run_live_spike as mod

    assert mod.SPIKE_MODEL_ID == LIVE_MODEL_LITERAL


# ---------------------------------------------------------------------------
# CLI behavior
# ---------------------------------------------------------------------------


def test_run_live_spike_help_renders() -> None:
    """``python -m spikes.scripts.run_live_spike --help`` exits 0 and
    advertises the ``--duration-s`` flag."""
    proc = subprocess.run(
        [sys.executable, "-m", "spikes.scripts.run_live_spike", "--help"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    assert proc.returncode == 0, (
        f"--help non-zero exit (rc={proc.returncode})\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert "duration-s" in proc.stdout


def test_run_live_spike_exits_cleanly_without_api_key() -> None:
    """Without ``GEMINI_API_KEY`` set, the smoke-import path returns 0
    and prints an informational hint pointing operators at the runbook."""
    env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
    # Belt-and-suspenders: blank value also triggers the hint branch.
    env["GEMINI_API_KEY"] = ""
    proc = subprocess.run(
        [sys.executable, "-m", "spikes.scripts.run_live_spike", "--duration-s", "1"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=30,
    )
    combined = proc.stdout + proc.stderr
    assert proc.returncode == 0, (
        f"smoke-import path must exit 0 (rc={proc.returncode})\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert "GEMINI_API_KEY" in combined, (
        f"missing operator hint in output:\n{combined}"
    )


# ---------------------------------------------------------------------------
# Kaan-action discharge runbook
# ---------------------------------------------------------------------------


def test_kaan_action_proxy_has_lat09() -> None:
    """``§LAT-09`` runbook exists and references the spike entry point."""
    assert KAAN_ACTION_PROXY.exists(), (
        f"missing discharge surface: {KAAN_ACTION_PROXY}"
    )
    text = KAAN_ACTION_PROXY.read_text(encoding="utf-8")
    assert "§LAT-09" in text, "KAAN-ACTION-PROXY missing §LAT-09 section"
    assert "run_live_spike" in text, (
        "§LAT-09 runbook must reference the spike entry point script"
    )
    # Sanity: the runbook must include step-by-step instructions, not just a header.
    assert "How to discharge" in text or "discharge" in text.lower(), (
        "§LAT-09 must include discharge instructions"
    )


# ---------------------------------------------------------------------------
# CI gate boundary — model literal location enforcement
# ---------------------------------------------------------------------------


def test_live_model_id_NOT_in_src_vibemix() -> None:
    """The spike model literal MUST NOT appear anywhere in
    ``src/vibemix/`` — including the allowlisted _router_config.py.
    Positive defense against accidental promotion of the spike model
    to a runtime SKU. Mirrors the Plan 41-01 grep gate behavior for
    this specific literal."""
    scope = REPO_ROOT / "src" / "vibemix"
    offending: list[Path] = []
    for py_path in scope.rglob("*.py"):
        text = py_path.read_text(encoding="utf-8")
        if LIVE_MODEL_LITERAL in text:
            offending.append(py_path.relative_to(REPO_ROOT))
    assert not offending, (
        f"spike literal {LIVE_MODEL_LITERAL!r} leaked into src/vibemix/: "
        f"{offending}. Live remains spike-only per Phase 41 CONTEXT.md."
    )


def test_live_model_id_allowed_in_spikes() -> None:
    """The spike script MUST carry the literal — if someone gutted the
    script accidentally, this test catches it before CI."""
    assert SPIKE_RUNNER.exists()
    text = SPIKE_RUNNER.read_text(encoding="utf-8")
    assert LIVE_MODEL_LITERAL in text, (
        f"spike runner {SPIKE_RUNNER.name} must carry the literal "
        f"{LIVE_MODEL_LITERAL!r} — without it the spike isn't actually "
        "exercising Gemini 3.1 Flash Live."
    )
