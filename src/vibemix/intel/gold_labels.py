# SPDX-License-Identifier: Apache-2.0
"""INTEL-15 private gold-label contracts.

Gold labels are eval evidence, not product actions. This module keeps the rows
typed, privacy-checked, and explicit about calibration/holdout/canary splits.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

GoldSplit = Literal["calibration", "holdout", "canary"]
GoldKind = Literal["section", "transition", "cue", "live_pill", "representation"]

RUBRIC_VERSION = "kaan_gold_v1"

ALLOWED_SPLITS: frozenset[str] = frozenset({"calibration", "holdout", "canary"})
SECTION_LABELS: frozenset[str] = frozenset(
    {"good", "small_nudge", "wrong_boundary", "wrong_role", "not_mixable", "unusable", "unclear"}
)
TRANSITION_LABELS: frozenset[str] = frozenset({"would_play", "maybe", "no"})
CUE_LABELS: frozenset[str] = frozenset(
    {"keep", "move", "delete", "relabel", "add_missing", "unclear"}
)
LIVE_PILL_LABELS: frozenset[str] = frozenset(
    {
        "helpful",
        "not_now",
        "wrong_timing",
        "too_late",
        "too_early",
        "distracting",
        "suppression_correct",
        "suppression_wrong",
        "unclear",
    }
)
REPRESENTATION_LABELS: frozenset[str] = frozenset(
    {
        "relevant_mixable",
        "relevant_not_mixable",
        "wrong_role",
        "wrong_vibe",
        "duplicate",
        "unsafe_low_confidence",
        "unclear",
    }
)
LEGACY_TRANSITION_LABELS: dict[str, str] = {"accept": "would_play", "reject": "no"}


@dataclass(frozen=True, slots=True)
class GoldLabel:
    label_id: str
    kind: GoldKind
    split: GoldSplit
    label: str
    rubric_version: str
    review_session_id: str | None
    review_item_id: str | None
    candidate_id: str | None = None
    transition_key: str | None = None
    proposal_id: str | None = None
    cue_id: str | None = None
    packet_id: str | None = None
    track_id: str | None = None
    section_id: str | None = None
    supersedes: str | None = None
    note: str | None = None
    raw: dict[str, Any] | None = None

    @property
    def action_ids(self) -> tuple[str, ...]:
        return tuple(
            item
            for item in (
                self.candidate_id,
                self.proposal_id,
                self.cue_id,
                self.packet_id,
                self.track_id,
                self.section_id,
            )
            if item
        )


def load_gold_labels(
    path: Path | str, *, default_split: GoldSplit = "calibration"
) -> tuple[GoldLabel, ...]:
    rows = _load_json_or_jsonl(Path(path))
    return tuple(parse_gold_label(row, default_split=default_split) for row in rows)


def parse_gold_label(row: dict[str, Any], *, default_split: GoldSplit = "calibration") -> GoldLabel:
    kind = _infer_kind(row)
    label = _normalize_label(kind, str(row.get("label") or ""))
    split = str(row.get("split") or default_split)
    return GoldLabel(
        label_id=str(row.get("label_id") or ""),
        kind=kind,
        split=split,  # type: ignore[arg-type]
        label=label,
        rubric_version=str(row.get("rubric_version") or row.get("rubric") or RUBRIC_VERSION),
        review_session_id=_str_or_none(row.get("review_session_id")),
        review_item_id=_str_or_none(row.get("review_item_id")),
        candidate_id=_str_or_none(row.get("candidate_id")),
        transition_key=_str_or_none(row.get("transition_key")),
        proposal_id=_str_or_none(row.get("proposal_id")),
        cue_id=_str_or_none(row.get("cue_id")),
        packet_id=_str_or_none(row.get("packet_id")),
        track_id=_str_or_none(row.get("track_id")),
        section_id=_str_or_none(row.get("section_id")),
        supersedes=_str_or_none(row.get("supersedes")),
        note=_str_or_none(row.get("note") or row.get("redacted_notes")),
        raw=dict(row),
    )


def allowed_labels_for_kind(kind: GoldKind) -> frozenset[str]:
    return {
        "section": SECTION_LABELS,
        "transition": TRANSITION_LABELS,
        "cue": CUE_LABELS,
        "live_pill": LIVE_PILL_LABELS,
        "representation": REPRESENTATION_LABELS,
    }[kind]


def _infer_kind(row: dict[str, Any]) -> GoldKind:
    explicit = row.get("review_item_type") or row.get("kind")
    if explicit in {"section", "transition", "cue", "live_pill", "representation"}:
        return explicit  # type: ignore[return-value]
    if row.get("proposal_id") or row.get("cue_id") or row.get("slot"):
        return "cue"
    if (
        row.get("message_kind")
        or row.get("action_taken")
        or row.get("playhead_confidence") is not None
    ):
        return "live_pill"
    if row.get("representation_run_id") or row.get("query") or row.get("result_rank") is not None:
        return "representation"
    if (
        row.get("candidate_id")
        or row.get("transition_key")
        or row.get("rubric")
        in {
            "transition_utility",
            "risk",
        }
    ):
        return "transition"
    return "section"


def _normalize_label(kind: GoldKind, label: str) -> str:
    clean = label.strip()
    if kind == "transition":
        return LEGACY_TRANSITION_LABELS.get(clean, clean)
    return clean


def _load_json_or_jsonl(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    raw = json.loads(text)
    return raw if isinstance(raw, list) else [raw]


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = [
    "ALLOWED_SPLITS",
    "RUBRIC_VERSION",
    "GoldKind",
    "GoldLabel",
    "GoldSplit",
    "allowed_labels_for_kind",
    "load_gold_labels",
    "parse_gold_label",
]
