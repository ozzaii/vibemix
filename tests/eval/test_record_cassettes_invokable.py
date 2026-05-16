# SPDX-License-Identifier: Apache-2.0
"""Phase 42 Plan 01 / GATE-02 — sanity tests for the VCR cassette recorder.

The recorder must NEVER subprocess pytest in default (dry-run) mode and must
refuse to run in --really mode without GEMINI_API_KEY.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure repo root on sys.path so `import scripts.eval.record_cassettes` works.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.eval.record_cassettes import (  # noqa: E402
    DEFAULT_CASSETTE_DIR,
    DEFAULT_TEST_DIR,
    discover_vcr_tests,
    main,
)


def test_discover_vcr_tests_returns_list() -> None:
    """The discovery heuristic must return a list (possibly empty) without error."""
    hits = discover_vcr_tests(DEFAULT_TEST_DIR)
    assert isinstance(hits, list)
    # Every entry is a relative file name, not a path.
    for name in hits:
        assert isinstance(name, str)
        assert name.startswith("test_")
        assert name.endswith(".py")


def test_discover_vcr_tests_handles_missing_dir(tmp_path: Path) -> None:
    """A non-existent test_dir must return [] (not raise)."""
    hits = discover_vcr_tests(tmp_path / "nope")
    assert hits == []


def test_discover_vcr_tests_finds_phase_27_judge_tests() -> None:
    """The Phase 27 judge tests reference VCR in their docstrings.

    Their module docstring contains `VCR_RECORD_MODE` so the heuristic must
    flag them as VCR-decorated even when the decorator is not yet on the
    test function itself.
    """
    hits = discover_vcr_tests(DEFAULT_TEST_DIR)
    # The pro + flash judge tests are the canonical VCR-dependent suite.
    assert any("judge_pro" in h for h in hits) or any(
        "judge_flash" in h for h in hits
    ), f"expected at least one judge_*.py in discovered VCR tests; got {hits}"


def test_main_default_does_not_subprocess_pytest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`main([])` (default) must not subprocess pytest."""
    import scripts.eval.record_cassettes as mod

    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def _spy(*args: object, **kwargs: object) -> object:  # pragma: no cover
        calls.append((args, kwargs))
        raise AssertionError("subprocess.run must not be called in default mode")

    monkeypatch.setattr(mod.subprocess, "run", _spy)
    rc = main([])
    assert rc == 0
    assert calls == []


def test_main_really_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`main([--really --record-mode new_episodes])` without the key exits 1."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    import scripts.eval.record_cassettes as mod

    def _spy(*_args: object, **_kwargs: object) -> object:  # pragma: no cover
        raise AssertionError(
            "subprocess.run must not be invoked when GEMINI_API_KEY is unset"
        )

    monkeypatch.setattr(mod.subprocess, "run", _spy)
    rc = main(["--really", "--record-mode", "new_episodes"])
    assert rc == 1


def test_main_really_with_record_mode_none_rejects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`--really` with `--record-mode none` must hard-fail with exit 1."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-not-used")

    import scripts.eval.record_cassettes as mod

    def _spy(*_args: object, **_kwargs: object) -> object:  # pragma: no cover
        raise AssertionError("subprocess.run must not be called when mode=none")

    monkeypatch.setattr(mod.subprocess, "run", _spy)
    rc = main(["--really", "--record-mode", "none"])
    assert rc == 1


def test_default_cassette_dir_under_tests_eval() -> None:
    """The default cassette dir must live under tests/eval/cassettes/."""
    parts = DEFAULT_CASSETTE_DIR.parts
    assert "tests" in parts and "eval" in parts and "cassettes" in parts
    assert DEFAULT_CASSETTE_DIR.name == "cassettes"
