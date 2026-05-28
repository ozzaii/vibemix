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
