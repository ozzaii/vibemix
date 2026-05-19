# SPDX-License-Identifier: Apache-2.0
"""Phase 42 Plan 01 / GATE-01 — sanity tests for the ack-bank resume wrapper.

The wrapper itself must NEVER call Gemini in dry-run mode. These tests pin
that contract along with the missing-entries inventory math.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure repo root on sys.path so `import scripts.eval.generate_ack_audio_resume`
# works when pytest is invoked from a worktree or subdir.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.eval.generate_ack_audio_resume import (  # noqa: E402
    DEFAULT_MANIFEST,
    list_missing_entries,
    main,
)


def _write_tiny_manifest(path: Path, n_entries: int = 40) -> list[dict[str, str]]:
    """Write a manifest matching the 5-bucket × 8-id layout used in prod.

    The full Phase 27 manifest has 40 entries (5 buckets × 8 ids). Tests use
    the same layout so list_missing_entries returns predictable counts.
    """
    buckets = [
        "drop_hit",
        "track_change",
        "mix_move",
        "silence_break",
        "generic_filler",
    ]
    entries: list[dict[str, str]] = []
    for bucket in buckets:
        for i in range(8):
            entries.append(
                {
                    "bucket": bucket,
                    "id": f"{bucket}_{i:02d}",
                    "text": f"tiny text {bucket}/{i}",
                }
            )
    entries = entries[:n_entries]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries), encoding="utf-8")
    return entries


def test_list_missing_entries_reads_manifest(tmp_path: Path) -> None:
    """With an empty output dir, every manifest entry is missing."""
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "ack_bank"
    output.mkdir()
    entries = _write_tiny_manifest(manifest)

    missing = list_missing_entries(manifest, output)

    assert len(missing) == 40
    assert len(missing) == len(entries)
    # Every bucket should be represented.
    buckets_seen = {e["bucket"] for e in missing}
    assert buckets_seen == {
        "drop_hit",
        "track_change",
        "mix_move",
        "silence_break",
        "generic_filler",
    }


def test_list_missing_entries_skips_present(tmp_path: Path) -> None:
    """A pre-existing <bucket>/<id>.opus reduces the missing count by 1."""
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "ack_bank"
    output.mkdir()
    _write_tiny_manifest(manifest)

    # Place a fake .opus file under one of the expected paths.
    fake = output / "drop_hit" / "drop_hit_00.opus"
    fake.parent.mkdir(parents=True, exist_ok=True)
    fake.write_bytes(b"fake-opus-bytes")

    missing = list_missing_entries(manifest, output)
    assert len(missing) == 39
    # The one we just wrote MUST NOT appear in the missing set.
    assert not any(
        e["bucket"] == "drop_hit" and e["id"] == "drop_hit_00" for e in missing
    )


def test_list_missing_entries_raises_on_missing_manifest(tmp_path: Path) -> None:
    """A non-existent manifest raises FileNotFoundError."""
    missing_path = tmp_path / "does_not_exist.json"
    with pytest.raises(FileNotFoundError):
        list_missing_entries(missing_path, tmp_path)


def test_resume_dry_run_does_not_call_gemini(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`main([--dry-run])` must not import google.genai or invoke subprocess."""
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "ack_bank"
    output.mkdir()
    _write_tiny_manifest(manifest)

    # Belt-and-braces: drop the API key from the env so even if the wrapper
    # ever tried to import google.genai, it would refuse to spend.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    # Force subprocess.run to raise if anyone calls it during dry-run.
    import scripts.eval.generate_ack_audio_resume as mod

    def _explode(*_args: object, **_kwargs: object) -> object:  # pragma: no cover
        raise AssertionError("subprocess.run must not be called in dry-run")

    monkeypatch.setattr(mod.subprocess, "run", _explode)

    # Snapshot before — other tests in the run may have imported google.genai
    # through vibemix.agent already. The contract under test is that the
    # dry-run wrapper itself doesn't import it as a side effect.
    genai_loaded_before = "google.genai" in sys.modules

    rc = main(
        [
            "--dry-run",
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ]
    )
    assert rc == 0
    # The wrapper must not import google.genai as a side-effect of the call.
    # (If it was already loaded by a prior test, that's not the wrapper's fault.)
    if not genai_loaded_before:
        assert "google.genai" not in sys.modules


def test_resume_default_mode_is_dry_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Calling main([]) with custom paths must default to dry-run inventory."""
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "ack_bank"
    output.mkdir()
    _write_tiny_manifest(manifest)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    import scripts.eval.generate_ack_audio_resume as mod

    def _explode(*_args: object, **_kwargs: object) -> object:  # pragma: no cover
        raise AssertionError("subprocess.run must not be called in default mode")

    monkeypatch.setattr(mod.subprocess, "run", _explode)

    rc = main(["--manifest", str(manifest), "--output", str(output)])
    assert rc == 0


def test_default_manifest_path_resolves_under_assets() -> None:
    """The default manifest constant must point under <repo>/assets/ack_bank/."""
    parts = DEFAULT_MANIFEST.parts
    assert "assets" in parts and "ack_bank" in parts
    assert DEFAULT_MANIFEST.name == "manifest.json"
