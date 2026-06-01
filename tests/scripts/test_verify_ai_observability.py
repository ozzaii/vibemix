# SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/verify_ai_observability.py."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import verify_ai_observability as verifier


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_session_verifier_accepts_saved_ai_message_with_moves(tmp_path, capsys) -> None:
    session = tmp_path / "recordings" / "20260531-120000"
    artifact_dir = session / "ai_messages" / "artifacts" / "live_001"
    artifact_dir.mkdir(parents=True)
    prompt_path = artifact_dir / "prompt.txt"
    response_path = artifact_dir / "response.txt"
    meta_path = artifact_dir / "meta.json"
    prompt_path.write_text("prompt", encoding="utf-8")
    response_path.write_text("response", encoding="utf-8")
    meta_path.write_text("{}", encoding="utf-8")
    _write_jsonl(
        session / "events.jsonl",
        [
            {"t": 0.0, "kind": "session_start"},
            {
                "t": 1.0,
                "kind": "ai_message",
                "engine": "live_coach",
                "message": "response",
                "moves": {
                    "recent_moves": [{"label": "A_low: flat->cut"}],
                    "deck_mixer": {"A": {"eq_low": 20}},
                },
                "artifacts": {
                    "session_prompt_path": str(prompt_path),
                    "session_response_path": str(response_path),
                    "session_meta_path": str(meta_path),
                },
            },
        ],
    )

    rc = verifier.main(
        [
            "--session-dir",
            str(session),
            "--require-artifacts",
            "--require-move-context",
            "--require-deck-mixer",
        ]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "session rows=1" in out


def test_session_verifier_rejects_missing_artifact(tmp_path, capsys) -> None:
    session = tmp_path / "recordings" / "20260531-120000"
    _write_jsonl(
        session / "events.jsonl",
        [
            {
                "t": 1.0,
                "kind": "ai_message",
                "engine": "live_coach",
                "message": "response",
                "moves": {"recent_moves": [{"label": "A_low: flat->cut"}]},
                "artifacts": {
                    "session_prompt_path": str(session / "missing_prompt.txt"),
                    "session_response_path": str(session / "missing_response.txt"),
                },
            },
        ],
    )

    rc = verifier.main(["--session-dir", str(session), "--require-artifacts"])

    err = capsys.readouterr().err
    assert rc == 1
    assert "does not exist" in err


def test_session_verifier_can_select_latest_session_with_ai_message(tmp_path, capsys) -> None:
    recordings = tmp_path / "recordings"
    idle = recordings / "20260531-130000"
    _write_jsonl(idle / "events.jsonl", [{"t": 0.0, "kind": "session_start"}])

    live = recordings / "20260531-120000"
    artifact_dir = live / "ai_messages" / "artifacts" / "live_001"
    artifact_dir.mkdir(parents=True)
    prompt_path = artifact_dir / "prompt.txt"
    response_path = artifact_dir / "response.txt"
    prompt_path.write_text("prompt", encoding="utf-8")
    response_path.write_text("response", encoding="utf-8")
    _write_jsonl(
        live / "events.jsonl",
        [
            {
                "t": 1.0,
                "kind": "ai_message",
                "engine": "live_coach",
                "message": "response",
                "moves": {"recent_moves": [{"label": "A_low: flat->cut"}]},
                "artifacts": {
                    "session_prompt_path": str(prompt_path),
                    "session_response_path": str(response_path),
                },
            },
        ],
    )

    rc = verifier.main(
        [
            "--recordings-root",
            str(recordings),
            "--latest-with-ai-message",
            "--require-artifacts",
            "--require-move-context",
            "--json",
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert report["session"]["session_dir"] == str(live)


def test_latest_session_selector_ignores_ai_message_text_without_kind(
    tmp_path, capsys
) -> None:
    recordings = tmp_path / "recordings"
    fake = recordings / "20260531-140000"
    _write_jsonl(
        fake / "events.jsonl",
        [{"t": 1.0, "kind": "note", "message": "quoted ai_message string"}],
    )

    rc = verifier.main(
        [
            "--recordings-root",
            str(recordings),
            "--latest-with-ai-message",
        ]
    )

    err = capsys.readouterr().err
    assert rc == 1
    assert "no sessions containing ai_message found" in err


def test_global_verifier_accepts_saved_artifacts(tmp_path, capsys) -> None:
    artifact_dir = tmp_path / "ai_messages" / "artifacts" / "chat_001"
    artifact_dir.mkdir(parents=True)
    prompt_path = artifact_dir / "prompt.txt"
    response_path = artifact_dir / "response.txt"
    meta_path = artifact_dir / "meta.json"
    prompt_path.write_text("prompt", encoding="utf-8")
    response_path.write_text("response", encoding="utf-8")
    meta_path.write_text("{}", encoding="utf-8")
    _write_jsonl(
        tmp_path / "ai_messages" / "ai_messages.jsonl",
        [
            {
                "engine": "codex",
                "surface": "viber_chat",
                "message": "response",
                "artifacts": {
                    "prompt_path": str(prompt_path),
                    "response_path": str(response_path),
                    "meta_path": str(meta_path),
                },
            }
        ],
    )

    rc = verifier.main(
        [
            "--skip-session",
            "--global-root",
            str(tmp_path),
            "--require-artifacts",
        ]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "global rows=1" in out


def test_verifier_requires_expected_engine_and_surface_across_sources(
    tmp_path, capsys
) -> None:
    session = tmp_path / "recordings" / "20260531-120000"
    _write_jsonl(
        session / "events.jsonl",
        [
            {
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session_reaction",
                "message": "Nice restraint.",
                "moves": {"deck_mixer": {"A": {"vol": 127}}},
            }
        ],
    )
    _write_jsonl(
        tmp_path / "ai_messages" / "ai_messages.jsonl",
        [
            {
                "engine": "codex",
                "surface": "viber_chat",
                "message": "Use the outgoing phrase as the anchor.",
            }
        ],
    )

    rc = verifier.main(
        [
            "--session-dir",
            str(session),
            "--global-root",
            str(tmp_path),
            "--require-engine",
            "live_coach",
            "--require-engine",
            "codex",
            "--require-surface",
            "session_reaction",
            "--require-surface",
            "viber_chat",
            "--json",
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert report["session"]["engines"] == ["live_coach"]
    assert report["global"]["surfaces"] == ["viber_chat"]


def test_verifier_rejects_missing_required_engine(tmp_path, capsys) -> None:
    session = tmp_path / "recordings" / "20260531-120000"
    _write_jsonl(
        session / "events.jsonl",
        [
            {
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session_reaction",
                "message": "response",
            }
        ],
    )

    rc = verifier.main(
        [
            "--session-dir",
            str(session),
            "--require-engine",
            "codex",
        ]
    )

    err = capsys.readouterr().err
    assert rc == 1
    assert "missing required ai_message engine(s): codex" in err
