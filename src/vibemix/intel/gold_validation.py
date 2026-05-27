# SPDX-License-Identifier: Apache-2.0
"""Validation and redacted reporting for INTEL-15 gold labels."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from vibemix.intel.gold_labels import (
    ALLOWED_SPLITS,
    GoldLabel,
    allowed_labels_for_kind,
)


@dataclass(frozen=True, slots=True)
class GoldKnownIds:
    candidate_ids: frozenset[str] = frozenset()
    transition_keys: frozenset[str] = frozenset()
    proposal_ids: frozenset[str] = frozenset()
    cue_ids: frozenset[str] = frozenset()
    packet_ids: frozenset[str] = frozenset()
    track_ids: frozenset[str] = frozenset()
    section_ids: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class GoldValidationResult:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    counts: dict[str, Any]


def validate_gold_labels(
    labels: tuple[GoldLabel, ...],
    *,
    known_ids: GoldKnownIds | None = None,
    require_all_splits: bool = True,
) -> GoldValidationResult:
    known = known_ids or GoldKnownIds()
    errors: list[str] = []
    warnings: list[str] = []
    by_label_id: dict[str, GoldLabel] = {}
    split_counts = {split: 0 for split in sorted(ALLOWED_SPLITS)}
    kind_counts: dict[str, int] = {}
    label_counts: dict[str, int] = {}

    for label in labels:
        prefix = f"{label.label_id or '<missing>'}:"
        if not label.label_id:
            errors.append(prefix + "missing_label_id")
        elif label.label_id in by_label_id:
            errors.append(prefix + "duplicate_label_id")
        else:
            by_label_id[label.label_id] = label
        if label.split not in ALLOWED_SPLITS:
            errors.append(prefix + f"invalid_split:{label.split}")
        else:
            split_counts[label.split] += 1
        if label.label not in allowed_labels_for_kind(label.kind):
            errors.append(prefix + f"invalid_{label.kind}_label:{label.label}")
        if label.rubric_version in {"", "transition_utility", "risk"}:
            warnings.append(prefix + "noncanonical_rubric_version")
        if _contains_private_payload(label.raw or {}):
            errors.append(prefix + "private_payload_present")
        if label.label_id in label.action_ids:
            errors.append(prefix + "label_id_used_as_action_id")
        for action_id in label.action_ids:
            if action_id.startswith(("lbl_", "gold_")):
                errors.append(prefix + f"label_like_action_id:{action_id}")
        _validate_known_ids(label, known, errors, prefix)
        kind_counts[label.kind] = kind_counts.get(label.kind, 0) + 1
        label_counts[label.label] = label_counts.get(label.label, 0) + 1

    for label in labels:
        if label.supersedes:
            old = by_label_id.get(label.supersedes)
            if old is None:
                errors.append(f"{label.label_id}:unknown_supersedes:{label.supersedes}")
            elif old.split == "holdout" and label.split != "holdout":
                errors.append(f"{label.label_id}:holdout_correction_must_remain_holdout")

    if require_all_splits:
        for split, count in split_counts.items():
            if count == 0:
                errors.append(f"missing_split:{split}")

    return GoldValidationResult(
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        counts={
            "total": len(labels),
            "splits": split_counts,
            "kinds": dict(sorted(kind_counts.items())),
            "labels": dict(sorted(label_counts.items())),
            "supersedes": sum(1 for label in labels if label.supersedes),
        },
    )


def redacted_gold_report(
    labels: tuple[GoldLabel, ...],
    validation: GoldValidationResult,
    *,
    salt: str,
) -> dict[str, Any]:
    examples: list[dict[str, Any]] = []
    for label in labels[:10]:
        examples.append(
            {
                "label_id_hash": _hash_id(label.label_id, salt),
                "kind": label.kind,
                "split": label.split,
                "label": label.label,
                "track_hash": _hash_id(label.track_id, salt) if label.track_id else None,
                "section_hash": _hash_id(label.section_id, salt) if label.section_id else None,
                "candidate_hash": _hash_id(label.candidate_id, salt)
                if label.candidate_id
                else None,
            }
        )
    return {
        "schema": "intel_gold_report_v1",
        "valid": validation.valid,
        "privacy": {"local_paths_redacted": True, "ids_hashed": True},
        "counts": validation.counts,
        "error_count": len(validation.errors),
        "warning_count": len(validation.warnings),
        "examples": examples,
    }


def _validate_known_ids(
    label: GoldLabel,
    known: GoldKnownIds,
    errors: list[str],
    prefix: str,
) -> None:
    checks = (
        ("candidate_id", label.candidate_id, known.candidate_ids),
        ("transition_key", label.transition_key, known.transition_keys),
        ("proposal_id", label.proposal_id, known.proposal_ids),
        ("cue_id", label.cue_id, known.cue_ids),
        ("packet_id", label.packet_id, known.packet_ids),
        ("track_id", label.track_id, known.track_ids),
        ("section_id", label.section_id, known.section_ids),
    )
    for name, value, allowed in checks:
        if value and allowed and value not in allowed:
            errors.append(prefix + f"unknown_{name}:{value}")


def _contains_private_payload(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).lower()
            in {"path", "filepath", "file_path", "local_path", "raw_audio", "vector"}
            or _contains_private_payload(item)
            for key, item in value.items()
        )
    if isinstance(value, list | tuple):
        return any(_contains_private_payload(item) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        return (
            value.startswith("/")
            or lowered.startswith("file://")
            or ":\\" in value
            or lowered.startswith("vector:")
            or lowered.startswith("audio:raw")
        )
    return False


def _hash_id(value: str, salt: str) -> str:
    return hashlib.sha256(f"{value}|{salt}".encode()).hexdigest()[:12]


__all__ = [
    "GoldKnownIds",
    "GoldValidationResult",
    "redacted_gold_report",
    "validate_gold_labels",
]
