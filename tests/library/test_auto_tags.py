# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import numpy as np

from vibemix.library.auto_tags import (
    AutoTagPrompt,
    PromptMatrix,
    accepted_tags,
    build_prompt_matrix,
    score_auto_tag_categories,
)


def _unit(vec: list[float]) -> np.ndarray:
    arr = np.asarray(vec, dtype=np.float32)
    return arr / np.linalg.norm(arr)


def test_score_auto_tags_accepts_clear_category_winner() -> None:
    prompts = (
        AutoTagPrompt("mood", "dark", "dark", "a dark DJ track"),
        AutoTagPrompt("mood", "euphoric", "euphoric", "a euphoric DJ track"),
        AutoTagPrompt("texture", "raw", "raw", "a raw DJ track"),
        AutoTagPrompt("texture", "airy", "airy", "an airy DJ track"),
    )
    matrix = PromptMatrix(
        mode="template",
        prompts=prompts,
        vectors=np.asarray(
            [
                _unit([1.0, 0.0, 0.0]),
                _unit([0.0, 1.0, 0.0]),
                _unit([1.0, 0.0, 0.0]),
                _unit([0.0, 0.0, 1.0]),
            ],
            dtype=np.float32,
        ),
    )

    decisions = score_auto_tag_categories(
        _unit([1.0, 0.0, 0.0]),
        matrix,
        thresholds={"mood": 0.4, "texture": 0.4, "instrument": 0.4},
        margin=0.05,
    )

    assert accepted_tags(decisions) == {"mood": {"dark"}, "texture": {"raw"}}


def test_score_auto_tags_abstains_below_floor_and_inside_tie_margin() -> None:
    prompts = (
        AutoTagPrompt("mood", "dark", "dark", "a dark DJ track"),
        AutoTagPrompt("mood", "euphoric", "euphoric", "a euphoric DJ track"),
        AutoTagPrompt("texture", "raw", "raw", "a raw DJ track"),
        AutoTagPrompt("texture", "airy", "airy", "an airy DJ track"),
    )
    matrix = PromptMatrix(
        mode="template",
        prompts=prompts,
        vectors=np.asarray(
            [
                _unit([1.0, 0.0]),
                _unit([0.96, 0.04]),
                _unit([0.0, 1.0]),
                _unit([1.0, 0.0]),
            ],
            dtype=np.float32,
        ),
    )

    decisions = score_auto_tag_categories(
        _unit([1.0, 0.0]),
        matrix,
        thresholds={"mood": 0.2, "texture": 1.1, "instrument": 0.2},
        margin=0.2,
    )
    by_category = {decision.category: decision for decision in decisions}

    assert by_category["mood"].accepted is False
    assert by_category["mood"].reason == "tie_margin"
    assert by_category["texture"].accepted is False
    assert by_category["texture"].reason == "below_threshold"


def test_build_prompt_matrix_embeds_bare_or_template_text() -> None:
    prompts = (AutoTagPrompt("mood", "dark", "dark", "a dark DJ track"),)
    calls: list[str] = []

    def embed_query(text: str) -> np.ndarray:
        calls.append(text)
        return np.asarray([1.0, 0.0], dtype=np.float32)

    bare = build_prompt_matrix(embed_query, mode="bare", prompts=prompts)
    template = build_prompt_matrix(embed_query, mode="template", prompts=prompts)

    assert calls == ["dark", "a dark DJ track"]
    assert bare.mode == "bare"
    assert template.mode == "template"
    assert bare.vectors.shape == (1, 2)
