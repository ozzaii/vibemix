# SPDX-License-Identifier: Apache-2.0
"""Plan 29-00 Task 2 Part B — `--debrief` short-circuit verification.

`python -m vibemix --debrief <session_dir>` MUST NOT engage audio I/O or
LiveKit. The dispatch in `cli_entry()` must early-return on
`args.debrief is not None` BEFORE any sounddevice / livekit / mido import
or initialization runs.

We assert this by:
  1. Calling `cli_entry(["--debrief", str(fixture)])` directly.
  2. Confirming the call returns without crashing on a machine without
     BlackHole installed (no `audio_backend.find_device(INPUT_DEVICE, ...)`
     RuntimeError → sys.exit(3) path is reached).
  3. Asserting that the heavy initialization inside `main()` is never
     invoked — we monkeypatch `vibemix.__main__.main` to raise if called.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def test_debrief_dispatches_before_main(monkeypatch, tmp_path: Path) -> None:
    """The debrief dispatch must fire before main() (the heavy runtime)."""
    import vibemix.__main__ as vm_main

    main_called = {"value": False}

    async def fake_main() -> None:
        main_called["value"] = True

    monkeypatch.setattr(vm_main, "main", fake_main)

    session = tmp_path / "20260515-112139"
    session.mkdir()

    # No assertion error / SystemExit expected — the debrief path exits cleanly
    vm_main.cli_entry(["--debrief", str(session)])

    assert main_called["value"] is False, (
        "main() must NOT be invoked when --debrief is passed"
    )


def test_debrief_with_no_arg_smoke(monkeypatch) -> None:
    """Bare `--debrief` (no session_dir) still short-circuits before main()."""
    import vibemix.__main__ as vm_main

    main_called = {"value": False}

    async def fake_main() -> None:
        main_called["value"] = True

    monkeypatch.setattr(vm_main, "main", fake_main)

    vm_main.cli_entry(["--debrief"])
    assert main_called["value"] is False


def test_debrief_does_not_load_sounddevice_or_livekit(monkeypatch, tmp_path: Path) -> None:
    """The debrief code path must not touch sounddevice or livekit at runtime.

    We can't easily prevent module-level imports that already happened (they
    fire when `vibemix.__main__` itself loads), but we CAN assert the
    `_run_debrief_sidecar` body is what runs — by spying on the dispatch.
    """
    import vibemix.__main__ as vm_main

    sidecar_called = {"path": None}

    def spy(session_dir: str) -> None:
        sidecar_called["path"] = session_dir

    monkeypatch.setattr(vm_main, "_run_debrief_sidecar", spy)

    async def fake_main() -> None:
        raise AssertionError("main() must not be reached in debrief mode")

    monkeypatch.setattr(vm_main, "main", fake_main)

    session = tmp_path / "20260515-112139"
    session.mkdir()
    vm_main.cli_entry(["--debrief", str(session)])

    assert sidecar_called["path"] == str(session)
