# SPDX-License-Identifier: Apache-2.0
"""AI-message observability rows."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace

from vibemix.audio.recorder import VoiceRecorder
from vibemix.runtime.ai_observability import (
    append_global_ai_message,
    record_session_ai_message,
    snapshot_state_for_ai_message,
)
from vibemix.runtime.recordings_index import RecordingsIndex

GENERATION_SCAN_ROOTS = (Path("src/vibemix"), Path("scripts/eval"))


class _Recorder:
    def __init__(self) -> None:
        self.rows: list[tuple[str, dict]] = []

    def log_event(self, kind: str, **fields) -> None:
        self.rows.append((kind, fields))


def test_record_session_ai_message_ties_reply_to_recent_moves() -> None:
    recorder = _Recorder()
    state = SimpleNamespace(
        recent_moves=[(0.4, "A_low: flat->cut"), (1.2, "xfader->A-side")],
        deck_a={"vol": 127, "eq_low": 20, "filter": 64, "play": True},
        deck_b={"vol": 0, "eq_low": 64, "filter": 64, "play": False},
        xfader=12,
        controller_connected=True,
        deck_confidence=0.7,
        audio_delta=["low energy fell 40%"],
        vocal_active=True,
        onset_density=3.5,
        audible_deck="A",
        audible_track="Track A",
        phase="build",
        set_seconds=93.0,
    )
    event = SimpleNamespace(type="MIX_MOVE", extra={"moves": [(0.2, "A_low: flat->cut")]})

    row = record_session_ai_message(
        recorder,
        engine="live_coach",
        surface="session",
        direction="assistant",
        text="Low cut was clear.",
        response_id="0001_120000",
        event="MIX_MOVE",
        provider="gemini",
        model="router-live-model",
        citation_count=1,
        citation_action="emit",
        state=state,
        event_obj=event,
    )

    assert recorder.rows[0][0] == "ai_message"
    assert recorder.rows[0][1] == row
    assert row["message"] == "Low cut was clear."
    assert row["moves"]["recent_moves"] == [
        {"label": "A_low: flat->cut", "age_s": 0.4},
        {"label": "xfader->A-side", "age_s": 1.2},
    ]
    assert row["moves"]["event_moves"] == [{"label": "A_low: flat->cut", "age_s": 0.2}]
    assert row["moves"]["deck_mixer"]["A"]["eq_low"] == 20
    assert row["moves"]["vocal_active"] is True
    assert row["moves"]["onset_density"] == 3.5
    assert row["citation"]["action"] == "emit"


def test_record_session_ai_message_saves_prompt_response_with_real_recorder(
    tmp_path,
) -> None:
    recorder = VoiceRecorder(root=tmp_path)
    try:
        row = record_session_ai_message(
            recorder,
            engine="live_coach",
            surface="session",
            direction="assistant",
            text="The low cut moved after the fader.",
            response_id="live_001",
            event="MIX_MOVE",
            provider="gemini",
            model="router-live-model",
            prompt="prompt with mixer_context[A_low=20 xfader=12]",
            response="The low cut moved after the fader.",
            live_context={"recent_moves": ["A_low: flat->cut"], "deck": "A"},
        )
    finally:
        recorder.close()

    prompt_path = Path(row["artifacts"]["session_prompt_path"])
    response_path = Path(row["artifacts"]["session_response_path"])
    meta_path = Path(row["artifacts"]["session_meta_path"])
    assert prompt_path.read_text(encoding="utf-8") == "prompt with mixer_context[A_low=20 xfader=12]"
    assert response_path.read_text(encoding="utf-8") == "The low cut moved after the fader."
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["response_id"] == "live_001"
    assert meta["moves"]["live_context_recent_moves"] == [{"label": "A_low: flat->cut"}]
    assert meta["artifacts"]["session_meta_path"] == str(meta_path)

    events = [
        json.loads(line)
        for line in recorder.events_path.read_text(encoding="utf-8").splitlines()
    ]
    ai_rows = [event for event in events if event.get("kind") == "ai_message"]
    assert len(ai_rows) == 1
    assert ai_rows[0]["artifacts"]["session_prompt_path"] == str(prompt_path)
    assert ai_rows[0]["artifacts"]["session_response_path"] == str(response_path)

    index_events, err = RecordingsIndex(tmp_path).read_events(recorder.session_dir.name)
    assert err is None
    assert index_events is not None
    replay_rows = [event for event in index_events if event.get("kind") == "ai_message"]
    assert len(replay_rows) == 1
    assert replay_rows[0]["message"] == "The low cut moved after the fader."
    assert replay_rows[0]["artifacts"]["session_meta_path"] == str(meta_path)


def test_snapshot_state_for_ai_message_freezes_mixer_fields() -> None:
    state = SimpleNamespace(
        audible=True,
        audible_deck="A",
        audible_track="Track A",
        audible_track_confidence=0.8,
        phase="peak",
        rms=0.05,
        bpm=128.0,
        recent_moves=[(0.4, "A_low: flat->cut")],
        deck_a={"vol": 127, "eq_low": 20, "filter": 64, "play": True},
        deck_b={"vol": 0, "eq_low": 64, "filter": 64, "play": False},
        xfader=10,
        controller_connected=True,
        deck_confidence=0.7,
        audio_delta=["low energy fell 40%"],
        set_seconds=93.0,
    )

    snap = snapshot_state_for_ai_message(state)
    state.recent_moves.append((0.1, "B_mid: flat->boost"))
    state.deck_a["eq_low"] = 99
    state.xfader = 120

    assert snap is not None
    assert snap.recent_moves == [(0.4, "A_low: flat->cut")]
    assert snap.deck_a["eq_low"] == 20
    assert snap.xfader == 10


def test_append_global_ai_message_saves_prompt_response_and_jsonl(tmp_path) -> None:
    row = append_global_ai_message(
        root=tmp_path,
        engine="codex",
        surface="viber_chat",
        direction="assistant",
        text="I see the filter move, not a proven transition.",
        response_id="chat_001",
        provider="codex_cli",
        model=None,
        stop_reason="model_done",
        live_context={"recent_moves": ["B_filter: flat->boost"], "deck": "B"},
        tool_trace=[{"name": "search_vibe", "arg": "acid", "ok": True}],
        prompt="DJ: was that good?",
        response="I see the filter move, not a proven transition.",
    )

    log_path = tmp_path / "ai_messages" / "ai_messages.jsonl"
    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["response_id"] == "chat_001"
    assert rows[0]["moves"]["live_context_recent_moves"] == [{"label": "B_filter: flat->boost"}]
    assert rows[0]["tool_trace"][0]["name"] == "search_vibe"
    assert row["artifacts"]["prompt_path"]
    assert row["artifacts"]["response_path"]
    meta = json.loads(Path(row["artifacts"]["meta_path"]).read_text(encoding="utf-8"))
    assert meta["artifacts"]["meta_path"] == row["artifacts"]["meta_path"]
    assert "DJ: was that good?" in (
        tmp_path / "ai_messages" / "artifacts" / "chat_001" / "prompt.txt"
    ).read_text(encoding="utf-8")


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _generation_call_files() -> set[Path]:
    files: set[Path] = set()
    for root in GENERATION_SCAN_ROOTS:
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    dotted = _dotted_name(node.func)
                elif isinstance(node, ast.Attribute):
                    dotted = _dotted_name(node)
                else:
                    continue
                if dotted.endswith((".generate_content", ".generate_content_stream")):
                    files.add(path)
                elif dotted.endswith(".chat.completions.create"):
                    files.add(path)
    return files


def test_generation_call_surfaces_have_ai_message_coverage() -> None:
    """Every assistant-producing model callsite has an observability owner."""
    expected_markers = {
        Path("src/vibemix/agent/dj_cohost.py"): "record_session_ai_message",
        Path("src/vibemix/bench/run.py"): "_record_bench_ai_message",
        Path("src/vibemix/debrief/drills.py"): "_record_drills_ai_message",
        Path("src/vibemix/debrief/tldr.py"): "_record_tldr_ai_message",
        Path("src/vibemix/state/deck_vision.py"): "append_global_ai_message",
        Path("scripts/eval/judge.py"): "_record_eval_judge_ai_message",
    }
    pass_through = {
        Path("src/vibemix/agent/openrouter_llm.py"): (
            "OpenRouter is streamed through DJCoHost.llm_node; "
            "src/vibemix/agent/dj_cohost.py owns record_session_ai_message."
        ),
        # 2026-06-08 "bench until perfection" Gemini-direct harness drivers
        # (e1bde672 lineage): offline dev/eval instruments that swap the dark
        # Respan transport for the live google-genai SDK. Their model calls
        # produce judge SCORES over already-recorded sessions (or fresh
        # bench-only candidate lines in the sim driver) — nothing reaches a
        # listener, so there is no assistant ai_message to record. Results
        # land in .planning/eval-runs/* JSON, the bench's own surface.
        Path("scripts/eval/bench_gemini_judge.py"): (
            "Blind judge over recorded Sven lines; emits scores to the "
            "bench report, not assistant messages."
        ),
        Path("scripts/eval/bench_openrouter_judge.py"): (
            "Same judge rubric on the OpenRouter transport; scores only."
        ),
        Path("scripts/eval/bench_sim_gemini.py"): (
            "Generates fresh candidate lines under a persona for bench "
            "scoring only — never spoken, never shown to a user."
        ),
    }

    found = _generation_call_files()
    allowed = set(expected_markers) | set(pass_through)
    assert found <= allowed, (
        "New model-generation file lacks ai_message coverage: "
        f"{sorted(str(path) for path in found - allowed)}"
    )
    for path, marker in expected_markers.items():
        assert path in found, f"Expected generation surface missing from audit: {path}"
        assert marker in path.read_text(encoding="utf-8"), (
            f"{path} calls a model but does not contain {marker}"
        )
    assert "record_session_ai_message" in Path(
        "src/vibemix/agent/dj_cohost.py"
    ).read_text(encoding="utf-8")


def test_non_model_assistant_surfaces_have_ai_message_coverage() -> None:
    """Codex/Viber and authored Learn tutor speech are assistant text too."""
    codex_src = Path("src/vibemix/library/codex_curate.py").read_text(encoding="utf-8")
    assert "_record_codex_ai_message" in codex_src
    assert 'surface="viber_curate"' in codex_src
    assert 'surface="viber_build_set"' in codex_src
    assert 'surface="viber_chat"' in codex_src

    runtime_src = Path("src/vibemix/learn/runtime.py").read_text(encoding="utf-8")
    main_src = Path("src/vibemix/__main__.py").read_text(encoding="utf-8")
    assert "learn_tutor_speak_observability_events" in runtime_src
    assert "learn_tutor_speak_observability_events" in main_src
    assert 'source="learn_runtime"' in runtime_src
    assert 'source="learn_observer"' in main_src
