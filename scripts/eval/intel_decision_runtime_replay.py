# SPDX-License-Identifier: Apache-2.0
"""Replay agent decisions against issued intel context packets.

This is an eval harness, not a runtime dependency. It validates saved
``AgentDecision`` rows against saved ``AgentContextEnvelope`` rows and reports
redacted grounding/claim/timing failure metrics.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from vibemix.intel.agent_contract import (
    SCHEMA_VERSION,
    AgentContextEnvelope,
    AgentDecision,
)
from vibemix.intel.decision_validator import validate_agent_decision

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_DIR = ROOT / "tests" / "intel" / "fixtures"


def replay_paths(
    *,
    contexts_path: Path | str,
    decisions_path: Path | str,
    source: str = "private:redacted",
) -> dict[str, Any]:
    contexts = {
        envelope.packet_id: envelope
        for envelope in (
            _envelope_from_raw(row) for row in _load_json_or_jsonl(Path(contexts_path))
        )
    }
    rows = _load_json_or_jsonl(Path(decisions_path))
    results: list[dict[str, Any]] = []
    for row in rows:
        packet_id = str(row.get("packet_id") or "")
        envelope = contexts.get(packet_id)
        if envelope is None:
            results.append(
                {
                    "packet_id": packet_id,
                    "decision_id": row.get("decision_id"),
                    "accepted": False,
                    "errors": ("unknown_packet_id",),
                }
            )
            continue
        decision = _decision_from_raw(row)
        validation = validate_agent_decision(envelope, decision)
        results.append(
            {
                "packet_id": packet_id,
                "decision_id": row.get("decision_id"),
                "accepted": validation.accepted,
                "action": decision.action,
                "candidate_id": decision.candidate_id,
                "errors": validation.errors,
            }
        )

    total = len(results)
    rejected = sum(1 for result in results if not result["accepted"])
    missing_claim = sum(
        1
        for result in results
        for error in result["errors"]
        if error.startswith("missing_claim_id")
    )
    unknown_candidate = sum(
        1 for result in results for error in result["errors"] if error == "unknown_candidate_id"
    )
    timing_floor = sum(
        1
        for result in results
        for error in result["errors"]
        if error in {"timing_not_allowed", "selected_candidate_has_no_exact_timing"}
    )
    return {
        "schema": "intel_decision_runtime_replay_v1",
        "source": source,
        "valid": total > 0,
        "privacy": {"local_paths_redacted": True},
        "totals": {
            "contexts": len(contexts),
            "decisions": total,
            "accepted": total - rejected,
            "rejected": rejected,
        },
        "metrics": {
            "unknown_id_rejection_rate": _rate(unknown_candidate, total),
            "unsupported_claim_rate": _rate(
                sum(
                    1
                    for result in results
                    for error in result["errors"]
                    if error.startswith("unsupported_claim:")
                ),
                total,
            ),
            "unsupported_musical_claim_rate": _rate(missing_claim, total),
            "validator_fallback_rate": _rate(rejected, total),
            "exact_timing_floor_violation_rate": _rate(timing_floor, total),
            "action_grounding_violation_rate": _rate(unknown_candidate, total),
        },
        "error_counts": _count_errors(results),
        "results": results,
    }


def replay_fixture_dir(fixture_dir: Path | str = DEFAULT_FIXTURE_DIR) -> dict[str, Any]:
    base = Path(fixture_dir)
    return replay_paths(
        contexts_path=base / "context_packets.json",
        decisions_path=base / "agent_decisions.jsonl",
        source=f"fixture:{base.name}",
    )


def _envelope_from_raw(row: dict[str, Any]) -> AgentContextEnvelope:
    candidate_rows = row.get("candidates")
    if not isinstance(candidate_rows, list):
        candidate_rows = [
            {
                "candidate_id": candidate_id,
                "recommended_cue_slot": None,
                "start_in_bars": None,
            }
            for candidate_id in row.get("candidate_ids", ())
        ]
    claim_summary = tuple(row.get("claim_summary") or ())
    claim_ids = tuple(row.get("claim_ids") or ())
    if not claim_ids:
        claim_ids = tuple(
            claim_id
            for claim_id in row.get("allowed_claims", ())
            if str(claim_id).startswith("clm_")
        )
    allowed_claims = tuple(
        claim for claim in row.get("allowed_claims", ()) if not str(claim).startswith("clm_")
    )
    return AgentContextEnvelope(
        schema_version=str(row.get("schema_version") or SCHEMA_VERSION),
        packet_id=str(row["packet_id"]),
        mode=row.get("mode", "prep"),
        intent=row.get("intent", "chat"),
        current=dict(row.get("current") or {}),
        candidates=tuple(dict(candidate) for candidate in candidate_rows),
        constraints=dict(row.get("constraints") or {}),
        allowed_actions=tuple(row.get("allowed_actions") or ()),
        allowed_claims=allowed_claims,
        forbidden_claims=tuple(row.get("forbidden_claims") or ()),
        citation_scope={k: tuple(v) for k, v in dict(row.get("citation_scope") or {}).items()},
        confidence_policy=dict(row.get("confidence_policy") or {}),
        claim_ids=claim_ids,
        claim_summary=claim_summary,
    )


def _decision_from_raw(row: dict[str, Any]) -> AgentDecision:
    cited_claims = tuple(row.get("cited_claims") or ())
    cited_claim_ids = tuple(row.get("cited_claim_ids") or ())
    if not cited_claim_ids and any(str(claim).startswith("clm_") for claim in cited_claims):
        cited_claim_ids = tuple(
            str(claim) for claim in cited_claims if str(claim).startswith("clm_")
        )
        cited_claims = tuple(
            str(claim) for claim in cited_claims if not str(claim).startswith("clm_")
        )
    return AgentDecision(
        schema_version=str(row.get("schema_version") or SCHEMA_VERSION),
        action=row.get("action", "suppress"),
        candidate_id=row.get("candidate_id"),
        cue_slot=row.get("cue_slot"),
        timing_text=row.get("timing_text"),
        spoken_text=str(row.get("spoken_text") or ""),
        cited_claims=cited_claims,
        cited_claim_ids=cited_claim_ids,
        confidence=float(row.get("confidence") or 0.0),
    )


def _load_json_or_jsonl(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    raw = json.loads(text)
    return raw if isinstance(raw, list) else [raw]


def _count_errors(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        for error in result["errors"]:
            counts[str(error)] = counts.get(str(error), 0) + 1
    return dict(sorted(counts.items()))


def _rate(count: int, total: int) -> float:
    return round(count / total, 6) if total else 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    parser.add_argument("--contexts", type=Path, help="Context packet JSON/JSONL")
    parser.add_argument("--decisions", type=Path, help="Agent decision JSONL")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args(argv)

    if args.contexts or args.decisions:
        if not args.contexts or not args.decisions:
            parser.error("--contexts and --decisions must be provided together")
        result = replay_paths(
            contexts_path=args.contexts,
            decisions_path=args.decisions,
            source="private:redacted",
        )
    else:
        result = replay_fixture_dir(args.fixture_dir)
    if args.json:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        print(
            "Decision replay: "
            f"contexts={result['totals']['contexts']} decisions={result['totals']['decisions']} "
            f"accepted={result['totals']['accepted']} rejected={result['totals']['rejected']}"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
