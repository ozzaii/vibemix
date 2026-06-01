# SPDX-License-Identifier: Apache-2.0
"""Phase 27 Plan 02 — 2-judge cross-check architecture (EVAL-02).

Replaces Plan 01's ``--judges noop`` stub with the real Gemini 3 Pro 6-axis
JSON + Gemini 3 Flash binary cross-check. Per Pitfall P42 (self-bias
collusion mitigation), the final F1 aggregation is ``min(pro_f1, flash_f1)``
per session — NEVER mean — so a single judge agreeing with itself cannot
inflate the gate.

Per CONTEXT decisions section "2-judge cross-check (P42)":
    Different rubric framings — Pro asks "would this fool a human?";
    Flash asks "does the sentence semantically anchor to the citation?"
    Final score = min(pro_f1, flash_f1) to prevent self-bias collusion.

Pure-logic surface (no API):
    - PRO_VERDICT_SCHEMA / FLASH_VERDICT_SCHEMA dicts (Gemini structured-output)
    - load_rubric(name) — caches rubric file content
    - aggregate_session_f1(pro, flash) — returns min, not mean (Pitfall P42)

API-backed surface (gated by genai.Client + cassettes in tests):
    - call_pro_judge(response, evidence, client) → dict
    - call_flash_judge(response, evidence, client) → dict
    - call_judges(judges, response, evidence, ..., client) → dict
"""

from __future__ import annotations

import asyncio
import json
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from vibemix.runtime.ai_observability import append_global_ai_message

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_RUBRICS_DIR = _PROJECT_ROOT / "eval" / "rubrics"

PRO_MODEL = "gemini-3-pro"
FLASH_MODEL = "gemini-3-flash"

# Gemini structured-output JSON schemas — drop-in to response_schema in
# google.genai.types.GenerateContentConfig.
PRO_VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "groundedness": {"type": "number"},
        "timing": {"type": "number"},
        "substance": {"type": "number"},
        "tone": {"type": "number"},
        "relevance": {"type": "number"},
        "brevity": {"type": "number"},
        "verdict": {"type": "string", "enum": ["pass", "fail", "borderline"]},
        "rationale": {"type": "string"},
    },
    "required": [
        "groundedness",
        "timing",
        "substance",
        "tone",
        "relevance",
        "brevity",
        "verdict",
        "rationale",
    ],
}

FLASH_VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "pass": {"type": "boolean"},
        "why": {"type": "string"},
    },
    "required": ["pass", "why"],
}


@lru_cache(maxsize=4)
def load_rubric(name: str) -> str:
    """Read eval/rubrics/judge_<name>.md and cache the content."""
    path = _RUBRICS_DIR / f"judge_{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"rubric not found: {path}")
    return path.read_text(encoding="utf-8")


def _format_evidence_for_judge(evidence: dict[str, Any]) -> str:
    """Render the event payload as a compact JSON snippet for the judge prompt."""
    # Pick only the fields useful to the judge — full payload would dilute attention.
    return json.dumps(
        {
            "type": evidence.get("type", ""),
            "t_session": evidence.get("t_session", 0.0),
            "session": evidence.get("session", ""),
            "payload": evidence.get("payload", {}),
        },
        sort_keys=True,
    )


def _assemble_judge_prompt(response: str, evidence: dict[str, Any]) -> str:
    """Build the user-message portion of the judge invocation."""
    return (
        "Spoken response:\n"
        f"  {response!r}\n\n"
        "Evidence payload (the ground-truth event the response should anchor to):\n"
        f"  {_format_evidence_for_judge(evidence)}\n"
    )


def _eval_live_context(evidence: dict[str, Any]) -> dict[str, Any]:
    payload = evidence.get("payload")
    payload = payload if isinstance(payload, dict) else {}
    ctx: dict[str, Any] = {}
    recent_moves = payload.get("recent_moves")
    if isinstance(recent_moves, list):
        ctx["recent_moves"] = recent_moves
    elif evidence.get("type") == "MIX_MOVE":
        control = payload.get("control") or payload.get("move") or payload.get("label")
        if control:
            ctx["recent_moves"] = [str(control)]
    if isinstance(payload.get("deck_mixer"), dict):
        ctx["deck_mixer"] = payload["deck_mixer"]
    if isinstance(payload.get("audio_delta"), list):
        ctx["audio_delta"] = payload["audio_delta"]
    deck = payload.get("deck") or payload.get("side")
    if deck:
        ctx["deck"] = str(deck)
    return ctx


def _record_eval_judge_ai_message(
    *,
    judge: str,
    model: str,
    prompt: str,
    response_text: str,
    response_under_judgment: str,
    evidence: dict[str, Any],
    stop_reason: str,
    latency_s: float,
    verdict: dict[str, Any] | None = None,
    error: Exception | None = None,
) -> None:
    try:
        append_global_ai_message(
            engine="eval_judge",
            surface=f"eval_judge_{judge}",
            direction="assistant",
            text=response_text,
            event="eval_judge",
            provider="gemini",
            model=model,
            stop_reason=stop_reason,
            latency_s=round(latency_s, 3),
            prompt=prompt,
            response=response_text,
            live_context=_eval_live_context(evidence),
            extra={
                "judge": judge,
                "evidence_type": evidence.get("type"),
                "evidence_session": evidence.get("session"),
                "evidence_t_session": evidence.get("t_session"),
                "response_under_judgment_chars": len(response_under_judgment),
                "verdict": verdict,
                "error": str(error) if error else None,
            },
        )
    except Exception:
        pass


async def call_pro_judge(
    response: str, evidence: dict[str, Any], client: Any
) -> dict[str, Any]:
    """Invoke Gemini 3 Pro with the 6-axis structured-JSON rubric."""
    # Lazy import — keeps the module importable in environments without google-genai.
    from google.genai import types

    cfg = types.GenerateContentConfig(
        system_instruction=load_rubric("pro"),
        response_mime_type="application/json",
        response_schema=PRO_VERDICT_SCHEMA,
        temperature=0.1,
    )
    prompt = _assemble_judge_prompt(response, evidence)
    start = time.perf_counter()
    try:
        api_response = client.models.generate_content(
            model=PRO_MODEL,
            contents=[prompt],
            config=cfg,
        )
    except Exception as exc:
        _record_eval_judge_ai_message(
            judge="pro",
            model=PRO_MODEL,
            prompt=prompt,
            response_text="",
            response_under_judgment=response,
            evidence=evidence,
            stop_reason="api_error",
            latency_s=time.perf_counter() - start,
            error=exc,
        )
        raise
    text = api_response.text or ""
    try:
        verdict = json.loads(text)
    except json.JSONDecodeError as e:
        err = ValueError(f"Pro judge returned non-JSON: {text!r}")
        _record_eval_judge_ai_message(
            judge="pro",
            model=PRO_MODEL,
            prompt=prompt,
            response_text=text,
            response_under_judgment=response,
            evidence=evidence,
            stop_reason="parse_error",
            latency_s=time.perf_counter() - start,
            error=err,
        )
        raise err from e
    missing = set(PRO_VERDICT_SCHEMA["required"]) - set(verdict.keys())
    if missing:
        err = ValueError(f"Pro verdict missing keys {sorted(missing)}: {verdict}")
        _record_eval_judge_ai_message(
            judge="pro",
            model=PRO_MODEL,
            prompt=prompt,
            response_text=text,
            response_under_judgment=response,
            evidence=evidence,
            stop_reason="schema_error",
            latency_s=time.perf_counter() - start,
            verdict=verdict,
            error=err,
        )
        raise err
    _record_eval_judge_ai_message(
        judge="pro",
        model=PRO_MODEL,
        prompt=prompt,
        response_text=text,
        response_under_judgment=response,
        evidence=evidence,
        stop_reason="parsed",
        latency_s=time.perf_counter() - start,
        verdict=verdict,
    )
    return verdict


async def call_flash_judge(
    response: str, evidence: dict[str, Any], client: Any
) -> dict[str, Any]:
    """Invoke Gemini 3 Flash with the binary pass/fail rubric."""
    from google.genai import types

    cfg = types.GenerateContentConfig(
        system_instruction=load_rubric("flash"),
        response_mime_type="application/json",
        response_schema=FLASH_VERDICT_SCHEMA,
        temperature=0.1,
    )
    prompt = _assemble_judge_prompt(response, evidence)
    start = time.perf_counter()
    try:
        api_response = client.models.generate_content(
            model=FLASH_MODEL,
            contents=[prompt],
            config=cfg,
        )
    except Exception as exc:
        _record_eval_judge_ai_message(
            judge="flash",
            model=FLASH_MODEL,
            prompt=prompt,
            response_text="",
            response_under_judgment=response,
            evidence=evidence,
            stop_reason="api_error",
            latency_s=time.perf_counter() - start,
            error=exc,
        )
        raise
    text = api_response.text or ""
    try:
        verdict = json.loads(text)
    except json.JSONDecodeError as e:
        err = ValueError(f"Flash judge returned non-JSON: {text!r}")
        _record_eval_judge_ai_message(
            judge="flash",
            model=FLASH_MODEL,
            prompt=prompt,
            response_text=text,
            response_under_judgment=response,
            evidence=evidence,
            stop_reason="parse_error",
            latency_s=time.perf_counter() - start,
            error=err,
        )
        raise err from e
    missing = set(FLASH_VERDICT_SCHEMA["required"]) - set(verdict.keys())
    if missing:
        err = ValueError(f"Flash verdict missing keys {sorted(missing)}: {verdict}")
        _record_eval_judge_ai_message(
            judge="flash",
            model=FLASH_MODEL,
            prompt=prompt,
            response_text=text,
            response_under_judgment=response,
            evidence=evidence,
            stop_reason="schema_error",
            latency_s=time.perf_counter() - start,
            verdict=verdict,
            error=err,
        )
        raise err
    _record_eval_judge_ai_message(
        judge="flash",
        model=FLASH_MODEL,
        prompt=prompt,
        response_text=text,
        response_under_judgment=response,
        evidence=evidence,
        stop_reason="parsed",
        latency_s=time.perf_counter() - start,
        verdict=verdict,
    )
    return verdict


def _noop_stub(response: str, evidence: dict[str, Any]) -> dict[str, Any]:
    """Plan 01 noop stub — kept for regression."""
    return {
        "pro": {"verdict": "pass", "substance": 0.7, "f1_contribution": 1.0},
        "flash": {"pass": True, "why": "noop stub"},
    }


async def call_judges(
    judges: list[str],
    response: str,
    evidence: dict[str, Any],
    audio_buf: Any = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """Dispatch over the requested judges. Returns combined verdict dict.

    ``judges`` is a list of judge names. Supported: ``"noop"`` (stub
    from Plan 01), ``"gemini-3-pro"``, ``"gemini-3-flash"``. Multiple
    real-judge names are invoked concurrently via asyncio.gather.

    The combined dict has shape:
        {
            "pro": {<pro verdict>} | None,
            "flash": {<flash verdict>} | None,
            "judges_invoked": [...],
        }
    """
    if "noop" in judges:
        return {
            **_noop_stub(response, evidence),
            "judges_invoked": ["noop"],
        }
    if client is None:
        raise ValueError("client required for non-noop judges")

    tasks = []
    names: list[str] = []
    if "gemini-3-pro" in judges:
        tasks.append(call_pro_judge(response, evidence, client))
        names.append("pro")
    if "gemini-3-flash" in judges:
        tasks.append(call_flash_judge(response, evidence, client))
        names.append("flash")
    if not tasks:
        raise ValueError(f"no recognized judges in {judges!r}")

    results = await asyncio.gather(*tasks, return_exceptions=True)
    out: dict[str, Any] = {"pro": None, "flash": None, "judges_invoked": names}
    for name, result in zip(names, results, strict=True):
        if isinstance(result, Exception):
            out[name] = {"error": str(result), "_failed": True}
        else:
            out[name] = result
    return out


def _verdict_to_bool(verdict: dict[str, Any] | None) -> bool | None:
    """Map a judge verdict to a binary pass/fail. None means no verdict."""
    if verdict is None or verdict.get("_failed"):
        return None
    # Pro emits string verdict; Flash emits bool pass.
    if "verdict" in verdict:
        return verdict["verdict"] == "pass"
    if "pass" in verdict:
        return bool(verdict["pass"])
    return None


def _judge_f1(predictions: list[bool], ground_truth: list[bool]) -> float:
    """Binary F1 with explicit zero-division handling."""
    if not predictions or len(predictions) != len(ground_truth):
        return 0.0
    tp = sum(1 for p, g in zip(predictions, ground_truth, strict=True) if p and g)
    fp = sum(1 for p, g in zip(predictions, ground_truth, strict=True) if p and not g)
    fn = sum(1 for p, g in zip(predictions, ground_truth, strict=True) if not p and g)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def aggregate_session_f1(
    pro_verdicts: list[dict[str, Any]],
    flash_verdicts: list[dict[str, Any]],
    ground_truth_pass: list[bool] | None = None,
) -> float:
    """Compute ``min(pro_f1, flash_f1)`` for the session (Pitfall P42).

    When ``ground_truth_pass`` is omitted, assume all ground-truth events
    are pass (the common case for the synthetic happy path — Plan 01
    fixture). Returns 0.0 when both judge verdict lists are empty.
    """
    n_pro = len(pro_verdicts)
    n_flash = len(flash_verdicts)
    if n_pro == 0 and n_flash == 0:
        return 0.0
    n = max(n_pro, n_flash)
    if ground_truth_pass is None:
        ground_truth_pass = [True] * n

    pro_preds = [
        (_verdict_to_bool(v) if v is not None else None) for v in pro_verdicts
    ]
    flash_preds = [
        (_verdict_to_bool(v) if v is not None else None) for v in flash_verdicts
    ]
    # Replace None predictions with False (failed judge = no pass).
    pro_preds_clean = [(p is True) for p in pro_preds]
    flash_preds_clean = [(p is True) for p in flash_preds]

    pro_f1 = _judge_f1(pro_preds_clean, ground_truth_pass[:n_pro] or ground_truth_pass)
    flash_f1 = _judge_f1(
        flash_preds_clean, ground_truth_pass[:n_flash] or ground_truth_pass
    )

    # Pitfall P42: min — NEVER mean.
    if n_pro == 0:
        return flash_f1
    if n_flash == 0:
        return pro_f1
    return min(pro_f1, flash_f1)
