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
