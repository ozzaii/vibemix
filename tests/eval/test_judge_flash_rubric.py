# SPDX-License-Identifier: Apache-2.0
"""Phase 27-02 — Flash judge rubric file gates (pure file-grep tests).

API-backed Flash judge invocation tests require VCR cassettes (deferred to
KAAN-ACTION-LEGAL.md). This file enforces the rubric file's structural
contract: anti-self-praise instruction present, divergent framing from
Pro side, structured-output schema documented.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
FLASH_RUBRIC = PROJECT_ROOT / "eval" / "rubrics" / "judge_flash.md"
PRO_RUBRIC = PROJECT_ROOT / "eval" / "rubrics" / "judge_pro.md"


def test_flash_rubric_exists_and_non_empty() -> None:
    assert FLASH_RUBRIC.exists()
    assert FLASH_RUBRIC.stat().st_size > 200, (
        "Flash rubric must contain a real instruction; got near-empty file"
    )


def test_flash_rubric_asks_orthogonal_question() -> None:
    """Per Pitfall P42, Flash MUST ask the semantic-anchor question.

    Different reasoning path from Pro's 6-axis grading.
    """
    text = FLASH_RUBRIC.read_text(encoding="utf-8").lower()
    assert "semantically anchor" in text, (
        "Flash rubric must ask the semantic-anchor question (P42 mitigation)"
    )


def test_flash_rubric_documents_binary_output() -> None:
    """Flash emits pass/fail (true/false), NOT 6-axis scores."""
    text = FLASH_RUBRIC.read_text(encoding="utf-8")
    assert '"pass":' in text
    assert "true" in text
    assert "false" in text


def test_flash_rubric_includes_anti_self_praise_instruction() -> None:
    """Pitfall P42 mitigation: anti-self-praise line MUST be present."""
    text = FLASH_RUBRIC.read_text(encoding="utf-8").lower()
    assert "anti-self-praise" in text


def test_flash_rubric_diverges_from_pro_rubric() -> None:
    """The two rubric files must NOT have identical content."""
    assert FLASH_RUBRIC.read_text(encoding="utf-8") != PRO_RUBRIC.read_text(
        encoding="utf-8"
    ), "Pro and Flash rubrics are identical — P42 mitigation broken"


def test_flash_rubric_documents_eight_words_min() -> None:
    """Pitfall P45 cross-reference: Flash rubric mentions the 8-word floor."""
    text = FLASH_RUBRIC.read_text(encoding="utf-8")
    assert "8 words" in text


def test_pro_rubric_documents_six_axes() -> None:
    """The 6-axis convention is explicit in the Pro rubric body."""
    text = PRO_RUBRIC.read_text(encoding="utf-8").lower()
    for axis in [
        "groundedness",
        "timing",
        "substance",
        "tone",
        "relevance",
        "brevity",
    ]:
        assert axis in text, f"Pro rubric missing axis: {axis}"


def test_pro_rubric_documents_verdict_enum() -> None:
    """Pro emits 'pass' | 'fail' | 'borderline'."""
    text = PRO_RUBRIC.read_text(encoding="utf-8")
    assert "pass" in text
    assert "fail" in text
    assert "borderline" in text


def test_pro_rubric_includes_anti_sycophancy_language() -> None:
    """The 'real DJ friend' vs 'polite AI assistant' framing is locked."""
    text = PRO_RUBRIC.read_text(encoding="utf-8").lower()
    assert "polite" in text or "vague" in text
    assert "sycophant" in text or "praise" in text
