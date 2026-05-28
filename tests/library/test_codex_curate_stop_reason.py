# SPDX-License-Identifier: Apache-2.0
"""Phase 99 HARDEN-RETRY — Plan 99-04 cross-process propagation tests.

These pin Channel A (RESEARCH.md § Stop-Reason Propagation Channel) end-to-end:

* The wrapper allocates ``stop_reason.json`` inside its
  ``tempfile.TemporaryDirectory(prefix="viber-codex...")`` block.
* The wrapper sets ``env["VIBEMIX_STOP_REASON_FILE"]`` on the subprocess env
  arg BEFORE spawning Codex via ``_runner`` (NOT on the parent's
  ``os.environ`` — test isolation).
* When the toolset (running inside the MCP subprocess) writes the file,
  the wrapper reads it INSIDE the ``with`` block AFTER ``_runner`` returns
  and translates the dict payload into
  ``CodexCurateResult(stop_reason="tool_starvation", error=<hint>)`` /
  ``CodexBuildSetResult`` parallel BEFORE attempting to parse ``out.json``
  (the side-channel short-circuit wins over the out.json parse).
* Absent file → wrapper falls through to existing parse logic (no
  regression).
* Malformed file → wrapper falls through gracefully (T-99-07 / T-99-08
  defense-in-depth).

The ``_runner`` injection seam (Decision 7) means these tests need no real
Codex install. The fake runner inspects the ``env`` kwarg the wrapper
passes in, writes both ``out.json`` (at the ``-o`` argv slot) and
``stop_reason.json`` (at the env-var path) as appropriate, then returns a
``subprocess.CompletedProcess``.

Phase 100 forward-compat: the wrapper must branch on
``payload.get("reason") == "tool_starvation"`` so Phase 100 can add a
sibling ``elif`` for ``"clarification_needed"`` without refactoring.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vibemix.library.codex_curate import (
    CodexCurateResult,
    build_set_with_codex,
    curate_with_codex,
)
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry


def _track(tid: str) -> TrackEntry:
    return TrackEntry(
        track_id=tid,
        title=f"T{tid}",
        artist="A",
        album="X",
        bpm=124.0,
        key="8A",
        duration_s=300.0,
        cues=(),
        filepath=f"/tmp/{tid}.mp3",
    )


@pytest.fixture
def library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    lib.tracks = {f"t{i:03d}": _track(f"t{i:03d}") for i in range(5)}
    return lib


def _out_path_from_argv(argv: list[str]) -> str:
    return argv[argv.index("-o") + 1]


def _runner_with_side_channel(
    *,
    side_channel_payload: dict | str | None,
    out_payload: dict | None = None,
    returncode: int = 0,
    stderr: str = "",
):
    """Build a fake subprocess.run that writes BOTH out.json AND stop_reason.json.

    ``side_channel_payload``:
      - dict → written as JSON to env["VIBEMIX_STOP_REASON_FILE"]
      - str  → written as raw text (malformed-JSON scenarios)
      - None → file is NOT written (absent-side-channel scenario)

    ``out_payload``:
      - dict → written as JSON to the -o argv slot
      - None → out.json is NOT written (mirrors the empty-output path)
    """

    def runner(argv, **kw):
        # Write out.json at the argv-indicated path so the parse fallthrough
        # path has something to read when the side-channel short-circuit does
        # NOT fire.
        if out_payload is not None:
            out_path = _out_path_from_argv(argv)
            Path(out_path).write_text(json.dumps(out_payload), encoding="utf-8")

        # Write stop_reason.json at the env-var path the wrapper allocated
        # inside its TemporaryDirectory. The wrapper passes env via kwargs;
        # the toolset would normally do this from inside the MCP child.
        env = kw.get("env") or {}
        sr_path = env.get("VIBEMIX_STOP_REASON_FILE")
        if sr_path and side_channel_payload is not None:
            if isinstance(side_channel_payload, str):
                Path(sr_path).write_text(side_channel_payload, encoding="utf-8")
            else:
                Path(sr_path).write_text(
                    json.dumps(side_channel_payload), encoding="utf-8"
                )

        return subprocess.CompletedProcess(argv, returncode, stdout="", stderr=stderr)

    return runner


# ---------------------------------------------------------------------------
# Plan 99-04 Task 3 — wrapper-side propagation (RED on current source).
#
# These four tests pin the wrapper side of Channel A:
#   1. Side-channel present + tool_starvation reason → short-circuit
#      returns CodexCurateResult/CodexBuildSetResult with
#      stop_reason="tool_starvation" + error=<hint>.
#   2. Same for build_set_with_codex (uniform set-prep + plain curation).
#   3. Absent side-channel → existing parse path runs unchanged (regression).
#   4. Malformed side-channel → graceful fall-through to existing parse
#      logic (T-99-07 mitigation).
# ---------------------------------------------------------------------------


def test_curate_propagates_starvation_via_side_channel(library):
    """Side-channel file with tool_starvation reason → wrapper short-circuits.

    The wrapper must NOT proceed to parse out.json — the side-channel reading
    sits INSIDE the tempfile.TemporaryDirectory `with` block AFTER `_runner`
    returns BUT BEFORE the out.json parse (RESEARCH.md Code Example, Pitfall
    4 mitigation). The translated result carries the hint as ``error``.
    """
    runner = _runner_with_side_channel(
        side_channel_payload={
            "reason": "tool_starvation",
            "hint": "library has 0 tracks — run `library ingest` first",
            "tool": "search_vibe",
            "consecutive": 3,
        },
        # Even if out.json had a valid result, the side-channel must win.
        out_payload={"name": "P", "track_ids": ["t000"], "rationale": "r"},
    )

    res = curate_with_codex(
        "theme",
        library,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert isinstance(res, CodexCurateResult), (
        f"wrapper must return CodexCurateResult; got {type(res).__name__}"
    )
    assert res.stop_reason == "tool_starvation", (
        f'stop_reason must be "tool_starvation" (side-channel short-circuit '
        f"won over out.json); got {res.stop_reason!r}"
    )
    assert res.error == "library has 0 tracks — run `library ingest` first", (
        f'error must carry the hint string from the side-channel payload; '
        f"got {res.error!r}"
    )
    # Side-channel short-circuit MUST happen BEFORE out.json parse —
    # otherwise we'd see track_ids=['t000'] from the out.json payload.
    assert res.track_ids == [], (
        f"track_ids must be empty (short-circuit before parse); "
        f"got {res.track_ids!r}"
    )
    assert res.playlist_name is None, (
        f"playlist_name must be None (short-circuit before persist); "
        f"got {res.playlist_name!r}"
    )


def test_build_set_propagates_starvation(library):
    """Same propagation for set-prep — uniform across both wrappers."""
    runner = _runner_with_side_channel(
        side_channel_payload={
            "reason": "tool_starvation",
            "hint": "no tracks matched 'too-narrow' — try a broader theme or different BPM range",
            "tool": "search_vibe",
            "consecutive": 3,
        },
        out_payload={
            "name": "Set",
            "track_ids": ["t002"],
            "export_path": "",
            "rationale": "r",
        },
    )

    res = build_set_with_codex(
        "too-narrow",
        library,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert isinstance(res, CodexCurateResult), (
        f"build_set_with_codex returns CodexCurateResult; got {type(res).__name__}"
    )
    assert res.stop_reason == "tool_starvation"
    assert "no tracks matched" in (res.error or ""), (
        f"error must carry the side-channel hint; got {res.error!r}"
    )
    assert res.track_ids == []
    assert res.export_path is None


def test_no_side_channel_no_regression(library, monkeypatch, tmp_path):
    """Absent side-channel file → existing parse path runs unchanged.

    Pins the no-regression guarantee: the wrapper must not change behavior
    on the cold path. The fake runner writes a normal out.json but does NOT
    write stop_reason.json — wrapper falls through to the existing
    grounding-revalidation + persist path.
    """
    import importlib

    cp_mod = importlib.import_module("vibemix.library.create_playlist")
    monkeypatch.setattr(cp_mod, "PLAYLISTS_DIR", tmp_path)

    runner = _runner_with_side_channel(
        side_channel_payload=None,  # NOT written
        out_payload={
            "name": "Normal",
            "track_ids": ["t000", "t001"],
            "rationale": "fine",
        },
    )

    res = curate_with_codex(
        "theme",
        library,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert res.stop_reason == "created", (
        f'absent side-channel must hit the normal "created" path; '
        f"got {res.stop_reason!r}"
    )
    assert res.track_ids == ["t000", "t001"]
    assert res.playlist_name == "Normal"


def test_malformed_side_channel_falls_through(library, monkeypatch, tmp_path):
    """Malformed side-channel file → graceful fall-through (T-99-07 / T-99-08).

    Wrapper-side ``try/except (OSError, json.JSONDecodeError)`` + the
    ``isinstance(payload, dict) and payload.get("reason") == "tool_starvation"``
    defense-in-depth check (RESEARCH.md Code Example) MUST keep a corrupt
    file from raising. Wrapper falls through to the existing out.json parse.
    """
    import importlib

    cp_mod = importlib.import_module("vibemix.library.create_playlist")
    monkeypatch.setattr(cp_mod, "PLAYLISTS_DIR", tmp_path)

    runner = _runner_with_side_channel(
        side_channel_payload="not-json-at-all{{{",  # raw text → JSONDecodeError
        out_payload={
            "name": "Normal",
            "track_ids": ["t000"],
            "rationale": "fine",
        },
    )

    res = curate_with_codex(
        "theme",
        library,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    # Malformed file → fall-through → normal parse path.
    assert res.stop_reason == "created", (
        f"malformed side-channel must fall through to existing parse "
        f"logic; got {res.stop_reason!r}"
    )
    assert res.track_ids == ["t000"]


# ---------------------------------------------------------------------------
# Plan 99-08 — INTEGRATION SEAL.
#
# These three tests close the chain by exercising the REAL toolset's
# ``_build_starvation_payload`` (NOT a hardcoded dict) → side-channel write
# → wrapper short-circuit → ``CodexCurateResult.to_dict()``.
#
# If any future PR breaks any leg of the chain — payload-generator shape
# drift, wrapper short-circuit reordering, dataclass field rename — one
# of these tests fails LOUDLY with a precise diff.
#
# Forward-compat (Phase 100): the same posture (real generator + real
# wrapper + fake _runner with side-channel) clones for
# ``clarification_needed`` — swap the generator call for
# ``_build_clarification_payload`` and the asserted substring strings.
# ---------------------------------------------------------------------------


# Import the toolset HERE — the seal tests construct the real generator
# inline. Kept local to the seal block so the file's import order signals
# which suites need the toolset (seal) vs. wrapper-only (99-04 tests above).
#
# Plan deviation note (Rule 1 — plan/code drift fix): the 99-08 plan
# frontmatter calls out ``CodexBuildSetResult.to_dict()`` as a separate
# shape pin, but the shipped codebase uses ONE ``CodexCurateResult``
# dataclass for BOTH ``curate_with_codex`` and ``build_set_with_codex``
# return values (see codex_curate.py:397 + :731 — both declared as
# ``-> CodexCurateResult``). The seal still proves "uniform shape across
# both wrappers" — it just does so via the same dataclass rather than a
# parallel class. The ``test_to_dict_serializes_starvation_shape`` test
# pins all field keys so any future split of the dataclass surfaces here
# with a precise field-name diff.
from vibemix.library.rekordbox import RekordboxLibrary as _RekordboxLibrary  # noqa: E402
from vibemix.library.toolset import LibraryToolset as _LibraryToolset  # noqa: E402
from unittest.mock import MagicMock as _MagicMock  # noqa: E402


def _empty_library() -> _RekordboxLibrary:
    """Zero-track library — triggers Case A (zero-track) in
    ``_build_starvation_payload``."""
    lib = _RekordboxLibrary()
    lib.tracks = {}
    return lib


def _make_real_payload(library: _RekordboxLibrary, last_tool: str, args: dict) -> dict:
    """Generate the side-channel payload via the REAL toolset method.

    Plan 99-08 seal contract: the seal test must NOT hardcode a payload
    dict — it must invoke ``LibraryToolset._build_starvation_payload`` on a
    real toolset constructed against the supplied library. This proves the
    payload that COMES OUT of the toolset's generator is the same one the
    wrapper consumes (no shape drift).
    """
    toolset = _LibraryToolset(_MagicMock(), _MagicMock(), library)
    # Simulate the threshold-trip site: counter equals threshold at the
    # moment the payload is built (matches toolset.py:1175-1176).
    toolset._consecutive_empties = 3
    return toolset._build_starvation_payload(last_tool=last_tool, args=args)


def test_uniform_propagation_curate_path():
    """SEAL: real generator → side-channel file → wrapper → CodexCurateResult.to_dict().

    Exercises REQ-HARDEN-RETRY-02 (terminal stop_reason discriminator
    surfaces through to dataclass), REQ-HARDEN-RETRY-03 (hint carried
    through to ``error`` field), AND REQ-HARDEN-RETRY-07 (uniform
    propagation seam from toolset → wrapper).

    The fake ``_runner`` GENERATES the side-channel payload via the real
    ``_build_starvation_payload`` method (Case A, zero-track library),
    writes it to the env-var path, and returns a normal
    ``CompletedProcess(returncode=0)``. The wrapper MUST short-circuit
    with ``stop_reason="tool_starvation"`` and surface the hint as
    ``error``, and the resulting ``to_dict()`` MUST carry the same
    fields the JSON / GUI consumer reads.
    """
    empty_lib = _empty_library()
    real_payload = _make_real_payload(
        empty_lib, last_tool="search_vibe", args={"query": "anything"}
    )
    # Case A hint structure is the Plan 99-03 contract.
    assert real_payload["reason"] == "tool_starvation", (
        f"generator pre-check: real payload must have reason='tool_starvation'; "
        f"got {real_payload.get('reason')!r}"
    )
    assert "library has 0 tracks" in real_payload["hint"], (
        f"generator pre-check: Case A hint must contain "
        f'"library has 0 tracks"; got {real_payload.get("hint")!r}'
    )

    runner = _runner_with_side_channel(
        side_channel_payload=real_payload,
        out_payload=None,  # MCP child wrote stop_reason.json INSTEAD of out.json
    )

    res = curate_with_codex(
        "anything",
        empty_lib,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    # Wrapper-side dataclass shape.
    assert isinstance(res, CodexCurateResult), (
        f"wrapper must return CodexCurateResult; got {type(res).__name__}"
    )
    assert res.stop_reason == "tool_starvation", (
        f'stop_reason must propagate as "tool_starvation"; got {res.stop_reason!r}'
    )
    assert res.error is not None, "error must carry the hint string"
    assert "library has 0 tracks" in res.error, (
        f"hint substring must round-trip through wrapper; got error={res.error!r}"
    )
    assert res.playlist_name is None
    assert res.track_ids == []
    assert res.m3u_path is None

    # to_dict() — the GUI / JSON consumer surface.
    d = res.to_dict()
    assert d["stop_reason"] == "tool_starvation", (
        f"to_dict()['stop_reason'] must propagate; got {d.get('stop_reason')!r}"
    )
    assert "library has 0 tracks" in (d.get("error") or ""), (
        f"to_dict()['error'] must carry the hint; got {d.get('error')!r}"
    )
    assert d["track_ids"] == []
    assert d["playlist_name"] is None
    assert d["m3u_path"] is None


def test_uniform_propagation_build_set_path():
    """SEAL: same chain via build_set_with_codex (parallel wrapper).

    Proves the SAME ``_build_starvation_payload`` output reaches the
    set-prep wrapper too — the propagation surface is uniform across
    both wrappers. Uses Case B (no-theme-match) to exercise a different
    hint case than the curate-path test.
    """
    # Library with tracks — triggers Case B (no-theme-match) when last_tool
    # is search_vibe and the counter hits threshold.
    lib = _RekordboxLibrary()
    lib.tracks = {f"t{i:03d}": _track(f"t{i:03d}") for i in range(5)}

    real_payload = _make_real_payload(
        lib, last_tool="search_vibe", args={"query": "too-narrow-theme"}
    )
    assert real_payload["reason"] == "tool_starvation"
    assert "no tracks matched" in real_payload["hint"], (
        f"generator pre-check: Case B hint must contain "
        f'"no tracks matched"; got {real_payload.get("hint")!r}'
    )
    assert "too-narrow-theme" in real_payload["hint"], (
        f"Case B hint must interpolate the theme string; "
        f"got {real_payload.get('hint')!r}"
    )

    runner = _runner_with_side_channel(
        side_channel_payload=real_payload,
        out_payload=None,
    )

    res = build_set_with_codex(
        "too-narrow-theme",
        lib,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    # build_set_with_codex returns CodexCurateResult (the codebase ships
    # ONE dataclass for BOTH wrappers — see plan-deviation note at the
    # top of the seal block). The seal still proves "uniform shape across
    # both wrappers" — same dataclass, same propagation contract.
    assert isinstance(res, CodexCurateResult), (
        f"build_set_with_codex must return CodexCurateResult; "
        f"got {type(res).__name__}"
    )
    assert res.stop_reason == "tool_starvation", (
        f'stop_reason must propagate as "tool_starvation"; got {res.stop_reason!r}'
    )
    assert res.error is not None
    assert "no tracks matched" in res.error, (
        f"hint substring must round-trip through set-prep wrapper; "
        f"got error={res.error!r}"
    )
    assert "too-narrow-theme" in res.error, (
        f"theme interpolation must reach the wrapper; got error={res.error!r}"
    )
    assert res.track_ids == []
    assert res.export_path is None

    # to_dict() — GUI/JSON surface.
    d = res.to_dict()
    assert d["stop_reason"] == "tool_starvation"
    assert "no tracks matched" in (d.get("error") or "")
    assert d["track_ids"] == []
    assert d["export_path"] is None


def test_to_dict_serializes_starvation_shape():
    """SEAL: dataclass shape pin.

    Direct construction of both result dataclasses with starvation fields,
    then ``to_dict()`` must surface every documented key. Any future field
    rename / drop / reorder fails this test with a precise field-name diff
    (T-99-SHAPE mitigation).
    """
    # CodexCurateResult — plain-curation surface.
    cr = CodexCurateResult(
        theme="x",
        stop_reason="tool_starvation",
        error="test hint",
    )
    d = cr.to_dict()
    # Required keys for the GUI / JSON consumer (matches the field list in
    # codex_curate.py:205-215).
    required_curate_keys = {
        "theme",
        "stop_reason",
        "playlist_name",
        "track_ids",
        "m3u_path",
        "json_path",
        "rationale",
        "error",
        "export_path",
    }
    missing = required_curate_keys - set(d.keys())
    assert not missing, (
        f"CodexCurateResult.to_dict() missing required keys: {missing}. "
        f"A dataclass field was renamed or dropped — update the consumer "
        f"contracts (CLI / Telegram / Tauri bridge) accordingly."
    )
    assert d["stop_reason"] == "tool_starvation"
    assert d["error"] == "test hint"
    assert d["theme"] == "x"
    # Default values must remain stable — empty list / None for the
    # starvation surface (no partial playlist written).
    assert d["track_ids"] == [], (
        f"track_ids default must remain []; got {d.get('track_ids')!r}"
    )
    assert d["playlist_name"] is None
    assert d["m3u_path"] is None

    # Set-prep starvation surface — same CodexCurateResult dataclass, but
    # with the ``export_path`` field carrying the set-prep null. The seal
    # proves: even on the set-prep code path, the returned dataclass
    # exposes the SAME starvation contract (stop_reason + error + cleared
    # outputs). This is the "uniform shape" pin.
    br = CodexCurateResult(
        theme="x",
        stop_reason="tool_starvation",
        error="test hint",
        export_path=None,  # set-prep null on starvation — no XML written
    )
    d2 = br.to_dict()
    # Same required-key set (same dataclass). The set-prep ``export_path``
    # field is part of that set already.
    missing2 = required_curate_keys - set(d2.keys())
    assert not missing2, (
        f"CodexCurateResult set-prep starvation surface missing required keys: "
        f"{missing2}. Dataclass field was renamed or dropped."
    )
    assert d2["stop_reason"] == "tool_starvation"
    assert d2["error"] == "test hint"
    assert d2["track_ids"] == []
    assert d2["export_path"] is None
    # Cross-check: the curate-path and set-prep-path to_dict() outputs
    # share the same key set — proving the "ONE dataclass for both
    # wrappers" surface (T-99-SHAPE mitigation). Drift here would break
    # the Tauri bridge / Telegram normalizer / CLI exit-code dispatcher
    # all at once.
    assert set(d.keys()) == set(d2.keys()), (
        f"curate and set-prep to_dict() key sets must match (uniform "
        f"shape contract); diff={set(d.keys()) ^ set(d2.keys())}"
    )


# ---------------------------------------------------------------------------
# Phase 100 HARDEN-CLARIFY-03/07 seal tests.
#
# Sibling extension of the Phase 99-08 seal block above. The contract: a
# clarification_needed side-channel payload (generated by the REAL toolset's
# ``_build_clarification_payload`` helper from Plan 100-01) MUST propagate
# through both wrappers as ``CodexCurateResult(stop_reason="clarification_needed",
# question=<str>, choices=<list[str]>)``. Plans 100-04 (CLI exit 11) and 100-05
# (Telegram format_reply branch) consume these new dataclass fields.
#
# Decision-tree shape (Decision 3, Phase 99-04 SUMMARY authorized this drop-in):
#   if  payload["reason"] == "tool_starvation":   (Phase 99 — byte-equivalent)
#   if  payload["reason"] == "clarification_needed": (Phase 100-03 — new)
#   else: fall through to existing out.json parse.
#
# RED on current source: CodexCurateResult lacks ``question`` + ``choices``
# fields (TypeError on construction kwarg) AND the wrapper lacks the
# elif clarification branch (falls through to no_playlist / empty_output).
# ---------------------------------------------------------------------------


def _make_real_clarification_payload(
    library: _RekordboxLibrary, question: str, choices: list[str]
) -> dict:
    """Generate the side-channel payload via the REAL toolset method.

    Mirrors Phase 99-08's ``_make_real_payload`` — the seal test must NOT
    hardcode a payload dict; it must invoke
    ``LibraryToolset._build_clarification_payload`` on a real toolset so the
    payload that COMES OUT of the toolset's generator is the same one the
    wrapper consumes (no shape drift). Plan 100-01 shipped this helper.
    """
    toolset = _LibraryToolset(_MagicMock(), _MagicMock(), library)
    return toolset._build_clarification_payload(question, choices)


def test_uniform_clarification_propagation_curate_path():
    """SEAL: real generator → side-channel file → wrapper → CodexCurateResult.

    Exercises HARDEN-CLARIFY-03 (clarification_needed discriminator surfaces
    through to dataclass) AND HARDEN-CLARIFY-07 (uniform propagation seam from
    toolset → wrapper). The fake ``_runner`` writes the REAL generator's
    payload to the env-var path; the wrapper MUST short-circuit with
    ``stop_reason="clarification_needed"`` and populate ``question`` +
    ``choices`` fields. ``to_dict()`` MUST round-trip those same fields for
    Plan 100-04 (CLI) + Plan 100-05 (Telegram) consumers.
    """
    empty_lib = _empty_library()
    question = "What BPM range?"
    choices = ["slow (90-110)", "fast (130-140)", "mixed"]
    real_payload = _make_real_clarification_payload(empty_lib, question, choices)

    # Generator pre-check: real payload shape locked by Plan 100-01 tests.
    assert real_payload["reason"] == "clarification_needed", (
        f"generator pre-check: real payload must have "
        f'reason="clarification_needed"; got {real_payload.get("reason")!r}'
    )
    assert real_payload["question"] == question
    assert real_payload["choices"] == choices
    assert real_payload["tool"] == "request_clarification"

    runner = _runner_with_side_channel(
        side_channel_payload=real_payload,
        out_payload=None,  # MCP child wrote stop_reason.json INSTEAD of out.json
    )

    res = curate_with_codex(
        "ambiguous theme",
        empty_lib,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    # Wrapper-side dataclass shape: stop_reason + new fields.
    assert isinstance(res, CodexCurateResult), (
        f"wrapper must return CodexCurateResult; got {type(res).__name__}"
    )
    assert res.stop_reason == "clarification_needed", (
        f'stop_reason must propagate as "clarification_needed"; '
        f"got {res.stop_reason!r}"
    )
    assert res.question == question, (
        f"question must round-trip through wrapper; got {res.question!r}"
    )
    assert res.choices == choices, (
        f"choices must round-trip through wrapper; got {res.choices!r}"
    )
    # Cleared-output contract (same as tool_starvation surface).
    assert res.track_ids == []
    assert res.playlist_name is None
    assert res.m3u_path is None

    # to_dict() — Plan 100-04 / 100-05 consumer surface.
    d = res.to_dict()
    assert d["stop_reason"] == "clarification_needed"
    assert d["question"] == question
    assert d["choices"] == choices
    assert d["track_ids"] == []
    assert d["playlist_name"] is None


def test_uniform_clarification_propagation_build_set_path():
    """SEAL: same chain via build_set_with_codex (parallel wrapper).

    Proves the SAME ``_build_clarification_payload`` output reaches the
    set-prep wrapper too — the propagation surface is uniform across both
    wrappers. Different question + choices than the curate-path test to
    catch any cross-wired theme/brief leakage.
    """
    lib = _RekordboxLibrary()
    lib.tracks = {f"t{i:03d}": _track(f"t{i:03d}") for i in range(5)}

    question = "Which context?"
    choices = ["bedroom", "club", "festival"]
    real_payload = _make_real_clarification_payload(lib, question, choices)
    assert real_payload["reason"] == "clarification_needed"
    assert real_payload["question"] == question
    assert real_payload["choices"] == choices

    runner = _runner_with_side_channel(
        side_channel_payload=real_payload,
        out_payload=None,
    )

    res = build_set_with_codex(
        "ambiguous brief",
        lib,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert isinstance(res, CodexCurateResult), (
        f"build_set_with_codex must return CodexCurateResult; "
        f"got {type(res).__name__}"
    )
    assert res.stop_reason == "clarification_needed"
    assert res.question == question
    assert res.choices == choices
    assert res.track_ids == []
    assert res.export_path is None

    # to_dict() — uniform GUI/JSON shape across both wrappers.
    d = res.to_dict()
    assert d["stop_reason"] == "clarification_needed"
    assert d["question"] == question
    assert d["choices"] == choices
    assert d["track_ids"] == []
    assert d["export_path"] is None


def test_to_dict_serializes_clarification_shape():
    """SEAL: dataclass shape pin for the clarification surface.

    Direct construction of CodexCurateResult with the new question + choices
    fields, then ``to_dict()`` must surface every documented key. The key set
    MUST equal the pre-100-03 set PLUS exactly {"question", "choices"} — a
    future field rename / drop / reorder fails LOUDLY with a precise diff
    (T-100-03-SHAPE mitigation).

    Cold-path serialization is also pinned: a non-clarification result must
    serialize ``question`` + ``choices`` as ``None`` (default field values
    preserve the cold path — zero regression on Phase 99 propagation tests).
    """
    # Clarification surface — direct construction with the new fields.
    cr = CodexCurateResult(
        theme="x",
        stop_reason="clarification_needed",
        question="Q?",
        choices=["A", "B", "C"],
    )
    d = cr.to_dict()
    # Required keys = the Phase 99 set PLUS the two new clarification fields.
    required_keys = {
        "theme",
        "stop_reason",
        "playlist_name",
        "track_ids",
        "m3u_path",
        "json_path",
        "rationale",
        "error",
        "export_path",
        "question",
        "choices",
    }
    missing = required_keys - set(d.keys())
    assert not missing, (
        f"CodexCurateResult.to_dict() missing required keys: {missing}. "
        f"A dataclass field was renamed or dropped — update the consumer "
        f"contracts (Plan 100-04 CLI / Plan 100-05 Telegram) accordingly."
    )
    assert d["stop_reason"] == "clarification_needed"
    assert d["question"] == "Q?"
    assert d["choices"] == ["A", "B", "C"]
    assert d["track_ids"] == []
    assert d["playlist_name"] is None

    # Cold-path serialization — the existing "created" surface MUST keep
    # question + choices as None. Zero regression on Phase 99 contract.
    cold = CodexCurateResult(
        theme="y",
        stop_reason="created",
        playlist_name="p",
        track_ids=["t1"],
    )
    dc = cold.to_dict()
    assert dc["question"] is None, (
        f"cold-path question default must remain None; got {dc.get('question')!r}"
    )
    assert dc["choices"] is None, (
        f"cold-path choices default must remain None; got {dc.get('choices')!r}"
    )
    # Existing fields unchanged.
    assert dc["stop_reason"] == "created"
    assert dc["playlist_name"] == "p"
    assert dc["track_ids"] == ["t1"]


def test_clarification_side_channel_propagation_with_real_writer(
    monkeypatch, tmp_path
):
    """SEAL: real toolset writes side-channel + wrapper reads.

    Wires the FULL chain: real toolset.request_clarification handler writes
    the side-channel JSON via ``_write_side_channel`` (Plan 99-04 reused
    unchanged); then a fake ``_runner`` that does NOT write the file is
    invoked (because the toolset already wrote it). The wrapper MUST pick
    up the pre-existing file and return the clarification result.

    This proves the cross-process seam end-to-end without spawning Codex:
    the toolset's writer + the wrapper's reader interoperate via the
    side-channel file at the env-var-allocated path.
    """
    empty_lib = _empty_library()
    question = "Which mood?"
    choices = ["chill", "energetic", "dark"]

    # Real toolset writes the side-channel file at the env-var path. We
    # cannot easily route the toolset's write into the wrapper's
    # TemporaryDirectory (allocated at runtime), so we use a runner that
    # invokes the toolset INSIDE the subprocess emulation — the toolset
    # sees env["VIBEMIX_STOP_REASON_FILE"] via monkeypatch on os.environ.
    def runner(argv, **kw):
        # Emulate the MCP child: the toolset reads VIBEMIX_STOP_REASON_FILE
        # from its OWN env. Bridge: temporarily set os.environ to the kw env
        # so the toolset's _write_side_channel finds the path.
        env = kw.get("env") or {}
        sr_path = env.get("VIBEMIX_STOP_REASON_FILE")
        if sr_path:
            monkeypatch.setenv("VIBEMIX_STOP_REASON_FILE", sr_path)
            # Real handler call writes the side-channel via _write_side_channel.
            toolset = _LibraryToolset(_MagicMock(), _MagicMock(), empty_lib)
            toolset.request_clarification(
                {"question": question, "choices": choices}
            )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    res = curate_with_codex(
        "ambiguous",
        empty_lib,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    # Wrapper picked up the toolset-written side-channel file.
    assert res.stop_reason == "clarification_needed", (
        f"real-writer chain must end in clarification_needed; "
        f"got {res.stop_reason!r}"
    )
    assert res.question == question
    assert res.choices == choices
    assert res.track_ids == []


# ---------------------------------------------------------------------------
# Phase 100 HARDEN-CLARIFY-07 — integration seal (end-to-end uniform propagation)
#
# The Plan 100-03 propagation tests above stop at ``CodexCurateResult.to_dict()``.
# Plan 100-07 extends the seal to the USER-VISIBLE surfaces — the CLI exit code
# + 2-block stderr render (Plan 100-04) and the Telegram ``format_reply`` chat
# render (Plan 100-05). The chain is:
#
#   toolset.request_clarification (REAL handler — Plan 100-01)
#     -> _build_clarification_payload (REAL helper — Plan 100-01)
#       -> side-channel JSON written through _write_side_channel (REAL — 99-04 reused)
#         -> curate_with_codex / build_set_with_codex wrapper read (REAL — 100-03)
#           -> CodexCurateResult(stop_reason="clarification_needed", question, choices)
#             -> [CLI leg]      _cmd_library_curate_codex: rc=11 + 2-block stderr render
#             -> [Telegram leg] _normalize_codex_curate_result -> format_reply render
#
# Codex CLI is the ONLY mocked boundary (via ``_runner_with_side_channel``) —
# every link inside vibemix runs REAL implementations. Same posture as
# Phase 99 Plan 99-08's seal block above.
#
# Forward-compat: future stop_reasons (12 = user_canceled, 13 = ..., ...) drop
# in by sibling-elif additions in (a) toolset handler (b) _build_<reason>_payload
# (c) wrapper elif (d) CLI elif (e) format_reply elif (f) normalizer if. No
# refactoring of existing code — discriminated-union pattern locked across
# Phases 99 + 100.
# ---------------------------------------------------------------------------


from unittest.mock import patch as _patch  # noqa: E402


def test_clarification_full_chain_to_cli_curate(capsys):
    """SEAL: REAL toolset payload -> REAL wrapper -> CLI _cmd_library_curate_codex.

    Pins HARDEN-CLARIFY-07 uniform propagation across the CLI surface. The
    seal MUST exercise:
      * REAL ``_build_clarification_payload`` (Plan 100-01) — not a hardcoded dict.
      * REAL ``curate_with_codex`` side-channel-read elif branch (Plan 100-03).
      * REAL ``_cmd_library_curate_codex`` clarification dispatch + 2-block
        stderr render + exit 11 (Plan 100-04).

    Codex CLI is the ONLY mocked boundary (``_runner_with_side_channel``).
    Drift in ANY layer fails this test LOUDLY with a precise substring diff —
    the test is the regression-pin for the full CLI chain.
    """
    import argparse
    import vibemix.__main__ as _main

    empty_lib = _empty_library()
    question = "What BPM range?"
    choices = ["slow (90-110)", "fast (130-140)", "mixed"]

    # REAL payload — generator output is what the wrapper consumes.
    real_payload = _make_real_clarification_payload(empty_lib, question, choices)
    assert real_payload["reason"] == "clarification_needed", (
        f"generator pre-check: real payload must have "
        f'reason="clarification_needed"; got {real_payload.get("reason")!r}'
    )

    # REAL wrapper read via side-channel.
    runner = _runner_with_side_channel(
        side_channel_payload=real_payload,
        out_payload=None,
    )
    result = curate_with_codex(
        "ambiguous theme",
        empty_lib,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )
    # Pre-check: result carries the expected dataclass shape before we hand it
    # to the CLI handler. If this fails, the seal is broken at the wrapper
    # layer (Plan 100-03 drift) — fix Plan 100-03, not this test.
    assert result.stop_reason == "clarification_needed", (
        f"wrapper pre-check: stop_reason must be clarification_needed; "
        f"got {result.stop_reason!r}"
    )
    assert result.question == question
    assert result.choices == choices

    # CLI dispatch leg: REAL _cmd_library_curate_codex receives the result via
    # a patched module-attr (the handler does a function-local
    # `from vibemix.library.codex_curate import curate_with_codex`, so we patch
    # the SOURCE module attr — matches the pattern in test_cli_exit_codes.py).
    args = argparse.Namespace(theme="ambiguous theme", name=None)
    lib_sentinel = object()
    with _patch(
        "vibemix.library.codex_curate.curate_with_codex",
        return_value=result,
    ):
        rc = _main._cmd_library_curate_codex(args, lib_sentinel)

    captured = capsys.readouterr()
    # Exit 11 — reserved range 10-19 (Plan 99-06 + 100-04).
    assert rc == 11, (
        f"expected exit 11 on clarification_needed across full CLI chain; "
        f"got rc={rc!r}; stderr={captured.err!r}"
    )
    # 2-block stderr render (Plan 100-04 / Decision 6).
    assert "clarification_needed" in captured.err, (
        f"stderr must carry clarification_needed discriminator; got {captured.err!r}"
    )
    assert "What BPM range?" in captured.err, (
        f"question substring must propagate through full chain to stderr; "
        f"got {captured.err!r}"
    )
    for choice in ["slow (90-110)", "fast (130-140)", "mixed"]:
        assert choice in captured.err, (
            f"choice substring '{choice}' must propagate through full chain "
            f"to stderr; got {captured.err!r}"
        )
    # Re-run hint (single-turn closure — vibemix retains NO state).
    assert "Re-run with:" in captured.err, (
        f"re-run hint (single-turn closure) must surface; got {captured.err!r}"
    )
    assert "library curate" in captured.err, (
        f"re-run hint must echo 'library curate' command form; "
        f"got {captured.err!r}"
    )
    # stdout stays clean on the clarification path (Decision 6).
    assert captured.out == "", (
        f"stdout must be clean on clarification_needed (Decision 6 — non-success "
        f"path goes to stderr only); got {captured.out!r}"
    )


def test_clarification_full_chain_to_telegram():
    """SEAL: REAL toolset payload -> REAL wrapper -> normalizer -> format_reply.

    Pins HARDEN-CLARIFY-07 uniform propagation across the Telegram surface.
    The seal MUST exercise:
      * REAL ``_build_clarification_payload`` (Plan 100-01) — not a hardcoded dict.
      * REAL ``curate_with_codex`` side-channel-read elif branch (Plan 100-03).
      * REAL ``_normalize_codex_curate_result`` clarification dict shape
        (Plan 100-04 contract bridge).
      * REAL ``format_reply`` clarification branch + numbered choices +
        leak-strip defense (Plan 100-05).

    Includes a leak-strip regression-pin: a malicious-shaped payload with an
    FS path in the question MUST be scrubbed by ``strip_leaks`` before chat
    render — T-100-05-01 mitigation pin at the integration boundary.
    """
    from vibemix.__main__ import _normalize_codex_curate_result
    from vibemix.library.telegram_bridge import format_reply

    empty_lib = _empty_library()
    question = "What BPM range?"
    choices = ["slow (90-110)", "fast (130-140)", "mixed"]

    # REAL chain: generator -> side-channel -> wrapper.
    real_payload = _make_real_clarification_payload(empty_lib, question, choices)
    runner = _runner_with_side_channel(
        side_channel_payload=real_payload,
        out_payload=None,
    )
    result = curate_with_codex(
        "ambiguous theme",
        empty_lib,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    # Normalizer leg (Plan 100-04 contract bridge).
    norm = _normalize_codex_curate_result(result)
    assert norm == {
        "ok": False,
        "stop_reason": "clarification_needed",
        "question": question,
        "choices": choices,
    }, (
        f"_normalize_codex_curate_result must emit the Plan 100-05 contract "
        f"shape; got {norm!r}"
    )

    # Telegram render leg (Plan 100-05).
    rendered = format_reply(norm)
    assert isinstance(rendered, str) and rendered, (
        f"format_reply must return a non-empty string; got {rendered!r}"
    )
    assert question in rendered, (
        f"format_reply must surface the question; got {rendered!r}"
    )
    for choice in choices:
        assert choice in rendered, (
            f"format_reply must surface each choice; missing '{choice}' "
            f"in {rendered!r}"
        )
    # Distinguishing glyph: NOT the ⚠️ used by error/starvation branches —
    # Plan 100-05 chose a separate glyph (currently ❓) so a sighted user can
    # distinguish "needs user input" from "error" at a glance. Test accepts
    # any non-⚠️ leading glyph (the exact glyph is executor-latitude per
    # Plan 100-05 Decision; ear-pass refinements stay free).
    assert not rendered.startswith("⚠️"), (
        f"clarification render must use a distinguishing leading glyph (not ⚠️) "
        f"to differentiate from error/starvation branches; got {rendered!r}"
    )

    # Leak-strip defense (T-100-05-01 at the integration boundary): a malicious
    # payload with an FS path in the question MUST be scrubbed before chat
    # render. Use a direct-construction norm to inject the leak — proves the
    # defense holds at the format_reply layer regardless of upstream payload
    # provenance.
    malicious_norm = {
        "ok": False,
        "stop_reason": "clarification_needed",
        "question": "Library at /Users/ozai/.cache/vibemix — pick context?",
        "choices": ["a", "b"],
    }
    scrubbed = format_reply(malicious_norm)
    assert "/Users/ozai" not in scrubbed, (
        f"strip_leaks must scrub FS paths from clarification render; "
        f"got {scrubbed!r}"
    )
    assert "[path]" in scrubbed, (
        f"strip_leaks must replace scrubbed paths with [path] marker; "
        f"got {scrubbed!r}"
    )
    # The non-path portion of the question must survive scrubbing.
    assert "pick context?" in scrubbed, (
        f"non-path question text must survive strip_leaks; got {scrubbed!r}"
    )


def test_clarification_build_set_path_seal(capsys):
    """SEAL: build_set_with_codex sibling parity through the CLI surface.

    Same chain as ``test_clarification_full_chain_to_cli_curate`` but via the
    set-prep wrapper. Pins:
      * ``build_set_with_codex`` propagates the SAME clarification payload as
        ``curate_with_codex`` (uniform across both wrappers — Plan 100-03).
      * ``_cmd_library_build_set_codex`` exit 11 + 2-block stderr render
        (Plan 100-04 sibling).
      * Re-run hint uses ``library build-set`` (NOT ``library curate``) —
        the brief is echoed in place of the theme.
    """
    import argparse
    import vibemix.__main__ as _main

    lib = _RekordboxLibrary()
    lib.tracks = {f"t{i:03d}": _track(f"t{i:03d}") for i in range(5)}

    question = "Which energy curve?"
    choices = ["slow-build", "peak-time", "wave"]
    real_payload = _make_real_clarification_payload(lib, question, choices)

    runner = _runner_with_side_channel(
        side_channel_payload=real_payload,
        out_payload=None,
    )
    result = build_set_with_codex(
        "ambiguous brief",
        lib,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )
    # Pre-check: build-set wrapper carries the same clarification dataclass
    # shape as the curate wrapper — proves uniform propagation across both
    # wrappers (Plan 100-03 contract).
    assert isinstance(result, CodexCurateResult), (
        f"build_set_with_codex must return CodexCurateResult; "
        f"got {type(result).__name__}"
    )
    assert result.stop_reason == "clarification_needed"
    assert result.question == question
    assert result.choices == choices

    # CLI dispatch leg — build-set sibling.
    args = argparse.Namespace(
        brief="peak-time 60 min",
        curve=None,
        name=None,
        n_slots=None,
        export=None,
    )
    lib_sentinel = object()
    with _patch(
        "vibemix.library.codex_curate.build_set_with_codex",
        return_value=result,
    ):
        rc = _main._cmd_library_build_set_codex(args, lib_sentinel)

    captured = capsys.readouterr()
    assert rc == 11, (
        f"expected exit 11 on clarification_needed across build-set CLI chain; "
        f"got rc={rc!r}; stderr={captured.err!r}"
    )
    assert "clarification_needed" in captured.err
    assert question in captured.err
    for choice in choices:
        assert choice in captured.err, (
            f"choice substring '{choice}' must propagate through build-set CLI; "
            f"got {captured.err!r}"
        )
    # Re-run hint must use the build-set command form, NOT the curate form.
    assert "Re-run with:" in captured.err
    assert "library build-set" in captured.err, (
        f"build-set re-run hint must echo 'library build-set' command form "
        f"(NOT 'library curate'); got {captured.err!r}"
    )
    # The brief is echoed in the re-run hint (the user typed it, no PII leak).
    assert "peak-time 60 min" in captured.err, (
        f"brief must be echoed in build-set re-run hint; got {captured.err!r}"
    )
    # stdout stays clean on the clarification path (Decision 6).
    assert captured.out == ""
