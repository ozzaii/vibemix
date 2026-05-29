# SPDX-License-Identifier: Apache-2.0
"""``library doctor`` — the capability self-check.

The recurring "every module is failing" report is usually a stale build or a
missing optional piece. ``doctor`` turns the manual liveness probing into one
runnable command. These tests pin the runner CONTRACT (structured report,
never-raises, honest aggregation) — the individual probes are best-effort
environment inspections exercised against whatever env the test runs in.
"""

from __future__ import annotations

from vibemix.library import doctor


def test_run_doctor_returns_structured_report() -> None:
    report = doctor.run_doctor()
    assert set(report) == {"checks", "ok_count", "total", "all_ok", "deep"}
    assert report["total"] == len(doctor.CHECKS)
    assert report["ok_count"] == sum(1 for c in report["checks"] if c["ok"])
    assert report["all_ok"] == (report["ok_count"] == report["total"])
    for c in report["checks"]:
        assert set(c) >= {"name", "ok", "detail", "fix"}
        assert isinstance(c["ok"], bool)
        assert isinstance(c["name"], str) and c["name"]


def test_run_doctor_captures_a_crashing_probe_instead_of_raising(monkeypatch) -> None:
    """A probe that blows up must become a FAILED check, never propagate — a
    diagnostic that crashes is useless exactly when you need it most."""

    def _boom() -> dict:
        raise RuntimeError("kaboom 8842")

    monkeypatch.setattr(doctor, "CHECKS", (doctor.check_web_search, _boom))
    report = doctor.run_doctor()  # must not raise
    assert report["total"] == 2
    crashed = [c for c in report["checks"] if c["name"] == "_boom"]
    assert len(crashed) == 1
    assert crashed[0]["ok"] is False
    assert "kaboom 8842" in crashed[0]["detail"]


def test_clap_runtime_and_dj_knowledge_probes_are_present() -> None:
    """The two checks that map to this session's real failures (the
    onnxruntime ModuleNotFoundError + the orphaned-knowledge-store dim mismatch)
    must be in the board — they're the whole reason doctor exists."""
    names = {fn().get("name") for fn in doctor.CHECKS}
    assert "clap_runtime" in names
    assert "dj_knowledge" in names


def test_deep_mode_adds_functional_probes_on_top_of_presence_checks() -> None:
    """``--deep`` runs the functional probes (a real end-to-end search) ON TOP
    of the presence checks — the definitive 'is it actually working' answer that
    presence checks alone can't give (an orphaned store passes presence, fails
    function). The deep report must be a superset and carry the deep flag."""
    shallow = doctor.run_doctor()
    deep = doctor.run_doctor(deep=True)
    assert shallow["deep"] is False
    assert deep["deep"] is True
    assert deep["total"] == shallow["total"] + len(doctor.DEEP_CHECKS)
    assert "search_live" in {c["name"] for c in deep["checks"]}
    assert "search_live" not in {c["name"] for c in shallow["checks"]}


def test_format_report_is_readable_and_flags_failures() -> None:
    report = {
        "checks": [
            {"name": "clap_runtime", "ok": True, "detail": "importable", "fix": ""},
            {"name": "web_search", "ok": False, "detail": "no key", "fix": "set TAVILY_API_KEY"},
        ],
        "ok_count": 1,
        "total": 2,
        "all_ok": False,
    }
    out = doctor.format_report(report)
    assert "1/2 ok" in out
    assert "[ok] clap_runtime" in out
    assert "[!!] web_search" in out
    assert "fix: set TAVILY_API_KEY" in out  # the fix is surfaced for failures
