# SPDX-License-Identifier: Apache-2.0
"""Zero-shot CLAP auto-tags for cached library vectors.

This module is the mechanism only: fixed text prompts in the same CLAP space as
the cached audio vectors, deterministic cosine scoring, and honest abstention
below a per-category floor or inside a tie margin. It does not write runtime
state, does not touch Sven, and imports no torch/librosa/heavy CLAP deps at
module import time.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np

AutoTagCategory = Literal["mood", "texture", "instrument"]
PromptMode = Literal["template", "bare"]

DEFAULT_MARGIN: float = 0.015
DEFAULT_THRESHOLDS: dict[AutoTagCategory, float] = {
    "mood": 0.18,
    "texture": 0.18,
    "instrument": 0.18,
}


@dataclass(frozen=True)
class AutoTagPrompt:
    category: AutoTagCategory
    tag: str
    bare_label: str
    template_prompt: str


@dataclass(frozen=True)
class PromptMatrix:
    mode: PromptMode
    prompts: tuple[AutoTagPrompt, ...]
    vectors: np.ndarray


@dataclass(frozen=True)
class AutoTagDecision:
    category: AutoTagCategory
    tag: str | None
    score: float
    runner_up_tag: str | None
    runner_up_score: float
    margin: float
    threshold: float
    accepted: bool
    reason: str


PROMPT_BANK: tuple[AutoTagPrompt, ...] = (
    AutoTagPrompt("mood", "dark", "dark", "a DJ track with a dark mood"),
    AutoTagPrompt("mood", "euphoric", "euphoric", "a euphoric dance track for a DJ set"),
    AutoTagPrompt("mood", "aggressive", "aggressive", "an aggressive peak-time club track"),
    AutoTagPrompt("mood", "hypnotic", "hypnotic", "a hypnotic rolling dance track"),
    AutoTagPrompt("mood", "dreamy", "dreamy", "a dreamy atmospheric electronic track"),
    AutoTagPrompt("mood", "tense", "tense", "a tense suspenseful club track"),
    AutoTagPrompt("texture", "raw", "raw", "a raw rough-textured electronic track"),
    AutoTagPrompt("texture", "polished", "polished", "a polished cleanly produced dance track"),
    AutoTagPrompt("texture", "distorted", "distorted", "a distorted gritty electronic track"),
    AutoTagPrompt("texture", "airy", "airy", "an airy spacious electronic track"),
    AutoTagPrompt("texture", "metallic", "metallic", "a metallic percussive electronic texture"),
    AutoTagPrompt("texture", "warm", "warm", "a warm rounded electronic music texture"),
    AutoTagPrompt("texture", "percussive", "percussive", "a percussive rhythm-focused DJ track"),
    AutoTagPrompt("texture", "atmospheric", "atmospheric", "an atmospheric textured electronic track"),
    AutoTagPrompt("instrument", "vocal", "vocal", "a dance track with prominent vocals"),
    AutoTagPrompt("instrument", "drums", "drums", "a dance track dominated by drums"),
    AutoTagPrompt("instrument", "bassline", "bassline", "a dance track with a prominent bassline"),
    AutoTagPrompt("instrument", "acid_synth", "acid synth", "a dance track with acid synth lines"),
    AutoTagPrompt("instrument", "piano", "piano", "a dance track with piano chords or piano riffs"),
    AutoTagPrompt("instrument", "guitar", "guitar", "a track with guitar instrumentation"),
    AutoTagPrompt("instrument", "strings", "strings", "a track with string instrumentation"),
    AutoTagPrompt("instrument", "pads", "pads", "an electronic track with sustained synth pads"),
)


def _unit(vec: np.ndarray) -> np.ndarray:
    arr = np.asarray(vec, dtype=np.float32)
    norm = float(np.linalg.norm(arr))
    if norm < 1e-12:
        return arr.astype(np.float32, copy=False)
    return (arr / norm).astype(np.float32, copy=False)


def _unit_rows(vectors: np.ndarray) -> np.ndarray:
    arr = np.asarray(vectors, dtype=np.float32)
    if arr.ndim != 2:
        raise ValueError(f"expected (N, D) prompt vectors, got shape {arr.shape}")
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms < 1e-12, 1.0, norms)
    return (arr / norms).astype(np.float32, copy=False)


def prompt_text(prompt: AutoTagPrompt, mode: PromptMode) -> str:
    if mode == "template":
        return prompt.template_prompt
    if mode == "bare":
        return prompt.bare_label
    raise ValueError(f"unknown prompt mode {mode!r}")


def build_prompt_matrix(
    embed_query: Callable[[str], np.ndarray],
    *,
    mode: PromptMode = "template",
    prompts: Sequence[AutoTagPrompt] = PROMPT_BANK,
) -> PromptMatrix:
    """Embed the fixed prompt bank through the caller's CLAP text embedder."""
    rows = [_unit(np.asarray(embed_query(prompt_text(prompt, mode)), dtype=np.float32)) for prompt in prompts]
    if not rows:
        return PromptMatrix(
            mode=mode,
            prompts=tuple(),
            vectors=np.zeros((0, 0), dtype=np.float32),
        )
    return PromptMatrix(mode=mode, prompts=tuple(prompts), vectors=_unit_rows(np.stack(rows)))


def score_auto_tag_categories(
    audio_vector: np.ndarray,
    prompt_matrix: PromptMatrix,
    *,
    thresholds: Mapping[AutoTagCategory, float] | None = None,
    margin: float = DEFAULT_MARGIN,
) -> tuple[AutoTagDecision, ...]:
    """Return one accepted tag or one abstain decision per category."""
    thresholds = thresholds or DEFAULT_THRESHOLDS
    q = _unit(np.asarray(audio_vector, dtype=np.float32))
    if prompt_matrix.vectors.size == 0:
        return tuple()
    if q.shape[0] != prompt_matrix.vectors.shape[1]:
        raise ValueError(
            f"audio vector dim {q.shape[0]} does not match prompt dim "
            f"{prompt_matrix.vectors.shape[1]}"
        )

    scores = prompt_matrix.vectors @ q
    by_category: dict[AutoTagCategory, list[tuple[AutoTagPrompt, float]]] = defaultdict(list)
    for prompt, raw_score in zip(prompt_matrix.prompts, scores, strict=False):
        by_category[prompt.category].append((prompt, float(raw_score)))

    decisions: list[AutoTagDecision] = []
    for category in sorted(by_category):
        ranked = sorted(
            by_category[category],
            key=lambda item: (-item[1], item[0].tag),
        )
        best_prompt, best_score = ranked[0]
        runner_prompt, runner_score = (ranked[1] if len(ranked) > 1 else (None, -1.0))
        threshold = float(thresholds.get(category, DEFAULT_THRESHOLDS[category]))
        gap = best_score - float(runner_score)
        if best_score < threshold:
            decisions.append(
                AutoTagDecision(
                    category=category,
                    tag=None,
                    score=round(best_score, 6),
                    runner_up_tag=runner_prompt.tag if runner_prompt is not None else None,
                    runner_up_score=round(float(runner_score), 6),
                    margin=round(gap, 6),
                    threshold=threshold,
                    accepted=False,
                    reason="below_threshold",
                )
            )
            continue
        if gap < margin:
            decisions.append(
                AutoTagDecision(
                    category=category,
                    tag=None,
                    score=round(best_score, 6),
                    runner_up_tag=runner_prompt.tag if runner_prompt is not None else None,
                    runner_up_score=round(float(runner_score), 6),
                    margin=round(gap, 6),
                    threshold=threshold,
                    accepted=False,
                    reason="tie_margin",
                )
            )
            continue
        decisions.append(
            AutoTagDecision(
                category=category,
                tag=best_prompt.tag,
                score=round(best_score, 6),
                runner_up_tag=runner_prompt.tag if runner_prompt is not None else None,
                runner_up_score=round(float(runner_score), 6),
                margin=round(gap, 6),
                threshold=threshold,
                accepted=True,
                reason="accepted",
            )
        )
    return tuple(decisions)


def accepted_tags(decisions: Sequence[AutoTagDecision]) -> dict[AutoTagCategory, set[str]]:
    out: dict[AutoTagCategory, set[str]] = defaultdict(set)
    for decision in decisions:
        if decision.accepted and decision.tag:
            out[decision.category].add(decision.tag)
    return dict(out)


def known_tags_by_category(
    prompts: Sequence[AutoTagPrompt] = PROMPT_BANK,
) -> dict[AutoTagCategory, set[str]]:
    out: dict[AutoTagCategory, set[str]] = defaultdict(set)
    for prompt in prompts:
        out[prompt.category].add(prompt.tag)
    return dict(out)


__all__ = [
    "DEFAULT_MARGIN",
    "DEFAULT_THRESHOLDS",
    "PROMPT_BANK",
    "AutoTagCategory",
    "AutoTagDecision",
    "AutoTagPrompt",
    "PromptMatrix",
    "PromptMode",
    "accepted_tags",
    "build_prompt_matrix",
    "known_tags_by_category",
    "prompt_text",
    "score_auto_tag_categories",
]
