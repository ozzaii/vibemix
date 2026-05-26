# SPDX-License-Identifier: Apache-2.0
"""run_study — the injected-client runner + per-cell fail-safe + recorder.

The runner takes the genai client by INJECTION (``library/agent.py:306`` idiom),
so the offline ``_FakeClient`` makes the whole sweep green with ZERO API
(honest green). The real run swaps in a funded ``genai.Client`` via the
``vibemix bench run`` CLI.

THE 429 FAIL-SAFE (RESEARCH Pitfall 2, MANDATORY): each cell's
``generate_content`` is wrapped in ``try/except Exception`` → on error the cell
records ``error=repr(e)[:160]``, ``output=""``, and the sweep CONTINUES to the
next cell — never aborts, NEVER fabricates output. The floor study's real 429
billing block is the documented reason. A failed cell parks as a KAAN-ACTION.

Cost is bounded via ``SessionMeter.record`` on every successful real call.

Documented produce step:

    uv run python -m vibemix bench run --study A
"""

from __future__ import annotations

import concurrent.futures
import json
import os
from pathlib import Path

from vibemix.bench.assemble import build_cell_prompt
from vibemix.bench.cell import BenchCell, BenchResult
from vibemix.library.budget import ROUTE_PRICING, get_session_meter

__all__ = ["run_study", "resolve_track_path", "results_to_json"]

# WR-03: hard wall-clock per real generate_content call (mirrors
# library/agent.py:GEMINI_CALL_TIMEOUT_S). A silent network/server hang short
# of an HTTP error never blocks the whole sweep forever — the timeout raises,
# the existing per-cell fail-safe parks the cell, and the sweep CONTINUES.
_BENCH_CALL_TIMEOUT_S = 60.0


def _pricing_path_for(model_alias: str) -> str:
    """Map a bench cell's router ALIAS to a ``ROUTE_PRICING`` key for billing.

    WR-01: ``meter.record`` prices by ``ROUTE_PRICING.get(path)``, whose keys are
    billing lanes (``live_coach`` / ``debrief`` / ``embedding`` …) — NOT the
    full router-alias set. The bench's reaction-model aliases (``library_auto_tag``
    for the whole STUDY_A sweep, plus ``live_coach``) would otherwise fall into
    the ``rate is None`` branch → every cell billing $0.00 and the cost summary
    silently under-reporting the real spend (defeating the cost-bounding gate).

    Aliases that ARE pricing keys (e.g. ``live_coach``) bill against themselves;
    any other reaction-model alias bills against ``live_coach`` as the
    conservative reaction-model proxy (it carries the highest output rate of the
    live lanes, so worst-case spend is never under-stated). No model LITERAL is
    introduced — only router-path / pricing-lane names.
    """
    if model_alias in ROUTE_PRICING:
        return model_alias
    return "live_coach"


def _bench_data_dir() -> Path:
    """The .mp3 excerpt dir, env-overridable via ``VIBEMIX_BENCH_DATA_DIR``.

    Default points at the in-repo ``tests/bench/data/`` (outside ``src/`` so the
    excerpts never enter the wheel). Resolved relative to the repo root inferred
    from this module's location.
    """
    override = os.environ.get("VIBEMIX_BENCH_DATA_DIR")
    if override:
        return Path(override)
    # src/vibemix/bench/run.py -> repo root is parents[3]
    return Path(__file__).resolve().parents[3] / "tests" / "bench" / "data"


def resolve_track_path(track: str, data_dir: Path | None = None) -> Path | None:
    """Resolve a cell's ``track`` basename-prefix to its ``.mp3`` under ``data_dir``.

    Cells store a short prefix (e.g. ``"t1"``); the on-disk file is
    ``t1_pyrez_darkside.mp3``. Returns the first ``<prefix>*.mp3`` match, or the
    exact ``<track>.mp3`` if present, else ``None`` (the runner parks the cell).
    """
    base = data_dir or _bench_data_dir()
    exact = base / f"{track}.mp3"
    if exact.exists():
        return exact
    matches = sorted(base.glob(f"{track}*.mp3"))
    return matches[0] if matches else None


def _usage_dict(usage_metadata: object) -> dict:
    """Extract the bench usage dict from a Gemini ``usage_metadata`` namespace.

    Tolerant of missing attributes (the fake client + real SDK both expose the
    four token counts). Returns ``{}`` when ``usage_metadata`` is None.
    """
    if usage_metadata is None:
        return {}
    return {
        "prompt_token_count": getattr(usage_metadata, "prompt_token_count", None),
        "candidates_token_count": getattr(
            usage_metadata, "candidates_token_count", None
        ),
        "total_token_count": getattr(usage_metadata, "total_token_count", None),
        "cached_content_token_count": getattr(
            usage_metadata, "cached_content_token_count", None
        ),
    }


def run_study(
    cells,
    *,
    client,
    data_dir: Path | None = None,
    results_path: Path | None = None,
    audio_seconds: float = 80.0,
) -> list[BenchResult]:
    """Run one study sweep, returning a :class:`BenchResult` per cell.

    For each cell: assemble the prompt from the real seams, append the audio
    Part bytes for audio-grounding cells, issue ONE
    ``client.models.generate_content`` call wrapped in the per-cell fail-safe,
    and record the cell verbatim. On a successful call, feed
    ``SessionMeter.record`` for cost bounding.

    Args:
        cells: an iterable of :class:`BenchCell` (e.g. ``STUDY_A``).
        client: the genai client (injected — the fake client makes this
            offline-green; the CLI injects the real funded client).
        data_dir: override the .mp3 excerpt dir (else env / in-repo default).
        results_path: when set, the recorder writes the JSON artifact here.
        audio_seconds: forwarded to the parts-suffix wording.

    Returns:
        One :class:`BenchResult` per cell, in study order. Errored cells carry
        ``error`` set + ``output==""`` (parked, never fabricated).
    """
    # The audio Part type is imported lazily so the offline assemble path (and
    # the fake-client tests for non-audio studies) never require the SDK type.
    results: list[BenchResult] = []
    meter = get_session_meter()

    for cell in cells:
        system, contents, model, _tier = build_cell_prompt(
            cell, audio_seconds=audio_seconds
        )
        prompt_text = "".join(p for p in contents if isinstance(p, str))

        call_contents = list(contents)
        if cell.uses_audio and cell.track:
            track_path = resolve_track_path(cell.track, data_dir)
            if track_path is not None:
                from google.genai import types

                audio_bytes = track_path.read_bytes()
                call_contents.append(
                    types.Part.from_bytes(data=audio_bytes, mime_type="audio/mp3")
                )

        # --- THE 429 FAIL-SAFE — per-cell; never abort, never fabricate ---- #
        # WR-03: the call runs under a hard wall-clock timeout so a silent hang
        # (network wedge / server stall short of an HTTP error) raises
        # TimeoutError instead of blocking the sweep forever — the broad except
        # below then parks the cell and the sweep CONTINUES.
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(
                    client.models.generate_content,
                    model=model,
                    contents=call_contents,
                    config=None,
                )
                resp = fut.result(timeout=_BENCH_CALL_TIMEOUT_S)
            usage = _usage_dict(getattr(resp, "usage_metadata", None))
            # WR-02: the real SDK returns ``None`` from ``response.text`` on a
            # blocked / no-text / function-call-only candidate. A None output is
            # neither a real reaction nor a parked error — recording it as a
            # success (output=None, error=None) violates the produce-and-park
            # contract (output=="" == parked, non-empty == success). Coerce an
            # empty/blocked candidate into the PARKED state, never a fabricated
            # success.
            text = resp.text or ""
            if not text:
                results.append(
                    BenchResult(
                        cell=cell,
                        prompt=prompt_text,
                        output="",  # parked — never fabricate output
                        dsp_snapshot=fixture_snapshot_for(cell),
                        usage=usage,
                        error="blocked: no text candidate",
                    )
                )
                continue
            results.append(
                BenchResult(
                    cell=cell,
                    prompt=prompt_text,
                    output=text,
                    dsp_snapshot=fixture_snapshot_for(cell),
                    usage=usage,
                    error=None,
                )
            )
            # Cost bounding — feed the real usage to the session meter, billed
            # against the alias's pricing LANE (WR-01) so the cost summary
            # reports real spend instead of $0.00 for every reaction-model cell.
            meter.record(
                _pricing_path_for(cell.model_path),
                prompt=int(usage.get("prompt_token_count") or 0),
                cached=int(usage.get("cached_content_token_count") or 0),
                output=int(usage.get("candidates_token_count") or 0),
            )
        except Exception as e:  # noqa: BLE001 — the fail-safe MUST catch broadly
            results.append(
                BenchResult(
                    cell=cell,
                    prompt=prompt_text,
                    output="",  # NEVER fabricate output for a failed cell
                    dsp_snapshot=fixture_snapshot_for(cell),
                    usage={},
                    error=repr(e)[:160],
                )
            )

    if results_path is not None:
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(results_to_json(results), encoding="utf-8")

    return results


def fixture_snapshot_for(cell: BenchCell) -> dict[str, dict[str, tuple[float, ...]]]:
    """The DSP-fact snapshot the cell was assembled against (for the eval).

    Re-derives the same snapshot ``build_cell_prompt`` grounded the cell on, so
    each ``BenchResult`` carries its OWN snapshot for BENCH-02's groundedness
    re-check (``CitationLinter.check(output, dsp_snapshot)``).
    """
    from vibemix.bench.fixtures import fixture_state_for

    _state, snap = fixture_state_for(cell.contexting, cell.grounding)
    return snap


def results_to_json(results: list[BenchResult]) -> str:
    """Serialize the recorded cells verbatim to JSON.

    Writes prompt + output + usage + error + the cell's axes ONLY — never the
    API key (T-81-04). The DSP snapshot is rendered with string-keyed atoms so
    it round-trips through ``json.loads``.
    """
    payload = []
    for r in results:
        payload.append(
            {
                "cell": {
                    "model_path": r.cell.model_path,
                    "grounding": r.cell.grounding,
                    "prompting": r.cell.prompting,
                    "contexting": r.cell.contexting,
                    "lens": r.cell.lens,
                    "taste": r.cell.taste,
                    "skill": r.cell.skill,
                    "track": r.cell.track,
                },
                "prompt": r.prompt,
                "output": r.output,
                "usage": r.usage,
                "error": r.error,
                "dsp_snapshot": {
                    src: {key: list(times) for key, times in atoms.items()}
                    for src, atoms in (r.dsp_snapshot or {}).items()
                },
            }
        )
    return json.dumps(payload, indent=2, ensure_ascii=False)
