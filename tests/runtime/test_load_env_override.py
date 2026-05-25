# SPDX-License-Identifier: Apache-2.0
"""Phase 77 Plan 01 (Wave 0) — WIRE-06 failing scaffold: .env overrides ghost env.

``_load_env_robust`` (``__main__.py:117``) loads ``.env`` with
``override=False``, so a stale/ghost ``GEMINI_API_KEY`` already in the shell
process environment shadows the funded key in ``.env``. This is the real bug
diagnosed this session (ghost ``...QSFyBQ`` shadowed ``.env``'s funded
``...32u744``). WIRE-06 flips both ``load_dotenv`` calls to ``override=True``
so ``.env`` wins.

Two tiers:

  * OVERRIDE — set a decoy ``GEMINI_API_KEY`` in os.environ, write a temp
    ``.env`` with ``GEMINI_API_KEY=REAL_FUNDED`` at the candidate path
    ``_load_env_robust`` probes (cwd-relative via ``find_dotenv(usecwd=True)``),
    call ``_load_env_robust()``, assert the env now reads ``REAL_FUNDED``.
    xfail-strict until Plan 03 flips override=True.
  * SECURITY — the diagnostic stderr line NEVER emits the key VALUE (only the
    file PATH). GREEN now and MUST stay true (V7 secrets — T-77-01-02).

Env is mutated only inside fixtures with teardown restore. The decoy/real
values are literals — never a real funded key. No genai.Client, no network.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import vibemix.__main__ as main_mod

_DECOY = "DECOY_GHOST_SHELL_KEY"
_REAL = "REAL_FUNDED"


@pytest.fixture
def _restore_env():
    """Snapshot + restore GEMINI_API_KEY around a test that mutates it."""
    sentinel = object()
    saved = os.environ.get("GEMINI_API_KEY", sentinel)
    try:
        yield
    finally:
        if saved is sentinel:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = saved  # type: ignore[assignment]


@pytest.mark.xfail(
    reason="WIRE-06 override=True not yet flipped (Plan 03)", strict=True
)
def test_dotenv_overrides_ghost_shell_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _restore_env
) -> None:
    """A funded .env value overrides a stale ghost GEMINI_API_KEY in the shell."""
    # Ghost shell key already present (the bug condition).
    monkeypatch.setenv("GEMINI_API_KEY", _DECOY)

    # Write a .env with the real funded key at a probed candidate path.
    env_file = tmp_path / ".env"
    env_file.write_text(f"GEMINI_API_KEY={_REAL}\n", encoding="utf-8")
    # find_dotenv(usecwd=True) walks up from cwd — point cwd at the temp dir.
    monkeypatch.chdir(tmp_path)
    # Keep the argv guard off the "library" CLI branch so the diagnostic prints.
    monkeypatch.setattr("sys.argv", ["vibemix"])

    main_mod._load_env_robust()

    assert os.environ["GEMINI_API_KEY"] == _REAL, (
        "the funded .env key must override the ghost shell key (override=True)"
    )


def test_diagnostic_never_prints_the_key_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    _restore_env,
) -> None:
    """The env-load diagnostic emits the file PATH, never the key VALUE (V7).

    True today and MUST stay true post-Plan-03 — the override flip must not
    start logging the secret. This is the WIRE-06 security pin (T-77-01-02).
    """
    monkeypatch.setenv("GEMINI_API_KEY", _DECOY)
    env_file = tmp_path / ".env"
    env_file.write_text(f"GEMINI_API_KEY={_REAL}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["vibemix"])

    main_mod._load_env_robust()

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    # Neither the decoy nor the real key value may appear in the diagnostics.
    assert _REAL not in combined, "the diagnostic leaked the .env key value"
    assert _DECOY not in combined, "the diagnostic leaked the shell key value"
    # The diagnostic DOES surface which file loaded (the path is not a secret).
    assert "env:" in combined
