# SPDX-License-Identifier: Apache-2.0
"""Cohost/Viber session report automation.

This module is deliberately deterministic: it reads the artifacts the product
already writes (session ``events.jsonl`` plus optional global Viber
``ai_messages.jsonl``), then produces a compact repair queue. It does not call a
model or touch audio hardware, so it can run after every dev session.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPORT_SCHEMA = "cohost_viber_automation_report_v1"
REPROMPT_PACK_SCHEMA = "cohost_viber_reprompt_pack_v1"
CANDIDATE_SCORE_SCHEMA = "cohost_viber_reprompt_candidate_score_v1"
AUTO_REPAIR_SCHEMA = "cohost_viber_auto_repair_run_v1"
AUTOPILOT_SCHEMA = "cohost_viber_autopilot_v1"
HISTORY_SWEEP_SCHEMA = "cohost_viber_history_sweep_v1"
FAILURE_CORPUS_SCHEMA = "cohost_viber_failure_corpus_v1"
CORPUS_BENCHMARK_SCHEMA = "cohost_viber_corpus_benchmark_v1"

_ACK_SNIPPETS = (
    "i'm listening",
    "im listening",
    "i am listening",
    "listening",
    "i hear it",
)
_ZERO_ACK_LOOP_THRESHOLD = 3

_SEVERITY_RANK = {"blocker": 0, "care": 1, "watch": 2}
_SILENT_COHOST_REPAIR_CODES = {
    "citation_strip_silent",
    "citation_strip",
    "citation_bypass",
    "citation_zero_emit",
    "citation_zero_ack_loop",
    "live_claim_guard_spoken_fallback",
}
_CITATION_SILENT_REPAIR_CODES = {
    "citation_strip_silent",
    "citation_strip",
    "citation_bypass",
    "citation_zero_emit",
    "citation_zero_ack_loop",
}
_AUDIO_EVIDENCE_DEBT_CODES = frozenset(
    {
        "audio_vibe_control_causality",
        "audio_vibe_hidden_source_detail",
        "cohost_audio_source_detail_emit",
        "live_claim_guard",
        "live_claim_guard_spoken_fallback",
        "viber_library_request_guarded_reply",
        "viber_library_request_live_leak",
        "viber_live_guarded_reply",
        "viber_live_verification",
        "viber_prompt_missing_audio_contract",
    }
)

Repairer = Callable[[dict[str, Any]], dict[str, Any]]

_LIBRARY_REQUEST_RE = re.compile(
    r"\b("
    r"find|search|discover|dig|recommend|suggest|give me|make me|build|curate|"
    r"playlist|crate|set|tracks?|songs?|vibe"
    r")\b",
    re.IGNORECASE,
)
_LIVE_LEAK_RE = re.compile(
    r"\b("
    r"live(?:[- ]?read|[- ]?move|[- ]?deck)?|current deck|deck blocker|"
    r"claim_policy|resolved decks?|evidence gate|sound change|transition|blend|"
    r"switch|segue|handoff|bridge|layer|that drop|the drop|move right there"
    r")\b",
    re.IGNORECASE,
)
_OUTCOME_CLAIM_RE = re.compile(
    r"\b("
    r"great transition|nice transition|clean blend|blend was clean|nice switch|"
    r"caught the live move|sound change right there|incoming track came in clean|"
    r"drop happened|low cut cleaned|energy shifted"
    r")\b",
    re.IGNORECASE,
)
_HONEST_EMPTY_LIBRARY_RE = re.compile(
    r"\b("
    r"no grounded|no local library|no library results|could(?:n't| not) search|"
    r"do not have grounded results|don't have grounded results|try again"
    r")\b",
    re.IGNORECASE,
)
_AUDIO_CAUSAL_WORD_RE = re.compile(
    r"\b("
    r"eq|fader|filter|knob|cue|low cut|high cut|bass cut"
    r")\b.{0,80}\b("
    r"made|fixed|cleaned|cleared|tightened|opened|saved|improved|caused"
    r")\b|"
    r"\b("
    r"made|fixed|cleaned|cleared|tightened|opened|saved|improved|caused"
    r")\b.{0,80}\b("
    r"eq|fader|filter|knob|cue|low cut|high cut|bass cut"
    r")\b",
    re.IGNORECASE,
)
_AUDIO_SOURCE_DETAIL_NOUN_RE = re.compile(
    r"\b("
    r"vocal|vocals|voice|lyric|lyrics|kick|kickdrum|kick drum|snare|clap|"
    r"hi[- ]?hat|hat|hats|drum|drums|bassline|lead|synth|pad|stem|stems|"
    r"acapella|instrumental"
    r")\b",
    re.IGNORECASE,
)
_AUDIO_SOURCE_DETAIL_CLAIM_RE = re.compile(
    r"\b("
    r"hear|heard|hearing|sounds?|feels?|opened(?:\s+up)?|opening|"
    r"tight(?:ened|er|ening)?|clean(?:ed|er)?|clear(?:ed|er)?|brighter|"
    r"darker|wider|punch(?:y|ier)|muddy|muddier|landed|came in|sits?|"
    r"cut(?:s|ting)? through|present|up front"
    r")\b",
    re.IGNORECASE,
)
_AUDIO_SOURCE_DETAIL_BOUNDARY_RE = re.compile(
    r"\b("
    r"can't tell|cannot tell|can't say|cannot say|not enough proof|not proof|"
    r"don't have proof|do not have proof|won't claim|will not claim|"
    r"not source[- ]level proof|not stem proof|not isolated"
    r")\b",
    re.IGNORECASE,
)
_AUDIO_LISTENER_READ_RE = re.compile(
    r"\b("
    r"low end|sub|bass|mid|high|top end|energy|texture|density|motion|mood|"
    r"room|mix|sound|audio|hollow|thin|thick|bright|brighter|dark|darker|"
    r"wide|wider|muddy|muddier|clean|cleaner|quiet|quieter|loud|louder|"
    r"silent|silence|fell|dropped|rose|lifted"
    r")\b",
    re.IGNORECASE,
)
_AUDIO_KICK_EVENT_TYPES = {
    "KICK_SWAP",
    "KICK_DENSITY_SHIFT",
    "BREAKDOWN_KICK_KILL",
    "REENTRY_KICK_LAND",
}
_AUDIO_VOCAL_NOUNS = {"vocal", "vocals", "voice", "lyric", "lyrics", "acapella"}
_AUDIO_KICK_NOUNS = {"kick", "kickdrum", "kick drum"}
_ACTIVE_LIVE_CONTEXT_PROMPT_MARKER = "LIVE CONTEXT USE: active_live_context"
_LIVE_AUDIO_CONTRACT_MARKERS = (
    "LIVE AUDIO CONTRACT",
    "never credit or blame the control from audio alone",
)
_PROMPT_REPAIR_FIELDS = (
    "prompt_patch",
    "prompt_delta",
    "prompt_rewrite",
    "system_instruction_patch",
)


@dataclass(frozen=True)
class ReportIssue:
    code: str
    severity: str
    surface: str
    title: str
    detail: str
    repair: str
    response_id: str | None = None
    artifact: str | None = None
    prompt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out = {
            "code": self.code,
            "severity": self.severity,
            "surface": self.surface,
            "title": self.title,
            "detail": self.detail,
            "repair": self.repair,
        }
        if self.response_id:
            out["response_id"] = self.response_id
        if self.artifact:
            out["artifact"] = self.artifact
        if self.prompt:
            out["prompt"] = self.prompt
        return out


@dataclass
class _ReportBuilder:
    session_dir: Path
    global_root: Path | None
    include_viber: bool
    max_global_rows: int
    global_since_iso: str | None = None
    rows: list[dict[str, Any]] = field(default_factory=list)
    global_rows: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    issues: list[ReportIssue] = field(default_factory=list)

    def build(self) -> dict[str, Any]:
        self.rows = _read_jsonl(self.session_dir / "events.jsonl", self.errors)
        if self.include_viber and self.global_root is not None:
            global_log = self.global_root / "ai_messages" / "ai_messages.jsonl"
            global_rows = _read_jsonl(global_log, self.errors) if global_log.exists() else []
            self.global_rows = _recent_viber_rows(
                global_rows,
                limit=self.max_global_rows,
                since_iso=self.global_since_iso,
            )

        session_metrics = self._session_metrics()
        viber_metrics = self._viber_metrics()
        self._inspect_session_rows()
        self._inspect_viber_rows()
        self._add_absence_issues(session_metrics, viber_metrics)

        issue_dicts = [issue.to_dict() for issue in _sorted_issues(self.issues)]
        return {
            "schema": REPORT_SCHEMA,
            "ok": not any(issue.severity == "blocker" for issue in self.issues) and not self.errors,
            "session_dir": str(self.session_dir),
            "global_root": str(self.global_root) if self.global_root is not None else None,
            "metrics": {
                "session": session_metrics,
                "viber": viber_metrics,
                "audio_evidence_debt": _audio_evidence_debt(issue_dicts),
            },
            "issues": issue_dicts,
            "automation_queue": _automation_queue(issue_dicts),
            "errors": self.errors,
        }

    def _session_metrics(self) -> dict[str, Any]:
        ai_messages = [row for row in self.rows if row.get("kind") == "ai_message"]
        citation_counts = [
            row for row in self.rows if row.get("kind") == "citation_count"
        ]
        live_rows = [row for row in ai_messages if row.get("engine") == "live_coach"]
        heard = [row for row in self.rows if row.get("kind") == "ai_text"]
        zero_emit = [
            row
            for row in ai_messages
            if _citation_action(row) in {"emit", "bypass"} and _citation_count(row) == 0
        ]
        ack_zero = [row for row in zero_emit if _is_ack(_message_text(row))]
        non_ack_zero = [row for row in zero_emit if not _is_ack(_message_text(row))]
        return {
            "events": len(self.rows),
            "ai_messages": len(ai_messages),
            "live_coach_messages": len(live_rows),
            "heard_ai_text": len(heard),
            "citation_count_events": len(citation_counts),
            "citation_count_zero_events": sum(
                1 for row in citation_counts if _int_or_none(row.get("count")) == 0
            ),
            "citation_zero_emits": len(zero_emit),
            "citation_zero_ack_emits": len(ack_zero),
            "citation_zero_non_ack_emits": len(non_ack_zero),
            "citation_strips": _kind_count(self.rows, "citation_strip"),
            "citation_bypasses": _kind_count(self.rows, "citation_bypass"),
            "slop_suppressed": _kind_count(self.rows, "slop_suppressed"),
            "manual_silence_short_circuits": _kind_count(
                self.rows, "manual_silence_short_circuit"
            ),
            "live_claim_guard_corrections": _kind_count(self.rows, "live_claim_guard"),
            "deck_audio_part_turns": sum(
                1 for row in live_rows if _extra_int(row, "deck_audio_parts") > 0
            ),
            "no_deck_audio_part_turns": sum(
                1 for row in live_rows if _extra_int(row, "deck_audio_parts") == 0
            ),
        }

    def _viber_metrics(self) -> dict[str, Any]:
        rows = self.global_rows
        violations = 0
        guard_violations = 0
        guarded = 0
        errors = 0
        for row in rows:
            verification = _live_verification(row)
            row_violations = verification.get("violations")
            row_guard_violations = verification.get("guard_violations")
            if isinstance(row_violations, list):
                violations += len(row_violations)
            if isinstance(row_guard_violations, list):
                guard_violations += len(row_guard_violations)
            if verification.get("guard_applied"):
                guarded += 1
            extra = row.get("extra")
            if isinstance(extra, dict) and extra.get("error"):
                errors += 1
        return {
            "rows_inspected": len(rows),
            "live_verification_violations": violations,
            "guarded_reply_violations": guard_violations,
            "guarded_replies": guarded,
            "errored_rows": errors,
            "surfaces": sorted(
                {
                    str(row.get("surface"))
                    for row in rows
                    if isinstance(row.get("surface"), str)
                }
            ),
        }

    def _inspect_session_rows(self) -> None:
        spoken_fallback_texts = _live_claim_guard_spoken_fallback_texts(self.rows)
        zero_ack_rows = _zero_citation_ack_rows(self.rows)
        ai_rows_by_response_id = _ai_rows_by_response_id(self.rows)
        if len(zero_ack_rows) >= _ZERO_ACK_LOOP_THRESHOLD:
            response_ids = [
                str(row.get("response_id"))
                for row in zero_ack_rows
                if isinstance(row.get("response_id"), str) and row.get("response_id")
            ]
            self.issues.append(
                ReportIssue(
                    code="citation_zero_ack_loop",
                    severity="blocker",
                    surface="cohost",
                    title="Cohost repeated uncertain ack-only TTS",
                    detail=_bounded(
                        f"zero_citation_ack_count={len(zero_ack_rows)} "
                        f"response_ids={','.join(response_ids[:5]) or 'unknown'}"
                    ),
                    repair=(
                        "Repeated no-evidence acknowledgements should become silence. "
                        "If the model is unsure, do not perform confidence through TTS."
                    ),
                    response_id=response_ids[0] if response_ids else None,
                    prompt=(
                        "Replay these turns and assert repeated ack-only, zero-citation "
                        "responses produce no spoken chunks."
                    ),
                )
            )
        for row in self.rows:
            kind = row.get("kind")
            if kind == "citation_strip":
                response_id = _str_or_none(row.get("response_id"))
                ai_row = ai_rows_by_response_id.get(response_id or "")
                silent_pre_tts = _citation_strip_was_silent_pre_tts(row, ai_row)
                self.issues.append(
                    ReportIssue(
                        code="citation_strip_silent" if silent_pre_tts else "citation_strip",
                        severity="care" if silent_pre_tts else "blocker",
                        surface="cohost",
                        title=(
                            "Cohost stayed silent on an ungrounded reply"
                            if silent_pre_tts
                            else "Cohost stripped an ungrounded reply"
                        ),
                        detail=_bounded(
                            str(row.get("reason") or "citation linter stripped a reply")
                        ),
                        repair=(
                            "Replay this invocation and tighten the event prompt so the model "
                            "chooses silence itself when it lacks evidence."
                            if silent_pre_tts
                            else (
                                "Replay this invocation and tighten the event prompt so unsupported "
                                "claims become silence, not a fabricated cited sentence."
                            )
                        ),
                        response_id=response_id,
                        artifact=_artifact_for(ai_row or row),
                        prompt=(
                            "Keep the no-TTS behavior, then reprompt this turn toward "
                            "`<silence/>` before the linter has to catch it."
                            if silent_pre_tts
                            else (
                                "Open the invocation prompt/response pair and add a regression "
                                "fixture for the missing citation atom."
                            )
                        ),
                    )
                )
            elif kind == "citation_bypass":
                self.issues.append(
                    ReportIssue(
                        code="citation_bypass",
                        severity="blocker",
                        surface="cohost",
                        title="Cohost spoke through the one-shot citation bypass",
                        detail=_bounded(str(row.get("raw_text") or row.get("reason") or "unverified text was spoken")),
                        repair=(
                            "Treat this as a release blocker: the bypass exists for continuity, "
                            "but the prompt/guard must make this turn citeable or silent."
                        ),
                        response_id=_str_or_none(row.get("response_id")),
                        prompt="Reprompt the exact event with 'if no citation resolves, say nothing' and compare against the linter.",
                    )
                )
            elif kind == "slop_suppressed":
                self.issues.append(
                    ReportIssue(
                        code="slop_suppressed",
                        severity="blocker",
                        surface="cohost",
                        title="Post-hoc slop filter caught the reply",
                        detail=_bounded("matches=" + ",".join(str(x) for x in row.get("matches", []))),
                        repair=(
                            "Promote this phrase class into the prompt negative examples and "
                            "keep the runtime filter as the last line of defense."
                        ),
                        prompt="Add a prompt regression for the matched phrase and verify the replacement stays specific to the event.",
                    )
                )
            elif kind == "live_claim_guard":
                self.issues.append(
                    ReportIssue(
                        code="live_claim_guard",
                        severity="care",
                        surface="cohost",
                        title="Live-claim guard had to correct a deck/outcome claim",
                        detail=_bounded(str(row.get("summary") or row.get("reason") or "")),
                        repair=(
                            "Use the raw/corrected pair as a prompt patch: the model should "
                            "avoid multi-deck praise before the guard has to catch it."
                        ),
                        prompt="Turn the raw_text into a failing example and the corrected_text into the desired behavior.",
                    )
                )
            elif kind == "ai_message":
                self._inspect_ai_message(row, spoken_fallback_texts=spoken_fallback_texts)

    def _inspect_ai_message(
        self,
        row: dict[str, Any],
        *,
        spoken_fallback_texts: set[str] | None = None,
    ) -> None:
        if row.get("engine") != "live_coach":
            return
        text = _message_text(row)
        action = _citation_action(row)
        count = _citation_count(row)
        response_id = _str_or_none(row.get("response_id"))
        artifact = _artifact_for(row)
        if _norm_text(text) in (spoken_fallback_texts or set()) and action in {"emit", "bypass"}:
            self.issues.append(
                ReportIssue(
                    code="live_claim_guard_spoken_fallback",
                    severity="blocker",
                    surface="cohost",
                    title="Cohost spoke a live-claim guard fallback",
                    detail=_bounded(text or "(empty response)"),
                    repair=(
                        "Treat guard-corrected live claims as strip/silence on the spoken "
                        "path. Keep raw/corrected text in artifacts and repair queues only."
                    ),
                    response_id=response_id,
                    artifact=artifact,
                    prompt="Replay this turn and assert the guard hit emits no TTS chunks or cohost-reaction.",
                )
            )
        if action in {"emit", "bypass"} and _looks_like_unsupported_audio_source_detail(row, text):
            self.issues.append(
                ReportIssue(
                    code="cohost_audio_source_detail_emit",
                    severity="blocker",
                    surface="cohost",
                    title="Cohost spoke hidden song-part detail from broad audio",
                    detail=_bounded(text or "(empty response)"),
                    repair=(
                        "Treat raw audio as listener/vibe evidence unless a grounded detector "
                        "supports the source detail. The spoken path should use broad texture "
                        "language or stay silent."
                    ),
                    response_id=response_id,
                    artifact=artifact,
                    prompt=(
                        "Replay this prompt and fail any answer that invents vocals, kicks, "
                        "stems, or source-level song-part detail from broad audio."
                    ),
                )
            )
        if action in {"emit", "bypass"} and count == 0:
            ack = _is_ack(text)
            self.issues.append(
                ReportIssue(
                    code="citation_zero_ack" if ack else "citation_zero_emit",
                    severity="watch" if ack else "care",
                    surface="cohost",
                    title="Cohost emitted without citations" if not ack else "Cohost emitted only a thin ack",
                    detail=_bounded(text or "(empty response)"),
                    repair=(
                        "Ack-only is acceptable while idle, but active-set turns should either "
                        "cite real evidence or stay silent."
                        if ack
                        else "Require a concrete [ev:/aud:/midi:/mix:/track:] citation for this class of spoken line."
                    ),
                    response_id=response_id,
                    artifact=artifact,
                    prompt="Reprompt the saved prompt with a stricter citation requirement and compare citation_count.",
                )
            )
        if _extra_int(row, "deck_audio_parts") == 0:
            self.issues.append(
                ReportIssue(
                    code="no_deck_audio_parts",
                    severity="watch",
                    surface="cohost",
                    title="Turn had no isolated deck audio parts",
                    detail=f"response_id={response_id or 'unknown'}",
                    repair=(
                        "Run `vibemix library live-context --require-proof`; for transition "
                        "verdicts, Deck A/B audio proof needs to be present before praise."
                    ),
                    response_id=response_id,
                    artifact=artifact,
                )
            )

    def _inspect_viber_rows(self) -> None:
        for row in self.global_rows:
            surface = str(row.get("surface") or "viber")
            extra = row.get("extra")
            request = str(extra.get("request") or "") if isinstance(extra, dict) else ""
            verification = _live_verification(row)
            row_violations = _verification_violations(verification)
            if row_violations:
                self.issues.append(
                    ReportIssue(
                        code="viber_live_verification",
                        severity="blocker",
                        surface=surface,
                        title="Viber reply violated live-context proof",
                        detail=_bounded(",".join(row_violations)),
                        repair=(
                            "Keep `verify_live_reply_for_viber` at the result boundary and "
                            "reprompt with the exact live-context packet before accepting move grades."
                        ),
                        response_id=_str_or_none(row.get("response_id")),
                        artifact=_artifact_for(row),
                        prompt="Run `vibemix library verify-live-reply --context <proof> --chat-result <json>` for this captured turn.",
                    )
                )
            else:
                guard_violations = _verification_guard_violations(verification)
                if verification.get("guard_applied") and guard_violations:
                    guarded_library_leak = (
                        _is_library_request(request)
                        and "library_request_live_leak" in guard_violations
                    )
                    self.issues.append(
                        ReportIssue(
                            code=(
                                "viber_library_request_guarded_reply"
                                if guarded_library_leak
                                else "viber_live_guarded_reply"
                            ),
                            severity="care",
                            surface=surface,
                            title=(
                                "Viber guard caught library-request live leakage"
                                if guarded_library_leak
                                else "Viber guard corrected the raw live reply"
                            ),
                            detail=_bounded(",".join(guard_violations)),
                            repair=(
                                "Patch the silent_guard/library prompt so crate turns choose "
                                "grounded tool results or honest no-results text before the "
                                "result-boundary guard catches live leakage."
                                if guarded_library_leak
                                else (
                                    "Use the raw/corrected pair as a prompt patch: Viber should "
                                    "choose the evidence boundary itself instead of relying on "
                                    "result-boundary correction."
                                )
                            ),
                            response_id=_str_or_none(row.get("response_id")),
                            artifact=_artifact_for(row),
                            prompt=(
                                "Replay the original request with LIVE CONTEXT USE:silent_guard "
                                "and require the first model reply to avoid live/deck/move/"
                                "sound-change wording without guard_applied."
                                if guarded_library_leak
                                else (
                                    "Replay the saved prompt with the same live_context and require "
                                    "the first model reply to pass verify-live-reply without guard_applied."
                                )
                            ),
                        )
                    )
            prompt_issue = _viber_prompt_audio_contract_issue(row, surface=surface)
            if prompt_issue is not None:
                self.issues.append(prompt_issue)
            if _is_library_request(request) and _looks_like_live_leak(_message_text(row)):
                self.issues.append(
                    ReportIssue(
                        code="viber_library_request_live_leak",
                        severity="blocker",
                        surface=surface,
                        title="Viber answered a library request with live-move language",
                        detail=_bounded(_message_text(row)),
                        repair=(
                            "Reprompt this as a crate/library turn and require either grounded "
                            "tool results or an honest no-results reply; never fall back to live "
                            "move wording for silent_guard turns."
                        ),
                        response_id=_str_or_none(row.get("response_id")),
                        artifact=_artifact_for(row),
                        prompt=(
                            "Replay the original request with LIVE CONTEXT USE:silent_guard and "
                            "fail any answer that mentions live/deck/move/sound-change language."
                        ),
                    )
                )
            if isinstance(extra, dict) and extra.get("error"):
                self.issues.append(
                    ReportIssue(
                        code="viber_backend_error",
                        severity="care",
                        surface=surface,
                        title="Viber backend returned an error",
                        detail=_bounded(str(extra.get("error"))),
                        repair=(
                            "Make the error actionable in UI and add a fixture so this stop reason "
                            "does not look like an empty or successful Viber answer."
                        ),
                        response_id=_str_or_none(row.get("response_id")),
                        artifact=_artifact_for(row),
                    )
                )
            if row.get("stop_reason") == "tool_starvation":
                self.issues.append(
                    ReportIssue(
                        code="viber_tool_starvation",
                        severity="blocker",
                        surface=surface,
                        title="Viber stopped without enough grounded tool use",
                        detail=_bounded(_message_text(row)),
                        repair="Reprompt the agent to call grounded discovery tools before answering.",
                        response_id=_str_or_none(row.get("response_id")),
                        artifact=_artifact_for(row),
                    )
                )

    def _add_absence_issues(self, session_metrics: dict[str, Any], viber_metrics: dict[str, Any]) -> None:
        if session_metrics["ai_messages"] == 0:
            self.issues.append(
                ReportIssue(
                    code="no_session_ai_messages",
                    severity="watch",
                    surface="cohost",
                    title="No session ai_message rows found",
                    detail="The automation has no prompt/response artifacts to inspect.",
                    repair="Run a live session with AI observability enabled, then rerun this report.",
                )
            )
        if self.include_viber and viber_metrics["rows_inspected"] == 0:
            self.issues.append(
                ReportIssue(
                    code="no_viber_rows",
                    severity="watch",
                    surface="viber",
                    title="No recent Viber/Codex rows found",
                    detail="Global ai_messages did not contain Viber surfaces.",
                    repair="Run `vibemix library chat ... --json` or build-set, then rerun this report.",
                )
            )


def build_cohost_viber_report(
    session_dir: Path,
    *,
    global_root: Path | None = None,
    include_viber: bool = True,
    max_global_rows: int = 25,
    global_since_iso: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic cohost/Viber repair report for one session."""
    return _ReportBuilder(
        session_dir=Path(session_dir),
        global_root=Path(global_root) if global_root is not None else None,
        include_viber=include_viber,
        max_global_rows=max(1, int(max_global_rows)),
        global_since_iso=global_since_iso,
    ).build()


def latest_session(
    recordings_root: Path,
    *,
    require_ai_message: bool = True,
) -> Path | None:
    """Return the newest recording session, preferring one with ai_message rows."""
    try:
        dirs = sorted(
            (p for p in Path(recordings_root).iterdir() if p.is_dir()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return None
    if not require_ai_message:
        return dirs[0] if dirs else None
    for session_dir in dirs:
        rows = _read_jsonl(session_dir / "events.jsonl", [])
        if any(row.get("kind") == "ai_message" for row in rows):
            return session_dir
    return dirs[0] if dirs else None


def session_start_iso(session_dir: Path) -> str | None:
    """Best-effort ISO timestamp for anchoring per-session global Viber rows."""
    session_dir = Path(session_dir)
    rows = _read_jsonl(session_dir / "events.jsonl", [])
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("kind") == "session_start":
            for key in ("wall_clock_iso", "ts_iso"):
                parsed = _parse_iso_datetime(str(row.get(key) or ""))
                if parsed is not None:
                    return parsed.isoformat()
    for row in rows:
        if not isinstance(row, dict):
            continue
        parsed = _parse_iso_datetime(str(row.get("ts_iso") or ""))
        if parsed is not None:
            return parsed.isoformat()
    match = re.match(r"^(\d{8})-(\d{6})$", session_dir.name)
    if match:
        try:
            local_tz = datetime.now().astimezone().tzinfo or UTC
            parsed = datetime.strptime("".join(match.groups()), "%Y%m%d%H%M%S")
            return parsed.replace(tzinfo=local_tz).isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromtimestamp(session_dir.stat().st_mtime).astimezone().isoformat()
    except OSError:
        return None


def recent_sessions(
    recordings_root: Path,
    *,
    limit: int = 10,
    require_ai_message: bool = True,
) -> list[Path]:
    """Return newest recording session dirs, optionally requiring ai_message rows."""
    try:
        dirs = sorted(
            (p for p in Path(recordings_root).iterdir() if p.is_dir()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return []
    out: list[Path] = []
    for session_dir in dirs:
        if require_ai_message:
            rows = _read_jsonl(session_dir / "events.jsonl", [])
            if not any(row.get("kind") == "ai_message" for row in rows):
                continue
        out.append(session_dir)
        if len(out) >= max(1, int(limit)):
            break
    return out


def build_cohost_viber_history_sweep(
    recordings_root: Path,
    *,
    global_root: Path | None = None,
    max_sessions: int = 10,
    include_viber: bool = True,
    max_global_rows: int = 25,
    global_since_iso: str | None = None,
) -> dict[str, Any]:
    """Benchmark recent cohost sessions plus a single recent Viber window."""
    sessions = recent_sessions(recordings_root, limit=max_sessions)
    session_rows: list[dict[str, Any]] = []
    issue_code_counts: dict[str, int] = {}
    aggregate_counts = {"blocker": 0, "care": 0, "watch": 0}
    errors: list[str] = []
    for session_dir in sessions:
        report = build_cohost_viber_report(session_dir, include_viber=False)
        counts = _issue_counts(report.get("issues", []))
        for key, value in counts.items():
            aggregate_counts[key] += value
        for issue in report.get("issues", []):
            if isinstance(issue, dict):
                code = str(issue.get("code") or "unknown")
                issue_code_counts[code] = issue_code_counts.get(code, 0) + 1
        errors.extend(str(error) for error in report.get("errors", []) if error)
        metrics = report.get("metrics", {})
        session_metrics = metrics.get("session", {}) if isinstance(metrics, dict) else {}
        session_rows.append(
            {
                "session_dir": str(session_dir),
                "ok": bool(report.get("ok")),
                "issue_counts": counts,
                "ai_messages": int(session_metrics.get("ai_messages") or 0),
                "citation_zero_non_ack_emits": int(
                    session_metrics.get("citation_zero_non_ack_emits") or 0
                ),
                "citation_strips": int(session_metrics.get("citation_strips") or 0),
                "citation_bypasses": int(session_metrics.get("citation_bypasses") or 0),
                "live_claim_guard_corrections": int(
                    session_metrics.get("live_claim_guard_corrections") or 0
                ),
                "deck_audio_part_turns": int(session_metrics.get("deck_audio_part_turns") or 0),
                "no_deck_audio_part_turns": int(
                    session_metrics.get("no_deck_audio_part_turns") or 0
                ),
            }
        )

    viber_report: dict[str, Any] | None = None
    viber_issues: list[dict[str, Any]] = []
    viber_metrics: dict[str, Any] = {}
    if include_viber and global_root is not None and sessions:
        viber_report = build_cohost_viber_report(
            sessions[0],
            global_root=global_root,
            include_viber=True,
            max_global_rows=max_global_rows,
            global_since_iso=global_since_iso,
        )
        metrics = viber_report.get("metrics", {})
        viber_metrics = metrics.get("viber", {}) if isinstance(metrics, dict) else {}
        for issue in viber_report.get("issues", []):
            if not isinstance(issue, dict):
                continue
            surface = str(issue.get("surface") or "")
            code = str(issue.get("code") or "")
            if surface.startswith("viber") or code.startswith("viber_"):
                viber_issues.append(issue)
                severity = str(issue.get("severity") or "")
                if severity in aggregate_counts:
                    aggregate_counts[severity] += 1
                issue_code_counts[code or "unknown"] = issue_code_counts.get(code or "unknown", 0) + 1
        errors.extend(str(error) for error in viber_report.get("errors", []) if error)

    summary = {
        "schema": HISTORY_SWEEP_SCHEMA,
        "ok": aggregate_counts["blocker"] == 0 and not errors,
        "recordings_root": str(recordings_root),
        "session_dirs": [str(session_dir) for session_dir in sessions],
        "global_root": str(global_root) if global_root is not None else None,
        "global_since_iso": global_since_iso,
        "session_count": len(session_rows),
        "max_sessions": max(1, int(max_sessions)),
        "issue_counts": aggregate_counts,
        "issue_code_counts": dict(sorted(issue_code_counts.items())),
        "sessions": session_rows,
            "viber": {
                "included": bool(include_viber and global_root is not None),
                "rows_inspected": int(viber_metrics.get("rows_inspected") or 0),
                "live_verification_violations": int(
                    viber_metrics.get("live_verification_violations") or 0
                ),
                "guarded_reply_violations": int(
                    viber_metrics.get("guarded_reply_violations") or 0
                ),
                "guarded_replies": int(viber_metrics.get("guarded_replies") or 0),
                "errored_rows": int(viber_metrics.get("errored_rows") or 0),
            "issue_count": len(viber_issues),
            "issues": viber_issues,
        },
        "errors": errors,
    }
    return summary


def format_cohost_viber_history_markdown(sweep: dict[str, Any]) -> str:
    counts = sweep.get("issue_counts", {}) if isinstance(sweep.get("issue_counts"), dict) else {}
    viber = sweep.get("viber", {}) if isinstance(sweep.get("viber"), dict) else {}
    lines = [
        "# Cohost/Viber History Sweep",
        "",
        f"ok: `{bool(sweep.get('ok'))}`",
        f"sessions: `{sweep.get('session_count', 0)}`",
        (
            f"issues: blockers={counts.get('blocker', 0)} "
            f"care={counts.get('care', 0)} watch={counts.get('watch', 0)}"
        ),
        (
            f"viber: rows={viber.get('rows_inspected', 0)} "
            f"violations={viber.get('live_verification_violations', 0)} "
            f"issues={viber.get('issue_count', 0)}"
        ),
        "",
        "## Sessions",
        "",
    ]
    sessions = sweep.get("sessions")
    if isinstance(sessions, list) and sessions:
        for row in sessions:
            if not isinstance(row, dict):
                continue
            c = row.get("issue_counts", {}) if isinstance(row.get("issue_counts"), dict) else {}
            lines.append(
                f"- `{row.get('session_dir')}` ok={bool(row.get('ok'))} "
                f"blockers={c.get('blocker', 0)} care={c.get('care', 0)} watch={c.get('watch', 0)} "
                f"ai_messages={row.get('ai_messages', 0)}"
            )
    else:
        lines.append("No sessions found.")
    code_counts = sweep.get("issue_code_counts")
    if isinstance(code_counts, dict) and code_counts:
        lines.extend(["", "## Issue Codes", ""])
        for code, count in code_counts.items():
            lines.append(f"- `{code}`: {count}")
    errors = sweep.get("errors") or []
    if errors:
        lines.extend(["", "## Errors", ""])
        for error in errors:
            lines.append(f"- {error}")
    lines.append("")
    return "\n".join(lines)


def export_cohost_viber_failure_corpus(
    recordings_root: Path,
    out_dir: Path,
    *,
    global_root: Path | None = None,
    max_sessions: int = 10,
    include_viber: bool = True,
    max_global_rows: int = 25,
    severities: set[str] | None = None,
    include_policy_canaries: bool = True,
    session_dirs: list[Path] | None = None,
    global_since_iso: str | None = None,
) -> dict[str, Any]:
    """Export recent failures as a local regression corpus."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    wanted = set(severities or {"blocker", "care"})
    sessions = (
        [Path(session_dir) for session_dir in session_dirs]
        if session_dirs
        else recent_sessions(recordings_root, limit=max_sessions)
    )
    captured_fixtures: list[dict[str, Any]] = []
    errors: list[str] = []

    for session_dir in sessions:
        report = build_cohost_viber_report(session_dir, include_viber=False)
        errors.extend(str(error) for error in report.get("errors", []) if error)
        captured_fixtures.extend(
            _fixtures_from_issues(
                report.get("issues", []),
                source="cohost",
                session_dir=str(session_dir),
                wanted=wanted,
            )
        )

    if include_viber and global_root is not None and sessions:
        viber_report = build_cohost_viber_report(
            sessions[0],
            global_root=global_root,
            include_viber=True,
            max_global_rows=max_global_rows,
            global_since_iso=global_since_iso,
        )
        errors.extend(str(error) for error in viber_report.get("errors", []) if error)
        viber_issues = [
            issue
            for issue in viber_report.get("issues", [])
            if isinstance(issue, dict)
            and (
                str(issue.get("surface") or "").startswith("viber")
                or str(issue.get("code") or "").startswith("viber_")
            )
        ]
        captured_fixtures.extend(
            _fixtures_from_issues(
                viber_issues,
                source="viber",
                session_dir=str(sessions[0]),
                wanted=wanted,
            )
        )

    policy_canaries = _policy_canary_fixtures() if include_policy_canaries else []
    captured_fixtures = _dedupe_fixtures(captured_fixtures)
    fixtures = _dedupe_fixtures([*captured_fixtures, *policy_canaries])
    for fixture in fixtures:
        fixture_dir = out_dir / "cases" / str(fixture["fixture_id"])
        fixture_dir.mkdir(parents=True, exist_ok=True)
        (fixture_dir / "case.json").write_text(
            json.dumps(fixture, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    manifest_path = out_dir / "manifest.json"
    cases_path = out_dir / "cases.jsonl"
    fixtures_path = out_dir / "fixtures.jsonl"
    manifest = {
        "schema": FAILURE_CORPUS_SCHEMA,
        "ok": not errors,
        "release_ready": len(captured_fixtures) == 0 and not errors,
        "recordings_root": str(recordings_root),
        "session_dirs": [str(session_dir) for session_dir in sessions],
        "global_root": str(global_root) if global_root is not None else None,
        "global_since_iso": global_since_iso,
        "out_dir": str(out_dir),
        "manifest_path": str(manifest_path),
        "cases_path": str(cases_path),
        "fixtures_path": str(fixtures_path),
        "max_sessions": max(1, int(max_sessions)),
        "severities": sorted(wanted),
        "case_count": len(fixtures),
        "fixture_count": len(fixtures),
        "captured_case_count": len(captured_fixtures),
        "policy_canary_count": len(policy_canaries),
        "include_policy_canaries": bool(include_policy_canaries),
        "issue_code_counts": _fixture_code_counts(fixtures),
        "cases": fixtures,
        "fixtures": fixtures,
        "errors": errors,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    jsonl = "".join(json.dumps(fixture, ensure_ascii=False) + "\n" for fixture in fixtures)
    cases_path.write_text(jsonl, encoding="utf-8")
    fixtures_path.write_text(jsonl, encoding="utf-8")
    (out_dir / "README.md").write_text(_format_failure_corpus_markdown(manifest), encoding="utf-8")
    return manifest


def _policy_canary_fixtures() -> list[dict[str, Any]]:
    """Built-in red-team cases that should run even before a bad live capture exists."""
    audio_live_context = {
        "live_context_schema_version": 2,
        "live_context_capabilities": [
            "deck_state",
            "deck_source_status",
            "audio_part_context",
            "deck_audio_separation_context",
            "deck_audio_features_context",
            "deck_audio_delta_context",
            "deck_audio_window_context",
            "audio_window_map",
            "audio_delta",
            "live_evidence",
        ],
        "deck": "A",
        "audible": True,
        "deck_state": {"A": {"title": "Left", "confidence": 0.9}},
        "recent_moves": ["A_low: flat->killed"],
        "audio_delta": ["low energy fell 50% (strong)"],
    }
    canaries = [
        {
            "case_id": "policy_audio_vibe_not_control_causality",
            "fixture_id": "policy_audio_vibe_not_control_causality",
            "source": "policy_canary",
            "session_dir": None,
            "issue": {
                "code": "audio_vibe_control_causality",
                "severity": "blocker",
                "surface": "viber_chat",
                "title": "Audio vibe was promoted into EQ causality",
                "detail": "That EQ move made the vocal open up and the kick got tighter.",
                "repair": (
                    "Use audio for listener texture/energy only; do not claim a control "
                    "caused, fixed, cleaned, opened, or tightened the sound."
                ),
                "response_id": "policy-audio-vibe-causality",
                "prompt": (
                    "Candidate may say the low end got hollow, or stay silent; it must "
                    "not credit or blame the EQ from audio alone."
                ),
            },
            "artifact_dir": None,
            "paths": {},
            "request": "did that low cut fix it?",
            "original_response_preview": (
                "That EQ move made the vocal open up and the kick got tighter."
            ),
            "live_context": audio_live_context,
            "move_grades": [],
            "repair_gates": [
                "audio may describe texture, energy, motion, density, and mood",
                "audio must not prove EQ/fader/filter/cue causality",
                "candidate must pass the Viber live-claim verifier",
                "uncertain spoken cohost output should be silence or a pure listener read",
            ],
        },
        {
            "case_id": "policy_audio_vibe_listener_read_allowed",
            "fixture_id": "policy_audio_vibe_listener_read_allowed",
            "source": "policy_canary",
            "session_dir": None,
            "issue": {
                "code": "audio_vibe_listener_read_allowed",
                "severity": "care",
                "surface": "viber_chat",
                "title": "Safe audio listener read was muted",
                "detail": "The low end got hollow for a moment.",
                "repair": (
                    "Keep audio useful as a broad listener/vibe signal. Do not overcorrect "
                    "safe texture, energy, density, motion, or mood reads into silence."
                ),
                "response_id": "policy-audio-vibe-listener-read",
                "prompt": (
                    "Candidate should give a short listener read from audio, while avoiding "
                    "control causality and hidden source/stem detail."
                ),
            },
            "artifact_dir": None,
            "paths": {},
            "request": "what did the room hear after that move?",
            "original_response_preview": "The low end got hollow for a moment.",
            "live_context": audio_live_context,
            "move_grades": [],
            "repair_gates": [
                "audio should remain usable for broad listener/vibe reads",
                "candidate should not be silent when the safe listener-read lane is available",
                "audio must not prove EQ/fader/filter/cue causality",
                "audio must not infer vocals, kicks, stems, or source-level song parts",
                "candidate must pass the Viber live-claim verifier",
            ],
        },
        {
            "case_id": "policy_library_request_no_live_leak",
            "fixture_id": "policy_library_request_no_live_leak",
            "source": "policy_canary",
            "session_dir": None,
            "issue": {
                "code": "viber_library_request_live_leak",
                "severity": "blocker",
                "surface": "viber_chat",
                "title": "Library request leaked live-move language",
                "detail": "I caught the live move. The useful note is the sound change right there.",
                "repair": (
                    "Library/crate requests need grounded tool results or an honest "
                    "no-results reply, never live/deck/move/sound-change fallback text."
                ),
                "response_id": "policy-library-live-leak",
            },
            "artifact_dir": None,
            "paths": {},
            "request": "find me dark rolling hypnotic techno",
            "original_response_preview": (
                "I caught the live move. The useful note is the sound change right there."
            ),
            "repair_gates": _repair_gates_for_issue(
                {"code": "viber_library_request_live_leak"},
                "find me dark rolling hypnotic techno",
            ),
        },
        {
            "case_id": "policy_audio_vibe_not_hidden_source_detail",
            "fixture_id": "policy_audio_vibe_not_hidden_source_detail",
            "source": "policy_canary",
            "session_dir": None,
            "issue": {
                "code": "audio_vibe_hidden_source_detail",
                "severity": "blocker",
                "surface": "viber_chat",
                "title": "Audio vibe was promoted into hidden song-part detail",
                "detail": "The vocal opened up and the kick got tighter.",
                "repair": (
                    "Use audio for broad listener texture/energy only; do not infer "
                    "vocals, kicks, stems, or source-level song parts from a broad live delta."
                ),
                "response_id": "policy-audio-vibe-hidden-source",
                "prompt": (
                    "Candidate may say the low end got hollow, or stay silent; it must "
                    "not invent vocals, kicks, stems, or source-level detail."
                ),
            },
            "artifact_dir": None,
            "paths": {},
            "request": "did that low cut fix it?",
            "original_response_preview": "The vocal opened up and the kick got tighter.",
            "live_context": audio_live_context,
            "move_grades": [],
            "repair_gates": _repair_gates_for_issue(
                {"code": "audio_vibe_hidden_source_detail"},
                "did that low cut fix it?",
            ),
        },
        {
            "case_id": "policy_cohost_audio_source_detail_silence",
            "fixture_id": "policy_cohost_audio_source_detail_silence",
            "source": "policy_canary",
            "session_dir": None,
            "issue": {
                "code": "cohost_audio_source_detail_emit",
                "severity": "blocker",
                "surface": "cohost",
                "title": "Spoken cohost promoted broad audio into hidden source detail",
                "detail": "The vocal opened up and the kick got tighter.",
                "repair": (
                    "The spoken cohost path must use broad listener texture or stay silent "
                    "unless a grounded detector supports vocals, kicks, stems, or source-level parts."
                ),
                "response_id": "policy-cohost-audio-source-detail",
                "prompt": (
                    "Candidate may say the low end got hollow, or stay silent; it must not "
                    "invent source-level song-part detail in TTS."
                ),
            },
            "artifact_dir": None,
            "paths": {},
            "request": "live cohost automatic reaction",
            "original_response_preview": "The vocal opened up and the kick got tighter.",
            "repair_gates": _repair_gates_for_issue(
                {"code": "cohost_audio_source_detail_emit"},
                "live cohost automatic reaction",
            ),
        },
        {
            "case_id": "policy_cohost_uncertain_ack_loop_silence",
            "fixture_id": "policy_cohost_uncertain_ack_loop_silence",
            "source": "policy_canary",
            "session_dir": None,
            "issue": {
                "code": "citation_zero_ack_loop",
                "severity": "blocker",
                "surface": "cohost",
                "title": "Spoken cohost repeated uncertain ack-only TTS",
                "detail": "I'm listening. I'm listening. I'm listening.",
                "repair": (
                    "When the cohost lacks evidence, repeated ack-only TTS should become "
                    "silence instead of a confident-sounding voice line."
                ),
                "response_id": "policy-cohost-uncertain-ack-loop",
                "prompt": (
                    "Candidate must be silent; do not fill uncertainty with a determined "
                    "ack, correction, or fallback line."
                ),
            },
            "artifact_dir": None,
            "paths": {},
            "request": "live cohost uncertain idle run",
            "original_response_preview": "I'm listening. I'm listening. I'm listening.",
            "repair_gates": _repair_gates_for_issue(
                {"code": "citation_zero_ack_loop"},
                "live cohost uncertain idle run",
            ),
        },
    ]
    return canaries


def _fixtures_from_issues(
    issues: Any,
    *,
    source: str,
    session_dir: str,
    wanted: set[str],
) -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    if not isinstance(issues, list):
        return fixtures
    for index, issue in enumerate(issues, start=1):
        if not isinstance(issue, dict):
            continue
        severity = str(issue.get("severity") or "")
        if severity not in wanted:
            continue
        artifact_dir, paths = _issue_artifact_paths(issue)
        meta = _read_json_file(paths["meta_path"]) if paths.get("meta_path") else {}
        response = _read_text_optional(paths.get("response_path")) or str(meta.get("message") or "")
        extra = meta.get("extra")
        request = str(extra.get("request") or "") if isinstance(extra, dict) else ""
        fixture_id = _safe_slug(
            "_".join(
                str(part)
                for part in (
                    source,
                    issue.get("code") or "issue",
                    issue.get("response_id") or index,
                )
            ),
            limit=140,
        )
        fixture = {
            "case_id": fixture_id,
            "fixture_id": fixture_id,
            "source": source,
            "session_dir": session_dir,
            "issue": issue,
            "artifact_dir": str(artifact_dir) if artifact_dir is not None else None,
            "paths": {key: str(value) for key, value in paths.items() if value is not None},
            "request": request,
            "original_response_preview": _bounded(response, limit=500),
            "repair_gates": _repair_gates_for_issue(issue, request),
        }
        fixtures.append(fixture)
    return fixtures


def _dedupe_fixtures(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for fixture in fixtures:
        issue = fixture.get("issue", {}) if isinstance(fixture.get("issue"), dict) else {}
        key = (
            str(fixture.get("source") or ""),
            str(issue.get("code") or ""),
            str(issue.get("response_id") or ""),
            str(fixture.get("session_dir") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(fixture)
    return out


def _fixture_code_counts(fixtures: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for fixture in fixtures:
        issue = fixture.get("issue", {}) if isinstance(fixture.get("issue"), dict) else {}
        code = str(issue.get("code") or "unknown")
        counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items()))


def _format_failure_corpus_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Cohost/Viber Failure Corpus",
        "",
        f"release_ready: `{bool(manifest.get('release_ready'))}`",
        f"cases: `{manifest.get('case_count', manifest.get('fixture_count', 0))}`",
        f"captured_cases: `{manifest.get('captured_case_count', 0)}`",
        f"policy_canaries: `{manifest.get('policy_canary_count', 0)}`",
        "",
        "## Issue Codes",
        "",
    ]
    code_counts = manifest.get("issue_code_counts")
    if isinstance(code_counts, dict) and code_counts:
        for code, count in code_counts.items():
            lines.append(f"- `{code}`: {count}")
    else:
        lines.append("No failure fixtures exported.")
    lines.extend(["", "## Cases", ""])
    fixtures = manifest.get("cases") if isinstance(manifest.get("cases"), list) else manifest.get("fixtures")
    if isinstance(fixtures, list) and fixtures:
        for fixture in fixtures:
            issue = fixture.get("issue", {}) if isinstance(fixture, dict) else {}
            lines.append(
                f"- `{fixture.get('case_id') or fixture.get('fixture_id')}` [{issue.get('severity')}] "
                f"{issue.get('surface')}: {issue.get('title')}"
            )
    else:
        lines.append("No cases.")
    lines.append("")
    return "\n".join(lines)


def run_failure_corpus_benchmark(
    corpus_dir: Path,
    out_dir: Path | None = None,
    *,
    backend: str = "deterministic",
    repairer: Repairer | None = None,
) -> dict[str, Any]:
    """Run repair candidates across a saved failure corpus."""
    corpus_dir = Path(corpus_dir)
    backend = str(backend or "deterministic").strip() or "deterministic"
    manifest = _read_json_file(corpus_dir / "manifest.json")
    cases = _read_failure_corpus_cases(corpus_dir, manifest)
    bench_dir = Path(out_dir) if out_dir is not None else corpus_dir / "benchmark-runs" / backend
    bench_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for raw_case in cases:
        if not isinstance(raw_case, dict):
            continue
        results.append(
            _run_corpus_benchmark_case(
                raw_case,
                bench_dir,
                backend=backend,
                repairer=repairer,
            )
        )

    score_mode_counts: dict[str, int] = {}
    for result in results:
        mode = str(result.get("score_mode") or "unknown")
        score_mode_counts[mode] = score_mode_counts.get(mode, 0) + 1
    passed = sum(1 for item in results if item.get("ok") is True)
    failed = sum(1 for item in results if item.get("ok") is False)
    skipped = sum(1 for item in results if item.get("status") == "skipped")
    summary = {
        "schema": CORPUS_BENCHMARK_SCHEMA,
        "backend": backend,
        "corpus_dir": str(corpus_dir),
        "out_dir": str(bench_dir),
        "source_schema": manifest.get("schema"),
        "source_release_ready": bool(manifest.get("release_ready")),
        "release_gate_ok": bool(manifest.get("release_ready")) and failed == 0 and skipped == 0,
        "case_count": len(cases),
        "candidate_count": sum(1 for item in results if item.get("candidate_path")),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "score_mode_counts": dict(sorted(score_mode_counts.items())),
        "issue_code_counts": _corpus_issue_code_counts(cases),
        "ok": len(results) == len(cases) and failed == 0 and skipped == 0,
        "results": results,
    }
    (bench_dir / "benchmark_manifest.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (bench_dir / "README.md").write_text(_format_corpus_benchmark_markdown(summary), encoding="utf-8")
    return summary


def _read_failure_corpus_cases(corpus_dir: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    cases_path = corpus_dir / "cases.jsonl"
    cases: list[dict[str, Any]] = []
    if cases_path.exists():
        for row in _read_jsonl(cases_path, []):
            if isinstance(row, dict):
                cases.append(row)
        return cases
    raw_cases = manifest.get("cases") if isinstance(manifest.get("cases"), list) else manifest.get("fixtures")
    if isinstance(raw_cases, list):
        return [case for case in raw_cases if isinstance(case, dict)]
    return cases


def _run_corpus_benchmark_case(
    case: dict[str, Any],
    bench_dir: Path,
    *,
    backend: str,
    repairer: Repairer | None,
) -> dict[str, Any]:
    case_id = _safe_slug(str(case.get("case_id") or case.get("fixture_id") or "case"))
    case_dir = bench_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    job = _corpus_case_as_repair_job(case)
    try:
        candidate = (
            _deterministic_candidate_for_job(job)
            if backend == "deterministic"
            else _backend_candidate_for_job(job, backend=backend, repairer=repairer)
        )
        repair_error = None
    except Exception as exc:
        candidate = _error_candidate(str(exc))
        repair_error = f"{type(exc).__name__}: {exc}"

    candidate_path = case_dir / "candidate.json"
    candidate_path.write_text(
        json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    paths = job.get("paths") if isinstance(job.get("paths"), dict) else {}
    meta_path_raw = paths.get("meta_path")
    issue = case.get("issue") if isinstance(case.get("issue"), dict) else {}
    issue_code = str(issue.get("code") or "")
    if (
        issue_code != "viber_prompt_missing_audio_contract"
        and isinstance(meta_path_raw, str)
        and meta_path_raw
        and _is_viber_corpus_case(case)
    ):
        score = score_reprompt_candidate(Path(meta_path_raw), candidate_path)
        score_mode = "viber_meta"
    else:
        score = _score_corpus_candidate(case, candidate_path)
        score_mode = "corpus_gate"
    score_path = case_dir / "score.json"
    score_path.write_text(json.dumps(score, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "case_id": case_id,
        "issue_code": str(issue.get("code") or "unknown"),
        "severity": str(issue.get("severity") or ""),
        "surface": str(issue.get("surface") or ""),
        "status": "scored",
        "ok": bool(score.get("ok")),
        "score_mode": score_mode,
        "candidate_path": str(candidate_path),
        "score_path": str(score_path),
        "violations": list(score.get("violations") or []),
        **({"repair_error": repair_error} if repair_error else {}),
    }


def _is_viber_corpus_case(case: dict[str, Any]) -> bool:
    issue = case.get("issue") if isinstance(case.get("issue"), dict) else {}
    return (
        str(case.get("source") or "").startswith("viber")
        or str(issue.get("surface") or "").startswith("viber")
        or str(issue.get("code") or "").startswith("viber_")
    )


def _corpus_case_as_repair_job(case: dict[str, Any]) -> dict[str, Any]:
    issue = case.get("issue") if isinstance(case.get("issue"), dict) else {}
    paths = case.get("paths") if isinstance(case.get("paths"), dict) else {}
    return {
        "job_id": str(case.get("case_id") or case.get("fixture_id") or "case"),
        "issue": issue,
        "artifact_dir": case.get("artifact_dir"),
        "paths": {str(key): str(value) for key, value in paths.items() if value},
        "request": str(case.get("request") or ""),
        "original_response_preview": str(case.get("original_response_preview") or ""),
        "gates": list(case.get("repair_gates") or []),
        "status": "ready",
    }


def _score_corpus_candidate(case: dict[str, Any], candidate_path: Path) -> dict[str, Any]:
    payload = _candidate_payload(Path(candidate_path).read_text(encoding="utf-8"))
    reply = str(payload.get("reply") or "").strip()
    issue = case.get("issue") if isinstance(case.get("issue"), dict) else {}
    code = str(issue.get("code") or "")
    request = str(case.get("request") or "")
    violations: list[str] = []
    live_context = case.get("live_context") if isinstance(case.get("live_context"), dict) else None
    move_grades = [
        item for item in case.get("move_grades", []) if isinstance(item, dict)
    ] if isinstance(case.get("move_grades"), list) else []
    live_verification: dict[str, Any] | None = None
    if payload.get("error"):
        violations.append("repair_error")
    if code in _CITATION_SILENT_REPAIR_CODES and reply:
        violations.append("citation_issue_should_be_silent")
    if code == "live_claim_guard_spoken_fallback" and reply:
        violations.append("guard_fallback_should_be_silent")
    if code in {"live_claim_guard", "viber_live_verification"} and _looks_like_outcome_claim(reply):
        violations.append("unsupported_live_outcome_claim")
    if code == "audio_vibe_control_causality" and _looks_like_audio_causality(reply):
        violations.append("audio_vibe_control_causality")
    if code in {
        "audio_vibe_hidden_source_detail",
        "cohost_audio_source_detail_emit",
    } and _looks_like_audio_source_detail(reply):
        violations.append("unsupported_audio_source_detail_claim")
    if code == "audio_vibe_listener_read_allowed":
        if not reply:
            violations.append("audio_listener_read_should_not_be_silent")
        elif not _looks_like_audio_listener_read(reply):
            violations.append("missing_audio_listener_read")
    if code == "viber_prompt_missing_audio_contract" and not _has_live_audio_prompt_patch(
        payload
    ):
        violations.append("missing_prompt_audio_contract_patch")
    if live_context is not None and reply:
        live_verification = _verify_viber_reply(reply, live_context, move_grades)
        violations.extend(str(item) for item in live_verification.get("violations", []) if item)
    if _is_library_request(request):
        if _looks_like_live_leak(reply):
            violations.append("library_request_live_leak")
        has_grounded_result = bool(
            payload.get("tools_used")
            or payload.get("tool_trace")
            or payload.get("track_ids")
            or payload.get("seen_track_ids")
            or payload.get("playlist")
        )
        if not has_grounded_result and not _looks_like_honest_empty_library_reply(reply):
            violations.append("library_request_without_grounded_result")
    return {
        "schema": CANDIDATE_SCORE_SCHEMA,
        "ok": not violations,
        "candidate_path": str(candidate_path),
        "request": request,
        "reply": _bounded(reply, limit=500),
        "violations": violations,
        "live_verification": live_verification,
        "grounding": {
            "tools_used": [str(item) for item in payload.get("tools_used", []) if isinstance(item, str)],
            "tool_trace_count": len(payload.get("tool_trace", [])) if isinstance(payload.get("tool_trace"), list) else 0,
            "track_ids": [
                str(item)
                for item in (payload.get("track_ids") or payload.get("seen_track_ids") or [])
                if isinstance(item, str)
            ],
            "playlist": payload.get("playlist") if isinstance(payload.get("playlist"), dict) else None,
        },
    }


def _corpus_issue_code_counts(cases: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        issue = case.get("issue") if isinstance(case.get("issue"), dict) else {}
        code = str(issue.get("code") or "unknown")
        counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items()))


def _format_corpus_benchmark_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Cohost/Viber Corpus Benchmark",
        "",
        f"backend: `{summary.get('backend')}`",
        f"ok: `{bool(summary.get('ok'))}`",
        f"release_gate_ok: `{bool(summary.get('release_gate_ok'))}`",
        (
            f"cases={summary.get('case_count', 0)} candidates={summary.get('candidate_count', 0)} "
            f"passed={summary.get('passed', 0)} failed={summary.get('failed', 0)} "
            f"skipped={summary.get('skipped', 0)}"
        ),
        "",
        "## Issue Codes",
        "",
    ]
    code_counts = summary.get("issue_code_counts")
    if isinstance(code_counts, dict) and code_counts:
        for code, count in code_counts.items():
            lines.append(f"- `{code}`: {count}")
    else:
        lines.append("No cases.")
    lines.extend(["", "## Results", ""])
    results = summary.get("results")
    if isinstance(results, list) and results:
        for result in results:
            status = "pass" if result.get("ok") else "fail"
            violations = ",".join(str(v) for v in result.get("violations", []) if v)
            lines.append(
                f"- `{result.get('case_id')}` {status} "
                f"{result.get('score_mode')}"
                + (f" ({violations})" if violations else "")
            )
    else:
        lines.append("No benchmark results.")
    lines.append("")
    return "\n".join(lines)


def format_cohost_viber_markdown(report: dict[str, Any]) -> str:
    """Render the report as a compact Markdown repair queue."""
    metrics = report.get("metrics", {})
    session = metrics.get("session", {}) if isinstance(metrics, dict) else {}
    viber = metrics.get("viber", {}) if isinstance(metrics, dict) else {}
    audio_debt = metrics.get("audio_evidence_debt", {}) if isinstance(metrics, dict) else {}
    issues = report.get("issues", [])
    queue = report.get("automation_queue", [])
    lines = [
        "# Cohost/Viber Automation Report",
        "",
        f"session: `{report.get('session_dir', '')}`",
        f"ok: `{bool(report.get('ok'))}`",
        "",
        "## Metrics",
        "",
        (
            f"- cohost: ai_messages={session.get('ai_messages', 0)} "
            f"heard={session.get('heard_ai_text', 0)} "
            f"zero_citation_emits={session.get('citation_zero_emits', 0)} "
            f"strips={session.get('citation_strips', 0)} "
            f"bypasses={session.get('citation_bypasses', 0)} "
            f"live_claim_guards={session.get('live_claim_guard_corrections', 0)}"
        ),
        (
            f"- viber: rows={viber.get('rows_inspected', 0)} "
            f"violations={viber.get('live_verification_violations', 0)} "
            f"guarded={viber.get('guarded_reply_violations', 0)} "
            f"errors={viber.get('errored_rows', 0)}"
        ),
        f"- audio evidence debt: {int(audio_debt.get('total') or 0)}",
        "",
        "## Automation Queue",
        "",
    ]
    if queue:
        for idx, item in enumerate(queue, start=1):
            lines.append(
                f"{idx}. [{item.get('severity')}] {item.get('surface')}: "
                f"{item.get('title')} ({item.get('code')})"
            )
            lines.append(f"   repair: {item.get('repair')}")
    else:
        lines.append("No repair items found.")
    lines.extend(["", "## Issues", ""])
    if issues:
        for issue in issues:
            lines.append(
                f"- [{issue.get('severity')}] `{issue.get('code')}` "
                f"{issue.get('title')}: {issue.get('detail')}"
            )
    else:
        lines.append("No issues found.")
    errors = report.get("errors") or []
    if errors:
        lines.extend(["", "## Errors", ""])
        for error in errors:
            lines.append(f"- {error}")
    lines.append("")
    return "\n".join(lines)


def write_reprompt_pack(report: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    """Write a deterministic reprompt/evaluation pack for report failures."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    issues = [
        issue
        for issue in report.get("issues", [])
        if isinstance(issue, dict) and issue.get("severity") in {"blocker", "care"}
    ]
    jobs: list[dict[str, Any]] = []
    for index, issue in enumerate(issues, start=1):
        job = _build_reprompt_job(index, issue)
        jobs.append(job)
        _write_reprompt_job(out_dir, job)

    manifest = {
        "schema": REPROMPT_PACK_SCHEMA,
        "ok": bool(report.get("ok")) and not jobs,
        "report_schema": report.get("schema"),
        "session_dir": report.get("session_dir"),
        "global_root": report.get("global_root"),
        "out_dir": str(out_dir),
        "job_count": len(jobs),
        "jobs": jobs,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "README.md").write_text(_format_reprompt_pack_markdown(manifest), encoding="utf-8")
    return manifest


def score_reprompt_candidate(
    meta_path: Path,
    candidate_path: Path,
    *,
    issue_code: str | None = None,
) -> dict[str, Any]:
    """Score one repaired reply against the captured Viber live/library gates."""
    meta = _read_json_file(Path(meta_path))
    candidate_text = Path(candidate_path).read_text(encoding="utf-8")
    payload = _candidate_payload(candidate_text)
    reply = str(payload.get("reply") or "").strip()
    code = str(issue_code or "").strip()
    tools_used = [str(item) for item in payload.get("tools_used", []) if isinstance(item, str)]
    tool_trace = [item for item in payload.get("tool_trace", []) if isinstance(item, dict)]
    raw_track_ids = payload.get("track_ids")
    if not isinstance(raw_track_ids, list):
        raw_track_ids = payload.get("seen_track_ids")
    track_ids = [str(item) for item in (raw_track_ids or []) if isinstance(item, str)]
    move_grades = [item for item in payload.get("move_grades", []) if isinstance(item, dict)]
    playlist = payload.get("playlist") if isinstance(payload.get("playlist"), dict) else None

    live_context = meta.get("moves") if isinstance(meta.get("moves"), dict) else None
    live_verification = (
        _silent_candidate_live_verification(move_grades)
        if not reply and code in _SILENT_COHOST_REPAIR_CODES
        else _verify_viber_reply(reply, live_context, move_grades)
    )
    extra = meta.get("extra")
    request = str(extra.get("request") or "") if isinstance(extra, dict) else ""
    violations: list[str] = []
    if not reply and code not in _SILENT_COHOST_REPAIR_CODES:
        violations.append("empty_reply")
    if code in _CITATION_SILENT_REPAIR_CODES and reply:
        violations.append("citation_issue_should_be_silent")
    if code == "live_claim_guard_spoken_fallback" and reply:
        violations.append("guard_fallback_should_be_silent")
    for violation in live_verification.get("violations", []):
        violations.append(str(violation))
    if code == "viber_prompt_missing_audio_contract" and not _has_live_audio_prompt_patch(
        payload
    ):
        violations.append("missing_prompt_audio_contract_patch")
    if _is_library_request(request):
        if _looks_like_live_leak(reply):
            violations.append("library_request_live_leak")
        has_grounded_result = bool(tools_used or tool_trace or track_ids or playlist)
        if not has_grounded_result and not _looks_like_honest_empty_library_reply(reply):
            violations.append("library_request_without_grounded_result")
    return {
        "schema": CANDIDATE_SCORE_SCHEMA,
        "ok": not violations,
        "meta_path": str(meta_path),
        "candidate_path": str(candidate_path),
        **({"issue_code": code} if code else {}),
        "request": request,
        "reply": _bounded(reply, limit=500),
        "violations": violations,
        "live_verification": live_verification,
        "grounding": {
            "tools_used": tools_used,
            "tool_trace_count": len(tool_trace),
            "track_ids": track_ids,
            "playlist": playlist,
        },
    }


def run_cohost_viber_autopilot(
    session_dir: Path,
    out_dir: Path,
    *,
    global_root: Path | None = None,
    include_viber: bool = True,
    max_global_rows: int = 25,
    global_since_iso: str | None = None,
    repair_backend: str = "deterministic",
    repairer: Repairer | None = None,
    gate_policy: str = "automation",
) -> dict[str, Any]:
    """Run report -> reprompt-pack -> repair-pack and write one summary."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = build_cohost_viber_report(
        Path(session_dir),
        global_root=Path(global_root) if global_root is not None else None,
        include_viber=include_viber,
        max_global_rows=max_global_rows,
        global_since_iso=global_since_iso,
    )
    report_path = out_dir / "report.json"
    report_md_path = out_dir / "report.md"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_md_path.write_text(format_cohost_viber_markdown(report), encoding="utf-8")

    pack = write_reprompt_pack(report, out_dir / "reprompt-pack")
    repair: dict[str, Any] | None = None
    if int(pack.get("job_count") or 0) > 0:
        repair = run_reprompt_pack_repair(
            Path(pack["out_dir"]),
            out_dir / "repair-run",
            backend=repair_backend,
            repairer=repairer,
        )

    issue_counts = _issue_counts(report.get("issues", []))
    audio_debt = _audio_evidence_debt(report.get("issues", []))
    release_gate_ok = bool(report.get("ok"))
    repair_ok = None if repair is None else bool(repair.get("ok"))
    automation_ok = release_gate_ok or bool(repair_ok)
    has_care = int(issue_counts.get("care") or 0) > 0
    first_pass_clean = (
        release_gate_ok
        and int(issue_counts.get("blocker") or 0) == 0
        and int(issue_counts.get("care") or 0) == 0
    )
    reprompt_debt = int(issue_counts.get("blocker") or 0) + int(issue_counts.get("care") or 0)
    status = (
        "clean_with_care"
        if release_gate_ok and has_care
        else "clean"
        if release_gate_ok
        else "repaired_candidate_ready"
        if repair_ok
        else "needs_human"
    )
    gate_policy = str(gate_policy or "automation").strip() or "automation"
    if gate_policy in {"audio_evidence", "audio_debt", "audio-debt"}:
        gate_policy = "audio-evidence"
    if gate_policy == "release":
        gate_ok = release_gate_ok
    elif gate_policy in {"first-pass", "first_pass", "firstpass"}:
        gate_ok = first_pass_clean
    elif gate_policy == "audio-evidence":
        gate_ok = int(audio_debt.get("total") or 0) == 0
    else:
        gate_ok = automation_ok
    summary = {
        "schema": AUTOPILOT_SCHEMA,
        "ok": automation_ok,
        "gate_ok": gate_ok,
        "gate_policy": gate_policy,
        "status": status,
        "release_gate_ok": release_gate_ok,
        "initial_ok": release_gate_ok,
        "first_pass_clean": first_pass_clean,
        "reprompt_debt": reprompt_debt,
        "audio_evidence_debt": int(audio_debt.get("total") or 0),
        "audio_evidence_debt_by_code": audio_debt.get("issue_code_counts") or {},
        "repair_ok": repair_ok,
        "repair_backend": repair_backend,
        "session_dir": str(session_dir),
        "global_root": str(global_root) if global_root is not None else None,
        "global_since_iso": global_since_iso,
        "out_dir": str(out_dir),
        "artifacts": {
            "report_json": str(report_path),
            "report_md": str(report_md_path),
            "reprompt_pack": str(pack.get("out_dir")),
            "repair_run": str(repair.get("out_dir")) if repair else None,
        },
        "initial_issue_counts": issue_counts,
        "reprompt_jobs": int(pack.get("job_count") or 0),
        "repair": (
            {
                "job_count": int(repair.get("job_count") or 0),
                "candidate_count": int(repair.get("candidate_count") or 0),
                "passed": int(repair.get("passed") or 0),
                "failed": int(repair.get("failed") or 0),
                "skipped": int(repair.get("skipped") or 0),
            }
            if repair
            else None
        ),
    }
    summary_path = out_dir / "autopilot_summary.json"
    summary_md_path = out_dir / "README.md"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary_md_path.write_text(_format_autopilot_markdown(summary), encoding="utf-8")
    return summary


def run_reprompt_pack_repair(
    pack_dir: Path,
    out_dir: Path | None = None,
    *,
    backend: str = "deterministic",
    repairer: Repairer | None = None,
) -> dict[str, Any]:
    """Run repair candidates for a reprompt pack.

    ``backend=deterministic`` is the no-model, no-network floor. Other backends
    provide an injectable repairer so tests can exercise the rerun loop without
    spawning the real Viber/Codex process.
    """
    pack_dir = Path(pack_dir)
    backend = str(backend or "deterministic").strip() or "deterministic"
    manifest = _read_json_file(pack_dir / "manifest.json")
    jobs = manifest.get("jobs")
    if not isinstance(jobs, list):
        jobs = []
    repair_dir = Path(out_dir) if out_dir is not None else pack_dir / "repair-run"
    repair_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for raw_job in jobs:
        if not isinstance(raw_job, dict):
            continue
        result = _run_repair_job(raw_job, repair_dir, backend=backend, repairer=repairer)
        results.append(result)

    summary = {
        "schema": AUTO_REPAIR_SCHEMA,
        "backend": backend,
        "pack_dir": str(pack_dir),
        "out_dir": str(repair_dir),
        "job_count": len(jobs),
        "candidate_count": sum(1 for item in results if item.get("candidate_path")),
        "passed": sum(1 for item in results if item.get("ok") is True),
        "failed": sum(1 for item in results if item.get("ok") is False),
        "skipped": sum(1 for item in results if item.get("status") == "skipped"),
        "ok": not jobs or (len(results) == len(jobs) and all(item.get("ok") is True for item in results)),
        "results": results,
    }
    (repair_dir / "repair_manifest.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (repair_dir / "README.md").write_text(_format_repair_markdown(summary), encoding="utf-8")
    return summary


def _issue_counts(issues: Any) -> dict[str, int]:
    counts = {"blocker": 0, "care": 0, "watch": 0}
    if not isinstance(issues, list):
        return counts
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        severity = str(issue.get("severity") or "")
        if severity in counts:
            counts[severity] += 1
    return counts


def _audio_evidence_debt(issues: Any) -> dict[str, Any]:
    """Count first-pass live/audio evidence-boundary debt.

    Excludes safe listener-read and no-audio-part watch items. This answers:
    did audio/live context make the model say something confident that needed
    a guard, repair, or verifier rejection?
    """
    out: dict[str, Any] = {
        "total": 0,
        "blocker": 0,
        "care": 0,
        "issue_code_counts": {},
    }
    if not isinstance(issues, list):
        return out
    code_counts: dict[str, int] = {}
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        code = str(issue.get("code") or "")
        severity = str(issue.get("severity") or "")
        if code not in _AUDIO_EVIDENCE_DEBT_CODES or severity not in {"blocker", "care"}:
            continue
        out["total"] += 1
        out[severity] += 1
        code_counts[code] = code_counts.get(code, 0) + 1
    out["issue_code_counts"] = dict(sorted(code_counts.items()))
    return out


def _format_autopilot_markdown(summary: dict[str, Any]) -> str:
    counts = summary.get("initial_issue_counts", {})
    repair = summary.get("repair") if isinstance(summary.get("repair"), dict) else {}
    lines = [
        "# Cohost/Viber Autopilot",
        "",
        f"status: `{summary.get('status')}`",
        f"ok: `{bool(summary.get('ok'))}`",
        f"gate_ok: `{bool(summary.get('gate_ok'))}`",
        f"gate_policy: `{summary.get('gate_policy')}`",
        f"release_gate_ok: `{bool(summary.get('release_gate_ok'))}`",
        f"first_pass_clean: `{bool(summary.get('first_pass_clean'))}`",
        f"reprompt_debt: `{int(summary.get('reprompt_debt') or 0)}`",
        f"repair_backend: `{summary.get('repair_backend')}`",
        "",
        "## Counts",
        "",
        (
            f"- initial issues: blockers={counts.get('blocker', 0)} "
            f"care={counts.get('care', 0)} watch={counts.get('watch', 0)}"
        ),
        f"- audio evidence debt: {int(summary.get('audio_evidence_debt') or 0)}",
        (
            f"- repairs: jobs={summary.get('reprompt_jobs', 0)} "
            f"passed={repair.get('passed', 0)} failed={repair.get('failed', 0)} "
            f"skipped={repair.get('skipped', 0)}"
        ),
        "",
        "## Artifacts",
        "",
    ]
    artifacts = summary.get("artifacts") if isinstance(summary.get("artifacts"), dict) else {}
    for key in ("report_json", "report_md", "reprompt_pack", "repair_run"):
        value = artifacts.get(key)
        if value:
            lines.append(f"- {key}: `{value}`")
    lines.append("")
    return "\n".join(lines)


def _run_repair_job(
    job: dict[str, Any],
    repair_dir: Path,
    *,
    backend: str,
    repairer: Repairer | None,
) -> dict[str, Any]:
    job_id = _safe_slug(str(job.get("job_id") or "job"))
    job_dir = repair_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    paths = job.get("paths") if isinstance(job.get("paths"), dict) else {}
    meta_path_raw = paths.get("meta_path")
    if not isinstance(meta_path_raw, str) or not meta_path_raw:
        return {
            "job_id": job_id,
            "status": "skipped",
            "ok": False,
            "reason": "missing_meta_path",
        }

    try:
        candidate = (
            _deterministic_candidate_for_job(job)
            if backend == "deterministic"
            else _backend_candidate_for_job(job, backend=backend, repairer=repairer)
        )
        repair_error = None
    except Exception as exc:
        candidate = _error_candidate(str(exc))
        repair_error = f"{type(exc).__name__}: {exc}"
    candidate_path = job_dir / "candidate.json"
    candidate_path.write_text(
        json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    issue = job.get("issue") if isinstance(job.get("issue"), dict) else {}
    issue_code = str(issue.get("code") or "")
    score = score_reprompt_candidate(Path(meta_path_raw), candidate_path, issue_code=issue_code)
    score_path = job_dir / "score.json"
    score_path.write_text(json.dumps(score, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "job_id": job_id,
        "status": "scored",
        "ok": bool(score.get("ok")),
        "candidate_path": str(candidate_path),
        "score_path": str(score_path),
        "violations": list(score.get("violations") or []),
        **({"repair_error": repair_error} if repair_error else {}),
    }


def _backend_candidate_for_job(
    job: dict[str, Any],
    *,
    backend: str,
    repairer: Repairer | None,
) -> dict[str, Any]:
    if repairer is None:
        raise ValueError(f"repair backend {backend!r} needs a repairer")
    return _normalize_candidate_payload(repairer(job))


def _deterministic_candidate_for_job(job: dict[str, Any]) -> dict[str, Any]:
    issue = job.get("issue") if isinstance(job.get("issue"), dict) else {}
    request = str(job.get("request") or "")
    code = str(issue.get("code") or "")
    if code == "viber_prompt_missing_audio_contract":
        reply = "The low end got hollow for a moment."
    elif code in {
        "audio_vibe_listener_read_allowed",
        "audio_vibe_control_causality",
        "audio_vibe_hidden_source_detail",
        "cohost_audio_source_detail_emit",
    }:
        reply = "The low end got hollow for a moment."
    elif _is_library_request(request):
        reply = "I do not have grounded results to show yet."
    elif code in _SILENT_COHOST_REPAIR_CODES:
        reply = ""
    elif code in {"viber_live_guarded_reply", "viber_live_verification", "live_claim_guard"}:
        reply = "I need stronger live proof before I call that outcome."
    else:
        reply = "I do not have enough grounded evidence to answer that yet."
    return {
        "reply": reply,
        "tools_used": [],
        "tool_trace": [],
        "track_ids": [],
        "move_grades": [],
        "playlist": None,
        **(
            {
                "prompt_patch": (
                    "LIVE AUDIO CONTRACT: audio_delta and deck/audio context are "
                    "listener/vibe evidence for texture, energy, motion, density, "
                    "and mood. They are not proof of track/deck identity or "
                    "EQ/fader/filter/cue causality; never credit or blame the "
                    "control from audio alone."
                )
            }
            if code == "viber_prompt_missing_audio_contract"
            else {}
        ),
    }


def _error_candidate(error: str) -> dict[str, Any]:
    return {
        "reply": "",
        "tools_used": [],
        "tool_trace": [],
        "track_ids": [],
        "move_grades": [],
        "playlist": None,
        "error": error,
    }


def _normalize_candidate_payload(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"reply": str(raw or "")}
    track_ids = raw.get("track_ids")
    if not isinstance(track_ids, list):
        track_ids = raw.get("seen_track_ids")
    return {
        "reply": str(raw.get("reply") or raw.get("error") or ""),
        "tools_used": [str(item) for item in raw.get("tools_used", []) if isinstance(item, str)],
        "tool_trace": [item for item in raw.get("tool_trace", []) if isinstance(item, dict)],
        "track_ids": [str(item) for item in (track_ids or []) if isinstance(item, str)],
        "move_grades": [item for item in raw.get("move_grades", []) if isinstance(item, dict)],
        "playlist": raw.get("playlist") if isinstance(raw.get("playlist"), dict) else None,
        **{
            key: str(raw.get(key))
            for key in _PROMPT_REPAIR_FIELDS
            if isinstance(raw.get(key), str) and str(raw.get(key)).strip()
        },
        **({"stop_reason": str(raw.get("stop_reason"))} if raw.get("stop_reason") else {}),
        **({"error": str(raw.get("error"))} if raw.get("error") else {}),
    }


def _format_repair_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Cohost/Viber Auto Repair Run",
        "",
        f"schema: `{summary.get('schema')}`",
        f"backend: `{summary.get('backend')}`",
        f"pack: `{summary.get('pack_dir')}`",
        f"ok: `{bool(summary.get('ok'))}`",
        (
            f"jobs={summary.get('job_count', 0)} candidates={summary.get('candidate_count', 0)} "
            f"passed={summary.get('passed', 0)} failed={summary.get('failed', 0)} "
            f"skipped={summary.get('skipped', 0)}"
        ),
        "",
    ]
    results = summary.get("results")
    if isinstance(results, list) and results:
        lines.append("## Results")
        lines.append("")
        for result in results:
            status = "pass" if result.get("ok") else "fail"
            violations = ",".join(str(v) for v in result.get("violations", []) if v)
            lines.append(
                f"- `{result.get('job_id')}` {status}"
                + (f" ({violations})" if violations else "")
            )
    else:
        lines.append("No repair jobs were run.")
    lines.append("")
    return "\n".join(lines)


def _score_command_for_reprompt_job(issue: dict[str, Any], paths: dict[str, Path | None]) -> str | None:
    meta_path = paths.get("meta_path")
    if not meta_path:
        return None
    issue_code = str(issue.get("code") or "").strip()
    issue_arg = f" --issue-code {issue_code}" if issue_code else ""
    return (
        "python -m vibemix eval score-candidate "
        f"--meta {meta_path} --candidate <candidate.json>{issue_arg} --json"
    )


def _build_reprompt_job(index: int, issue: dict[str, Any]) -> dict[str, Any]:
    artifact_dir, paths = _issue_artifact_paths(issue)
    prompt = _read_text_optional(paths.get("prompt_path"))
    response = _read_text_optional(paths.get("response_path"))
    meta = _read_json_file(paths["meta_path"]) if paths.get("meta_path") else {}
    extra = meta.get("extra")
    request = str(extra.get("request") or "") if isinstance(extra, dict) else ""
    response_text = response or str(meta.get("message") or "")
    job_id = "_".join(
        part
        for part in (
            f"{index:02d}",
            _safe_slug(str(issue.get("surface") or "surface")),
            _safe_slug(str(issue.get("code") or "issue")),
            _safe_slug(str(issue.get("response_id") or "no_response")),
        )
        if part
    )
    gates = _repair_gates_for_issue(issue, request)
    reprompt = _reprompt_text(issue, request=request, prompt=prompt, response=response_text, gates=gates)
    candidate_contract = {
        "format": "JSON object preferred, plain reply accepted by score-candidate",
        "json_fields": [
            "reply",
            "tools_used",
            "tool_trace",
            "track_ids",
            "move_grades",
            "playlist",
            "prompt_patch",
        ],
        "score_command": _score_command_for_reprompt_job(issue, paths),
    }
    return {
        "job_id": job_id,
        "issue": issue,
        "artifact_dir": str(artifact_dir) if artifact_dir is not None else None,
        "paths": {key: str(value) for key, value in paths.items() if value is not None},
        "request": request,
        "original_response_preview": _bounded(response_text, limit=500),
        "original_prompt_chars": len(prompt) if prompt is not None else None,
        "gates": gates,
        "reprompt": reprompt,
        "candidate_contract": candidate_contract,
        "status": "ready" if prompt or response or meta else "needs_artifact",
    }


def _write_reprompt_job(out_dir: Path, job: dict[str, Any]) -> None:
    job_dir = out_dir / str(job["job_id"])
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "issue.json").write_text(
        json.dumps(job["issue"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (job_dir / "job.json").write_text(
        json.dumps(
            {key: value for key, value in job.items() if key != "reprompt"},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (job_dir / "reprompt.md").write_text(str(job["reprompt"]), encoding="utf-8")
    (job_dir / "candidate.example.json").write_text(
        json.dumps(
            {
                "reply": "",
                "tools_used": [],
                "tool_trace": [],
                "track_ids": [],
                "move_grades": [],
                "playlist": None,
                "prompt_patch": "",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _format_reprompt_pack_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Cohost/Viber Reprompt Pack",
        "",
        f"schema: `{manifest.get('schema')}`",
        f"session: `{manifest.get('session_dir')}`",
        f"jobs: `{manifest.get('job_count', 0)}`",
        "",
    ]
    jobs = manifest.get("jobs")
    if isinstance(jobs, list) and jobs:
        lines.append("## Jobs")
        lines.append("")
        for job in jobs:
            issue = job.get("issue", {}) if isinstance(job, dict) else {}
            lines.append(
                f"- `{job.get('job_id')}` [{issue.get('severity')}] "
                f"{issue.get('surface')}: {issue.get('title')}"
            )
            lines.append(f"  reprompt: `{job.get('job_id')}/reprompt.md`")
    else:
        lines.append("No reprompt jobs were needed.")
    lines.append("")
    return "\n".join(lines)


def _reprompt_text(
    issue: dict[str, Any],
    *,
    request: str,
    prompt: str | None,
    response: str,
    gates: list[str],
) -> str:
    prompt_body = prompt or "(original prompt artifact missing)"
    return "\n".join(
        [
            "# Vibemix Eval Reprompt Job",
            "",
            "You are repairing one captured cohost/Viber turn. Produce a candidate",
            "answer that would pass the deterministic gates below. Keep the output",
            "grounded in the original prompt and tool contract; do not invent tracks,",
            "cue ids, live deck facts, or transition outcomes.",
            "",
            "## Failure",
            "",
            f"- code: `{issue.get('code')}`",
            f"- severity: `{issue.get('severity')}`",
            f"- surface: `{issue.get('surface')}`",
            f"- detail: {issue.get('detail') or ''}",
            f"- repair: {issue.get('repair') or ''}",
            "",
            "## Original Request",
            "",
            request or "(unknown)",
            "",
            "## Original Reply",
            "",
            response or "(empty)",
            "",
            "## Candidate Gates",
            "",
            *[f"- {gate}" for gate in gates],
            "",
            "## Output Contract",
            "",
            "Return JSON with: reply, tools_used, tool_trace, track_ids, move_grades, playlist, prompt_patch.",
            "Use prompt_patch only when the failure is a prompt/system-instruction repair.",
            "If the request is a library/crate request, either use grounded library tools",
            "or say honestly that no grounded results are available. Do not answer with",
            "live/deck/move/sound-change language unless the user explicitly asked for",
            "the current live deck/move and the proof supports it.",
            "",
            "## Original Prompt",
            "",
            "```text",
            prompt_body,
            "```",
            "",
        ]
    )


def _repair_gates_for_issue(issue: dict[str, Any], request: str) -> list[str]:
    gates = [
        "candidate must not introduce unsupported track, cue, BPM, key, or deck facts",
        "candidate must pass the available live-context and source-detail verifiers",
    ]
    code = str(issue.get("code") or "")
    if code == "viber_library_request_live_leak" or _is_library_request(request):
        gates.extend(
            [
                "library/crate requests must stay in silent_guard mode",
                "library/crate replies must not mention live/deck/move/sound-change language",
                "library/crate replies need grounded tool results or an honest no-results reply",
            ]
        )
    if code in {"viber_live_guarded_reply", "viber_live_verification"}:
        gates.extend(
            [
                "current-live replies must pass verify-live-reply against the captured live_context",
                "do not turn partial live evidence into a transition verdict, move grade, or hidden source detail",
            ]
        )
    if code in {"citation_strip_silent", "citation_strip", "citation_bypass", "citation_zero_emit"}:
        gates.append("spoken cohost replies need concrete citation atoms or silence")
    if code == "citation_strip_silent":
        gates.append("pre-TTS safe strips should become first-model silence, not fallback speech")
    if code == "citation_zero_ack_loop":
        gates.extend(
            [
                "repeated uncertain ack-only TTS must become silence",
                "candidate must not speak a determined fallback or correction line",
            ]
        )
    if code == "live_claim_guard_spoken_fallback":
        gates.append("guard-corrected live claims must be silent on the spoken cohost path")
    if code == "viber_live_guarded_reply":
        gates.extend(
            [
                "Viber must choose the evidence boundary itself before result-boundary correction",
                "candidate must pass verify-live-reply without guard_applied",
            ]
        )
    if code == "audio_vibe_control_causality":
        gates.extend(
            [
                "audio may describe vibe, texture, energy, motion, density, and mood",
                "audio must not prove EQ/fader/filter/cue causality",
                "candidate must not speak a deterministic correction line",
            ]
        )
    if code == "audio_vibe_listener_read_allowed":
        gates.extend(
            [
                "audio should remain usable for broad listener/vibe reads",
                "candidate should not be silent when the safe listener-read lane is available",
                "audio must not prove EQ/fader/filter/cue causality or hidden source/stem detail",
            ]
        )
    if code in {"audio_vibe_hidden_source_detail", "cohost_audio_source_detail_emit"}:
        gates.extend(
            [
                "audio may describe broad listener vibe, texture, energy, motion, density, and mood",
                "audio must not invent vocals, kicks, stems, or source-level song-part detail",
                "candidate must pass the live audio source-detail verifier",
            ]
        )
    if code == "viber_prompt_missing_audio_contract":
        gates.extend(
            [
                "active-live Viber prompts must include the live audio contract",
                "audio may describe listener vibe, texture, energy, motion, density, and mood",
                "audio must not prove track/deck identity or EQ/fader/filter/cue causality",
            ]
        )
    if code == "slop_suppressed":
        gates.append("candidate must avoid the suppressed generic/filler phrase class")
    return gates


def _issue_artifact_paths(issue: dict[str, Any]) -> tuple[Path | None, dict[str, Path | None]]:
    raw = issue.get("artifact")
    if not isinstance(raw, str) or not raw:
        return None, {"prompt_path": None, "response_path": None, "meta_path": None}
    path = Path(raw)
    artifact_dir = path if path.is_dir() else path.parent
    paths = {
        "prompt_path": artifact_dir / "prompt.txt",
        "response_path": artifact_dir / "response.txt",
        "meta_path": artifact_dir / "meta.json",
    }
    if path.name == "prompt.txt":
        paths["prompt_path"] = path
    elif path.name == "response.txt":
        paths["response_path"] = path
    elif path.name == "meta.json":
        paths["meta_path"] = path
    return artifact_dir, {key: value if value.exists() else None for key, value in paths.items()}


def _candidate_payload(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {"reply": ""}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"reply": raw}
    if isinstance(parsed, dict):
        return parsed
    return {"reply": raw}


def _candidate_prompt_patch_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in _PROMPT_REPAIR_FIELDS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value)
        elif isinstance(value, (dict, list)):
            try:
                parts.append(json.dumps(value, ensure_ascii=False, sort_keys=True))
            except (TypeError, ValueError):
                continue
    return "\n".join(parts)


def _has_live_audio_prompt_patch(payload: dict[str, Any]) -> bool:
    patch_text = _candidate_prompt_patch_text(payload)
    return bool(patch_text) and all(
        marker in patch_text for marker in _LIVE_AUDIO_CONTRACT_MARKERS
    )


def _verify_viber_reply(
    reply: str,
    live_context: dict[str, Any] | None,
    move_grades: list[dict[str, Any]],
) -> dict[str, Any]:
    from vibemix.library.codex_curate import verify_live_reply_for_viber

    return verify_live_reply_for_viber(reply, live_context, move_grades=move_grades)


def _silent_candidate_live_verification(move_grades: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "ok": True,
        "violations": [],
        "reply": "",
        "corrected": False,
        "corrected_reply": None,
        "claim_policy": "silence",
        "transport_status": "not_applicable",
        "move_grades_allowed": True,
        "move_grades_seen": len(move_grades),
    }


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _read_text_optional(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return None


def _viber_prompt_audio_contract_issue(row: dict[str, Any], *, surface: str) -> ReportIssue | None:
    prompt_text, prompt_artifact = _prompt_artifact_text_for_row(row)
    if not prompt_text or _ACTIVE_LIVE_CONTEXT_PROMPT_MARKER not in prompt_text:
        return None
    missing_markers = [
        marker for marker in _LIVE_AUDIO_CONTRACT_MARKERS if marker not in prompt_text
    ]
    if not missing_markers:
        return None
    detail = "missing prompt markers: " + ", ".join(missing_markers)
    return ReportIssue(
        code="viber_prompt_missing_audio_contract",
        severity="blocker",
        surface=surface,
        title="Viber active-live prompt missed the audio-vibe contract",
        detail=_bounded(detail),
        repair=(
            "Regenerate this captured active-live prompt with the live audio contract "
            "before accepting listener reads or move verdicts."
        ),
        response_id=_str_or_none(row.get("response_id")),
        artifact=prompt_artifact or _artifact_for(row),
        prompt=(
            "The prompt must include LIVE AUDIO CONTRACT and remind the model to "
            "never credit or blame the control from audio alone."
        ),
    )


def _prompt_artifact_text_for_row(row: dict[str, Any]) -> tuple[str | None, str | None]:
    raw_prompt_path = _artifact_value_for(row, "prompt_path")
    if raw_prompt_path:
        prompt_path = Path(raw_prompt_path)
        prompt_text = _read_text_optional(prompt_path)
        if prompt_text is not None:
            return prompt_text, str(prompt_path)
    artifact = _artifact_for(row)
    if not artifact:
        return None, None
    _, paths = _issue_artifact_paths({"artifact": artifact})
    prompt_path = paths.get("prompt_path")
    prompt_text = _read_text_optional(prompt_path)
    return prompt_text, str(prompt_path) if prompt_path else artifact


def _is_library_request(text: str) -> bool:
    return bool(_LIBRARY_REQUEST_RE.search(str(text or "")))


def _looks_like_live_leak(text: str) -> bool:
    return bool(_LIVE_LEAK_RE.search(str(text or "")))


def _looks_like_outcome_claim(text: str) -> bool:
    return bool(_OUTCOME_CLAIM_RE.search(str(text or "")))


def _looks_like_audio_causality(text: str) -> bool:
    return bool(_AUDIO_CAUSAL_WORD_RE.search(str(text or "")))


def _looks_like_audio_source_detail(text: str) -> bool:
    raw = str(text or "")
    if not raw.strip() or _AUDIO_SOURCE_DETAIL_BOUNDARY_RE.search(raw):
        return False
    return bool(
        _AUDIO_SOURCE_DETAIL_NOUN_RE.search(raw)
        and _AUDIO_SOURCE_DETAIL_CLAIM_RE.search(raw)
    )


def _looks_like_unsupported_audio_source_detail(row: dict[str, Any], text: str) -> bool:
    if not _looks_like_audio_source_detail(text):
        return False
    moves = row.get("moves")
    moves = moves if isinstance(moves, dict) else {}
    event_type = str(row.get("event") or moves.get("event_type") or "").strip().upper()
    for match in _AUDIO_SOURCE_DETAIL_NOUN_RE.finditer(str(text or "")):
        noun = _audio_source_detail_noun_key(match.group(1))
        if not _audio_source_detail_noun_supported(noun, moves, event_type=event_type):
            return True
    return False


def _looks_like_audio_listener_read(text: str) -> bool:
    return bool(_AUDIO_LISTENER_READ_RE.search(str(text or "")))


def _audio_source_detail_noun_key(noun: str) -> str:
    return " ".join(str(noun or "").lower().replace("-", " ").split())


def _audio_source_detail_noun_supported(
    noun: str,
    moves: dict[str, Any],
    *,
    event_type: str,
) -> bool:
    if noun in _AUDIO_VOCAL_NOUNS:
        return bool(moves.get("vocal_active"))
    if noun in _AUDIO_KICK_NOUNS:
        return event_type in _AUDIO_KICK_EVENT_TYPES
    return False


def _looks_like_honest_empty_library_reply(text: str) -> bool:
    return bool(_HONEST_EMPTY_LIBRARY_RE.search(str(text or "")))


def _safe_slug(text: str, *, limit: int = 120) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(text or "").strip()).strip("._-")
    return slug[:limit] or "item"


def _norm_text(text: str) -> str:
    return " ".join(str(text or "").lower().replace("’", "'").split()).strip()


def _live_claim_guard_spoken_fallback_texts(rows: list[dict[str, Any]]) -> set[str]:
    texts: set[str] = set()
    for row in rows:
        if row.get("kind") != "live_claim_guard":
            continue
        for key in ("corrected_text", "fallback_text", "text", "message"):
            value = row.get(key)
            if isinstance(value, str):
                normalized = _norm_text(value)
                if normalized:
                    texts.add(normalized)
    return texts


def _ai_rows_by_response_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("kind") != "ai_message":
            continue
        response_id = _str_or_none(row.get("response_id"))
        if response_id:
            out[response_id] = row
    return out


def _citation_strip_was_silent_pre_tts(
    strip_row: dict[str, Any],
    ai_row: dict[str, Any] | None,
) -> bool:
    """True when a stripped reply was held until linting and never reached TTS."""
    if ai_row is None:
        return False
    if _citation_action(ai_row) != "strip":
        return False
    extra = ai_row.get("extra")
    if not isinstance(extra, dict) or extra.get("head_yielded") is not False:
        return False
    if _str_or_none(strip_row.get("response_id")) != _str_or_none(ai_row.get("response_id")):
        return False
    if extra.get("live_claim_defer_stream") is True:
        return True
    message = _message_text(ai_row).strip()
    spoken_chars = _extra_int(ai_row, "spoken_response_chars")
    return not message and spoken_chars == 0


def _read_jsonl(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with Path(path).open(encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    row = json.loads(text)
                except json.JSONDecodeError as exc:
                    errors.append(f"{path}:{lineno}: invalid JSON: {exc}")
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except FileNotFoundError:
        errors.append(f"{path}: missing")
    except OSError as exc:
        errors.append(f"{path}: read failed: {exc}")
    return rows


def _recent_viber_rows(
    rows: list[dict[str, Any]],
    *,
    limit: int,
    since_iso: str | None = None,
) -> list[dict[str, Any]]:
    since_dt = _parse_iso_datetime(since_iso)
    out = [
        row
        for row in rows
        if (
            str(row.get("surface") or "").startswith("viber_")
            or str(row.get("engine") or "") == "codex"
        )
        and _row_at_or_after(row, since_dt)
    ]
    return out[-limit:]


def _row_at_or_after(row: dict[str, Any], since_dt: datetime | None) -> bool:
    if since_dt is None:
        return True
    row_dt = _parse_iso_datetime(str(row.get("ts_iso") or ""))
    return row_dt is not None and row_dt >= since_dt


def _parse_iso_datetime(value: str | None) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _kind_count(rows: list[dict[str, Any]], kind: str) -> int:
    return sum(1 for row in rows if row.get("kind") == kind)


def _citation_action(row: dict[str, Any]) -> str:
    citation = row.get("citation")
    if isinstance(citation, dict):
        return str(citation.get("action") or "")
    return ""


def _citation_count(row: dict[str, Any]) -> int | None:
    citation = row.get("citation")
    if isinstance(citation, dict):
        return _int_or_none(citation.get("count"))
    return None


def _message_text(row: dict[str, Any]) -> str:
    return str(row.get("message") or row.get("text") or "")


def _is_ack(text: str) -> bool:
    low = " ".join(str(text or "").lower().replace("’", "'").split()).strip(".! ")
    if len(low) > 32:
        return False
    return any(snippet in low for snippet in _ACK_SNIPPETS)


def _zero_citation_ack_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("kind") == "ai_message"
        and row.get("engine") == "live_coach"
        and _citation_action(row) in {"emit", "bypass"}
        and _citation_count(row) == 0
        and _is_ack(_message_text(row))
    ]


def _extra_int(row: dict[str, Any], key: str) -> int:
    extra = row.get("extra")
    if not isinstance(extra, dict):
        return 0
    value = _int_or_none(extra.get(key))
    return int(value or 0)


def _int_or_none(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _artifact_for(row: dict[str, Any]) -> str | None:
    for key in ("session_meta_path", "meta_path", "prompt_path", "session_response_path", "response_path"):
        value = _artifact_value_for(row, key)
        if value:
            return value
    return None


def _artifact_value_for(row: dict[str, Any], key: str) -> str | None:
    artifacts = row.get("artifacts")
    if not isinstance(artifacts, dict):
        return None
    value = artifacts.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _live_verification(row: dict[str, Any]) -> dict[str, Any]:
    extra = row.get("extra")
    if isinstance(extra, dict) and isinstance(extra.get("live_verification"), dict):
        return extra["live_verification"]
    return {}


def _verification_violations(verification: dict[str, Any]) -> list[str]:
    out: list[str] = []
    value = verification.get("violations")
    if isinstance(value, list):
        out.extend(str(item) for item in value if item)
    return out


def _verification_guard_violations(verification: dict[str, Any]) -> list[str]:
    out: list[str] = []
    value = verification.get("guard_violations")
    if isinstance(value, list):
        out.extend(str(item) for item in value if item)
    return out


def _bounded(text: str, *, limit: int = 260) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 15].rstrip() + "...<truncated>"


def _sorted_issues(issues: list[ReportIssue]) -> list[ReportIssue]:
    return sorted(
        issues,
        key=lambda item: (
            _SEVERITY_RANK.get(item.severity, 99),
            item.surface,
            item.code,
            item.response_id or "",
        ),
    )


def _automation_queue(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "severity": issue["severity"],
            "surface": issue["surface"],
            "code": issue["code"],
            "title": issue["title"],
            "repair": issue["repair"],
            **({"response_id": issue["response_id"]} if issue.get("response_id") else {}),
            **({"artifact": issue["artifact"]} if issue.get("artifact") else {}),
            **({"prompt": issue["prompt"]} if issue.get("prompt") else {}),
        }
        for issue in issues
        if issue.get("severity") in {"blocker", "care"}
    ]
