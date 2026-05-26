# SPDX-License-Identifier: Apache-2.0
"""BENCH-01 — fake-client sweep + per-cell fail-safe (REAL-GREEN, flipped in Plan 02).

The runner takes the client by INJECTION (``library/agent.py:306`` idiom), so
the offline ``_FakeClient`` / ``_RaisingClient`` fixtures make the whole sweep
green with ZERO API calls (honest green). The Wave-0 ``xfail(strict=True)``
scaffolds flipped to real passes when Plan 02 landed ``vibemix.bench.run`` /
``vibemix.bench.matrix``.

The fail-safe (Pitfall 2): a per-cell error records ``result.error`` (non-None)
and the sweep CONTINUES to the next cell — never aborts, never fabricates
output. The floor study's real 429 billing block is the documented reason.
"""

from __future__ import annotations


def test_sweep_records_cells_zero_network(fake_client) -> None:
    """A study sweep with the FAKE client records one BenchResult per cell,
    each carrying prompt/output/dsp_snapshot/usage — and makes zero API calls.
    The fake client's call-spy proves the sweep actually issued the cells."""
    from vibemix.bench.matrix import STUDY_A
    from vibemix.bench.run import run_study

    results = run_study(STUDY_A, client=fake_client)
    assert len(results) == len(STUDY_A)
    assert len(fake_client.calls) == len(STUDY_A)  # offline only — spy proves it
    for r in results:
        assert r.prompt
        assert r.output  # canned cited line from the fake client
        assert r.dsp_snapshot is not None
        assert r.usage  # synthetic usage_metadata recorded
        assert r.error is None


def test_fail_safe_parks_cell_and_continues(raising_client) -> None:
    """With the raising client, each cell's error is recorded as result.error
    (non-None) and the sweep CONTINUES — no abort, no fabricated output."""
    from vibemix.bench.matrix import STUDY_A
    from vibemix.bench.run import run_study

    results = run_study(STUDY_A, client=raising_client)
    # The sweep did NOT abort: every cell produced a (parked) result.
    assert len(results) == len(STUDY_A)
    for r in results:
        assert r.error is not None  # the 429 was caught + parked
        assert not r.output  # NEVER fabricate output for a failed cell


def test_result_carries_usage_from_fake(fake_client) -> None:
    """Each recorded BenchResult carries the cell's usage tokens — the bench
    feeds these to SessionMeter for the real run's cost report."""
    from vibemix.bench.matrix import STUDY_A
    from vibemix.bench.run import run_study

    results = run_study(STUDY_A, client=fake_client)
    first = results[0]
    # The fake usage_metadata (prompt=1900, output=40, total=1940) flows through.
    assert first.usage.get("prompt_token_count") == 1900
    assert first.usage.get("candidates_token_count") == 40
    assert first.usage.get("total_token_count") == 1940


def test_study_a_records_nonzero_known_cost(fake_client) -> None:
    """WR-01: a STUDY_A cell (router alias ``library_auto_tag``, NOT a pricing
    key) must record a NON-ZERO KNOWN cost — the bench bills it against the
    ``live_coach`` pricing lane, not $0.00. Before the fix, the alias missed
    ROUTE_PRICING entirely → every STUDY_A cell billed $0.00 (cost-bounding
    silently no-op). Offline: the fake usage drives the meter, no live API."""
    from vibemix.bench.matrix import STUDY_A
    from vibemix.bench.run import run_study
    from vibemix.library.budget import get_session_meter

    meter = get_session_meter()
    meter.reset()
    run_study(STUDY_A, client=fake_client)
    summary = meter.summary()
    # STUDY_A's aliases all bill against live_coach — the known-priced lane.
    assert "live_coach" in summary["per_path"]
    # Real spend is reported, not the silent $0.00 of the alias-miss bug.
    assert summary["total_cost_eur"] > 0.0
    meter.reset()


def test_none_text_response_parks_cell(no_text_client) -> None:
    """WR-02: a blocked / no-text candidate (resp.text is None) is coerced into
    the PARKED state — output=="" + a descriptive error — never a fabricated
    success (output=None, error=None). The default fake client returns a string,
    so this no-text client is what exercises the contract offline."""
    from vibemix.bench.matrix import STUDY_A
    from vibemix.bench.run import run_study

    results = run_study(STUDY_A, client=no_text_client)
    assert len(results) == len(STUDY_A)
    for r in results:
        assert r.output == ""  # parked — never None, never fabricated
        assert r.error is not None  # descriptive parked reason recorded
        assert "no text candidate" in r.error


