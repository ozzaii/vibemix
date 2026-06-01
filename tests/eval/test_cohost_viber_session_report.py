# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import os
from pathlib import Path

from vibemix.eval.session_report import (
    build_cohost_viber_history_sweep,
    build_cohost_viber_report,
    export_cohost_viber_failure_corpus,
    format_cohost_viber_history_markdown,
    format_cohost_viber_markdown,
    latest_session,
    run_cohost_viber_autopilot,
    run_failure_corpus_benchmark,
    run_reprompt_pack_repair,
    score_reprompt_candidate,
    session_start_iso,
    write_reprompt_pack,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def _session(tmp_path: Path, name: str = "20260531-120000") -> Path:
    session = tmp_path / "recordings" / name
    response_path = session / "ai_messages" / "artifacts" / "0001" / "response.txt"
    response_path.parent.mkdir(parents=True, exist_ok=True)
    response_path.write_text("Great transition, that blend was clean.", encoding="utf-8")
    _write_jsonl(
        session / "events.jsonl",
        [
            {"t": 0.0, "kind": "session_start", "session_dir": name},
            {"t": 1.0, "kind": "citation_count", "count": 0, "response_id": "0001"},
            {
                "t": 1.1,
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": "0001",
                "message": "Great transition, that blend was clean.",
                "citation": {"count": 0, "action": "emit", "valid": None, "reason": None},
                "extra": {"deck_audio_parts": 0},
                "artifacts": {"session_response_path": str(response_path)},
            },
            {
                "t": 1.2,
                "kind": "citation_strip",
                "response_id": "0002",
                "raw_text": "That drop happened [ev:GHOST@9.0]",
                "reason": "invalid_atoms",
            },
            {
                "t": 1.3,
                "kind": "live_claim_guard",
                "summary": "resolved decks=none; live evidence gate: transition_block=no_resolved_decks",
                "raw_text": "Great blend.",
                "corrected_text": "I need both decks before I call the blend.",
            },
        ],
    )
    return session


def test_report_turns_session_and_viber_artifacts_into_repair_queue(tmp_path: Path) -> None:
    session = _session(tmp_path)
    global_root = tmp_path / "app"
    _write_jsonl(
        global_root / "ai_messages" / "ai_messages.jsonl",
        [
            {
                "schema_version": 1,
                "engine": "codex",
                "surface": "viber_chat",
                "response_id": "viber-1",
                "message": "I caught the live move. The useful note is the sound change right there.",
                "stop_reason": "model_done",
                "extra": {
                    "request": "find me dark rolling hypnotic techno",
                    "live_verification": {
                        "ok": False,
                        "violations": ["unsupported_live_outcome_claim"],
                        "guard_applied": True,
                    }
                },
            }
        ],
    )

    report = build_cohost_viber_report(session, global_root=global_root)

    assert report["ok"] is False
    assert report["metrics"]["session"]["citation_zero_non_ack_emits"] == 1
    assert report["metrics"]["session"]["citation_strips"] == 1
    assert report["metrics"]["viber"]["live_verification_violations"] == 1
    assert report["metrics"]["audio_evidence_debt"]["total"] == 3
    assert report["metrics"]["audio_evidence_debt"]["issue_code_counts"] == {
        "live_claim_guard": 1,
        "viber_library_request_live_leak": 1,
        "viber_live_verification": 1,
    }
    codes = {issue["code"] for issue in report["issues"]}
    assert {
        "citation_zero_emit",
        "citation_strip",
        "live_claim_guard",
        "viber_live_verification",
        "viber_library_request_live_leak",
    } <= codes
    assert any(item["surface"] == "viber_chat" for item in report["automation_queue"])


def test_report_treats_guarded_viber_reply_as_care_not_escaped_violation(tmp_path: Path) -> None:
    session = tmp_path / "recordings" / "20260601-011500"
    _write_jsonl(
        session / "events.jsonl",
        [
            {
                "t": 0.0,
                "kind": "session_start",
                "wall_clock_iso": "2026-05-31T16:00:00+03:00",
            },
            {
                "t": 1.0,
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": "idle-1",
                "message": "I'm listening.",
                "citation": {"count": 0, "action": "emit"},
                "extra": {"deck_audio_parts": 1},
            }
        ],
    )
    global_root = tmp_path / "app"
    artifact_dir = global_root / "ai_messages" / "artifacts" / "viber-guarded"
    artifact_dir.mkdir(parents=True)
    meta = {
        "schema_version": 1,
        "engine": "codex",
        "surface": "viber_chat",
        "response_id": "viber-guarded",
        "message": "I need stronger live proof before I call that outcome.",
        "moves": {
            "live_context_schema_version": 2,
            "live_context_deck": "A",
            "live_context_deck_mixer": {"connected": True},
        },
        "extra": {
            "request": "did that low cut fix it?",
            "live_verification": {
                "ok": True,
                "violations": [],
                "guard_applied": True,
                "guard_violations": ["unsupported_live_outcome_claim"],
            },
        },
    }
    (artifact_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (artifact_dir / "prompt.txt").write_text("original prompt", encoding="utf-8")
    (artifact_dir / "response.txt").write_text(str(meta["message"]), encoding="utf-8")
    _write_jsonl(
        global_root / "ai_messages" / "ai_messages.jsonl",
        [
            {
                **meta,
                "artifacts": {
                    "prompt_path": str(artifact_dir / "prompt.txt"),
                    "response_path": str(artifact_dir / "response.txt"),
                    "meta_path": str(artifact_dir / "meta.json"),
                },
            }
        ],
    )

    report = build_cohost_viber_report(session, global_root=global_root)

    assert report["ok"] is True
    assert report["metrics"]["viber"]["live_verification_violations"] == 0
    assert report["metrics"]["viber"]["guarded_reply_violations"] == 1
    assert report["metrics"]["viber"]["guarded_replies"] == 1
    assert report["metrics"]["audio_evidence_debt"]["total"] == 1
    assert report["metrics"]["audio_evidence_debt"]["issue_code_counts"] == {
        "viber_live_guarded_reply": 1
    }
    codes = {issue["code"] for issue in report["issues"]}
    assert "viber_live_verification" not in codes
    issue = next(issue for issue in report["issues"] if issue["code"] == "viber_live_guarded_reply")
    assert issue["severity"] == "care"
    assert issue["artifact"] == str(artifact_dir / "meta.json")
    assert "without guard_applied" in issue["prompt"]

    summary = run_cohost_viber_autopilot(
        session,
        tmp_path / "autopilot-guarded-viber",
        global_root=global_root,
        gate_policy="first-pass",
    )
    assert summary["gate_ok"] is False
    assert summary["first_pass_clean"] is False
    assert summary["reprompt_debt"] == 1
    assert summary["audio_evidence_debt"] == 1
    assert summary["audio_evidence_debt_by_code"] == {"viber_live_guarded_reply": 1}

    audio_summary = run_cohost_viber_autopilot(
        session,
        tmp_path / "autopilot-guarded-viber-audio-evidence",
        global_root=global_root,
        gate_policy="audio-evidence",
    )
    assert audio_summary["gate_policy"] == "audio-evidence"
    assert audio_summary["gate_ok"] is False
    assert audio_summary["audio_evidence_debt"] == 1


def test_report_names_guarded_library_request_leak_as_specific_care(tmp_path: Path) -> None:
    session = tmp_path / "recordings" / "20260601-011700"
    _write_jsonl(session / "events.jsonl", [{"t": 0.0, "kind": "session_start"}])
    global_root = tmp_path / "app"
    artifact_dir = global_root / "ai_messages" / "artifacts" / "viber-library-guarded"
    artifact_dir.mkdir(parents=True)
    meta = {
        "schema_version": 1,
        "engine": "codex",
        "surface": "viber_chat",
        "response_id": "viber-library-guarded",
        "message": "I kept that as a library request, but I do not have grounded results to show yet.",
        "moves": {
            "live_context_schema_version": 2,
            "live_context_deck": "none",
            "live_context_deck_mixer": {"connected": True},
        },
        "extra": {
            "request": "find me dark rolling hypnotic techno",
            "live_verification": {
                "ok": True,
                "violations": [],
                "guard_applied": True,
                "guard_violations": ["library_request_live_leak"],
            },
        },
    }
    (artifact_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (artifact_dir / "prompt.txt").write_text("LIVE CONTEXT USE: silent_guard", encoding="utf-8")
    (artifact_dir / "response.txt").write_text(str(meta["message"]), encoding="utf-8")
    _write_jsonl(
        global_root / "ai_messages" / "ai_messages.jsonl",
        [
            {
                **meta,
                "artifacts": {
                    "prompt_path": str(artifact_dir / "prompt.txt"),
                    "response_path": str(artifact_dir / "response.txt"),
                    "meta_path": str(artifact_dir / "meta.json"),
                },
            }
        ],
    )

    report = build_cohost_viber_report(session, global_root=global_root)

    assert report["ok"] is True
    assert report["metrics"]["audio_evidence_debt"]["total"] == 1
    assert report["metrics"]["audio_evidence_debt"]["issue_code_counts"] == {
        "viber_library_request_guarded_reply": 1
    }
    codes = {issue["code"] for issue in report["issues"]}
    assert "viber_library_request_live_leak" not in codes
    issue = next(
        issue for issue in report["issues"] if issue["code"] == "viber_library_request_guarded_reply"
    )
    assert issue["severity"] == "care"
    assert issue["artifact"] == str(artifact_dir / "meta.json")
    assert "LIVE CONTEXT USE:silent_guard" in issue["prompt"]
    assert "without guard_applied" in issue["prompt"]


def test_report_treats_pre_tts_citation_strip_as_safe_silence(tmp_path: Path) -> None:
    session = tmp_path / "recordings" / "20260601-001000"
    artifact_dir = session / "ai_messages" / "artifacts" / "0001"
    artifact_dir.mkdir(parents=True)
    meta_path = artifact_dir / "meta.json"
    meta_path.write_text("{}", encoding="utf-8")
    _write_jsonl(
        session / "events.jsonl",
        [
            {"t": 0.0, "kind": "session_start", "session_dir": session.name},
            {
                "t": 1.0,
                "kind": "citation_count",
                "count": 0,
                "response_id": "0001",
            },
            {
                "t": 1.1,
                "kind": "citation_strip",
                "response_id": "0001",
                "raw_text": "I'm listening.",
                "reason": "no_citations",
            },
            {
                "t": 1.2,
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": "0001",
                "message": "",
                "citation": {"count": 0, "action": "strip", "valid": False, "reason": "no_citations"},
                "extra": {"head_yielded": False, "spoken_response_chars": 0, "deck_audio_parts": 0},
                "artifacts": {"session_meta_path": str(meta_path)},
            },
        ],
    )

    report = build_cohost_viber_report(session, include_viber=False)

    assert report["ok"] is True
    issue = next(issue for issue in report["issues"] if issue["code"] == "citation_strip_silent")
    assert issue["severity"] == "care"
    assert issue["artifact"] == str(meta_path)
    assert "chooses silence itself" in issue["repair"]
    assert "citation_strip" not in {item["code"] for item in report["automation_queue"]}
    assert "citation_strip_silent" in {item["code"] for item in report["automation_queue"]}

    summary = run_cohost_viber_autopilot(
        session,
        tmp_path / "autopilot-safe-silence",
        include_viber=False,
    )

    assert summary["status"] == "clean_with_care"
    assert summary["ok"] is True
    assert summary["gate_ok"] is True
    assert summary["release_gate_ok"] is True
    assert summary["first_pass_clean"] is False
    assert summary["reprompt_debt"] == 1
    assert summary["audio_evidence_debt"] == 0
    assert summary["audio_evidence_debt_by_code"] == {}
    assert summary["initial_issue_counts"]["care"] == 1
    assert summary["reprompt_jobs"] == 1
    repair_manifest = json.loads(
        (Path(summary["artifacts"]["repair_run"]) / "repair_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    candidate_path = Path(repair_manifest["results"][0]["candidate_path"])
    score_path = Path(repair_manifest["results"][0]["score_path"])
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    score = json.loads(score_path.read_text(encoding="utf-8"))
    assert candidate["reply"] == ""
    assert score["ok"] is True

    strict_summary = run_cohost_viber_autopilot(
        session,
        tmp_path / "autopilot-safe-silence-first-pass",
        include_viber=False,
        gate_policy="first-pass",
    )

    assert strict_summary["gate_policy"] == "first-pass"
    assert strict_summary["gate_ok"] is False
    assert strict_summary["release_gate_ok"] is True
    assert strict_summary["first_pass_clean"] is False
    assert score["violations"] == []

    audio_only_summary = run_cohost_viber_autopilot(
        session,
        tmp_path / "autopilot-safe-silence-audio-evidence",
        include_viber=False,
        gate_policy="audio-evidence",
    )
    assert audio_only_summary["gate_policy"] == "audio-evidence"
    assert audio_only_summary["gate_ok"] is True
    assert audio_only_summary["first_pass_clean"] is False
    assert audio_only_summary["audio_evidence_debt"] == 0


def test_report_treats_deferred_live_claim_strip_as_safe_silence(tmp_path: Path) -> None:
    session = tmp_path / "recordings" / "20260601-004304"
    meta_path = session / "ai_messages" / "artifacts" / "0001_004311" / "meta.json"
    meta_path.parent.mkdir(parents=True)
    meta_path.write_text("{}", encoding="utf-8")
    _write_jsonl(
        session / "events.jsonl",
        [
            {"t": 0.0, "kind": "session_start", "session_dir": session.name},
            {
                "t": 1.1,
                "kind": "citation_strip",
                "response_id": "0001_004311",
                "raw_text": "I'm listening.",
                "reason": "no_citations",
            },
            {
                "t": 1.2,
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": "0001_004311",
                "message": "I'm listening.",
                "citation": {"count": 0, "action": "strip", "valid": False, "reason": "no_citations"},
                "extra": {
                    "head_yielded": False,
                    "live_claim_defer_stream": True,
                    "spoken_response_chars": 14,
                    "deck_audio_parts": 0,
                },
                "artifacts": {"session_meta_path": str(meta_path)},
            },
        ],
    )

    report = build_cohost_viber_report(session, include_viber=False)

    assert report["ok"] is True
    assert "citation_strip" not in {issue["code"] for issue in report["issues"]}
    issue = next(issue for issue in report["issues"] if issue["code"] == "citation_strip_silent")
    assert issue["severity"] == "care"
    assert issue["artifact"] == str(meta_path)


def test_report_accepts_pre_llm_manual_silence_without_repair(tmp_path: Path) -> None:
    session = tmp_path / "recordings" / "20260601-004404"
    meta_path = session / "ai_messages" / "artifacts" / "0001_004404" / "meta.json"
    meta_path.parent.mkdir(parents=True)
    meta_path.write_text("{}", encoding="utf-8")
    _write_jsonl(
        session / "events.jsonl",
        [
            {"t": 0.0, "kind": "session_start", "session_dir": session.name},
            {
                "t": 1.1,
                "kind": "manual_silence_short_circuit",
                "event": "MANUAL",
                "reason": "manual_no_live_evidence",
                "avoided_audio_tokens_est": 192,
            },
            {
                "t": 1.2,
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": "0001_004404",
                "message": "",
                "stop_reason": "manual_no_live_evidence",
                "suppression": "manual_no_evidence",
                "citation": {
                    "count": 0,
                    "action": "skip",
                    "valid": None,
                    "reason": "manual_no_live_evidence",
                },
                "extra": {
                    "head_yielded": False,
                    "pre_llm_short_circuit": True,
                    "spoken_response_chars": 0,
                    "deck_audio_parts": 0,
                },
                "artifacts": {"session_meta_path": str(meta_path)},
            },
        ],
    )

    report = build_cohost_viber_report(session, include_viber=False)

    issue_codes = {issue["code"] for issue in report["issues"]}
    assert report["ok"] is True
    assert report["metrics"]["session"]["manual_silence_short_circuits"] == 1
    assert "citation_strip_silent" not in issue_codes
    assert "citation_zero_emit" not in issue_codes
    assert "no_deck_audio_parts" in issue_codes
    assert report["automation_queue"] == []


def test_report_keeps_head_yielded_strip_as_blocker(tmp_path: Path) -> None:
    session = tmp_path / "recordings" / "20260601-001030"
    _write_jsonl(
        session / "events.jsonl",
        [
            {"t": 0.0, "kind": "session_start", "session_dir": session.name},
            {
                "t": 1.1,
                "kind": "citation_strip",
                "response_id": "0001",
                "raw_text": "I'm listening.",
                "reason": "no_citations",
            },
            {
                "t": 1.2,
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": "0001",
                "message": "I'm listening.",
                "citation": {"count": 0, "action": "strip", "valid": False, "reason": "no_citations"},
                "extra": {"head_yielded": True, "spoken_response_chars": 14, "deck_audio_parts": 0},
            },
        ],
    )

    report = build_cohost_viber_report(session, include_viber=False)

    assert report["ok"] is False
    issue = next(issue for issue in report["issues"] if issue["code"] == "citation_strip")
    assert issue["severity"] == "blocker"


def test_report_blocks_active_live_viber_prompt_without_audio_contract(tmp_path: Path) -> None:
    session = _session(tmp_path)
    global_root = tmp_path / "app"
    artifact_dir = global_root / "ai_messages" / "artifacts" / "viber-active"
    artifact_dir.mkdir(parents=True)
    prompt_path = artifact_dir / "prompt.txt"
    response_path = artifact_dir / "response.txt"
    meta_path = artifact_dir / "meta.json"
    prompt_path.write_text(
        "LIVE CONTEXT USE: active_live_context\n"
        "CURRENT LIVE DECK CONTEXT\n"
        "Use the current deck context carefully.\n",
        encoding="utf-8",
    )
    response_path.write_text("The low end got hollow for a moment.", encoding="utf-8")
    meta = {
        "response_id": "viber-active",
        "surface": "viber_chat",
        "message": "The low end got hollow for a moment.",
        "moves": {
            "live_context_schema_version": 2,
            "live_context_deck": "A",
            "live_context_deck_mixer": {"connected": True},
        },
        "extra": {
            "request": "did that low cut fix it?",
            "live_verification": {"ok": True, "violations": [], "guard_applied": False},
        },
    }
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    _write_jsonl(
        global_root / "ai_messages" / "ai_messages.jsonl",
        [
            {
                **meta,
                "engine": "codex",
                "ts_iso": "2026-05-31T16:00:05+03:00",
                "artifacts": {
                    "prompt_path": str(prompt_path),
                    "response_path": str(response_path),
                    "meta_path": str(meta_path),
                },
            }
        ],
    )

    report = build_cohost_viber_report(session, global_root=global_root)

    prompt_issue = next(
        issue for issue in report["issues"] if issue["code"] == "viber_prompt_missing_audio_contract"
    )
    assert prompt_issue["severity"] == "blocker"
    assert prompt_issue["artifact"] == str(prompt_path)
    assert "LIVE AUDIO CONTRACT" in prompt_issue["prompt"]

    manifest = export_cohost_viber_failure_corpus(
        tmp_path / "recordings",
        tmp_path / "corpus",
        global_root=global_root,
        max_sessions=1,
        include_policy_canaries=False,
    )
    assert manifest["issue_code_counts"]["viber_prompt_missing_audio_contract"] == 1
    cases_text = Path(manifest["cases_path"]).read_text(encoding="utf-8")
    assert "viber_prompt_missing_audio_contract" in cases_text
    assert "active-live Viber prompts must include the live audio contract" in cases_text

    benchmark = run_failure_corpus_benchmark(tmp_path / "corpus", tmp_path / "benchmark")
    prompt_result = next(
        result
        for result in benchmark["results"]
        if result["issue_code"] == "viber_prompt_missing_audio_contract"
    )
    assert prompt_result["ok"] is True
    assert prompt_result["score_mode"] == "corpus_gate"
    candidate = json.loads(Path(prompt_result["candidate_path"]).read_text(encoding="utf-8"))
    assert "LIVE AUDIO CONTRACT" in candidate["prompt_patch"]

    def missing_prompt_patch_repairer(job: dict) -> dict:
        return {
            "reply": "The low end got hollow for a moment.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "move_grades": [],
            "playlist": None,
        }

    bad_benchmark = run_failure_corpus_benchmark(
        tmp_path / "corpus",
        tmp_path / "bad-benchmark",
        backend="codex",
        repairer=missing_prompt_patch_repairer,
    )
    bad_prompt_result = next(
        result
        for result in bad_benchmark["results"]
        if result["issue_code"] == "viber_prompt_missing_audio_contract"
    )
    assert bad_prompt_result["ok"] is False
    assert "missing_prompt_audio_contract_patch" in bad_prompt_result["violations"]

    pack = write_reprompt_pack(report, tmp_path / "pack")
    prompt_job = next(
        job
        for job in pack["jobs"]
        if job["issue"]["code"] == "viber_prompt_missing_audio_contract"
    )
    assert "prompt_patch" in prompt_job["candidate_contract"]["json_fields"]
    assert "prompt_patch" in Path(tmp_path / "pack" / prompt_job["job_id"] / "reprompt.md").read_text(
        encoding="utf-8"
    )
    assert "--issue-code viber_prompt_missing_audio_contract" in str(
        prompt_job["candidate_contract"]["score_command"]
    )

    bad_candidate_path = tmp_path / "missing-prompt-patch.json"
    bad_candidate_path.write_text(
        json.dumps(missing_prompt_patch_repairer(prompt_job)),
        encoding="utf-8",
    )
    strict_score = score_reprompt_candidate(
        meta_path,
        bad_candidate_path,
        issue_code="viber_prompt_missing_audio_contract",
    )
    assert strict_score["ok"] is False
    assert "missing_prompt_audio_contract_patch" in strict_score["violations"]

    import vibemix.__main__ as main_mod

    score_rc = main_mod._run_eval_cli(
        [
            "score-candidate",
            "--meta",
            str(meta_path),
            "--candidate",
            str(bad_candidate_path),
            "--issue-code",
            "viber_prompt_missing_audio_contract",
            "--json",
        ]
    )
    assert score_rc == 1

    repair = run_reprompt_pack_repair(
        tmp_path / "pack",
        tmp_path / "bad-repair",
        backend="codex",
        repairer=missing_prompt_patch_repairer,
    )
    repair_result = next(
        result
        for result in repair["results"]
        if "viber_prompt_missing_audio_contract" in result["job_id"]
    )
    assert repair_result["ok"] is False
    repair_score = json.loads(Path(repair_result["score_path"]).read_text(encoding="utf-8"))
    assert "missing_prompt_audio_contract_patch" in repair_score["violations"]


def test_report_allows_active_live_viber_prompt_with_audio_contract(tmp_path: Path) -> None:
    session = _session(tmp_path)
    global_root = tmp_path / "app"
    artifact_dir = global_root / "ai_messages" / "artifacts" / "viber-active"
    artifact_dir.mkdir(parents=True)
    prompt_path = artifact_dir / "prompt.txt"
    response_path = artifact_dir / "response.txt"
    meta_path = artifact_dir / "meta.json"
    prompt_path.write_text(
        "LIVE CONTEXT USE: active_live_context\n"
        "LIVE AUDIO CONTRACT\n"
        "Audio can describe listener vibe and texture; "
        "never credit or blame the control from audio alone.\n",
        encoding="utf-8",
    )
    response_path.write_text("The low end got hollow for a moment.", encoding="utf-8")
    meta = {
        "response_id": "viber-active",
        "surface": "viber_chat",
        "message": "The low end got hollow for a moment.",
        "moves": {
            "live_context_schema_version": 2,
            "live_context_deck": "A",
            "live_context_deck_mixer": {"connected": True},
        },
        "extra": {
            "request": "did that low cut fix it?",
            "live_verification": {"ok": True, "violations": [], "guard_applied": False},
        },
    }
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    _write_jsonl(
        global_root / "ai_messages" / "ai_messages.jsonl",
        [
            {
                **meta,
                "engine": "codex",
                "artifacts": {
                    "prompt_path": str(prompt_path),
                    "response_path": str(response_path),
                    "meta_path": str(meta_path),
                },
            }
        ],
    )

    report = build_cohost_viber_report(session, global_root=global_root)

    assert "viber_prompt_missing_audio_contract" not in {
        issue["code"] for issue in report["issues"]
    }


def test_report_blocks_spoken_live_claim_guard_fallback(tmp_path: Path) -> None:
    session = tmp_path / "recordings" / "20260531-121500"
    fallback = "I can't call that a transition until I have clear two-deck proof."
    _write_jsonl(
        session / "events.jsonl",
        [
            {
                "t": 1.0,
                "kind": "live_claim_guard",
                "event": "PHASE",
                "policy": "blocked",
                "reason": "no_resolved_decks",
                "summary": "resolved decks=none",
                "raw_text": "That blend was perfect.",
                "corrected_text": fallback,
            },
            {
                "t": 1.1,
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": "0001",
                "message": fallback,
                "citation": {"count": 0, "action": "emit"},
                "extra": {"deck_audio_parts": 0},
            },
        ],
    )

    report = build_cohost_viber_report(session, include_viber=False)

    assert report["ok"] is False
    issue = next(i for i in report["issues"] if i["code"] == "live_claim_guard_spoken_fallback")
    assert issue["severity"] == "blocker"
    assert issue["response_id"] == "0001"
    assert issue["detail"] == fallback

    summary = run_cohost_viber_autopilot(
        session,
        tmp_path / "autopilot-spoken-guard-audio-evidence",
        global_root=tmp_path / "app",
        gate_policy="audio-evidence",
    )
    assert summary["gate_ok"] is False
    assert summary["audio_evidence_debt"] == 2
    assert summary["audio_evidence_debt_by_code"] == {
        "live_claim_guard": 1,
        "live_claim_guard_spoken_fallback": 1,
    }


def test_report_blocks_spoken_hidden_audio_source_detail(tmp_path: Path) -> None:
    session = tmp_path / "recordings" / "20260531-122000"
    _write_jsonl(
        session / "events.jsonl",
        [
            {
                "t": 0.0,
                "kind": "session_start",
                "wall_clock_iso": "2026-05-31T16:00:00+03:00",
            },
            {
                "t": 1.0,
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": "0001",
                "event": "MIX_MOVE",
                "message": "The vocal opened up and the kick got tighter.",
                "citation": {"count": 1, "action": "emit"},
                "moves": {
                    "event_type": "MIX_MOVE",
                    "event_moves": [{"label": "A_low: flat->killed"}],
                    "vocal_active": False,
                },
                "extra": {"deck_audio_parts": 1},
            },
            {
                "t": 1.1,
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": "0002",
                "event": "REENTRY_KICK_LAND",
                "message": "The kick came in clean.",
                "citation": {"count": 1, "action": "emit"},
                "moves": {"event_type": "REENTRY_KICK_LAND", "vocal_active": False},
                "extra": {"deck_audio_parts": 1},
            },
        ],
    )

    report = build_cohost_viber_report(session, include_viber=False)

    issue = next(i for i in report["issues"] if i["code"] == "cohost_audio_source_detail_emit")
    assert issue["severity"] == "blocker"
    assert issue["response_id"] == "0001"
    assert "vocal opened" in issue["detail"]
    assert "0002" not in {
        i.get("response_id") for i in report["issues"] if i["code"] == "cohost_audio_source_detail_emit"
    }


def test_ack_only_zero_citation_is_watch_not_blocker(tmp_path: Path) -> None:
    session = tmp_path / "recordings" / "20260531-130000"
    _write_jsonl(
        session / "events.jsonl",
        [
            {
                "t": 1.0,
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": "0001",
                "message": "I'm listening.",
                "citation": {"count": 0, "action": "emit"},
                "extra": {"deck_audio_parts": 0},
            }
        ],
    )

    report = build_cohost_viber_report(session, include_viber=False)

    assert report["ok"] is True
    issue = next(i for i in report["issues"] if i["code"] == "citation_zero_ack")
    assert issue["severity"] == "watch"


def test_repeated_ack_only_zero_citation_blocks_uncertain_tts(tmp_path: Path) -> None:
    session = tmp_path / "recordings" / "20260531-131000"
    _write_jsonl(
        session / "events.jsonl",
        [
            {
                "t": float(index),
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": f"000{index}",
                "message": "I'm listening.",
                "citation": {"count": 0, "action": "emit"},
                "extra": {"deck_audio_parts": 0},
            }
            for index in range(1, 4)
        ],
    )

    report = build_cohost_viber_report(session, include_viber=False)

    assert report["ok"] is False
    assert report["metrics"]["session"]["citation_zero_ack_emits"] == 3
    issue = next(i for i in report["issues"] if i["code"] == "citation_zero_ack_loop")
    assert issue["severity"] == "blocker"
    assert "zero_citation_ack_count=3" in issue["detail"]


def test_latest_session_prefers_newest_session_with_ai_message(tmp_path: Path) -> None:
    root = tmp_path / "recordings"
    older = root / "20260531-100000"
    newer = _session(tmp_path, "20260531-110000")
    _write_jsonl(older / "events.jsonl", [{"kind": "session_start"}])
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))

    assert latest_session(root) == newer


def test_session_start_iso_prefers_wall_clock_then_directory_name(tmp_path: Path) -> None:
    session = tmp_path / "recordings" / "20260601-004304"
    _write_jsonl(
        session / "events.jsonl",
        [
            {
                "kind": "session_start",
                "wall_clock_iso": "2026-06-01T00:43:04.815+03:00",
            }
        ],
    )

    assert session_start_iso(session) == "2026-06-01T00:43:04.815000+03:00"

    no_clock = tmp_path / "recordings" / "20260601-010203"
    _write_jsonl(no_clock / "events.jsonl", [{"kind": "session_start"}])

    assert session_start_iso(no_clock).startswith("2026-06-01T01:02:03")


def test_history_sweep_summarizes_recent_sessions_and_viber_window(tmp_path: Path) -> None:
    import vibemix.__main__ as main_mod

    failing = _session(tmp_path, "20260531-100000")
    clean = tmp_path / "recordings" / "20260531-110000"
    _write_jsonl(
        clean / "events.jsonl",
        [
            {
                "t": 1.0,
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": "clean-1",
                "message": "I'm listening.",
                "citation": {"count": 0, "action": "emit"},
                "extra": {"deck_audio_parts": 1},
            }
        ],
    )
    os.utime(failing, (1, 1))
    os.utime(clean, (2, 2))

    global_root = tmp_path / "app"
    _write_jsonl(
        global_root / "ai_messages" / "ai_messages.jsonl",
        [
            {
                "schema_version": 1,
                "engine": "codex",
                "surface": "viber_chat",
                "response_id": "viber-1",
                "message": "I caught the live move.",
                "extra": {
                    "request": "find me dark rolling hypnotic techno",
                    "live_verification": {
                        "ok": True,
                        "violations": [],
                        "guard_applied": True,
                        "guard_violations": ["unsupported_live_outcome_claim"],
                    },
                },
            }
        ],
    )

    sweep = build_cohost_viber_history_sweep(
        tmp_path / "recordings",
        global_root=global_root,
        max_sessions=2,
    )

    assert sweep["schema"] == "cohost_viber_history_sweep_v1"
    assert sweep["ok"] is False
    assert sweep["session_count"] == 2
    assert sweep["issue_counts"]["blocker"] >= 2
    assert sweep["issue_code_counts"]["citation_strip"] == 1
    assert sweep["issue_code_counts"]["viber_library_request_live_leak"] == 1
    assert sweep["viber"]["issue_count"] == 2
    md = format_cohost_viber_history_markdown(sweep)
    assert "# Cohost/Viber History Sweep" in md
    assert "citation_strip" in md

    rc = main_mod._run_eval_cli(
        [
            "history-sweep",
            "--recordings-root",
            str(tmp_path / "recordings"),
            "--global-root",
            str(global_root),
            "--max-sessions",
            "2",
            "--json",
        ]
    )
    assert rc == 1


def test_failure_corpus_exports_recent_replay_cases_without_full_prompts(tmp_path: Path) -> None:
    import vibemix.__main__ as main_mod

    _session(tmp_path, "20260531-123000")
    global_root = tmp_path / "app"
    artifact_dir = global_root / "ai_messages" / "artifacts" / "viber-1"
    artifact_dir.mkdir(parents=True)
    meta = {
        "response_id": "viber-1",
        "surface": "viber_chat",
        "message": "I caught the live move. The useful note is the sound change right there.",
        "moves": {
            "live_context_schema_version": 2,
            "live_context_deck": "none",
            "live_context_deck_mixer": {"connected": True},
        },
        "extra": {
            "request": "find me dark rolling hypnotic techno",
            "live_verification": {
                "ok": True,
                "violations": [],
                "guard_applied": True,
                "guard_violations": ["unsupported_live_outcome_claim"],
            },
        },
    }
    (artifact_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (artifact_dir / "prompt.txt").write_text(
        "FULL_PROMPT_BODY_SHOULD_STAY_IN_ARTIFACT_FILE",
        encoding="utf-8",
    )
    (artifact_dir / "response.txt").write_text(str(meta["message"]), encoding="utf-8")
    _write_jsonl(
        global_root / "ai_messages" / "ai_messages.jsonl",
        [
            {
                **meta,
                "engine": "codex",
                "ts_iso": "2026-05-31T16:00:05+03:00",
                "artifacts": {
                    "prompt_path": str(artifact_dir / "prompt.txt"),
                    "response_path": str(artifact_dir / "response.txt"),
                    "meta_path": str(artifact_dir / "meta.json"),
                },
            }
        ],
    )

    manifest = export_cohost_viber_failure_corpus(
        tmp_path / "recordings",
        tmp_path / "corpus",
        global_root=global_root,
        max_sessions=2,
    )

    assert manifest["schema"] == "cohost_viber_failure_corpus_v1"
    assert manifest["ok"] is True
    assert manifest["release_ready"] is False
    assert manifest["case_count"] >= 5
    assert manifest["captured_case_count"] >= 5
    assert manifest["policy_canary_count"] >= 4
    assert manifest["issue_code_counts"]["citation_strip"] == 1
    assert manifest["issue_code_counts"]["audio_vibe_listener_read_allowed"] == 1
    assert manifest["issue_code_counts"]["audio_vibe_control_causality"] == 1
    assert manifest["issue_code_counts"]["audio_vibe_hidden_source_detail"] == 1
    assert manifest["issue_code_counts"]["cohost_audio_source_detail_emit"] == 1
    assert manifest["issue_code_counts"]["citation_zero_ack_loop"] == 1
    assert manifest["issue_code_counts"]["viber_library_request_live_leak"] >= 2
    assert Path(manifest["manifest_path"]).exists()
    assert Path(manifest["cases_path"]).exists()
    cases_text = Path(manifest["cases_path"]).read_text(encoding="utf-8")
    assert "find me dark rolling hypnotic techno" in cases_text
    assert "I caught the live move" in cases_text
    assert "FULL_PROMPT_BODY_SHOULD_STAY_IN_ARTIFACT_FILE" not in cases_text
    first_case = json.loads(cases_text.splitlines()[0])
    assert first_case["case_id"]
    assert first_case["repair_gates"]

    rc = main_mod._run_eval_cli(
        [
            "failure-corpus",
            "--recordings-root",
            str(tmp_path / "recordings"),
            "--global-root",
            str(global_root),
            "--max-sessions",
            "2",
            "--out-dir",
            str(tmp_path / "corpus-cli"),
            "--json",
        ]
    )
    assert rc == 0
    cli_manifest = json.loads((tmp_path / "corpus-cli" / "manifest.json").read_text(encoding="utf-8"))
    assert cli_manifest["case_count"] == manifest["case_count"]

    benchmark = run_failure_corpus_benchmark(tmp_path / "corpus", tmp_path / "benchmark")
    assert benchmark["schema"] == "cohost_viber_corpus_benchmark_v1"
    assert benchmark["ok"] is True
    assert benchmark["release_gate_ok"] is False
    assert benchmark["case_count"] == manifest["case_count"]
    assert benchmark["passed"] == manifest["case_count"]
    assert benchmark["failed"] == 0
    assert benchmark["score_mode_counts"]["corpus_gate"] >= 1
    assert benchmark["score_mode_counts"]["viber_meta"] == 2
    assert Path(tmp_path / "benchmark" / "benchmark_manifest.json").exists()

    bench_rc = main_mod._run_eval_cli(
        [
            "corpus-benchmark",
            "--corpus-dir",
            str(tmp_path / "corpus"),
            "--out-dir",
            str(tmp_path / "benchmark-cli"),
            "--json",
        ]
    )
    assert bench_rc == 0
    cli_benchmark = json.loads(
        (tmp_path / "benchmark-cli" / "benchmark_manifest.json").read_text(encoding="utf-8")
    )
    assert cli_benchmark["passed"] == benchmark["passed"]


def test_failure_corpus_policy_canaries_run_without_captured_failures(tmp_path: Path) -> None:
    recordings = tmp_path / "recordings"
    recordings.mkdir()

    manifest = export_cohost_viber_failure_corpus(
        recordings,
        tmp_path / "policy-corpus",
        include_viber=False,
    )

    assert manifest["release_ready"] is True
    assert manifest["captured_case_count"] == 0
    assert manifest["policy_canary_count"] >= 4
    assert manifest["issue_code_counts"]["audio_vibe_listener_read_allowed"] == 1
    assert manifest["issue_code_counts"]["audio_vibe_control_causality"] == 1
    assert manifest["issue_code_counts"]["audio_vibe_hidden_source_detail"] == 1
    assert manifest["issue_code_counts"]["cohost_audio_source_detail_emit"] == 1
    assert manifest["issue_code_counts"]["citation_zero_ack_loop"] == 1
    assert manifest["issue_code_counts"]["viber_library_request_live_leak"] == 1

    benchmark = run_failure_corpus_benchmark(
        tmp_path / "policy-corpus",
        tmp_path / "policy-benchmark",
    )

    assert benchmark["ok"] is True
    assert benchmark["release_gate_ok"] is True
    assert benchmark["passed"] == benchmark["case_count"]

    def bad_repairer(job: dict) -> dict:
        job_id = str(job.get("job_id") or "")
        if "uncertain_ack_loop" in job_id or "citation_zero_ack_loop" in job_id:
            reply = "I'm listening."
        elif "audio_vibe_listener" in job_id:
            reply = ""
        elif "cohost_audio_source" in job_id or "cohost_audio_source_detail" in job_id:
            reply = "The vocal opened up and the kick got tighter."
        elif "audio_vibe_hidden" in job_id:
            reply = "The vocal opened up and the kick got tighter."
        elif "audio_vibe" in job_id:
            reply = "That EQ move made the vocal open up and the kick got tighter."
        else:
            reply = "I caught the live move. The useful note is the sound change right there."
        return {
            "reply": reply,
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "move_grades": [],
            "playlist": None,
        }

    bad_benchmark = run_failure_corpus_benchmark(
        tmp_path / "policy-corpus",
        tmp_path / "policy-bad-benchmark",
        backend="codex",
        repairer=bad_repairer,
    )

    assert bad_benchmark["ok"] is False
    assert bad_benchmark["release_gate_ok"] is False
    all_violations = {
        violation
        for result in bad_benchmark["results"]
        for violation in result.get("violations", [])
    }
    assert "audio_vibe_control_causality" in all_violations
    assert "unsupported_audio_source_detail_claim" in all_violations
    assert "audio_listener_read_should_not_be_silent" in all_violations
    assert "citation_issue_should_be_silent" in all_violations
    assert "library_request_live_leak" in all_violations


def test_failure_corpus_can_pin_current_session_and_filter_stale_viber_rows(
    tmp_path: Path,
) -> None:
    stale_session = _session(tmp_path, "20260531-100000")
    current_session = tmp_path / "recordings" / "20260531-230000"
    _write_jsonl(current_session / "events.jsonl", [{"kind": "session_start"}])
    os.utime(stale_session, (1, 1))
    os.utime(current_session, (2, 2))

    global_root = tmp_path / "app"
    _write_jsonl(
        global_root / "ai_messages" / "ai_messages.jsonl",
        [
            {
                "ts_iso": "2026-05-31T10:00:00+00:00",
                "engine": "codex",
                "surface": "viber_chat",
                "response_id": "old-viber",
                "message": "I caught the live move. The useful note is the sound change right there.",
                "extra": {
                    "request": "find me dark rolling hypnotic techno",
                    "live_verification": {
                        "ok": True,
                        "violations": [],
                        "guard_applied": True,
                        "guard_violations": ["unsupported_live_outcome_claim"],
                    },
                },
            }
        ],
    )

    manifest = export_cohost_viber_failure_corpus(
        tmp_path / "recordings",
        tmp_path / "current-corpus",
        global_root=global_root,
        session_dirs=[current_session],
        global_since_iso="2026-05-31T22:00:00+00:00",
    )

    assert manifest["release_ready"] is True
    assert manifest["captured_case_count"] == 0
    assert manifest["session_dirs"] == [str(current_session)]
    assert manifest["global_since_iso"] == "2026-05-31T22:00:00+00:00"
    assert manifest["issue_code_counts"]["viber_library_request_live_leak"] == 1
    cases_text = Path(manifest["cases_path"]).read_text(encoding="utf-8")
    assert "old-viber" not in cases_text
    assert "policy_library_request_no_live_leak" in cases_text


def test_markdown_contains_queue_and_metrics(tmp_path: Path) -> None:
    report = build_cohost_viber_report(_session(tmp_path), include_viber=False)
    md = format_cohost_viber_markdown(report)

    assert "# Cohost/Viber Automation Report" in md
    assert "## Automation Queue" in md
    assert "zero_citation_emits=1" in md


def test_eval_cli_latest_session_json(capsys, tmp_path: Path) -> None:
    import vibemix.__main__ as main_mod

    session = _session(tmp_path)

    rc = main_mod._run_eval_cli(
        ["latest-session", "--session-dir", str(session), "--no-viber", "--json"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert rc == 1
    assert payload["schema"] == "cohost_viber_automation_report_v1"
    assert payload["session_dir"] == str(session)


def test_reprompt_pack_writes_jobs_and_scores_candidates(tmp_path: Path) -> None:
    session = _session(tmp_path)
    global_root = tmp_path / "app"
    artifact_dir = global_root / "ai_messages" / "artifacts" / "viber-1"
    artifact_dir.mkdir(parents=True)
    meta = {
        "response_id": "viber-1",
        "surface": "viber_chat",
        "message": "I caught the live move. The useful note is the sound change right there.",
        "moves": {
            "live_context_schema_version": 2,
            "live_context_deck": "none",
            "live_context_deck_mixer": {"connected": True},
        },
        "extra": {
            "request": "find me dark rolling hypnotic techno",
            "live_verification": {
                "ok": True,
                "violations": [],
                "guard_applied": True,
                "guard_violations": ["unsupported_live_outcome_claim"],
            },
        },
    }
    (artifact_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (artifact_dir / "prompt.txt").write_text("original prompt", encoding="utf-8")
    (artifact_dir / "response.txt").write_text(str(meta["message"]), encoding="utf-8")
    _write_jsonl(
        global_root / "ai_messages" / "ai_messages.jsonl",
        [
            {
                **meta,
                "engine": "codex",
                "artifacts": {
                    "prompt_path": str(artifact_dir / "prompt.txt"),
                    "response_path": str(artifact_dir / "response.txt"),
                    "meta_path": str(artifact_dir / "meta.json"),
                },
            }
        ],
    )

    report = build_cohost_viber_report(session, global_root=global_root)
    pack = write_reprompt_pack(report, tmp_path / "pack")

    assert pack["schema"] == "cohost_viber_reprompt_pack_v1"
    assert pack["job_count"] >= 1
    reprompt = "\n".join(
        path.read_text(encoding="utf-8") for path in (tmp_path / "pack").glob("*/reprompt.md")
    )
    assert "dark rolling hypnotic techno" in reprompt
    assert "library/crate replies must not mention live/deck/move" in reprompt

    bad_candidate = tmp_path / "bad.json"
    bad_candidate.write_text(
        json.dumps({"reply": "I caught the live move.", "tools_used": [], "track_ids": []}),
        encoding="utf-8",
    )
    bad_score = score_reprompt_candidate(artifact_dir / "meta.json", bad_candidate)
    assert bad_score["ok"] is False
    assert "library_request_live_leak" in bad_score["violations"]

    good_candidate = tmp_path / "good.json"
    good_candidate.write_text(
        json.dumps(
            {
                "reply": "I do not have grounded results to show yet.",
                "tools_used": [],
                "track_ids": [],
            }
        ),
        encoding="utf-8",
    )
    good_score = score_reprompt_candidate(artifact_dir / "meta.json", good_candidate)
    assert good_score["ok"] is True


def test_repair_pack_generates_and_scores_deterministic_candidates(tmp_path: Path) -> None:
    import vibemix.__main__ as main_mod

    session = tmp_path / "recordings" / "20260531-140000"
    _write_jsonl(
        session / "events.jsonl",
        [
            {
                "t": 0.0,
                "kind": "session_start",
                "wall_clock_iso": "2026-05-31T16:00:00+03:00",
            },
            {
                "t": 1.0,
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": "0001",
                "message": "I'm listening.",
                "citation": {"count": 0, "action": "emit"},
                "extra": {"deck_audio_parts": 1},
            },
        ],
    )
    global_root = tmp_path / "app"
    artifact_dir = global_root / "ai_messages" / "artifacts" / "viber-1"
    artifact_dir.mkdir(parents=True)
    meta = {
        "response_id": "viber-1",
        "surface": "viber_chat",
        "message": "I caught the live move.",
        "moves": {
            "live_context_schema_version": 2,
            "live_context_deck": "none",
            "live_context_deck_mixer": {"connected": True},
        },
        "extra": {
            "request": "find me dark rolling hypnotic techno",
            "live_verification": {
                "ok": True,
                "violations": [],
                "guard_applied": True,
                "guard_violations": ["unsupported_live_outcome_claim"],
            },
        },
    }
    for name, body in {
        "meta.json": json.dumps(meta),
        "prompt.txt": "original prompt",
        "response.txt": str(meta["message"]),
    }.items():
        (artifact_dir / name).write_text(body, encoding="utf-8")
    _write_jsonl(
        global_root / "ai_messages" / "ai_messages.jsonl",
        [
            {
                **meta,
                "engine": "codex",
                "ts_iso": "2026-05-31T16:00:05+03:00",
                "artifacts": {
                    "prompt_path": str(artifact_dir / "prompt.txt"),
                    "response_path": str(artifact_dir / "response.txt"),
                    "meta_path": str(artifact_dir / "meta.json"),
                },
            }
        ],
    )
    pack_dir = tmp_path / "pack"
    report = build_cohost_viber_report(session, global_root=global_root)
    write_reprompt_pack(report, pack_dir)

    repair = run_reprompt_pack_repair(pack_dir, tmp_path / "repair")

    assert repair["schema"] == "cohost_viber_auto_repair_run_v1"
    assert repair["backend"] == "deterministic"
    assert repair["ok"] is True
    assert repair["passed"] == repair["job_count"]
    candidate = json.loads(
        Path(repair["results"][0]["candidate_path"]).read_text(encoding="utf-8")
    )
    assert candidate["reply"] == "I do not have grounded results to show yet."

    rc = main_mod._run_eval_cli(
        [
            "repair-pack",
            "--pack-dir",
            str(pack_dir),
            "--out-dir",
            str(tmp_path / "repair-cli"),
            "--backend",
            "deterministic",
            "--json",
        ]
    )
    assert rc == 0


def test_repair_pack_can_use_injected_model_backend(tmp_path: Path) -> None:
    session = tmp_path / "recordings" / "20260531-150000"
    _write_jsonl(
        session / "events.jsonl",
        [
            {
                "t": 1.0,
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": "0001",
                "message": "I'm listening.",
                "citation": {"count": 0, "action": "emit"},
                "extra": {"deck_audio_parts": 1},
            }
        ],
    )
    global_root = tmp_path / "app"
    artifact_dir = global_root / "ai_messages" / "artifacts" / "viber-2"
    artifact_dir.mkdir(parents=True)
    meta = {
        "response_id": "viber-2",
        "surface": "viber_chat",
        "message": "I caught the live move.",
        "moves": {
            "live_context_schema_version": 2,
            "live_context_deck": "none",
            "live_context_deck_mixer": {"connected": True},
        },
        "extra": {
            "request": "find me dark rolling hypnotic techno",
            "live_verification": {
                "ok": True,
                "violations": [],
                "guard_applied": True,
                "guard_violations": ["unsupported_live_outcome_claim"],
            },
        },
    }
    (artifact_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (artifact_dir / "prompt.txt").write_text("prompt", encoding="utf-8")
    (artifact_dir / "response.txt").write_text(str(meta["message"]), encoding="utf-8")
    _write_jsonl(
        global_root / "ai_messages" / "ai_messages.jsonl",
        [
            {
                **meta,
                "engine": "codex",
                "artifacts": {
                    "prompt_path": str(artifact_dir / "prompt.txt"),
                    "response_path": str(artifact_dir / "response.txt"),
                    "meta_path": str(artifact_dir / "meta.json"),
                },
            }
        ],
    )
    pack_dir = tmp_path / "pack"
    report = build_cohost_viber_report(session, global_root=global_root)
    write_reprompt_pack(report, pack_dir)
    seen_requests: list[str] = []

    def fake_repairer(job: dict) -> dict:
        seen_requests.append(str(job.get("request")))
        return {
            "reply": "Found 1 grounded library candidate for that vibe.",
            "tools_used": ["search_vibe"],
            "tool_trace": [{"name": "search_vibe", "arg": job.get("request"), "ok": True}],
            "track_ids": ["t000"],
            "move_grades": [],
            "playlist": None,
            "stop_reason": "model_done",
        }

    repair = run_reprompt_pack_repair(
        pack_dir,
        tmp_path / "repair-model",
        backend="codex",
        repairer=fake_repairer,
    )

    assert repair["backend"] == "codex"
    assert repair["ok"] is True
    assert repair["passed"] == repair["job_count"]
    assert seen_requests and seen_requests[0] == "find me dark rolling hypnotic techno"
    candidate = json.loads(
        Path(repair["results"][0]["candidate_path"]).read_text(encoding="utf-8")
    )
    assert candidate["tools_used"] == ["search_vibe"]


def test_autopilot_writes_report_pack_repair_and_summary(tmp_path: Path) -> None:
    import vibemix.__main__ as main_mod

    session = tmp_path / "recordings" / "20260531-160000"
    _write_jsonl(
        session / "events.jsonl",
        [
            {
                "t": 0.0,
                "kind": "session_start",
                "wall_clock_iso": "2026-05-31T16:00:00+03:00",
            },
            {
                "t": 1.0,
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": "0001",
                "message": "I'm listening.",
                "citation": {"count": 0, "action": "emit"},
                "extra": {"deck_audio_parts": 1},
            },
        ],
    )
    global_root = tmp_path / "app"
    artifact_dir = global_root / "ai_messages" / "artifacts" / "viber-3"
    artifact_dir.mkdir(parents=True)
    meta = {
        "response_id": "viber-3",
        "surface": "viber_chat",
        "message": "I caught the live move.",
        "moves": {
            "live_context_schema_version": 2,
            "live_context_deck": "none",
            "live_context_deck_mixer": {"connected": True},
        },
        "extra": {
            "request": "find me dark rolling hypnotic techno",
            "live_verification": {
                "ok": True,
                "violations": [],
                "guard_applied": True,
                "guard_violations": ["unsupported_live_outcome_claim"],
            },
        },
    }
    (artifact_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (artifact_dir / "prompt.txt").write_text("prompt", encoding="utf-8")
    (artifact_dir / "response.txt").write_text(str(meta["message"]), encoding="utf-8")
    _write_jsonl(
        global_root / "ai_messages" / "ai_messages.jsonl",
        [
            {
                **meta,
                "engine": "codex",
                "ts_iso": "2026-05-31T16:00:05+03:00",
                "artifacts": {
                    "prompt_path": str(artifact_dir / "prompt.txt"),
                    "response_path": str(artifact_dir / "response.txt"),
                    "meta_path": str(artifact_dir / "meta.json"),
                },
            }
        ],
    )

    summary = run_cohost_viber_autopilot(
        session,
        tmp_path / "autopilot",
        global_root=global_root,
    )

    assert summary["schema"] == "cohost_viber_autopilot_v1"
    assert summary["status"] == "repaired_candidate_ready"
    assert summary["ok"] is True
    assert summary["gate_ok"] is True
    assert summary["gate_policy"] == "automation"
    assert summary["release_gate_ok"] is False
    assert summary["first_pass_clean"] is False
    assert summary["reprompt_debt"] > 0
    assert summary["repair"]["passed"] == summary["reprompt_jobs"]
    assert Path(summary["artifacts"]["report_json"]).exists()
    assert Path(summary["artifacts"]["reprompt_pack"]).is_dir()
    assert Path(summary["artifacts"]["repair_run"]).is_dir()

    rc = main_mod._run_eval_cli(
        [
            "autopilot",
            "--session-dir",
            str(session),
            "--global-root",
            str(global_root),
            "--out-dir",
            str(tmp_path / "autopilot-cli"),
            "--json",
        ]
    )
    assert rc == 0

    strict_rc = main_mod._run_eval_cli(
        [
            "autopilot",
            "--session-dir",
            str(session),
            "--global-root",
            str(global_root),
            "--out-dir",
            str(tmp_path / "autopilot-release-gate"),
            "--fail-on",
            "release",
            "--json",
        ]
    )
    strict_summary = json.loads(
        (tmp_path / "autopilot-release-gate" / "autopilot_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert strict_rc == 1
    assert strict_summary["ok"] is True
    assert strict_summary["gate_ok"] is False
    assert strict_summary["gate_policy"] == "release"
    assert strict_summary["release_gate_ok"] is False

    first_pass_rc = main_mod._run_eval_cli(
        [
            "autopilot",
            "--session-dir",
            str(session),
            "--global-root",
            str(global_root),
            "--out-dir",
            str(tmp_path / "autopilot-first-pass-gate"),
            "--fail-on",
            "first-pass",
            "--json",
        ]
    )
    first_pass_summary = json.loads(
        (tmp_path / "autopilot-first-pass-gate" / "autopilot_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert first_pass_rc == 1
    assert first_pass_summary["ok"] is True
    assert first_pass_summary["gate_ok"] is False
    assert first_pass_summary["gate_policy"] == "first-pass"
    assert first_pass_summary["first_pass_clean"] is False

    audio_rc = main_mod._run_eval_cli(
        [
            "autopilot",
            "--session-dir",
            str(session),
            "--global-root",
            str(global_root),
            "--out-dir",
            str(tmp_path / "autopilot-audio-evidence-gate"),
            "--fail-on",
            "audio-evidence",
            "--json",
        ]
    )
    audio_summary = json.loads(
        (tmp_path / "autopilot-audio-evidence-gate" / "autopilot_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert audio_rc == 1
    assert audio_summary["ok"] is True
    assert audio_summary["gate_ok"] is False
    assert audio_summary["gate_policy"] == "audio-evidence"
    assert audio_summary["audio_evidence_debt"] > 0
