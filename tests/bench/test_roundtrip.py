# SPDX-License-Identifier: Apache-2.0
"""WR-04 — the serialize↔read contract for a JSON-reloaded bench cell.

``results_to_json`` writes the cell as a NESTED dict (``result["cell"]["lens"]``).
The eval/review readers must reach INTO ``result["cell"]`` — before the fix they
read top-level keys, so a JSON-reloaded cell always scored lens ``"hype"`` and
grouped under ``_UNGROUPED`` (the fallback), silently mis-scoring a real run
reloaded from the persisted artifact.

These tests round-trip a real BenchResult through ``results_to_json`` +
``json.loads`` and assert the reloaded dict scores its REAL lens + groups by its
REAL grounding — pure, offline, no API.
"""

from __future__ import annotations

import json

from tests.bench.conftest import _grounded_snapshot


def _roundtrip_cell(**axes):
    """Serialize a single BenchResult and return the reloaded dict stand-in."""
    from vibemix.bench.cell import BenchCell, BenchResult
    from vibemix.bench.run import results_to_json

    cell = BenchCell(
        model_path=axes.get("model_path", "library_auto_tag"),
        grounding=axes.get("grounding", "audio+dsp+traj+genre"),
        prompting=axes.get("prompting", "structured"),
        contexting=axes.get("contexting", "trajectory"),
        lens=axes.get("lens", "critique"),
        taste=axes.get("taste", "with_rubric"),
    )
    result = BenchResult(
        prompt="p",
        output="that 128 bpm 303 line opened up [aud:bpm@0.0]",
        dsp_snapshot=_grounded_snapshot(),
        usage={},
        error=None,
        cell=cell,
    )
    return json.loads(results_to_json([result]))[0]


def test_reloaded_cell_scores_real_lens() -> None:
    """WR-04: a JSON-reloaded cell scores its REAL lens (``critique``), not the
    ``"hype"`` fallback — the eval reader reaches into the nested cell dict."""
    from vibemix.bench.eval import _lens_of

    reloaded = _roundtrip_cell(lens="critique")
    assert _lens_of(reloaded) == "critique"


def test_reloaded_cell_groups_by_real_grounding() -> None:
    """WR-04: a JSON-reloaded cell groups under its REAL grounding axis, not the
    ``_UNGROUPED`` fallback — the review reader reaches into the nested cell."""
    from vibemix.bench.eval import score_cell
    from vibemix.bench.review import _UNGROUPED, _group_key

    reloaded = _roundtrip_cell(grounding="audio+dsp+traj+genre")
    key = _group_key(score_cell(reloaded), reloaded)
    assert key == "audio+dsp+traj+genre"
    assert key != _UNGROUPED


def test_reloaded_cell_renders_real_coordinates() -> None:
    """WR-04: the rendered coordinates line shows the reloaded cell's real axes,
    not ``?`` placeholders — coordinates read the nested cell dict too."""
    from vibemix.bench.review import _coordinates_line

    reloaded = _roundtrip_cell(
        model_path="library_auto_tag", grounding="audio+dsp", lens="tutor"
    )
    line = _coordinates_line(reloaded)
    assert line is not None
    assert "grounding=`audio+dsp`" in line
    assert "lens=`tutor`" in line
    assert "model=`library_auto_tag`" in line
